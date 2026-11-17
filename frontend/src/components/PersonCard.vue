<script setup>
// 3D 圖上點到的那個人：十欄原始值。extra 放各段要加的字（例如屬於各群的機率、異常第幾名）。hideLabel＝這一段還沒揭曉，不顯示他有沒有違約。
import { computed } from 'vue'
import { store, fmtValue } from '../shared.js'
const props = defineProps({ i: { type: Number, required: true }, raw: { type: Array, default: null }, extra: String, highlight: { type: Array, default: () => [] }, hideLabel: Boolean })
const emit = defineEmits(['close'])
const row = computed(() => props.raw || store.people?.[props.i] || [])
const lab = computed(() => props.raw || props.hideLabel ? null : store.labels?.[props.i])
</script>

<template>
  <div class="pc">
    <div class="h">
      <b>這個人</b>
      <span v-if="lab === 1" class="tag red">後來違約</span>
      <span v-else-if="lab === 0" class="tag">沒違約</span>
      <button class="x" @click="emit('close')">✕</button>
    </div>
    <div v-if="extra" class="ex">{{ extra }}</div>
    <div class="grid">
      <template v-for="(q, j) in store.meta.questions" :key="q.key">
        <span class="k" :class="{ hl: highlight.includes(q.key) }">{{ q.short }}</span>
        <span class="v" :class="{ hl: highlight.includes(q.key) }">{{ fmtValue(q, row[j]) }}</span>
      </template>
    </div>
  </div>
</template>

<style scoped>
.pc { border: 2px solid var(--ink); border-radius: 12px; padding: 10px 12px; margin-top: 8px; background: #fff; }
.h { display: flex; align-items: center; gap: 8px; }
.tag { font-size: 12px; padding: 2px 8px; border-radius: 999px; background: var(--paper-2); }
.tag.red { background: var(--red-soft); color: var(--red); font-weight: 700; }
.x { margin-left: auto; border: 0; background: none; font-size: 18px; }
.ex { font-size: 13px; margin: 4px 0; color: var(--ink-2); }
.grid { display: grid; grid-template-columns: auto 1fr; gap: 2px 12px; font-size: 14px; margin-top: 4px; }
.k { color: var(--ink-2); }
.hl { font-weight: 900; color: var(--ink); }
</style>

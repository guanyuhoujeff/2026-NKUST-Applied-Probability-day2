<script setup>
// 參考名字：老師按「看幾個例子」後才出現。full＝概念＋名字；concept＝只放概念那一句（第 4 步、分群卡用）。
import { reactive, watch, computed } from 'vue'
import { store, getJSON } from '../shared.js'
const props = defineProps({ seg: { type: String, required: true }, only: String, concept: Boolean, big: Boolean, colors: Array })
const on = computed(() => !!store.state?.name_ref?.[props.seg])
const rows = computed(() => Object.entries(cache[props.seg] || {}).filter(([s]) => !props.only || s === props.only))
const slotColor = s => props.colors?.[(store.meta?.name_slots[props.seg] || []).indexOf(s)]
watch(on, async v => {
  if (!v) { cache[props.seg] = null; return }
  const r = await getJSON('/api/name_ref?seg=' + props.seg)
  cache[props.seg] = r.error ? null : r.refs
}, { immediate: true })
</script>

<script>
const cache = reactive({})      // seg -> refs；同一頁多處共用
</script>

<template>
  <div v-if="on && rows.length" class="rf" :class="{ big, concept }">
    <div class="cap" v-if="!concept && !only">只是舉例，名字沒有標準答案。對得上最長的幾條、方向沒反，就是好名字。</div>
    <div v-for="[s, r] in rows" :key="s" class="it">
      <div class="c"><b v-if="!only" :style="slotColor(s) ? { color: slotColor(s) } : {}">{{ s }}</b>{{ r.concept }}</div>
      <div class="ns" v-if="!concept"><span v-for="n in r.names" :key="n">{{ n }}</span></div>
    </div>
  </div>
</template>

<style scoped>
.rf { border-left: 4px solid var(--teal); background: var(--paper-2); border-radius: 0 10px 10px 0; padding: 8px 12px; margin-top: 10px; }
.rf.concept { background: none; padding: 2px 10px; }
.cap { font-size: 14px; font-weight: 700; margin-bottom: 6px; }
.it + .it { margin-top: 8px; }
.c { font-size: 14px; line-height: 1.5; }
.c b { margin-right: 8px; }
.ns { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 4px; }
.ns span { font-size: 13px; font-weight: 700; padding: 3px 10px; border-radius: 999px; background: #fff; border: 1px solid var(--line); }
.big .cap { font-size: 20px; }
.big .c { font-size: 22px; }
.big .ns span { font-size: 20px; padding: 4px 14px; }
.big .it + .it { margin-top: 14px; }
</style>

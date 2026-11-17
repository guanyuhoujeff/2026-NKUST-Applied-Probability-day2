<script setup>
// 挑欄位：十個欄位的按鈕，v-model 是勾起來的 key 陣列（照原本順序）。
import { store } from '../shared.js'
const props = defineProps({ modelValue: { type: Array, required: true }, disabled: Boolean })
const emit = defineEmits(['update:modelValue'])
function toggle(k) {
  const on = new Set(props.modelValue)
  on.has(k) ? on.delete(k) : on.add(k)
  emit('update:modelValue', store.meta.keys.filter(x => on.has(x)))
}
function all(v) { emit('update:modelValue', v ? [...store.meta.keys] : []) }
</script>

<template>
  <div class="chips">
    <button v-for="q in store.meta.questions" :key="q.key" class="chip" :disabled="disabled"
      :class="{ on: modelValue.includes(q.key) }" @click="toggle(q.key)">{{ q.short }}</button>
  </div>
  <div class="row">
    <button class="mini" :disabled="disabled" @click="all(true)">全選</button>
    <button class="mini" :disabled="disabled" @click="all(false)">全不選</button>
    <span class="muted small">已挑 {{ modelValue.length }} 欄</span>
  </div>
</template>

<style scoped>
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip { font-size: 15px; font-weight: 700; padding: 10px 12px; border-radius: 999px; border: 2px solid var(--line); background: #fff; color: var(--ink-2); }
.chip.on { border-color: var(--red); background: var(--red-soft); color: var(--red); }
.row { display: flex; gap: 8px; align-items: center; margin-top: 8px; }
.mini { font-size: 13px; padding: 6px 10px; border-radius: 8px; border: 1px solid var(--line); background: #fff; }
.small { font-size: 13px; }
</style>

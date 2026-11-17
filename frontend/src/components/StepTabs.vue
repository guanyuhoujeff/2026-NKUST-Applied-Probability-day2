<script setup>
// 段落裡的小分頁：一次只看一步。第 1–N 步由老師頁控制（tab.lock），學生不能自己點；沒鎖的分頁（自己試）學生可以點，
// 點進去後用「回到老師這一步」回來。紅點＝那一步有新東西（揭曉）。
const props = defineProps({ tabs: { type: Array, required: true }, modelValue: [Number, String], home: [Number, String] })
const emit = defineEmits(['update:modelValue'])
function go(k) { emit('update:modelValue', k); window.scrollTo(0, 0) }
</script>

<template>
  <nav class="st" :style="{ gridTemplateColumns: `repeat(${tabs.length}, 1fr)` }">
    <button v-for="t in tabs" :key="t.key" :class="{ on: t.key === modelValue, lock: t.lock }" :disabled="t.lock" @click="go(t.key)">
      <small v-if="t.no">{{ t.no }}</small>{{ t.label }}<i v-if="t.dot" class="dot"></i>
    </button>
  </nav>
  <div class="note" v-if="tabs.find(t => t.key === modelValue)?.lock">步驟由老師切換，手機會自動跟著跳。</div>
  <button v-else class="back" @click="go(home)">← 回到老師這一步</button>
</template>

<style scoped>
.st { display: grid; gap: 4px; }
.st button { position: relative; font-size: 13px; font-weight: 800; line-height: 1.25; padding: 7px 2px; border-radius: 10px; border: 1.5px solid var(--line); background: #fff; color: var(--ink-2); }
.st button small { display: block; font-size: 11px; font-weight: 900; color: var(--red); }
.st button.on { border-color: var(--red); background: var(--red-soft); color: var(--ink); }
.st button.lock:not(.on) { background: var(--paper-2); color: #a39b8c; border-style: dashed; }
.st button.lock:not(.on) small { color: #a39b8c; }
.st button:disabled { opacity: 1; }
.dot { position: absolute; top: 4px; right: 5px; width: 8px; height: 8px; border-radius: 50%; background: var(--red); }
.note { font-size: 12px; color: var(--ink-2); text-align: center; margin-top: -4px; }
.back { font-size: 15px; font-weight: 800; padding: 10px; border-radius: 12px; border: 2px solid var(--ink); background: var(--ink); color: #fff; }
</style>

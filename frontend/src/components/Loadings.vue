<script setup>
// 一個主成分由哪些欄組成：權重由大到小畫成橫條；正的往右（紅）、負的往左（藍綠）。
import { computed } from 'vue'
import { store } from '../shared.js'
const props = defineProps({ w: { type: Object, required: true }, title: String, big: Boolean })
const zh = computed(() => Object.fromEntries(store.meta.questions.map(q => [q.key, q.short])))
const rows = computed(() => Object.entries(props.w).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1])))
const m = computed(() => Math.max(...rows.value.map(r => Math.abs(r[1])), 1e-9))
</script>

<template>
  <div class="ld" :class="{ big }">
    <div class="t" v-if="title">{{ title }}<slot name="help" /></div>
    <div v-for="[k, v] in rows" :key="k" class="r">
      <span class="k">{{ zh[k] }}</span>
      <span class="bar">
        <span class="neg"><i v-if="v < 0" :style="{ width: Math.abs(v) / m * 100 + '%' }"></i></span>
        <span class="pos"><i v-if="v > 0" :style="{ width: v / m * 100 + '%' }"></i></span>
      </span>
      <span class="v" :class="v > 0 ? 'red' : 'teal'">{{ v > 0 ? '+' : '' }}{{ v.toFixed(2) }}</span>
    </div>
  </div>
</template>

<style scoped>
.t { font-weight: 900; margin-bottom: 6px; }
.r { display: grid; grid-template-columns: 92px 1fr 48px; gap: 6px; align-items: center; font-size: 13px; margin: 3px 0; }
.big .r { grid-template-columns: 150px 1fr 70px; font-size: 20px; margin: 6px 0; }
.big .t { font-size: 24px; }
.bar { display: grid; grid-template-columns: 1fr 1fr; height: 12px; }
.big .bar { height: 20px; }
.neg { display: flex; justify-content: flex-end; border-right: 1px solid var(--ink-2); }
.neg i { background: var(--teal); display: block; height: 100%; }
.pos i { background: var(--red); display: block; height: 100%; }
.v { text-align: right; font-variant-numeric: tabular-nums; }
</style>

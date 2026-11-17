<script setup>
// 第 2 步：用前 k 個分數還原原本的欄位，每一欄還原得回來幾 %；最上面一條是整體（＝留下幾成資訊）。
import { computed } from 'vue'
import { store } from '../shared.js'
const props = defineProps({ cols: { type: Array, required: true }, row: { type: Array, required: true }, total: Number, big: Boolean })
const zh = computed(() => Object.fromEntries(store.meta.questions.map(q => [q.key, q.short])))
const rows = computed(() => props.cols.map((k, j) => [k, props.row[j]]).sort((a, b) => b[1] - a[1]))
</script>

<template>
  <div class="rc" :class="{ big }">
    <div class="r tot">
      <span class="k">整體</span>
      <span class="bar"><i :style="{ width: total * 100 + '%' }"></i></span>
      <span class="v">{{ Math.round(total * 100) }}%</span>
    </div>
    <div v-for="[k, v] in rows" :key="k" class="r">
      <span class="k">{{ zh[k] }}</span>
      <span class="bar"><i :style="{ width: v + '%' }"></i></span>
      <span class="v">{{ v }}%</span>
    </div>
  </div>
</template>

<style scoped>
.r { display: grid; grid-template-columns: 92px 1fr 44px; gap: 8px; align-items: center; font-size: 13px; margin: 3px 0; }
.big .r { grid-template-columns: 150px 1fr 80px; font-size: 20px; margin: 6px 0; }
.bar { background: var(--paper-2); height: 12px; border-radius: 6px; overflow: hidden; }
.big .bar { height: 20px; }
.bar i { display: block; height: 100%; background: var(--teal); transition: width .3s; }
.tot { font-weight: 900; margin-bottom: 8px; }
.tot .bar i { background: var(--red); }
.v { text-align: right; font-variant-numeric: tabular-nums; }
</style>

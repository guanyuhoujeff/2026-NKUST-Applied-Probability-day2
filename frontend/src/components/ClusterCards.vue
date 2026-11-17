<script setup>
// 每一群的長相：人數，以及跟全部 2,000 人比「特別高／特別低」的三個欄位（中位數）。揭曉後加違約比例。
import { computed } from 'vue'
import { store, fmtValue, fmtN, COLORS } from '../shared.js'
const props = defineProps({ res: { type: Object, required: true }, names: { type: Array, default: null }, big: Boolean })
const Q = computed(() => Object.fromEntries(store.meta.questions.map(q => [q.key, q])))
// 次數欄：「有的人佔幾 %」；其他欄：中位數
function say(k, d) {
  const q = Q.value[k]
  if (d.share !== undefined) return d.share === null ? '—' : `${d.share}%`
  return fmtValue(q, d.median)
}
const what = k => Q.value[k].kind === 'count' ? '≥1 的人佔' : '中位數'
// 挑哪三欄：照標準化平均，離全體最遠的排前面。
// 寫「偏高／偏低」：照畫面上那兩個數字比（這一群 vs 全部），免得字和數字方向相反；兩個數字印出來一樣的欄就跳過，換下一欄。
const num = d => (d.share !== undefined ? d.share : d.median)
function tops(c) {
  const out = []
  for (const [k] of Object.entries(c.zmean).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))) {
    const a = num(c.desc[k]), b = num(props.res.overall[k])
    if (a == null || b == null || a === b || say(k, c.desc[k]) === say(k, props.res.overall[k])) continue
    out.push([k, a > b ? 1 : -1])
    if (out.length === 3) break
  }
  return out
}
</script>

<template>
  <div class="cards" :class="{ big }">
    <template v-for="(c, i) in res.clusters" :key="i"><div v-if="c.n" class="cc" :style="{ borderColor: COLORS.cluster[i] }">
      <div class="h"><b :style="{ color: COLORS.cluster[i] }">第 {{ i + 1 }} 群</b><span v-if="names?.[i]" class="nm">「{{ names[i] }}」</span><span class="muted">{{ fmtN(c.n) }} 人</span></div>
      <div v-for="[k, z] in tops(c)" :key="k" class="f">
        <span class="arrow" :class="z > 0 ? 'red' : 'teal'">{{ z > 0 ? '偏高' : '偏低' }}</span>
        <span>{{ Q[k].short }}</span>
        <span class="muted">{{ what(k) }} {{ say(k, c.desc[k]) }}（全部 {{ say(k, res.overall[k]) }}）</span>
      </div>
      <div v-if="c.rate_test !== undefined" class="rate">
        違約比例 <b>{{ c.rate_test }}%</b>
        <span class="muted small">考題 {{ fmtN(c.n_test) }} 人中 {{ fmtN(c.k_test) }} 人；這 2,000 人 {{ c.rate_student }}%（{{ fmtN(c.k_student) }}／{{ fmtN(c.n) }}）</span>
      </div>
    </div></template>
  </div>
</template>

<style scoped>
.cards { display: grid; gap: 8px; }
.big.cards { grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 14px; }
.cc { border: 2px solid; border-radius: 12px; padding: 10px 12px; background: #fff; }
.h { display: flex; gap: 8px; align-items: baseline; flex-wrap: wrap; font-size: 17px; }
.big .h { font-size: 26px; }
.nm { font-weight: 900; }
.f { display: flex; gap: 6px; flex-wrap: wrap; font-size: 14px; margin-top: 4px; }
.big .f { font-size: 19px; }
.arrow { font-weight: 900; }
.rate { margin-top: 8px; font-size: 16px; }
.rate b { font-size: 24px; color: var(--red); }
.big .rate { font-size: 20px; }
.big .rate b { font-size: 36px; }
.small { font-size: 12px; display: block; }
</style>

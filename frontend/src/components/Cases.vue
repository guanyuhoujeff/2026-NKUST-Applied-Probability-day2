<script setup>
// 揭曉「異常≠違約」：最異常卻沒違約的人、從沒逾期過的違約者、收入填 0 的人。
import { store, fmtValue } from '../shared.js'
const props = defineProps({ cases: { type: Object, required: true }, big: Boolean })
const qs = store.meta.questions
</script>

<template>
  <div class="cs" :class="{ big }">
    <div class="it">
      <b>最異常、卻沒違約的人（10 欄全用，考題裡排前面的）</b>
      <div class="scroll"><table>
        <tr><td></td><td v-for="(p, i) in cases.odd_not_default" :key="i" class="muted">第 {{ i + 1 }} 位</td></tr>
        <tr v-for="(q, j) in qs" :key="q.key"><td class="muted">{{ q.short }}</td>
          <td v-for="(p, i) in cases.odd_not_default" :key="i" :class="{ hot: q.key === 'util' || (q.key === 'debt' && p.raw[j] > 10) }">{{ fmtValue(q, p.raw[j]) }}</td></tr>
      </table></div>
      <div class="muted">額度使用率幾百萬 %：比較像資料打錯，不是壞客戶。</div>
    </div>
    <div class="it"><b>違約的人裡，{{ cases.defaulters_never_late_pct }}% 過去從沒逾期過</b>
      <div class="muted">這些人看起來很普通，只有 {{ cases.defaulters_never_late_caught_pct }}% 被標成異常。找異常的方法，抓不到普通人的違約。</div></div>
    <div class="it"><b>月收入填 0 的 {{ cases.income0_n_test.toLocaleString() }} 人：{{ cases.income0_flagged_pct }}% 被標成異常</b>
      <div class="muted">但他們的違約比例 {{ cases.income0_rate_test }}%，比全部的 {{ cases.base_rate_test }}% 還低。少見不等於危險。</div></div>
  </div>
</template>

<style scoped>
.it { margin: 10px 0; font-size: 14px; }
.big .it { font-size: 21px; margin: 18px 0; }
table { border-collapse: collapse; margin: 6px 0; font-size: 13px; }
.big table { font-size: 18px; }
td { padding: 2px 8px; border-bottom: 1px solid var(--line); white-space: nowrap; }
.hot { color: var(--red); font-weight: 900; }
.muted { color: var(--ink-2); }
.scroll { overflow-x: auto; }
</style>

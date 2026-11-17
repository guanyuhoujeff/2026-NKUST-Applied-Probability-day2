<script setup>
// 第 4 步（揭曉）：各主成分分數高低兩半、最高 10% 的違約比例（學生資料 2,000 人）。
defineProps({ rev: { type: Object, required: true }, big: Boolean })
</script>

<template>
  <table class="bp" :class="{ big }">
    <tr class="th"><td></td><td>分數較低的一半</td><td>分數較高的一半</td><td>分數最高的 10%</td></tr>
    <tr v-for="b in rev.by_pc" :key="b.pc">
      <td class="pc">{{ b.pc }}</td><td>{{ b.low }}%</td><td>{{ b.high }}%</td>
      <td :class="{ hot: b.top10 >= 2 * rev.base }">{{ b.top10 }}%</td>
    </tr>
    <tr class="th"><td colspan="4">全部 2,000 人的違約比例：{{ rev.base }}%</td></tr>
  </table>
</template>

<style scoped>
.bp { width: 100%; border-collapse: collapse; font-size: 15px; font-variant-numeric: tabular-nums; }
.bp td { padding: 6px 4px; border-top: 1px solid var(--line); text-align: right; }
.bp td:first-child { text-align: left; }
.th td { font-size: 12px; color: var(--ink-2); }
.pc { font-weight: 900; }
.hot { color: var(--red); font-weight: 900; }
.big { font-size: 24px; }
.big .th td { font-size: 17px; }
</style>

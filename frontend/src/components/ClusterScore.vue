<script setup>
// 分群「自己試」的分數：各群違約比例差得多開（學生資料 2,000 人）。長條＝每群的違約比例；直線＝全部的人的比例。
// 少於 min_n 人的群不算分。只在老師揭曉後才有（揭曉前 res.score 不存在）。
import { computed } from 'vue'
import { store, COLORS, fmtN } from '../shared.js'
import Help from './Help.vue'
const props = defineProps({ res: { type: Object, required: true }, base: { type: Number, default: null }, best: { type: Number, default: null } })
const minN = computed(() => store.meta.cluster.min_n)
const tot = computed(() => props.res.clusters.reduce((a, c) => a + c.n, 0))
const overall = computed(() => props.res.clusters.reduce((a, c) => a + c.k_student, 0) / tot.value * 100)
const top = computed(() => Math.max(20, ...props.res.clusters.map(c => c.rate_student || 0)))
const w = v => (v / top.value * 100).toFixed(1) + '%'
const small = computed(() => props.res.clusters.filter(c => c.n && c.n < minN.value).length)
</script>

<template>
  <div class="sc">
    <div class="top">
      <div class="num"><span>鑑別度</span><b>{{ res.score.toFixed(1) }}</b></div>
      <div class="side">
        <div v-if="base !== null">第 1～3 步看的那一份：<b>{{ base.toFixed(1) }}</b><small>（10 欄、GMM、3 群）</small></div>
        <div v-if="best !== null">自己的最好紀錄：<b>{{ best.toFixed(1) }}</b></div>
      </div>
    </div>
    <div class="cap">每一群的違約比例（這 2,000 人）
      <Help title="鑑別度怎麼算？">
        <p>鑑別度：分出來的群，能不能把會違約和不會違約的人分開。</p>
        <p>算法：看每一群的違約比例，跟全部的人（{{ overall.toFixed(1) }}%）差多少。</p>
        <p><b>差越多、那一群人越多，分數越高。</b></p>
        <p>每一群都差不多：0 分，沒有鑑別度。<br>有一群全是違約的人、其他群都沒有：100 分。</p>
        <p class="muted">少於 {{ minN }} 人的群不算，人太少不準。</p>
      </Help>
    </div>
    <div class="bars">
      <div class="line" :style="{ left: `calc(64px + (100% - 64px - 92px) * ${overall / top})` }"><i>全部 {{ overall.toFixed(1) }}%</i></div>
      <div v-for="(c, i) in res.clusters" v-show="c.n" :key="i" class="row" :class="{ off: c.n < minN }">
        <span class="nm" :style="{ color: COLORS.cluster[i] }">第 {{ i + 1 }} 群</span>
        <span class="track"><span class="fill" :style="{ width: w(c.rate_student || 0), background: COLORS.cluster[i] }"></span></span>
        <span class="v"><b>{{ c.rate_student }}%</b><small>{{ fmtN(c.n) }} 人</small></span>
      </div>
    </div>
    <div class="muted small" v-if="small">灰掉的 {{ small }} 群少於 {{ minN }} 人，不算分。</div>
  </div>
</template>

<style scoped>
.sc { border: 2px solid var(--ink); border-radius: 12px; padding: 12px; margin: 12px 0; background: #fff; }
.top { display: flex; gap: 14px; align-items: center; }
.num span { display: block; font-size: 13px; font-weight: 800; color: var(--ink-2); }
.num b { font-size: 40px; line-height: 1; color: var(--red); font-variant-numeric: tabular-nums; }
.side { font-size: 14px; line-height: 1.7; }
.side small { display: block; font-size: 11px; color: var(--ink-2); line-height: 1.2; margin-bottom: 4px; }
.cap { font-size: 13px; font-weight: 800; color: var(--ink-2); margin: 12px 0 18px; }
.bars { position: relative; display: grid; gap: 6px; }
.row { display: grid; grid-template-columns: 64px 1fr 92px; align-items: center; font-size: 14px; }
.row.off { opacity: .35; }
.nm { font-weight: 900; }
.track { height: 16px; background: var(--paper-2); border-radius: 4px; overflow: hidden; }
.fill { display: block; height: 100%; min-width: 2px; }
.v { text-align: right; font-variant-numeric: tabular-nums; }
.v small { display: block; font-size: 11px; color: var(--ink-2); }
.line { position: absolute; top: -4px; bottom: -2px; width: 0; border-left: 2px dashed var(--ink); z-index: 1; pointer-events: none; }
.line i { position: absolute; top: -15px; left: -4px; font-size: 11px; font-style: normal; font-weight: 800; white-space: nowrap; }
.small { font-size: 13px; margin-top: 8px; }
</style>

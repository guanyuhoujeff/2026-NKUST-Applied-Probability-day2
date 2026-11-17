<script setup>
// 第 1 步：兩欄壓成 1 個分數。按「壓到線上」看每個人被壓到線上；紅線＝還原不回來的部分。
import { ref, computed } from 'vue'
import { store, fmtValue, COLORS } from '../shared.js'
import Scatter2D from './Scatter2D.vue'
import Help from './Help.vue'
const props = defineProps({ d: { type: Object, required: true }, big: Boolean })
const t = ref(0)
const resid = ref(false)
const sel = ref(-1)
let raf = 0
const f2 = v => (v < 0 ? '−' : '') + Math.abs(v).toFixed(2)
const par = v => (v < 0 ? `（${f2(v)}）` : f2(v))          // 負數加括號，算式才好讀
const isLog = q => (store.meta.log_keys || []).includes(q.key)
const qs = computed(() => props.d.cols.map(k => store.meta.questions.find(q => q.key === k)))
const idx = computed(() => props.d.cols.map(k => store.meta.keys.indexOf(k)))
const colors = computed(() => store.labels ? store.labels.map(y => (y ? COLORS.red : '#6f675a')) : null)
function squash() {
  const from = t.value, to = from < 0.5 ? 1 : 0, t0 = performance.now()
  cancelAnimationFrame(raf)
  const step = now => {
    const a = Math.min(1, (now - t0) / 900)
    t.value = from + (to - from) * (a < 0.5 ? 2 * a * a : 1 - (-2 * a + 2) ** 2 / 2)
    if (a < 1) raf = requestAnimationFrame(step)
  }
  raf = requestAnimationFrame(step)
}
</script>

<template>
  <div :class="{ big }">
    <Scatter2D :pts="d.pts" :dir="d.dir" :t="t" :resid="resid" :labels="qs.map(q => q.short)" :colors="colors"
      :selected="sel" :height="big ? 520 : 300" :size="big ? 3.4 : 2.6" @pick="i => sel = i" />
    <div class="tools">
      <button class="go" @click="squash">{{ t < 0.5 ? '壓到線上' : '放回原位' }}</button>
      <label><input type="checkbox" v-model="resid" /> 畫出每個人到線的距離</label>
    </div>
    <div class="keep">兩欄的相關係數 {{ d.r }}。壓成 1 個分數後，猜得回來 <b>{{ Math.round(d.keep * 100) }}%</b>，
      丟掉 {{ 100 - Math.round(d.keep * 100) }}%。丟掉的就是紅線。</div>
    <div class="pc" v-if="sel >= 0">
      <div class="h"><b>這個人</b>
        <Help title="分數和還原怎麼算？">
          <p><b>① 標準化</b>：每一欄換成「離平均幾個標準差」（{{ qs.filter(isLog).map(q => q.short).join('、') }}先取 log）。</p>
          <div class="f">z ＝（x − 平均）÷ 標準差</div>
          <p class="n">這個人：{{ qs[0].short }} z₁ ＝ {{ f2(d.pts[sel][0]) }}，{{ qs[1].short }} z₂ ＝ {{ f2(d.pts[sel][1]) }}</p>
          <p><b>② 算分數</b>：兩個 z 各乘上綠線的方向（{{ f2(d.dir[0]) }}，{{ f2(d.dir[1]) }}），再相加。</p>
          <div class="f">分數 ＝ {{ f2(d.dir[0]) }} × z₁ ＋ {{ par(d.dir[1]) }} × z₂</div>
          <p class="n">＝ {{ f2(d.dir[0]) }} × {{ par(d.pts[sel][0]) }} ＋ {{ par(d.dir[1]) }} × {{ par(d.pts[sel][1]) }} ＝ <b>{{ f2(d.score[sel]) }}</b></p>
          <p><b>③ 還原</b>：分數乘回方向，猜出兩個 z。</p>
          <div class="f">猜回來的 z ＝ 分數 × 方向</div>
          <p class="n">{{ qs[0].short }}：{{ f2(d.score[sel]) }} × {{ par(d.dir[0]) }} ＝ {{ f2(d.score[sel] * d.dir[0]) }}（原本 {{ f2(d.pts[sel][0]) }}）</p>
          <p class="n">{{ qs[1].short }}：{{ f2(d.score[sel]) }} × {{ par(d.dir[1]) }} ＝ {{ f2(d.score[sel] * d.dir[1]) }}（原本 {{ f2(d.pts[sel][1]) }}）</p>
          <p><b>④ 換回原本的單位</b>，就是表格右邊那一欄：{{ qs.map((q, j) => q.short + ' ' + fmtValue(q, d.restored[sel][j])).join('、') }}。</p>
          <p class="muted">數字四捨五入過，手算會差一點。</p>
        </Help>
        <button class="x" @click="sel = -1">✕</button></div>
      <div class="grid">
        <span></span><span class="th">原本</span><span class="th">只記 1 個分數，猜回來的值</span>
        <template v-for="(q, j) in qs" :key="q.key">
          <span class="k">{{ q.short }}</span>
          <span>{{ fmtValue(q, store.people[sel][idx[j]]) }}</span>
          <span class="rs">{{ fmtValue(q, d.restored[sel][j]) }}</span>
        </template>
      </div>
      <div class="muted small">分數＝{{ d.score[sel] }}。黑圈是原本的位置，紅點是猜回來的位置，虛線是猜不回來的部分。</div>
    </div>
  </div>
</template>

<style scoped>
.tools { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin-top: 8px; font-size: 14px; }
.go { font-size: 16px; font-weight: 900; padding: 10px 18px; border: 0; border-radius: 10px; background: var(--ink); color: #fff; }
.keep { font-size: 14px; margin-top: 8px; }
.keep b { color: var(--red); font-size: 18px; }
.big .tools, .big .keep { font-size: 20px; }
.big .keep b { font-size: 30px; }
.big .go { font-size: 20px; }
.pc { border: 2px solid var(--ink); border-radius: 12px; padding: 10px 12px; margin-top: 8px; background: #fff; }
.h { display: flex; align-items: center; }
.x { margin-left: auto; border: 0; background: none; font-size: 18px; }
.grid { display: grid; grid-template-columns: auto 1fr 1fr; gap: 2px 12px; font-size: 15px; margin: 4px 0; }
.big .grid { font-size: 22px; }
.th { font-size: 12px; color: var(--ink-2); font-weight: 700; }
.k { color: var(--ink-2); }
.rs { color: var(--teal); font-weight: 700; }
.small { font-size: 12px; }
</style>

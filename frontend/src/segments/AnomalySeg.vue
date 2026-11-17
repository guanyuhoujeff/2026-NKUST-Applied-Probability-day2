<script setup>
// 異常偵測段（比賽：抓異常）。四條路線，學生自己選（2026-11-17）：挑欄位 →（要不要 PCA）→（要不要分群）→ 提交哪些人是異常。
// 不分群：電腦標最異常的 10%（馬氏距離）；分群：人數最少的那一群就是異常（電腦挑；原本讓學生指定，會變成猜違約，FACTS-28）。分數是鑑別度（跟分群段同一把尺，FACTS-29）。
import { ref, computed, watch, onMounted } from 'vue'
import { store, getJSON, postJSON, colsParam, COLORS, fmtN, routeText } from '../shared.js'
import ClusterCards from '../components/ClusterCards.vue'
import Scatter3D from '../components/Scatter3D.vue'
import PersonCard from '../components/PersonCard.vue'
import ColPicker from '../components/ColPicker.vue'
import SizeCurve from '../components/SizeCurve.vue'
import Cases from '../components/Cases.vue'
import StepTabs from '../components/StepTabs.vue'
import VoteCard from '../components/VoteCard.vue'

const props = defineProps({ nickname: String, submitted: Array, myVotes: Object })
const emit = defineEmits(['submitted', 'voted'])
const voteHere = computed(() => store.votes?.question?.seg === 'anomaly')
const picked = ref([])
const usePca = ref(false), pcaK = ref(1)          // 要不要先做 PCA、留前幾個分數
const useClu = ref(false), cluK = ref(3), method = ref('kmeans')     // 要不要分群
const subErr = ref(''), sending = ref(false)       // 提交的錯誤要顯示在提交鈕旁邊；送出中不能再按
// 設定一改，舊的結果就收起來（免得畫面上的設定和分數對不起來、或把舊的勾選套到新的群上）
watch([picked, usePca, pcaK, useClu, cluK, method], () => { runSeq++; busy.value = false; res.value = null; err.value = ''; subErr.value = '' }, { deep: true })
watch(() => props.nickname, () => { subErr.value = '' })
const mySub = ref(null)                            // 這支手機交出去的那一組（寫給學生看：交的是哪一組）
const maxK = computed(() => Math.max(1, picked.value.length))
watch(maxK, m => { if (pcaK.value > m) pcaK.value = m })
const res = ref(null)
const xyz = ref(null)
const sel = ref(-1)
const err = ref('')
const busy = ref(false)
const history = ref([])
const rev = ref(null)
const tab = ref(store.state.step?.anomaly || 1)
const TABS = computed(() => [{ key: 1, no: '第 1 步', lock: true, label: '規則、先猜', dot: tab.value !== 1 && voteHere.value && !!store.votes?.answer }, { key: 2, no: '第 2 步', lock: true, label: '抓異常' }, { key: 3, no: '第 3 步', lock: true, label: '揭曉', dot: tab.value !== 3 && !!rev.value }])
const A = computed(() => store.meta.anomaly)
const zh = computed(() => Object.fromEntries(store.meta.questions.map(q => [q.key, q.short])))
const closed = computed(() => store.state.phase === 'closed' || store.state.closed || store.state.reveal.anomaly)
const flaggedSet = computed(() => res.value ? new Set(res.value.flagged) : new Set())
const colors = computed(() => !res.value ? null : store.people.map((_, i) => flaggedSet.value.has(i) ? COLORS.amber : COLORS.gray))
const front = computed(() => res.value ? store.people.map((_, i) => flaggedSet.value.has(i)) : null)
// 比賽中不顯示誰違約（前兩段公布過也一樣）；排行榜揭曉後才畫紅框
const ring = computed(() => store.labels && store.state.reveal.anomaly ? store.labels.map(y => !!y) : null)
const myRow = computed(() => rev.value?.rows.findIndex(r => r.nickname === props.nickname?.trim()))
const rankOf = i => res.value?.top.findIndex(t => t.i === i)

const query = () => colsParam(picked.value) + (usePca.value ? `&pca=${pcaK.value}` : '') + (useClu.value ? `&k=${cluK.value}&method=${method.value}` : '')
let runSeq = 0
async function run() {
  err.value = ''
  if (!picked.value.length) { err.value = '至少挑一欄'; return }
  busy.value = true
  const seq = ++runSeq
  try {
    const [r, p] = await Promise.all([getJSON('/api/anomaly?cols=' + query()), getJSON('/api/pca?cols=' + colsParam(picked.value))])
    if (seq !== runSeq) return                     // 計算中又改了設定：這一次的結果不要了
    if (r.error) { err.value = r.error; return }
    res.value = r; xyz.value = p.xyz; sel.value = -1
    history.value.unshift({ n: history.value.length + 1, cols: r.cols.length > 4 ? `共 ${r.cols.length} 欄` : r.cols.map(k => zh.value[k]).join('、'), route: routeText(r), eta: r.student.eta })
  } catch (e) { err.value = '連不上伺服器：' + e.message } finally { busy.value = false }
}
async function submit() {
  subErr.value = ''
  if (!props.nickname?.trim()) { subErr.value = '提交要先在最上面填暱稱'; return }
  if (sending.value) return
  sending.value = true
  let r
  try { r = await postJSON('/api/anomaly/submit', { nickname: props.nickname, cols: res.value.cols, pca: res.value.pca_k, k: res.value.k, method: res.value.method || 'kmeans' }) } catch (e) { subErr.value = '連不上伺服器，再按一次'; return } finally { sending.value = false }
  if (r.error) { subErr.value = r.error; return }
  mySub.value = { text: routeText(res.value), eta: res.value.student.eta, n: res.value.cols.length }
  emit('submitted', r.cols)
}
async function loadReveal() {
  const r = store.state.reveal.anomaly ? await getJSON('/api/anomaly/reveal') : null
  rev.value = r && !r.error && store.state.reveal.anomaly ? r : null      // 老師剛揭曉又收起：回來的是錯誤訊息，不能當資料畫
}
watch(() => store.state.reveal.anomaly, loadReveal)
watch(() => store.cleared, () => { history.value = []; res.value = null; mySub.value = null })
watch(() => store.state.step?.anomaly, v => { if (v) { tab.value = v; window.scrollTo(0, 0) } })   // 老師切步，手機跟著跳
onMounted(loadReveal)
</script>

<template>
  <StepTabs :tabs="TABS" v-model="tab" :home="store.state.step?.anomaly || 1" />

  <section class="card" v-if="tab === 1">
    <div class="qt">抓異常：哪些人跟大家不一樣？</div>
    <div class="muted small rules">
      <div>① 挑欄位。</div>
      <div>② 要不要先做 PCA？把挑的欄位壓成幾個分數再用。</div>
      <div>③ 要不要分群？
        <div class="sub">不分群：電腦算每個人「有多少見」，最少見的 10%（{{ fmtN(A.n_flag_student) }} 人）就是異常。</div>
        <div class="sub">分群：人數最少的那一群就是異常。</div></div>
      <div>④ 對答案，算鑑別度：異常的人和正常的人，違約比例差越多，鑑別度越高（跟分群那一段一樣）。異常的人不到 {{ store.meta.cluster.min_n }} 個就不算。</div>
      <div>全程<b>不看誰違約</b>。排名看另外 {{ fmtN(store.meta.test_n) }} 人（考題）的鑑別度，老師揭曉才看得到。每人只能提交一次。</div>
    </div>
    <div class="next">動手抓異常在第 2 步。老師切換後，手機會自動跳過去。</div>
  </section>

  <VoteCard v-if="tab === 1 && voteHere" :nickname="nickname" :mine="myVotes" @voted="(q, c) => emit('voted', q, c)" />

  <section class="card" v-if="tab === 2">
    <div class="h2">① 挑哪些欄位？</div>
    <ColPicker v-model="picked" :disabled="busy" />
    <div class="h2 mt">② 要不要先做 PCA？</div>
    <div class="opt" :class="{ lock: busy }"><button :class="{ on: !usePca }" @click="usePca = false">不做</button><button :class="{ on: usePca }" @click="usePca = true">做 PCA</button></div>
    <div class="opt" :class="{ lock: busy }" v-if="usePca"><span class="lab">留幾個分數</span>
      <button v-for="n in maxK" :key="n" class="num" :class="{ on: pcaK === n }" @click="pcaK = n">{{ n }}</button></div>
    <div class="muted small" v-if="usePca && picked.length">把挑的 {{ picked.length }} 欄壓成 {{ pcaK }} 個分數，後面只用這 {{ pcaK }} 個分數。</div>
    <div class="h2 mt">③ 要不要分群？</div>
    <div class="opt" :class="{ lock: busy }"><button :class="{ on: !useClu }" @click="useClu = false">不分群：最少見的 10% 是異常</button><button :class="{ on: useClu }" @click="useClu = true">分群：人數最少的那群是異常</button></div>
    <template v-if="useClu">
      <div class="opt" :class="{ lock: busy }"><span class="lab">方法</span><button :class="{ on: method === 'kmeans' }" @click="method = 'kmeans'">K-means</button><button :class="{ on: method === 'gmm' }" @click="method = 'gmm'">GMM</button></div>
      <div class="opt" :class="{ lock: busy }"><span class="lab">群數</span><button v-for="x in store.meta.cluster.ks" :key="x" class="num" :class="{ on: cluK === x }" @click="cluK = x">{{ x }}</button></div>
    </template>
    <button class="go" :disabled="busy || !picked.length" @click="run()">{{ busy ? '計算中…' : '算算看' }}</button>
    <div class="err" v-if="err">{{ err }}</div>
  </section>

  <section class="card" v-if="tab === 2 && res && res.student">
    <div class="score"><span class="muted small">鑑別度</span><b>{{ res.student.eta.toFixed(1) }}</b><span class="muted small">分（我的 {{ fmtN(store.meta.sample_n) }} 人）</span></div>
    <div class="muted small">{{ routeText(res) }}</div>
    <div class="two">
      <div class="g odd"><small>異常 {{ fmtN(res.student.n_flag) }} 人</small><b>{{ res.student.rate_flag }}%</b><small>後來違約</small></div>
      <div class="g"><small>正常 {{ fmtN(res.student.n_rest) }} 人</small><b>{{ res.student.rate_rest }}%</b><small>後來違約</small></div>
    </div>
    <div class="muted small">兩邊差越多，鑑別度越高。全部 {{ res.student.positives }} 個違約的人，有 {{ Math.round(res.student.tp) }} 個在異常這邊。
      <span v-if="res.student.n_flag < store.meta.cluster.min_n">異常這群不到 {{ store.meta.cluster.min_n }} 人，人太少不算分。</span></div>
    <div class="muted small" v-if="res.student.tie_group > 1">第 {{ res.student.n_flag }} 名附近有 {{ fmtN(res.student.tie_group) }} 人一樣異常，電腦抽籤補滿 {{ res.student.n_flag }} 人。</div>
    <div class="h3">3D 圖：橘色＝被標成異常</div>
    <Scatter3D :xyz="xyz" :colors="colors" :front="front" :ring="ring" :selected="sel" @pick="i => sel = i"
      :axes="['PC1', res.cols.length > 1 ? 'PC2' : '', res.cols.length > 2 ? 'PC3' : '']" />
    <div class="muted small">圖是用挑的欄位畫的。{{ ring ? '紅框＝後來違約。' : '' }}</div>
    <PersonCard v-if="sel >= 0" :i="sel" :highlight="res.cols" :hide-label="!ring" @close="sel = -1"
      :extra="flaggedSet.has(sel) ? '被標成異常' + (rankOf(sel) >= 0 ? `（異常第 ${rankOf(sel) + 1} 名）` : '') : '沒被標'" />
    <template v-if="res.top.length">
      <div class="h3">最異常的 {{ res.top.length }} 個人</div>
      <div class="tops"><button v-for="(t, j) in res.top" :key="t.i" class="mini" @click="sel = t.i">第 {{ j + 1 }} 名</button></div>
    </template>
    <template v-if="res.k">
      <div class="h3">分出來的 {{ res.k }} 群（第 {{ res.pick[0] + 1 }} 群人最少，當成異常）</div>
      <ClusterCards :res="res" />
    </template>
    <button class="submit" :disabled="!!submitted || closed || sending" @click="submit">
      {{ submitted ? '已提交' : closed ? '已截止' : '提交這一組（每人一次）' }}</button>
    <div class="muted small" v-if="submitted && mySub">交出去的是：{{ mySub.n }} 欄，{{ mySub.text }}，鑑別度 {{ mySub.eta.toFixed(1) }}。之後再算的不會改到它。</div>
    <div class="muted small" v-else-if="submitted">已經交過一組了，之後再算的不會改到它。</div>
    <div class="err" v-if="subErr">{{ subErr }}</div>
  </section>

  <section class="card" v-if="tab === 2 && history.length">
    <div class="h2">我的紀錄</div>
    <table>
      <tr class="muted small"><td>#</td><td>欄位／做法</td><td>鑑別度</td></tr>
      <tr v-for="h in history" :key="h.n"><td class="muted">{{ h.n }}</td><td>{{ h.cols }}<div class="muted small">{{ h.route }}</div></td><td><b>{{ h.eta.toFixed(1) }}</b></td></tr>
    </table>
  </section>

  <section class="card" v-if="tab === 3 && rev">
    <div class="h2">揭曉：考題的鑑別度</div>
    <div v-if="myRow >= 0" class="me">我是第 {{ rev.rows[myRow].rank }} 名：考題 <b>{{ rev.rows[myRow].test.toFixed(1) }}</b> 分</div>
    <table>
      <tr class="muted small"><td>#</td><td>暱稱</td><td>欄位／做法</td><td>鑑別度</td></tr>
      <tr v-for="r in rev.rows.slice(0, 10)" :key="r.nickname"><td>{{ r.rank }}</td><td>{{ r.nickname }}</td>
        <td class="small">{{ r.cols.map(k => zh[k]).join('、') }}<div class="muted">{{ routeText(r) }}</div></td><td><b>{{ r.test.toFixed(1) }}</b></td></tr>
    </table>
    <div class="h3">不做 PCA、不分群時，挑幾欄最好？（1,023 種挑法，考題的鑑別度）</div>
    <SizeCurve :curve="rev.curve" />
    <div class="h3">異常≠會違約</div>
    <Cases :cases="rev.cases" />
  </section>
  <VoteCard v-if="tab === 3 && voteHere && store.votes?.answer" :nickname="nickname" :mine="myVotes" @voted="(q, c) => emit('voted', q, c)" />
  <section class="card muted" v-if="tab === 3 && !rev">老師還沒揭曉。揭曉後，這裡會出現排行榜和考題分數。</section>
</template>

<style scoped>
.qt { font-weight: 900; font-size: 19px; margin-bottom: 6px; }
.h2 { font-weight: 900; font-size: 17px; margin-bottom: 8px; }
.h3 { font-weight: 900; margin: 14px 0 6px; }
.small { font-size: 13px; }
.rules div { margin: 3px 0; }
.go, .submit { width: 100%; margin-top: 14px; font-size: 19px; font-weight: 900; padding: 14px; border: 0; border-radius: 14px; color: #fff; }
.go { background: var(--ink); }
.submit { background: var(--red); }
.go:disabled, .submit:disabled { opacity: .45; }
.err { color: var(--red); font-weight: 700; margin-top: 8px; }
.score { display: flex; align-items: baseline; gap: 8px; }
.score b { font-size: 40px; color: var(--red); }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 8px 0; }
.two .g { border: 2px solid var(--line); border-radius: 12px; padding: 8px 10px; text-align: center; }
.two .g.odd { border-color: var(--amber, #d08a1e); }
.two .g b { display: block; font-size: 26px; }
.two .g small { display: block; font-size: 12px; color: var(--ink-2); }
.tops { display: flex; gap: 6px; flex-wrap: wrap; }
.mini { font-size: 14px; padding: 6px 10px; border-radius: 8px; border: 1px solid var(--line); background: #fff; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
td { padding: 5px 4px; border-bottom: 1px solid var(--line); }
.me { font-size: 18px; margin-bottom: 8px; }
.me b { color: var(--red); font-size: 24px; }
.next { margin-top: 10px; padding: 8px 10px; border-radius: 10px; background: var(--paper-2); font-size: 14px; font-weight: 800; }
.mt { margin-top: 16px; }
.rules .sub { margin: 2px 0 2px 18px; }
.opt { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; margin: 6px 0; }
.opt .lab { font-size: 13px; font-weight: 800; color: var(--ink-2); margin-right: 2px; }
.opt button { font-size: 15px; font-weight: 800; padding: 9px 12px; border-radius: 10px; border: 2px solid var(--line); background: #fff; color: var(--ink-2); }
.opt button.num { min-width: 40px; padding: 8px 0; }
.opt.lock { pointer-events: none; opacity: .5; }
.opt button.on { border-color: var(--ink); background: var(--ink); color: #fff; }
</style>

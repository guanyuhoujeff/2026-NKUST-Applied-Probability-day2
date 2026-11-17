<script setup>
// 老師大螢幕：切段落、公布違約者、投票、揭曉；每段的大圖與全班取的名字；異常偵測排行榜。
import { ref, computed, watch, onMounted } from 'vue'
import { store, getJSON, postJSON, loadMeta, connectWS, colsParam, COLORS, fmtN, SEG_NAMES, STEP_NAMES, routeText, teacher, setTeacherKey } from './shared.js'
import Scatter3D from './components/Scatter3D.vue'
import Loadings from './components/Loadings.vue'
import Demo2 from './components/Demo2.vue'
import Recon from './components/Recon.vue'
import RestoreCard from './components/RestoreCard.vue'
import ByPc from './components/ByPc.vue'
import ClusterCards from './components/ClusterCards.vue'
import PersonCard from './components/PersonCard.vue'
import ColPicker from './components/ColPicker.vue'
import SizeCurve from './components/SizeCurve.vue'
import Cases from './components/Cases.vue'
import RefNames from './components/RefNames.vue'
import ClusterPlot from './components/ClusterPlot.vue'
import ClusterAnim from './components/ClusterAnim.vue'
import PcMix from './components/PcMix.vue'

const names = ref(null)
const rows = ref([])
const pca = ref(null)
const pdemo = ref(null)
const prev = ref(null)
const pstep = ref(1)          // PCA 四步：老師頁一次放大一步
const pk = ref(3)
const PSTEPS = ['2 欄壓成 1 個分數', '壓成幾個、丟掉多少', '每個分數在量什麼', '違約的人在哪裡']
const cls = ref(null)
const sel = ref(-1)
const rev = ref(null)
const demoCols = ref([])
const demo = ref(null)
const demoXyz = ref(null)

const S = computed(() => store.state)
const seg = computed(() => (S.value?.phase === 'closed' ? 'anomaly' : S.value?.phase))
const zh = computed(() => Object.fromEntries((store.meta?.questions || []).map(q => [q.key, q.short])))
const labelColors = computed(() => store.labels ? store.labels.map(y => (y ? COLORS.red : COLORS.gray)) : null)
const labelFront = computed(() => store.labels ? store.labels.map(y => !!y) : null)
const ring = computed(() => store.labels ? store.labels.map(y => !!y) : null)
const v = computed(() => store.votes)
const votePct = computed(() => {
  const o = {}
  if (!v.value) return o
  for (const [k, n] of Object.entries(v.value.counts)) o[k] = v.value.total ? Math.round(n / v.value.total * 100) : 0
  return o
})
const flagged = computed(() => demo.value ? new Set(demo.value.flagged) : new Set())

async function post(path, body) { return postJSON(path, body) }
// 揭曉、公布這些鈕是「開／關」：連按兩下會開了又關（還會讓頁面抓到一半的資料）。按一次後鎖 0.8 秒。
const locked = ref(false)
const once = fn => async (...a) => {
  if (locked.value) return
  locked.value = true
  try { await fn(...a) } finally { setTimeout(() => { locked.value = false }, 800) }
}
// 大螢幕學生也看得到：這一段還沒揭曉，就不畫違約的紅框（前一段公布過也一樣）
const cring = computed(() => (S.value?.reveal.cluster ? ring.value : null))
const aring = computed(() => (S.value?.reveal.anomaly ? ring.value : null))
const setPhase = p => post('/api/phase', { phase: p })
// 截止過之後再按「③ 異常偵測」：先問要不要重新開放提交。不重開就維持截止（只是把畫面帶回這一段）。
const openAnomaly = () => post('/api/phase', { phase: 'anomaly', reopen: !!S.value.closed && confirm('已經截止提交了。要重新開放提交嗎？\n按「取消」＝維持截止。') })
// PCA、分群：圖上一出現誰違約、或這一段一揭曉，投票答案就等於露出來了。所以這一題還沒揭曉時，這兩顆鈕一律走「揭曉答案」那一整套。
const voteOpen = () => (seg.value === 'pca' || seg.value === 'cluster') && v.value?.question?.seg === seg.value && !v.value?.answer
// PCA 第 3 步沒有圖，看不到紅點：在那一步按「公布誰違約」就順便帶到第 4 步
const toggleLabels = () => {
  if (!S.value.labels && voteOpen()) return voteReveal()
  if (!S.value.labels && seg.value === 'pca' && pstep.value === 3) setStep('pca', 4)
  return post('/api/labels/toggle', { on: !S.value.labels })
}
// 學生不能自己切步，所以揭曉時順便把手機帶到看得到結果的那一步（PCA、分群第 4 步；異常偵測第 3 步）
const LAST = { pca: 4, cluster: 3, anomaly: 3 }
const toggleReveal = () => {
  const on = !S.value.reveal[seg.value]
  if (on && voteOpen()) return voteReveal()
  if (on) setStep(seg.value, LAST[seg.value])
  return post('/api/reveal', { seg: seg.value, on })
}
// 每段只有一題投票，所以換題＝換段：學生手機只在「投票所屬的那一段」顯示投票卡，只換題不換段學生會看不到。
const voteGoto = i => setPhase(store.meta.votes[i].seg)
// PCA、分群：「揭曉答案」一次做完三件事——投票答案、公布誰違約（圖上變紅）、這一段的違約比例；並把手機帶到最後一步。
// 上面的「公布誰違約」「揭曉：某段」在這一題還沒揭曉時，也走這一整套（見 voteOpen）；揭曉之後才單獨開關。異常偵測的排行榜另外揭曉，不跟投票綁在一起。
async function voteReveal() {
  const vs = v.value?.question?.seg, turningOn = !v.value?.answer
  if (turningOn && (vs === 'pca' || vs === 'cluster')) {
    setStep(vs, LAST[vs])
    await post('/api/labels/toggle', { on: true })
    await post('/api/reveal', { seg: vs, on: true })
  }
  return post('/api/vote/reveal', { on: turningOn })
}
const cview = ref('gmm'), ckm = ref(null)      // 分群圖看哪一種方法：gmm＝全班那一份；kmeans＝同樣 10 欄、3 群
const cshown = computed(() => (cview.value === 'kmeans' && ckm.value ? ckm.value : cls.value))
async function setCView(m) {
  sel.value = -1
  if (m === 'kmeans') { const c = store.meta.cluster.class_cfg; ckm.value = await getJSON(`/api/cluster?cols=${colsParam(c.cols)}&k=${c.k}&method=kmeans&start=${c.start}`) }
  cview.value = m
}
// 老師提示：照現在的狀態，告訴老師「學生看到什麼」和「接下來按哪一顆」；右邊的按鈕就是那一顆（也可以不理它，自己按上面的）。
// 學生不能自己切步，老師漏按一步，學生就看不到後面的東西（投票卡、挑欄位都發生過）。
const tip = computed(() => {
  const g = seg.value, st = S.value.step?.[g] || 1, nm = STEP_NAMES[g]
  const ans = v.value?.question?.seg === g && !!v.value?.answer, nv = v.value?.question?.seg === g ? v.value.total : 0
  const go = n => ({ btn: `切到第 ${n} 步：${nm[n - 1]}`, act: () => setStep(g, n) })
  if (g === 'pca') {
    if (st < 3) return { see: `學生手機在第 ${st} 步「${nm[st - 1]}」。`, next: '講完這一步就往下切。', ...go(st + 1) }
    if (st === 3) return S.value.name_ref?.pca
      ? { see: '學生看得到幾個取名的例子了。', next: '接著切到第 4 步，讓學生投票猜違約的人在哪裡。', ...go(4) }
      : { see: `學生正在替 PC1、PC2 取名字（已 ${names.value?.pca_n ?? 0} 人）。`, next: '收得差不多，就公布幾個例子。', btn: '看幾個例子', act: () => toggleRef('pca') }
    return ans ? { see: '答案已揭曉，圖上違約的人是紅點。', next: 'PCA 結束，換到分群。', btn: '② 分群', act: () => setPhase('cluster') }
      : { see: `學生正在投票（已 ${nv} 票）。`, next: '投得差不多，就揭曉。', btn: '揭曉答案＋公布誰違約', act: voteReveal }
  }
  if (g === 'cluster') {
    if (st === 1) return { see: '學生只看到分群圖，還看不到投票。', next: '講完圖，切到第 2 步：學生看每群長相、投票。', ...go(2) }
    if (!ans && st === 3) return { see: '學生在第 3 步，看不到投票卡，投票答案也還沒揭曉。', next: '要再投票就切回第 2 步；要看答案就揭曉。', btn: '揭曉答案＋公布誰違約', act: voteReveal }
    if (!ans) return { see: `學生在看每群長相、投票（已 ${nv} 票）。`, next: '投得差不多，就揭曉。', btn: '揭曉答案＋公布誰違約', act: voteReveal }
    return { see: '已揭曉。學生可以點「自己試」拼鑑別度。', next: '玩夠了，換到異常偵測。', btn: '③ 異常偵測', act: openAnomaly }
  }
  if (S.value.reveal.anomaly) return ans ? { see: '學生看得到排行榜和投票答案了。', next: '全部結束。' }
    : { see: '學生看得到排行榜了。', next: '最後揭曉投票答案（會出現在排行榜下面）。', btn: '揭曉答案', act: voteReveal }
  if (S.value.phase === 'closed') return { see: `已截止，共 ${S.value.n_submitted} 人提交。`, next: '揭曉排行榜。', btn: '揭曉：異常偵測', act: toggleReveal }
  if (st === 1) return { see: `學生只看到規則和投票（已 ${nv} 票），還不能動手。`, next: '講完規則，切到第 2 步，比賽才開始。', ...go(2) }
  return { see: `學生正在抓異常（已提交 ${S.value.n_submitted} 人）。`, next: '時間到就截止。', btn: '④ 截止提交', act: () => setPhase('closed') }
})
const showAnim = ref(false)       // 分群：一步一步怎麼跑的示範（只在老師頁）
const toggleRef = s => post('/api/name_ref', { seg: s, on: !S.value.name_ref?.[s] })
// 切步：老師頁放大那一步（PCA），同時讓學生手機跳到同一步
const setStep = (s, n) => { if (s === 'pca') pstep.value = n; sel.value = -1; post('/api/step', { seg: s, step: n }) }
watch(() => S.value?.step?.pca, n => { if (n) pstep.value = n }, { immediate: true })
async function clearAll() {
  if (!confirm(`清掉全部 ${S.value.n_submitted} 筆提交、全部投票和取名？無法復原。`)) return
  await post('/api/clear')
}

async function loadSeg() {
  if (!store.meta) return
  const all = colsParam(store.meta.keys)
  if (!pca.value) pca.value = await getJSON('/api/pca?cols=' + all)
  if (!pdemo.value) pdemo.value = await getJSON('/api/pca/demo')
  const pr = S.value.reveal.pca ? await getJSON('/api/pca/reveal') : null
  prev.value = pr && !pr.error ? pr : null
  if (seg.value === 'cluster') {
    const c = store.meta.cluster.class_cfg
    cls.value = await getJSON(`/api/cluster?cols=${colsParam(c.cols)}&k=${c.k}&method=${c.method}&start=${c.start}`)
  }
  const ar = S.value.reveal.anomaly ? await getJSON('/api/anomaly/reveal') : null
  rev.value = ar && !ar.error ? ar : null
}
async function runDemo() {
  if (!demoCols.value.length) return
  const q = colsParam(demoCols.value)
  const [r, p] = await Promise.all([getJSON('/api/anomaly?cols=' + q), getJSON('/api/pca?cols=' + q)])
  if (!r.error) { demo.value = r; demoXyz.value = p.xyz }
}
watch(() => [seg.value, S.value?.reveal.pca, S.value?.reveal.cluster, S.value?.reveal.anomaly], () => { sel.value = -1; loadSeg() })

// 老師頁密碼：先問伺服器密碼對不對（沒設密碼的伺服器直接過），過了才載入
const authed = ref(false), keyInput = ref(''), keyMsg = ref('')
async function login(k) {
  const r = await postJSON('/api/teacher/login', { key: k })
  if (r.ok) { setTeacherKey(k); authed.value = true; start() } else if (k) keyMsg.value = '密碼不對'
}
watch(() => teacher.denied, d => { if (d) { authed.value = false; keyMsg.value = '密碼失效，請重新輸入' } })
onMounted(() => login(teacher.key))
let started = false
async function start() {
  if (started) return
  started = true
  await loadMeta()
  names.value = await getJSON('/api/names')
  rows.value = (await getJSON('/api/board')).rows
  loadSeg()
  connectWS('teacher', {
    onopen: async () => { names.value = await getJSON('/api/names'); rows.value = (await getJSON('/api/board')).rows },
    onmessage: m => {
      if (m.type === 'names') names.value = m
      if (m.type === 'board') { rows.value = m.rows; if (m.revealed) loadSeg() }
    },
  })
}
</script>

<template>
  <form class="login" v-if="!authed" @submit.prevent="login(keyInput)">
    <div class="lt">老師頁</div>
    <input v-model="keyInput" type="password" placeholder="老師頁密碼" autocomplete="off" autofocus />
    <button type="submit">進入</button>
    <div class="lm" v-if="keyMsg">{{ keyMsg }}</div>
  </form>
  <header class="top" v-if="authed && store.meta && S">
    <div class="row">
      <h1>第二天・非監督式學習</h1>
      <div class="ctrl">
        <button :class="{ on: S.phase === 'pca' }" @click="setPhase('pca')">① PCA</button>
        <button :class="{ on: S.phase === 'cluster' }" @click="setPhase('cluster')">② 分群</button>
        <button :class="{ on: S.phase === 'anomaly' }" @click="openAnomaly">③ 異常偵測</button>
        <button :class="{ on: S.phase === 'closed' }" @click="setPhase('closed')">④ 截止提交</button>
        <span class="sep"></span>
        <button class="rev" :class="{ on: S.labels }" :disabled="locked" @click="once(toggleLabels)()">{{ S.labels ? '藏起違約者' : '公布誰違約' }}</button>
        <button class="rev" :class="{ on: S.reveal[seg] }" :disabled="locked" @click="once(toggleReveal)()">{{ S.reveal[seg] ? '收起揭曉' : `揭曉：${SEG_NAMES[seg]}` }}</button>
        <button class="danger" @click="clearAll">清除</button>
      </div>
    </div>
    <div class="stat">學生資料 {{ fmtN(store.meta.sample_n) }} 人（違約 {{ store.meta.sample_k }}）　考題 {{ fmtN(store.meta.test_n) }} 人　
      PCA 取名 {{ names?.pca_n ?? 0 }} 人　異常偵測已提交 {{ S.n_submitted }} 人</div>
  </header>

  <main class="page" v-if="authed && store.meta && S">
    <div class="tip" v-if="tip">
      <span class="tl">提示</span>
      <span class="tt">{{ tip.see }}<b>{{ tip.next }}</b></span>
      <button v-if="tip.btn" :disabled="locked" @click="once(tip.act)()">{{ tip.btn }} ▸</button>
    </div>
    <!-- 投票 -->
    <section class="card" v-if="v && (seg !== 'pca' || pstep === 4)">
      <div class="row">
        <div class="h">投票 {{ v.idx + 1 }}／{{ v.n_questions }}：{{ v.question.question }}</div>
        <div class="vctrl">
          <button :disabled="v.idx === 0" @click="voteGoto(v.idx - 1)">上一題{{ v.idx > 0 ? `（回 ${SEG_NAMES[store.meta.votes[v.idx - 1].seg]}）` : '' }}</button>
          <button :disabled="v.idx === v.n_questions - 1" @click="voteGoto(v.idx + 1)">下一題{{ v.idx < v.n_questions - 1 ? `（到 ${SEG_NAMES[store.meta.votes[v.idx + 1].seg]}）` : '' }}</button>
          <button class="rev" :class="{ on: !!v.answer }" :disabled="locked" @click="once(voteReveal)()">{{ v.answer ? '收起答案' : (v.question.seg === 'anomaly' ? '揭曉答案' : '揭曉答案＋公布誰違約') }}</button>
        </div>
      </div>
      <div v-for="o in v.question.options" :key="o.id" class="vrow">
        <span class="vlabel" :class="{ win: v.answer?.answer_id === o.id }">{{ o.text }}</span>
        <span class="vbar"><i :style="{ width: (votePct[o.id] || 0) + '%' }"></i></span>
        <span class="vnum">{{ v.counts[o.id] }} 票（{{ votePct[o.id] || 0 }}%）</span>
      </div>
      <div class="vans" v-if="v.answer">{{ v.answer.answer_text }}</div>
      <div class="note" v-else-if="v.locked">這一題已經停止投票（答案露出來過）。</div>
    </section>

    <!-- PCA：四步 -->
    <template v-if="seg === 'pca' && pca && pdemo">
      <nav class="steps">
        <button v-for="(t, i) in PSTEPS" :key="i" :class="{ on: pstep === i + 1 }" @click="setStep('pca', i + 1)">{{ i + 1 }}　{{ t }}</button>
        <span class="stepnote">切步時，學生手機會跟著跳到同一步</span>
      </nav>
      <section class="card" v-if="pstep === 1">
        <div class="h">第 1 步　2 欄壓成 1 個分數：額度使用率 × 年齡</div>
        <Demo2 :d="pdemo" big />
      </section>
      <section class="card two" v-if="pstep === 2">
        <div>
          <div class="h">10 欄的前 3 個分數（PC1 × PC2 × PC3）</div>
          <Scatter3D :xyz="pca.xyz" :colors="labelColors" :front="labelFront" :height="560" :size="3.2" :selected="sel" @pick="i => sel = i" />
          <RestoreCard v-if="sel >= 0" :i="sel" :k="pk" :loadings="pca.loadings" big @close="sel = -1" />
        </div>
        <div>
          <div class="h">只記 <b class="kk">{{ pk }}</b> 個分數，猜得回來多少（還原）</div>
          <input class="slider" type="range" min="1" max="10" v-model.number="pk" />
          <Recon :cols="pca.cols" :row="pca.recon[pk - 1]" :total="pca.cum[pk - 1]" big />
          <div class="note">旁註：{{ pdemo.n_codes_student }} 個人的逾期欄填 96/98（資料代碼）。若照原樣放進去，PC1 從 {{ Math.round(pdemo.ev1 * 100) }}% 變 {{ Math.round(pdemo.keep_ev1 * 100) }}%。</div>
        </div>
      </section>
      <template v-if="pstep === 3">
        <section class="card two">
          <Loadings v-for="(w, i) in pca.loadings.slice(0, 2)" :key="i" :w="w" :title="`PC${i + 1}（留下 ${Math.round(pca.ev[i] * 100)}% 的資訊）`" big />
        </section>
        <section class="card">
          <button class="refbtn" :class="{ on: S.name_ref?.pca }" :disabled="locked" @click="once(toggleRef)('pca')">{{ S.name_ref?.pca ? '收起例子' : '看幾個例子' }}</button>
          <span class="refnote">按下後，學生手機的取名卡和第 4 步也會出現</span>
        </section>
        <section class="card two">
          <div v-for="slot in store.meta.name_slots.pca" :key="slot">
            <div class="h">全班替 {{ slot }} 取的名字</div>
            <div class="names"><span v-for="[n, c] in names?.pca?.[slot] || []" :key="n" :style="{ fontSize: 18 + Math.min(c, 8) * 4 + 'px' }">{{ n }}<small>×{{ c }}</small></span></div>
            <RefNames seg="pca" :only="slot" big />
          </div>
        </section>
      </template>
      <section class="card two" v-if="pstep === 4">
        <div>
          <div class="h">PC1 × PC2 × PC3 <small v-if="!S.labels">（按「公布誰違約」，違約的人變紅點）</small></div>
          <Scatter3D :xyz="pca.xyz" :colors="labelColors" :front="labelFront" :height="560" :size="3.2" :selected="sel" @pick="i => sel = i" />
          <PersonCard v-if="sel >= 0" :i="sel" @close="sel = -1" />
        </div>
        <div>
          <PcMix :loadings="pca.loadings" big />
          <RefNames seg="pca" concept big />
          <template v-if="prev">
            <div class="h mt">各分數高的那頭，違約比例</div>
            <ByPc :rev="prev" big />
          </template>
        </div>
      </section>
    </template>

    <!-- 分群、異常偵測：老師頁是一整頁；這排按鈕只用來帶學生手機跳到某一步 -->
    <nav class="steps" v-if="seg !== 'pca'">
      <span class="stepnote lead">學生手機跳到：</span>
      <button v-for="(t, i) in STEP_NAMES[seg]" :key="i" :class="{ on: S.step?.[seg] === i + 1 }" @click="setStep(seg, i + 1)">{{ i + 1 }}　{{ t }}</button>
    </nav>

    <!-- 分群 -->
    <template v-if="seg === 'cluster' && cls && pca">
      <section class="card">
        <div class="row"><div class="h" style="margin:0">示範：分群是怎麼一步一步跑出來的</div>
          <button class="refbtn" :class="{ on: showAnim }" @click="showAnim = !showAnim">{{ showAnim ? '收起示範' : '打開示範' }}</button></div>
        <ClusterAnim v-if="showAnim" :xyz="pca.xyz" style="margin-top:14px" />
      </section>
      <section class="card two">
        <div>
          <div class="h">10 欄、分成 {{ cls.k }} 群：
            <button class="mbtn" :class="{ on: cview === 'gmm' }" @click="setCView('gmm')">GMM（全班這一份）</button>
            <button class="mbtn" :class="{ on: cview === 'kmeans' }" @click="setCView('kmeans')">K-means</button>
            <small v-if="cview === 'kmeans'">右邊的卡片和投票仍是 GMM 那一份</small></div>
          <ClusterPlot v-if="store.people" :xyz="pca.xyz" :colors="cshown.labels.map(l => COLORS.cluster[l])" :ring="cring" :labels="cshown.labels" :groups="cshown.clusters" :selected="sel" big @pick="i => sel = i" />
          <PersonCard v-if="sel >= 0" :i="sel" :hide-label="!cring" @close="sel = -1"
            :extra="cview === 'gmm' ? '屬於各群的機率：' + cls.prob[sel].map((p, c) => `第 ${c + 1} 群 ${Math.round(p * 100)}%`).join('、') : `K-means 只說他在第 ${cshown.labels[sel] + 1} 群，不給機率`" />
        </div>
        <div>
          <ClusterCards :res="cls" big />
        </div>
      </section>
    </template>

    <!-- 異常偵測 -->
    <template v-if="seg === 'anomaly'">
      <section class="card two" v-if="!S.reveal.anomaly">
        <div>
          <div class="h">示範（最簡單的做法）：挑欄位、標出最異常的 10%</div>
          <ColPicker v-model="demoCols" />
          <button class="go" @click="runDemo">算算看</button>
          <template v-if="demo">
            <div class="big">鑑別度 <b>{{ demo.student.eta.toFixed(1) }}</b>　異常 {{ demo.student.n_flag }} 人違約 {{ demo.student.rate_flag }}%，正常 {{ fmtN(demo.student.n_rest) }} 人違約 {{ demo.student.rate_rest }}%</div>
          </template>
        </div>
        <div v-if="demo && demoXyz">
          <Scatter3D :xyz="demoXyz" :colors="demoXyz.map((_, i) => flagged.has(i) ? COLORS.amber : COLORS.gray)" :front="demoXyz.map((_, i) => flagged.has(i))" :ring="aring" :height="520" :size="3.2" :selected="sel" @pick="i => sel = i" />
          <PersonCard v-if="sel >= 0" :i="sel" :highlight="demo.cols" :hide-label="!aring" @close="sel = -1" />
        </div>
      </section>
      <section class="card waiting" v-if="!S.reveal.anomaly">已提交 <b>{{ S.n_submitted }}</b> 人，排行榜還沒揭曉</section>
      <template v-if="rev">
        <section class="card">
          <div class="h">排行榜（考題 {{ fmtN(store.meta.test_n) }} 人）</div>
          <table class="rank">
            <tr class="muted"><td>#</td><td>暱稱</td><td>挑的欄位</td><td>做法</td><td>鑑別度（考題）</td><td>異常幾人、違約比例／正常的違約比例</td><td>自己 2,000 人</td></tr>
            <tr v-for="r in rev.rows" :key="r.nickname">
              <td class="no">{{ r.rank }}</td><td class="nick">{{ r.nickname }}</td>
              <td class="feats">{{ r.cols.map(k => zh[k]).join('、') }}</td><td class="feats">{{ routeText(r) }}</td>
              <td class="score">{{ r.test.toFixed(1) }}</td><td>{{ fmtN(r.test_n_flag) }} 人 {{ r.test_rate_flag }}%／{{ r.test_rate_rest }}%</td><td class="muted">{{ r.student.toFixed(1) }}</td>
            </tr>
            <tr v-if="!rev.rows.length"><td colspan="7" class="muted">還沒有人提交</td></tr>
          </table>
        </section>
        <section class="card two">
          <div><div class="h">不做 PCA、不分群時，挑幾欄最好？（1,023 種挑法，考題的鑑別度）</div><SizeCurve :curve="rev.curve" big /></div>
          <div><div class="h">異常≠會違約</div><Cases :cases="rev.cases" big /></div>
        </section>
      </template>
    </template>
  </main>
</template>

<style scoped>
.top { background: var(--ink); color: var(--paper); padding: 14px 28px; }
.row { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
h1 { margin: 0; font-size: 26px; }
.ctrl { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.ctrl button { font-size: 16px; font-weight: 700; padding: 8px 14px; border-radius: 10px; border: 1px solid #4f493f; background: transparent; color: #cfc7b6; cursor: pointer; }
.ctrl button.on { background: var(--paper); color: var(--ink); border-color: var(--paper); }
.ctrl .rev.on { background: var(--red); color: #fff; border-color: var(--red); }
.ctrl .danger { color: #e9a79a; }
.sep { width: 12px; }
.stat { margin-top: 8px; font-size: 15px; color: #cfc7b6; }
.page { padding: 18px 28px 60px; display: flex; flex-direction: column; gap: 18px; }
.h { font-size: 24px; font-weight: 900; margin-bottom: 12px; }
.h small { font-size: 16px; color: var(--red); }
.two { display: grid; grid-template-columns: 1.2fr 1fr; gap: 28px; align-items: start; }
.steps { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.stepnote { font-size: 15px; color: var(--ink-2); margin-left: 8px; }
.login { max-width: 360px; margin: 18vh auto; display: grid; gap: 12px; padding: 24px; background: #fff; border: 2px solid var(--ink); border-radius: 16px; }
.login .lt { font-size: 24px; font-weight: 900; }
.login input { font-size: 20px; padding: 12px; border: 2px solid var(--line); border-radius: 10px; }
.login button { font-size: 20px; font-weight: 900; padding: 12px; border: 0; border-radius: 10px; background: var(--ink); color: #fff; }
.login .lm { color: var(--red); font-weight: 800; }
.tip { display: flex; align-items: center; gap: 14px; margin-bottom: 14px; padding: 12px 16px; border: 3px solid var(--red); border-radius: 14px; background: #fff; font-size: 19px; }
.tip .tl { font-weight: 900; color: #fff; background: var(--red); border-radius: 8px; padding: 2px 10px; white-space: nowrap; }
.tip .tt { flex: 1; }
.tip .tt b { margin-left: 6px; }
.tip button { font-size: 19px; font-weight: 900; padding: 10px 18px; border-radius: 12px; border: 0; background: var(--red); color: #fff; white-space: nowrap; cursor: pointer; }
.stepnote.lead { margin-left: 0; font-weight: 800; color: var(--ink); font-size: 17px; }
.steps button { font-size: 18px; font-weight: 800; padding: 10px 16px; border-radius: 10px; border: 2px solid var(--line); background: #fff; color: var(--ink-2); cursor: pointer; }
.steps button.on { background: var(--ink); color: #fff; border-color: var(--ink); }
.lead { font-size: 26px; line-height: 1.6; margin: 10px 0; }
.kk { color: var(--red); font-size: 34px; }
.slider { width: 100%; margin: 6px 0 16px; }
.note { font-size: 18px; color: var(--ink-2); margin-top: 18px; }
.vctrl { display: flex; gap: 8px; }
.vctrl button { font-size: 16px; font-weight: 700; padding: 8px 14px; border-radius: 10px; border: 1px solid var(--line); background: #fff; cursor: pointer; }
.vctrl button:disabled { opacity: .4; }
.vctrl .rev.on { background: var(--red); color: #fff; border-color: var(--red); }
.vrow { display: grid; grid-template-columns: 300px 1fr 180px; gap: 16px; align-items: center; margin: 8px 0; font-size: 22px; }
.vlabel { font-weight: 700; }
.vlabel.win { color: var(--red); font-weight: 900; }
.vbar { background: var(--paper-2); border-radius: 10px; height: 32px; overflow: hidden; }
.vbar i { display: block; height: 100%; background: var(--red); transition: width .4s; }
.vnum { font-weight: 900; }
.vans { font-size: 24px; font-weight: 900; color: var(--red); margin-top: 10px; }
.names { display: flex; flex-wrap: wrap; gap: 8px 18px; align-items: baseline; margin-top: 6px; }
.names span { font-weight: 900; }
.refbtn { font-size: 18px; font-weight: 800; padding: 10px 18px; border-radius: 10px; border: 2px solid var(--teal); background: #fff; color: var(--teal); cursor: pointer; }
.refbtn.on { background: var(--teal); color: #fff; }
.refnote { margin-left: 14px; font-size: 16px; color: var(--ink-2); }
.mt { margin-top: 18px; }
.mbtn { font-size: 18px; font-weight: 800; padding: 6px 14px; margin-left: 6px; border-radius: 10px; border: 2px solid var(--line); background: #fff; color: var(--ink-2); cursor: pointer; vertical-align: middle; }
.mbtn.on { background: var(--teal); border-color: var(--teal); color: #fff; }
.names small { font-size: 14px; color: var(--ink-2); margin-left: 2px; font-weight: 400; }
.go { margin-top: 12px; font-size: 20px; font-weight: 900; padding: 12px 28px; border: 0; border-radius: 12px; background: var(--ink); color: #fff; cursor: pointer; }
.big { font-size: 22px; margin-top: 14px; }
.big b { font-size: 40px; color: var(--red); }
.waiting { font-size: 24px; text-align: center; padding: 30px; }
.rank { width: 100%; border-collapse: collapse; font-size: 19px; }
.rank td { padding: 8px 10px; border-top: 1px solid var(--line); }
.rank .no { font-weight: 900; }
.rank .nick { font-size: 22px; font-weight: 900; }
.rank .score { font-size: 26px; font-weight: 900; color: var(--red); }
.rank .feats { font-size: 17px; }
</style>

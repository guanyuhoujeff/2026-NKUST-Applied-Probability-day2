<script setup>
// 分群段：全班同一份（10 欄、GMM、3 群）→ 看每群長相、先猜哪群最會違約（投票）→ 揭曉違約比例 → 自己試（欄位、群數、方法，拼分數）。
// 2026-11-17：投票從第 3 步搬到第 2 步；「換起點」從自己試搬到第 1 步當示範（自己試固定起點，免得靠換起點刷分）；自己試加分數。
import { ref, computed, watch, onMounted } from 'vue'
import { store, getJSON, colsParam, COLORS, fmtN } from '../shared.js'
import Scatter3D from '../components/Scatter3D.vue'
import ClusterPlot from '../components/ClusterPlot.vue'
import ClusterCards from '../components/ClusterCards.vue'
import PersonCard from '../components/PersonCard.vue'
import ColPicker from '../components/ColPicker.vue'
import StepTabs from '../components/StepTabs.vue'
import VoteCard from '../components/VoteCard.vue'
import ClusterScore from '../components/ClusterScore.vue'
import PcMix from '../components/PcMix.vue'

const props = defineProps({ nickname: String, myVotes: Object })
const emit = defineEmits(['voted'])
const cfg = computed(() => store.meta.cluster.class_cfg)
const xyz = ref(null)          // 全班：十欄 PCA 座標（畫圖用）
const cls = ref(null)
const sel = ref(-1)
const mine = ref([])
const k = ref(3)
const method = ref('gmm')
const my = ref(null)
const myXyz = ref(null)
const myLoad = ref(null)           // 自己試：這次挑的欄位重算的 PCA 權重（圖的三個軸各由哪幾欄組成）
const mySel = ref(-1)
const err = ref('')
const showMine = ref(false)
const busy = ref(false)
const view = ref('gmm')            // 第 1 步看哪一種方法分的：gmm＝全班那一份；kmeans＝同樣 10 欄、3 群，換成 K-means
const vstart = ref(0)             // 第 1 步示範用的起點（0＝全班那一份的起點）
const alt = ref(null)             // 第 1 步：不是全班那一份時（換了方法或起點）的結果
const best = ref(null)            // 自己試：最好紀錄
const tab = ref(store.state.step?.cluster || 1)
const voteHere = computed(() => store.votes?.question?.seg === 'cluster')
const TABS = computed(() => [{ key: 1, no: '第 1 步', lock: true, label: '分成幾群' }, { key: 2, no: '第 2 步', lock: true, label: '長相、先猜', dot: tab.value !== 2 && voteHere.value && !store.votes?.answer },
  { key: 3, no: '第 3 步', lock: true, label: '揭曉', dot: tab.value !== 3 && (store.state.reveal.cluster || (voteHere.value && !!store.votes?.answer)) }, { key: 4, no: '加碼', label: '自己試' }])

// 分群揭曉前不顯示誰違約（PCA 段公布過也一樣），不然還沒投票就看得到答案
const known = computed(() => !!store.state.reveal.cluster)
const ring = computed(() => store.labels && known.value ? store.labels.map(y => !!y) : null)
const colorsFor = res => res ? res.labels.map(l => COLORS.cluster[l]) : null
const probText = (res, i) => res.method === 'gmm'
  ? '屬於各群的機率：' + res.prob[i].map((p, c) => `第 ${c + 1} 群 ${Math.round(p * 100)}%`).join('、')
  : `K-means 只說他在第 ${res.labels[i] + 1} 群，不給機率`
const ambiguous = computed(() => cls.value ? cls.value.prob.map((p, i) => [Math.max(...p), i]).filter(([m]) => m < store.meta.cluster.ambiguous).map(([, i]) => i) : [])

async function loadClass() {
  const c = cfg.value
  cls.value = await getJSON(`/api/cluster?cols=${colsParam(c.cols)}&k=${c.k}&method=${c.method}&start=${c.start}`)
}
const isClass = computed(() => view.value === 'gmm' && vstart.value === 0)
const shown = computed(() => (!isClass.value && alt.value ? alt.value : cls.value))
let altSeq = 0
async function loadAlt() {
  const c = cfg.value, my = ++altSeq
  const r = isClass.value ? null : await getJSON(`/api/cluster?cols=${colsParam(c.cols)}&k=${c.k}&method=${view.value}&start=${vstart.value}`)
  if (my === altSeq) alt.value = r      // 連按「換一個起點」：只收最後一次的
}
async function setView(m, st = 0) { sel.value = -1; view.value = m; vstart.value = st; await loadAlt() }
const nextStart = () => setView(view.value, (vstart.value + 1) % store.meta.cluster.starts.length)
const sizes = res => res.clusters.map(c => fmtN(c.n)).join('、')
const BEST_KEY = 'day2-cluster-best'
let mineSeq = 0, mineTimer = null
async function runMine() {
  err.value = ''
  const seq = ++mineSeq
  if (!mine.value.length) { err.value = '至少挑一欄'; my.value = null; return }
  busy.value = true
  try {
    const q = colsParam(mine.value)
    const [r, p] = await Promise.all([getJSON(`/api/cluster?cols=${q}&k=${k.value}&method=${method.value}&start=0`), getJSON('/api/pca?cols=' + q)])
    if (seq !== mineSeq) return                    // 這期間又改了設定：舊的結果丟掉（慢的 8 群不能蓋掉後來的 2 群）
    if (r.error) { err.value = r.error; return }
    my.value = r; myXyz.value = p.xyz; myLoad.value = p.loadings; mySel.value = -1
    if (r.score !== undefined && (best.value === null || r.score > best.value)) { best.value = r.score; try { localStorage.setItem(BEST_KEY, JSON.stringify({ epoch: store.epoch, score: r.score })) } catch (e) { /* 存不了就只留在這一頁 */ } }
  } catch (e) { if (seq === mineSeq) err.value = '連不上伺服器，等一下再試' } finally { if (seq === mineSeq) busy.value = false }
}
watch(() => store.state.reveal.cluster, () => { loadClass(); loadAlt(); if (my.value) runMine() })
// 手停 0.4 秒才送：連點欄位時不要每一下都叫伺服器算（實測 50 人連點會塞到 11 秒，FACTS-30）
watch([mine, k, method], () => { if (!showMine.value) return; clearTimeout(mineTimer); mineTimer = setTimeout(runMine, 400) })
watch(() => store.cleared, () => { best.value = null; try { localStorage.removeItem(BEST_KEY) } catch (e) { /* 沒有就算了 */ } })
watch(() => store.state.step?.cluster, v => { if (v) { tab.value = v; window.scrollTo(0, 0) } })   // 老師切步，手機跟著跳
onMounted(async () => {
  try { const b = JSON.parse(localStorage.getItem(BEST_KEY)); if (b && b.epoch === store.epoch && typeof b.score === 'number') best.value = b.score } catch (e) { /* 沒有紀錄，或是上一輪的 */ }
  xyz.value = (await getJSON('/api/pca?cols=' + colsParam(store.meta.keys))).xyz
  await loadClass()
  mine.value = [...store.meta.keys]
})
watch(tab, t => { sel.value = -1; if (t === 4) { showMine.value = true; if (!my.value) runMine() } })
</script>

<template>
  <StepTabs :tabs="TABS" v-model="tab" :home="store.state.step?.cluster || 1" />

  <section class="card" v-if="tab === 1">
    <div class="qt">把 2,000 人分成幾群</div>
    <div class="muted small">分群：讓電腦把相像的人放在同一群，一樣不看誰違約。
      這裡用的方法叫 GMM，會算出每個人「屬於各群的機率」。</div>
  </section>

  <section class="card" v-if="tab === 1 && cls && xyz">
    <div class="h2">10 欄、分成 {{ cfg.k }} 群</div>
    <div class="mth">
      <span class="lab">方法</span>
      <button :class="{ on: view === 'gmm' }" @click="setView('gmm')">GMM（全班這一份）</button>
      <button :class="{ on: view === 'kmeans' }" @click="setView('kmeans')">K-means</button>
    </div>
    <div class="mth">
      <span class="lab">起點</span>
      <button class="on" @click="nextStart">第 {{ vstart + 1 }} 個起點　換一個 ↻</button>
    </div>
    <div class="muted small">各群人數：{{ sizes(shown) }}。電腦是從隨機的起點開始找群的。換個起點或換個方法，分出來的群可能不一樣。</div>
    <div class="muted small" v-if="!isClass">全班接下來看的還是「GMM、第 1 個起點」那一份。<button class="mini" @click="setView('gmm', 0)">回到那一份</button></div>
    <ClusterPlot :xyz="xyz" :colors="colorsFor(shown)" :ring="ring" :labels="shown.labels" :groups="shown.clusters" :selected="sel" @pick="i => sel = i" />
    <PersonCard v-if="sel >= 0" :i="sel" :extra="probText(shown, sel)" :hide-label="!known" @close="sel = -1" />
    <div class="muted small" v-else>點一個圓點，看那個人在哪一群。按「第 1 群」可以只看那一群。</div>
    <div class="muted small amb" v-if="isClass">兩群都像的人（最像的那一群，機率不到 {{ Math.round(store.meta.cluster.ambiguous * 100) }}%）：{{ ambiguous.length }} 人
      <button v-if="ambiguous.length" class="mini" @click="sel = ambiguous[0]">看一個</button></div>
    <div class="muted small">圖的軸（PCA 的分數）只是用來畫圖：分群是直接用 10 個欄位算的，沒有先做 PCA。</div>
    <div class="muted small">想改欄位、改群數，到「自己試」分頁。</div>
  </section>

  <section class="card" v-if="tab === 2">
    <div class="h2">看長相，先猜：哪一群最會違約？</div>
    <div class="muted small">分群的時候，電腦沒有看誰違約。先看每一群長什麼樣，再到下面投票。</div>
  </section>
  <section class="card" v-if="tab === 3">
    <div class="h2">揭曉：每一群的違約比例</div>
    <div class="muted small" v-if="store.state.reveal.cluster">每一群的卡片最下面，多了違約比例。</div>
    <div class="muted small" v-else>老師還沒揭曉。揭曉後，每一群的卡片會出現違約比例。</div>
  </section>

  <section class="card" v-if="(tab === 2 || tab === 3) && cls">
    <div class="h2">每一群長什麼樣？</div>
    <ClusterCards :res="cls" />
  </section>
  <VoteCard v-if="voteHere && (tab === 2 || (tab === 3 && store.votes?.answer))" :nickname="nickname" :mine="myVotes" @voted="(q, c) => emit('voted', q, c)" />

  <section class="card" v-if="tab === 4">
    <div class="qt">自己試：換欄位、群數、方法，拼鑑別度</div>
    <div class="muted small">分群時電腦一樣不看誰違約，分完才對答案，看分出來的群有沒有<b>鑑別度</b>：有的群違約多、有的群違約少，分數就高。少於 {{ store.meta.cluster.min_n }} 人的群不算。</div>
    <template v-if="showMine">
      <ColPicker v-model="mine" />
      <div class="opt-row">
        <span class="lab">群數</span>
        <button v-for="x in store.meta.cluster.ks" :key="x" class="seg" :class="{ on: k === x }" @click="k = x">{{ x }}</button>
      </div>
      <div class="opt-row">
        <span class="lab">方法</span>
        <button class="seg" :class="{ on: method === 'gmm' }" @click="method = 'gmm'">GMM（給機率）</button>
        <button class="seg" :class="{ on: method === 'kmeans' }" @click="method = 'kmeans'">K-means</button>
      </div>
      <div class="err" v-if="err">{{ err }}</div>
      <div class="muted small" v-if="busy">計算中…</div>
      <template v-if="my && myXyz">
        <ClusterScore v-if="my.score !== undefined" :res="my" :base="cls?.score ?? null" :best="best" />
        <div class="wait" v-else>老師揭曉之後，這裡才有鑑別度分數。</div>
        <Scatter3D :xyz="myXyz" :colors="colorsFor(my)" :ring="ring" :selected="mySel" @pick="i => mySel = i" />
        <PersonCard v-if="mySel >= 0" :i="mySel" :extra="probText(my, mySel)" :hide-label="!known" @close="mySel = -1" />
        <div class="muted small">圖的三個軸（PC1、PC2、PC3）只是用來畫圖：分群是直接用挑的欄位算的，沒有先做 PCA。軸是用這次挑的欄位重新算的，跟第 1 步不一樣。</div>
        <PcMix v-if="myLoad" :loadings="myLoad" :top="3" />
        <ClusterCards :res="my" />
      </template>
    </template>
  </section>
</template>

<style scoped>
.mth { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; margin-bottom: 8px; }
.mth .lab { font-size: 13px; font-weight: 800; color: var(--ink-2); }
.mth button { font-size: 14px; font-weight: 800; padding: 8px 10px; border-radius: 10px; border: 2px solid var(--line); background: #fff; color: var(--ink-2); }
.mth button.on { border-color: var(--teal); background: var(--teal); color: #fff; }
.qt { font-weight: 900; font-size: 19px; margin-bottom: 6px; }
.h2 { font-weight: 900; font-size: 17px; margin-bottom: 8px; }
.small { font-size: 13px; }
.amb { margin-top: 8px; }
.mini { font-size: 13px; padding: 4px 10px; border-radius: 8px; border: 1px solid var(--line); background: #fff; margin-left: 6px; }
.opt-row { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; margin-top: 10px; }
.lab { width: 40px; font-weight: 700; }
.seg { font-size: 15px; padding: 8px 12px; border-radius: 10px; border: 2px solid var(--line); background: #fff; color: var(--ink-2); }
.seg.on { border-color: var(--teal); background: var(--teal-soft); color: var(--ink); font-weight: 700; }
.err { color: var(--red); font-weight: 700; }
.wait { border: 2px dashed var(--line); border-radius: 12px; padding: 12px; margin: 12px 0; font-weight: 800; color: var(--ink-2); }
</style>

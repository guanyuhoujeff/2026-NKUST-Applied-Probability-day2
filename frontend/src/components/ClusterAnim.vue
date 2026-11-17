<script setup>
// 老師頁示範：分群一步一步怎麼跑。資料是真的 2,000 人，但只用兩個數字（PC1、PC2）才畫得出過程。
// K-means：① 每個人塗成最近中心的顏色 ② 中心移到那群人的平均。GMM：① 算每個人屬於各橢圓的機率（顏色混在一起＝不確定）② 橢圓依機率調整位置、形狀、大小。
// 這只是看懂算法的示範；全班那一份是 10 欄、GMM，結果不會一樣。
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { COLORS } from '../shared.js'

const props = defineProps({ xyz: { type: Array, required: true }, height: { type: Number, default: 560 } })
const method = ref('kmeans')
const k = ref(3)
const seed = ref(1)
const half = ref(0)          // 做了幾個半步；偶數＝接下來做 ①，奇數＝接下來做 ②
const moved = ref(null)      // 上一次 ① 有幾個人換了群
const done = ref(false)
const playing = ref(false)
const cv = ref(null), wrap = ref(null)
let W = 600, H = props.height, dpr = 1, raf = 0, timer = 0

const X = computed(() => props.xyz.map(p => [p[0], p[1]]))
const RGB = COLORS.cluster.map(h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16)))
let S = null     // 目前的狀態（不放進 reactive：2,000 人的陣列每步都換）

function rng(a) { return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296 } }
function init() {
  stop()
  const r = rng(seed.value * 7919 + k.value * 31 + (method.value === 'gmm' ? 5 : 0)), x = X.value, n = x.length
  const pickIdx = []
  while (pickIdx.length < k.value) { const i = Math.floor(r() * n); if (!pickIdx.includes(i)) pickIdx.push(i) }
  const mx = x.reduce((a, p) => a + p[0], 0) / n, my = x.reduce((a, p) => a + p[1], 0) / n
  let a = 0, b = 0, c = 0
  for (const p of x) { a += (p[0] - mx) ** 2; b += (p[0] - mx) * (p[1] - my); c += (p[1] - my) ** 2 }
  const base = [a / n / k.value, b / n / k.value, c / n / k.value]
  S = { mu: pickIdx.map(i => [...x[i]]), prev: null, lab: null, resp: null, cov: pickIdx.map(() => [...base]), pi: pickIdx.map(() => 1 / k.value), n: pickIdx.map(() => 0) }
  half.value = 0; moved.value = null; done.value = false
  redraw()
}
const dens = (p, mu, cv3) => {      // 2 維常態分配的密度
  const [a, b, c] = cv3, det = Math.max(a * c - b * b, 1e-12), dx = p[0] - mu[0], dy = p[1] - mu[1]
  return Math.exp(-0.5 * (c * dx * dx - 2 * b * dx * dy + a * dy * dy) / det) / (2 * Math.PI * Math.sqrt(det))
}
function stepAssign() {
  const x = X.value, K = k.value, old = S.lab
  const lab = new Array(x.length); let resp = null
  if (method.value === 'kmeans') {
    x.forEach((p, i) => { let bj = 0, bd = Infinity; for (let j = 0; j < K; j++) { const d = (p[0] - S.mu[j][0]) ** 2 + (p[1] - S.mu[j][1]) ** 2; if (d < bd) { bd = d; bj = j } } lab[i] = bj })
  } else {
    resp = x.map((p, i) => { const w = S.mu.map((m, j) => S.pi[j] * dens(p, m, S.cov[j])); const t = w.reduce((s, v) => s + v, 0) || 1e-300; const r = w.map(v => v / t); lab[i] = r.indexOf(Math.max(...r)); return r })
  }
  moved.value = old ? lab.reduce((s, l, i) => s + (l !== old[i] ? 1 : 0), 0) : null
  S.lab = lab; S.resp = resp
  S.n = Array.from({ length: K }, (_, j) => lab.filter(l => l === j).length)
}
function stepMove() {
  const x = X.value, K = k.value
  const prev = S.mu.map(m => [...m])
  for (let j = 0; j < K; j++) {
    let sw = 0, sx = 0, sy = 0
    x.forEach((p, i) => { const w = method.value === 'kmeans' ? (S.lab[i] === j ? 1 : 0) : S.resp[i][j]; sw += w; sx += w * p[0]; sy += w * p[1] })
    if (sw < 1e-9) continue                       // 沒有人的群：中心留在原地
    const mu = [sx / sw, sy / sw]
    if (method.value === 'gmm') {
      let a = 0, b = 0, c = 0
      x.forEach((p, i) => { const w = S.resp[i][j], dx = p[0] - mu[0], dy = p[1] - mu[1]; a += w * dx * dx; b += w * dx * dy; c += w * dy * dy })
      S.cov[j] = [a / sw + 1e-3, b / sw, c / sw + 1e-3]; S.pi[j] = sw / x.length
    }
    S.mu[j] = mu
  }
  S.prev = prev
  const shift = Math.max(...S.mu.map((m, j) => Math.hypot(m[0] - prev[j][0], m[1] - prev[j][1])))
  // 停下來的條件：K-means＝沒有人換群；GMM＝沒有人換群而且橢圓幾乎不動（或跑滿 60 輪）
  if (method.value === 'kmeans' ? moved.value === 0 : ((moved.value === 0 && shift < 0.003) || half.value >= 119)) done.value = true
}
function next() {
  if (done.value) return
  if (half.value % 2 === 0) stepAssign(); else stepMove()
  half.value++
  if (method.value === 'kmeans' && half.value % 2 === 1 && moved.value === 0) done.value = true     // 塗完發現沒人換群，就不用再移了
  if (done.value) stop()
  redraw()
}
function play() { if (done.value) return; playing.value = true; timer = setInterval(next, method.value === 'kmeans' ? 700 : 350) }
function stop() { playing.value = false; clearInterval(timer) }
function reseed() { seed.value++; init() }
const round = computed(() => Math.floor(half.value / 2) + (half.value % 2))
const say = computed(() => {
  const km = method.value === 'kmeans'
  if (half.value === 0) return km ? `先隨便挑 ${k.value} 個人的位置當「中心」（大圓圈）。所有人還沒有顏色。` : `先隨便挑 ${k.value} 個人的位置，各放一個一樣大的橢圓（一個橢圓＝一個常態分配）。`
  if (done.value) return km ? `第 ${round.value} 輪沒有人換群，停。同樣的資料，換一組起點再跑，結果可能不一樣。` : `橢圓幾乎不動、也沒有人換群了，停。顏色混濁的人＝兩群都像、分不太清楚。`
  if (half.value % 2 === 1) return km ? `第 ${round.value} 輪 ①：每個人塗成「離他最近的中心」的顏色。` + (moved.value !== null ? `這一輪有 ${moved.value} 人換了群。` : '') + ' 接下來 ②：把每個中心移到同色那群人的平均位置。'
    : `第 ${round.value} 輪 ①：用貝氏定理算每個人屬於各橢圓的機率，顏色照機率混在一起。` + (moved.value !== null ? `最像的那一群換了的有 ${moved.value} 人。` : '') + ' 接下來 ②：每個橢圓照機率重新算中心、形狀和大小。'
  return km ? `第 ${round.value} 輪 ②：中心移到那群人的平均位置（細線是移動的路徑）。接下來回到 ①，重新塗顏色。` : `第 ${round.value} 輪 ②：橢圓移動、變形了（橢圓框住那一群大約 86% 的人）。接下來回到 ①，重新算機率。`
})

// ---- 畫圖 ----
let bx = [-1, 1], by = [-1, 1]
function bounds() { const xs = X.value.map(p => p[0]), ys = X.value.map(p => p[1]); bx = [Math.min(...xs), Math.max(...xs)]; by = [Math.min(...ys), Math.max(...ys)] }
const sc = () => Math.min((W - 60) / (bx[1] - bx[0]), (H - 50) / (by[1] - by[0]))      // 等比例，橢圓才不會歪
const px = p => { const s = sc(); return [W / 2 + (p[0] - (bx[0] + bx[1]) / 2) * s, H / 2 - (p[1] - (by[0] + by[1]) / 2) * s] }
function draw() {
  raf = 0
  const c = cv.value; if (!c || !S) return
  const g = c.getContext('2d'); g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, W, H)
  g.fillStyle = '#4f493f'; g.font = '700 16px system-ui, sans-serif'; g.textAlign = 'right'; g.fillText('PC1 →', W - 10, H - 10); g.textAlign = 'left'; g.fillText('↑ PC2', 8, 20)
  X.value.forEach((p, i) => {
    const [x, y] = px(p)
    if (!S.lab) g.fillStyle = 'rgb(163,155,140)'
    else if (S.resp) { const r = S.resp[i]; const m = [0, 1, 2].map(ch => Math.round(r.reduce((s, w, j) => s + w * RGB[j][ch], 0))); g.fillStyle = `rgb(${m[0]},${m[1]},${m[2]})` }
    else g.fillStyle = COLORS.cluster[S.lab[i]]
    g.globalAlpha = 0.75; g.beginPath(); g.arc(x, y, 3, 0, Math.PI * 2); g.fill()
  })
  g.globalAlpha = 1
  S.mu.forEach((m, j) => {
    const [x, y] = px(m), s = sc()
    if (method.value === 'gmm') {         // 2 個標準差的橢圓
      const [a, b, cc] = S.cov[j], tr = (a + cc) / 2, dd = Math.sqrt(Math.max(((a - cc) / 2) ** 2 + b * b, 0))
      const l1 = tr + dd, l2 = Math.max(tr - dd, 1e-9), ang = 0.5 * Math.atan2(2 * b, a - cc)
      g.save(); g.translate(x, y); g.rotate(-ang); g.strokeStyle = COLORS.cluster[j]; g.lineWidth = 4
      g.beginPath(); g.ellipse(0, 0, 2 * Math.sqrt(l1) * s, 2 * Math.sqrt(l2) * s, 0, 0, Math.PI * 2); g.stroke()
      g.globalAlpha = 0.08; g.fillStyle = COLORS.cluster[j]; g.fill(); g.restore(); g.globalAlpha = 1
    }
    if (S.prev) { const [ox, oy] = px(S.prev[j]); g.strokeStyle = '#1f1c17'; g.lineWidth = 2; g.setLineDash([5, 4]); g.beginPath(); g.moveTo(ox, oy); g.lineTo(x, y); g.stroke(); g.setLineDash([]) }
    g.fillStyle = COLORS.cluster[j]; g.strokeStyle = '#1f1c17'; g.lineWidth = 3
    g.beginPath(); g.arc(x, y, 13, 0, Math.PI * 2); g.fill(); g.stroke()
    g.fillStyle = '#fff'; g.font = '900 15px system-ui, sans-serif'; g.textAlign = 'center'; g.fillText(String(j + 1), x, y + 5)
  })
}
function redraw() { if (!raf) raf = requestAnimationFrame(draw) }
function resize() {
  if (!wrap.value || !cv.value) return
  W = wrap.value.clientWidth; H = props.height; dpr = window.devicePixelRatio || 1
  cv.value.width = W * dpr; cv.value.height = H * dpr; cv.value.style.width = W + 'px'; cv.value.style.height = H + 'px'
  redraw()
}
let ro
onMounted(() => { bounds(); init(); ro = new ResizeObserver(resize); ro.observe(wrap.value); resize() })
onBeforeUnmount(() => { stop(); ro && ro.disconnect(); cancelAnimationFrame(raf) })
watch([method, k], init)
watch(() => props.xyz, () => { bounds(); init() })
const sizes = computed(() => (half.value, S?.lab ? S.n : null))
</script>

<template>
  <div class="ca">
    <div class="bar">
      <span class="lab">方法</span>
      <button :class="{ on: method === 'kmeans' }" @click="method = 'kmeans'">K-means（中心）</button>
      <button :class="{ on: method === 'gmm' }" @click="method = 'gmm'">GMM（橢圓＋機率）</button>
      <span class="lab sp">群數</span>
      <button v-for="n in [2, 3, 4, 5]" :key="n" :class="{ on: k === n }" @click="k = n">{{ n }}</button>
    </div>
    <div class="bar">
      <button class="go" :disabled="done || playing" @click="next">下一步 ▸</button>
      <button class="go" :disabled="done" @click="playing ? stop() : play()">{{ playing ? '暫停 ❚❚' : '自動播放 ▶' }}</button>
      <button @click="init">回到開頭</button>
      <button @click="reseed">換一組起點 ↻（第 {{ seed }} 組）</button>
      <span class="stat">第 <b>{{ round }}</b> 輪<template v-if="moved !== null">　這一輪換群 <b>{{ moved }}</b> 人</template><template v-if="done">　<b class="red">停了</b></template></span>
    </div>
    <div class="say">{{ say }}</div>
    <div ref="wrap" class="plot"><canvas ref="cv"></canvas></div>
    <div class="sizes" v-if="sizes"><span v-for="(n, j) in sizes" :key="j"><i :style="{ background: COLORS.cluster[j] }"></i>第 {{ j + 1 }} 群 {{ n }} 人</span></div>
    <div class="note">示範用：資料是真的 2,000 人，但只用 PC1、PC2 兩個數字，才畫得出過程。全班接下來看的那一份是用 10 個欄位、GMM 分的，結果不會一樣。</div>
  </div>
</template>

<style scoped>
.bar { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-bottom: 10px; }
.lab { font-size: 17px; font-weight: 800; color: var(--ink-2); }
.lab.sp { margin-left: 16px; }
.bar button { font-size: 17px; font-weight: 800; padding: 9px 14px; border-radius: 10px; border: 2px solid var(--line); background: #fff; color: var(--ink); cursor: pointer; }
.bar button.on { background: var(--ink); color: #fff; border-color: var(--ink); }
.bar button.go { border-color: var(--red); color: var(--red); }
.bar button:disabled { opacity: .35; cursor: default; }
.stat { margin-left: 12px; font-size: 20px; }
.stat b { font-size: 26px; }
.say { font-size: 22px; line-height: 1.5; font-weight: 700; min-height: 66px; padding: 10px 14px; border-radius: 12px; background: var(--paper-2); margin-bottom: 10px; }
.plot { border: 1px solid var(--line); border-radius: 12px; background: #fbf8f2; overflow: hidden; }
canvas { display: block; }
.sizes { display: flex; gap: 16px; flex-wrap: wrap; font-size: 18px; margin-top: 8px; }
.sizes i { display: inline-block; width: 14px; height: 14px; border-radius: 50%; margin-right: 6px; }
.note { font-size: 16px; color: var(--ink-2); margin-top: 8px; }
</style>

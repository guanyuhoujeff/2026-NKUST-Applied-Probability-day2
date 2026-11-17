<script setup>
// 平面散布圖：橫軸、直軸各是一個原始欄位或一個 PCA 分數（pc1、pc2、pc3）。每個點是一個人，顏色由外面給；ring＝紅框（違約）。
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { store } from '../shared.js'
import { buildAxes, unitPos, tickPos, tickText, axisLabel } from '../axes.js'

const props = defineProps({ named: Boolean,
  xk: { type: String, required: true }, yk: { type: String, required: true }, xyz: { type: Array, default: null },
  colors: { type: Array, default: null }, ring: { type: Array, default: null }, show: { type: Array, default: null },
  selected: { type: Number, default: -1 }, height: { type: Number, default: 320 }, size: { type: Number, default: 2.6 }, big: Boolean,
})
const emit = defineEmits(['pick'])
const cv = ref(null), wrap = ref(null)
let W = 300, H = props.height, dpr = 1, raf = 0
const PAD = props.big ? { l: 70, r: 16, t: 30, b: 54 } : { l: 46, r: 12, t: 20, b: 38 }
const both = computed(() => (store.people ? buildAxes([props.xk, props.yk], props.xyz) : null))
const ax = computed(() => both.value?.axes[0])
const ay = computed(() => both.value?.axes[1])
const hidden = computed(() => (both.value ? both.value.mask.filter(m => !m).length : 0))
let PTS = []      // 目前畫面上每個人的位置（px）；跟畫布寬度有關，所以每次重畫時算
function calcPts() {
  if (!both.value) return []
  return both.value.mask.map((m, i) => (m && (!props.show || props.show[i]))
    ? [PAD.l + unitPos(ax.value, ax.value.vals[i], i, 1) * (W - PAD.l - PAD.r), H - PAD.b - unitPos(ay.value, ay.value.vals[i], i, 2) * (H - PAD.t - PAD.b)]
    : null)
}
function draw() {
  raf = 0
  const c = cv.value; if (!c || !ax.value) return
  const g = c.getContext('2d'); g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, W, H)
  const P = PTS = calcPts()
  g.font = (props.big ? 16 : 11) + 'px system-ui, sans-serif'; g.fillStyle = '#6f675a'; g.strokeStyle = '#e6dfd0'; g.lineWidth = 1
  let last = -1e9
  for (const v of ax.value.ticks) {
    const x = PAD.l + tickPos(ax.value, v) * (W - PAD.l - PAD.r)
    if (x - last < (props.big ? 60 : 34)) continue
    last = x; g.beginPath(); g.moveTo(x, PAD.t); g.lineTo(x, H - PAD.b); g.stroke()
    g.textAlign = 'center'; g.fillText(tickText(ax.value, v), x, H - PAD.b + (props.big ? 20 : 13))
  }
  last = 1e9
  for (const v of ay.value.ticks) {
    const y = H - PAD.b - tickPos(ay.value, v) * (H - PAD.t - PAD.b)
    if (last - y < (props.big ? 28 : 18)) continue
    last = y; g.beginPath(); g.moveTo(PAD.l, y); g.lineTo(W - PAD.r, y); g.stroke()
    g.textAlign = 'right'; g.fillText(tickText(ay.value, v), PAD.l - 5, y + 4)
  }
  g.strokeStyle = '#a39b8c'; g.strokeRect(PAD.l, PAD.t, W - PAD.l - PAD.r, H - PAD.t - PAD.b)
  g.fillStyle = '#1f1c17'; g.font = '700 ' + (props.big ? 20 : 12) + 'px system-ui, sans-serif'
  g.textAlign = 'right'; g.fillText(axisLabel(props.xk, props.named) + ' →', W - PAD.r, H - (props.big ? 10 : 6))
  g.textAlign = 'left'; g.fillText('↑ ' + axisLabel(props.yk, props.named), 4, props.big ? 20 : 11)
  const r = props.size
  g.globalAlpha = 0.7
  P.forEach((p, i) => { if (!p) return; g.fillStyle = props.colors?.[i] || '#a39b8c'; g.beginPath(); g.arc(p[0], p[1], r, 0, Math.PI * 2); g.fill() })
  g.globalAlpha = 1
  if (props.ring) { g.strokeStyle = '#c4553a'; g.lineWidth = 1.4; P.forEach((p, i) => { if (p && props.ring[i]) { g.beginPath(); g.arc(p[0], p[1], r + 2, 0, Math.PI * 2); g.stroke() } }) }
  if (props.selected >= 0 && P[props.selected]) { const p = P[props.selected]; g.strokeStyle = '#1f1c17'; g.lineWidth = 2.5; g.beginPath(); g.arc(p[0], p[1], 9, 0, Math.PI * 2); g.stroke() }
}
function redraw() { if (!raf) raf = requestAnimationFrame(draw) }
function resize() {
  if (!wrap.value || !cv.value) return
  W = wrap.value.clientWidth; H = props.height; dpr = window.devicePixelRatio || 1
  cv.value.width = W * dpr; cv.value.height = H * dpr; cv.value.style.width = W + 'px'; cv.value.style.height = H + 'px'
  redraw()
}
function click(e) {
  const b = cv.value.getBoundingClientRect(), x = e.clientX - b.left, y = e.clientY - b.top
  let best = -1, bd = 18 * 18
  PTS.forEach((p, i) => { if (!p) return; const d = (p[0] - x) ** 2 + (p[1] - y) ** 2; if (d < bd) { bd = d; best = i } })
  if (best >= 0) emit('pick', best)
}
let ro
onMounted(() => { ro = new ResizeObserver(resize); ro.observe(wrap.value); resize() })
onBeforeUnmount(() => { ro && ro.disconnect(); cancelAnimationFrame(raf) })
watch(() => [props.xk, props.yk, props.xyz, props.colors, props.ring, props.show, props.selected, props.height], () => { resize() })
</script>

<template>
  <div ref="wrap" class="xy" :class="{ big }">
    <canvas ref="cv" @click="click"></canvas>
    <div class="nt" v-if="ax?.isCount || ay?.isCount || ax?.useLog || ay?.useLog || hidden || (ax?.over || 0) + (ay?.over || 0)">
      <span v-if="ax?.isCount || ay?.isCount">次數是整數，同一格的人稍微散開畫，才不會疊成一點。</span>
      <span v-if="ax?.useLog || ay?.useLog">{{ [ax, ay].filter(a => a?.useLog).map(a => a.q.short).join('、') }}的刻度不是等距（越大的數字擠得越近）。</span>
      <span v-if="(ax?.over || 0) + (ay?.over || 0)">最大的 1% 畫在邊上。</span>
      <span v-if="hidden">{{ hidden }} 人少了其中一欄（沒填{{ [xk, yk].includes('debt') ? '，或月收入是 0、負債比算不出來' : '' }}），沒畫出來。</span>
    </div>
  </div>
</template>

<style scoped>
.xy { border: 1px solid var(--line); border-radius: 12px; background: #fff; overflow: hidden; }
canvas { display: block; touch-action: manipulation; }
.nt { font-size: 12px; color: var(--ink-2); padding: 4px 10px 8px; line-height: 1.5; }
.nt span { margin-right: 6px; }
.big .nt { font-size: 16px; }
</style>

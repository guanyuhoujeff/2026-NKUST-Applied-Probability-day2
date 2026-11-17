<script setup>
// 第 1 步：兩欄的散布圖＋PCA 那條線。t＝0 每個人在原位；t＝1 每個人被壓到線上（只剩 1 個分數）。
// resid：畫出每個人到線的距離（還原不回來的部分）。點一下選人。
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  pts: { type: Array, required: true },       // [[x, y], …]（標準化後）
  dir: { type: Array, required: true },       // 線的方向（單位向量）
  t: { type: Number, default: 0 },
  resid: { type: Boolean, default: false },
  labels: { type: Array, default: () => ['', ''] },
  colors: { type: Array, default: null },
  selected: { type: Number, default: -1 },
  height: { type: Number, default: 300 },
  size: { type: Number, default: 2.6 },
})
const emit = defineEmits(['pick'])
const cv = ref(null)
const wrap = ref(null)
let W = 300, H = props.height, dpr = 1, raf = 0
let bx = [-1, 1], by = [-1, 1]

function bounds() {
  const xs = props.pts.map(p => p[0]), ys = props.pts.map(p => p[1])
  bx = [Math.min(...xs), Math.max(...xs)]; by = [Math.min(...ys), Math.max(...ys)]
}
function sc() {     // 等比例：線和距離的角度才不會歪
  const pad = 28
  return Math.min((W - 2 * pad) / (bx[1] - bx[0]), (H - 2 * pad) / (by[1] - by[0]))
}
function toPx(x, y) {
  const s = sc()
  const cx = (bx[0] + bx[1]) / 2, cy = (by[0] + by[1]) / 2
  return [W / 2 + (x - cx) * s, H / 2 - (y - cy) * s]
}
function onLine(p) { const d = p[0] * props.dir[0] + p[1] * props.dir[1]; return [d * props.dir[0], d * props.dir[1]] }
function pos(p) { const q = onLine(p), t = props.t; return [p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t] }

function draw() {
  raf = 0
  const c = cv.value
  if (!c) return
  const g = c.getContext('2d')
  g.setTransform(dpr, 0, 0, dpr, 0, 0)
  g.clearRect(0, 0, W, H)
  // 軸（0 在平均）
  g.strokeStyle = '#d8d0c0'; g.lineWidth = 1
  let a = toPx(bx[0], 0), b = toPx(bx[1], 0)
  g.beginPath(); g.moveTo(a[0], a[1]); g.lineTo(b[0], b[1]); g.stroke()
  a = toPx(0, by[0]); b = toPx(0, by[1])
  g.beginPath(); g.moveTo(a[0], a[1]); g.lineTo(b[0], b[1]); g.stroke()
  g.fillStyle = '#4f493f'; g.font = '600 12px system-ui, sans-serif'
  const xe = toPx(bx[1], 0), ye = toPx(0, by[1])
  g.textAlign = 'right'; g.fillText(props.labels[0] + ' →', Math.min(W - 6, xe[0]), xe[1] - 6)
  g.textAlign = 'left'; g.fillText('↑ ' + props.labels[1], ye[0] + 6, Math.max(14, ye[1] + 4))
  // 到線的距離
  if (props.resid) {
    g.strokeStyle = 'rgba(196,85,58,.35)'; g.lineWidth = 1
    g.beginPath()
    for (const p of props.pts) {
      const q = pos(p), l = onLine(p)
      const A = toPx(q[0], q[1]), B = toPx(l[0], l[1])
      g.moveTo(A[0], A[1]); g.lineTo(B[0], B[1])
    }
    g.stroke()
  }
  // 點
  const r = props.size
  props.pts.forEach((p, i) => {
    const q = pos(p), [x, y] = toPx(q[0], q[1])
    g.globalAlpha = 0.6
    g.fillStyle = props.colors?.[i] || '#6f675a'
    g.fillRect(x - r / 2, y - r / 2, r, r)
  })
  g.globalAlpha = 1
  // 線
  const L = Math.max(bx[1] - bx[0], by[1] - by[0])
  a = toPx(-L * props.dir[0], -L * props.dir[1]); b = toPx(L * props.dir[0], L * props.dir[1])
  g.save(); g.beginPath(); g.rect(0, 0, W, H); g.clip()
  g.strokeStyle = '#1f8a8a'; g.lineWidth = 2.5
  g.beginPath(); g.moveTo(a[0], a[1]); g.lineTo(b[0], b[1]); g.stroke()
  g.restore()
  // 選到的人：原位、線上的位置、兩者之間的距離
  if (props.selected >= 0) {
    const p = props.pts[props.selected], l = onLine(p)
    const A = toPx(p[0], p[1]), B = toPx(l[0], l[1])
    g.strokeStyle = '#c4553a'; g.lineWidth = 2.5; g.setLineDash([5, 4])
    g.beginPath(); g.moveTo(A[0], A[1]); g.lineTo(B[0], B[1]); g.stroke(); g.setLineDash([])
    g.strokeStyle = '#1f1c17'; g.lineWidth = 2.5
    g.beginPath(); g.arc(A[0], A[1], 8, 0, Math.PI * 2); g.stroke()
    g.fillStyle = '#c4553a'; g.beginPath(); g.arc(B[0], B[1], 5, 0, Math.PI * 2); g.fill()
  }
}
function redraw() { if (!raf) raf = requestAnimationFrame(draw) }
function resize() {
  if (!wrap.value || !cv.value) return
  W = wrap.value.clientWidth; H = props.height; dpr = window.devicePixelRatio || 1
  cv.value.width = W * dpr; cv.value.height = H * dpr
  cv.value.style.width = W + 'px'; cv.value.style.height = H + 'px'
  redraw()
}
function pick(e) {
  const rect = cv.value.getBoundingClientRect()
  const x = e.clientX - rect.left, y = e.clientY - rect.top
  let best = -1, bd = 24 * 24
  props.pts.forEach((p, i) => {
    const q = pos(p), [px, py] = toPx(q[0], q[1])
    const d = (px - x) ** 2 + (py - y) ** 2
    if (d < bd) { bd = d; best = i }
  })
  if (best >= 0) emit('pick', best)
}
watch(() => props.pts, () => { bounds(); redraw() })
watch(() => [props.t, props.resid, props.selected, props.colors], redraw)
let ro
onMounted(() => { bounds(); resize(); ro = new ResizeObserver(resize); ro.observe(wrap.value) })
onBeforeUnmount(() => { ro && ro.disconnect(); raf && cancelAnimationFrame(raf) })
</script>

<template>
  <div ref="wrap" class="s2d"><canvas ref="cv" @click="pick"></canvas></div>
</template>

<style scoped>
.s2d { width: 100%; background: #fbf8f2; border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }
canvas { display: block; }
</style>

<script setup>
// 3D 散布圖（canvas 自己畫，不靠外部套件）：單指拖曳旋轉、雙指縮放、點一下看那個人。
// 顏色：colors[i] 是 CSS 顏色字串；ring[i] 為 true 的點外加紅框（例如違約者）；front 的點最後畫（不被蓋住）。
import { ref, watch, onMounted, onBeforeUnmount, computed } from 'vue'

const props = defineProps({
  xyz: { type: Array, required: true },
  colors: { type: Array, default: null },
  ring: { type: Array, default: null },
  front: { type: Array, default: null },     // bool 陣列
  axes: { type: Array, default: () => ['PC1', 'PC2', 'PC3'] },
  height: { type: Number, default: 320 },
  selected: { type: Number, default: -1 },
  size: { type: Number, default: 2.4 },
  show: { type: Array, default: null },      // bool 陣列：false 的人不畫、也點不到（例如只看某一群）
  flat: Boolean,          // 一開始從正面看前兩個軸（像平面圖）；仍然可以拖動轉成立體
})
const emit = defineEmits(['pick'])

const cv = ref(null)
const wrap = ref(null)
let yaw = props.flat ? 0 : -0.7, pitch = props.flat ? 0 : 0.35, zoom = 1
let W = 300, H = props.height, dpr = 1
let raf = 0

const maxAbs = computed(() => {
  let m = 1e-9
  for (const p of props.xyz) for (const v of p) if (Math.abs(v) > m) m = Math.abs(v)
  return m
})

function proj(p, s) {
  const cy = Math.cos(yaw), sy = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch)
  const x1 = p[0] * cy - p[2] * sy
  const z1 = p[0] * sy + p[2] * cy
  const y2 = p[1] * cp - z1 * sp
  const z2 = p[1] * sp + z1 * cp
  return [W / 2 + x1 * s, H / 2 - y2 * s, z2]
}

function scale() { return 0.4 * Math.min(W, H) / maxAbs.value * zoom }

function draw() {
  raf = 0
  const c = cv.value
  if (!c) return
  const g = c.getContext('2d')
  g.setTransform(dpr, 0, 0, dpr, 0, 0)
  g.clearRect(0, 0, W, H)
  const s = scale()
  const L = maxAbs.value
  // 座標軸
  g.lineWidth = 1
  g.font = '600 13px system-ui, sans-serif'
  const ends = [[[-L, 0, 0], [L, 0, 0]], [[0, -L, 0], [0, L, 0]], [[0, 0, -L], [0, 0, L]]]
  ends.forEach(([a, b], i) => {
    const pa = proj(a, s), pb = proj(b, s)
    g.strokeStyle = '#b9b0a0'
    g.beginPath(); g.moveTo(pa[0], pa[1]); g.lineTo(pb[0], pb[1]); g.stroke()
    g.fillStyle = '#4f493f'
    g.fillText(props.axes[i] || '', pb[0] + 4, pb[1] - 4)
  })
  // 點：遠的先畫；front 的最後畫
  const n = props.xyz.length
  const P = new Array(n)
  for (let i = 0; i < n; i++) P[i] = proj(props.xyz[i], s)
  const order = [...Array(n).keys()].sort((a, b) => {
    const fa = props.front?.[a] ? 1 : 0, fb = props.front?.[b] ? 1 : 0
    return fa - fb || P[a][2] - P[b][2]
  })
  const r = props.size
  for (const i of order) {
    if (props.show && !props.show[i]) continue
    const [x, y] = P[i]
    const big = props.front?.[i] ? r * 1.5 : r
    g.fillStyle = props.colors?.[i] || '#a39b8c'
    g.globalAlpha = props.front && !props.front[i] ? 0.55 : 0.9
    g.fillRect(x - big / 2, y - big / 2, big, big)
    if (props.ring?.[i]) {
      g.globalAlpha = 1
      g.strokeStyle = '#c4553a'; g.lineWidth = 1.4
      g.strokeRect(x - big / 2 - 1.5, y - big / 2 - 1.5, big + 3, big + 3)
    }
  }
  g.globalAlpha = 1
  if (props.selected >= 0 && props.selected < n && (!props.show || props.show[props.selected])) {
    const [x, y] = P[props.selected]
    g.strokeStyle = '#1f1c17'; g.lineWidth = 2.5
    g.beginPath(); g.arc(x, y, 9, 0, Math.PI * 2); g.stroke()
  }
}

function redraw() { if (!raf) raf = requestAnimationFrame(draw) }

function resize() {
  if (!wrap.value || !cv.value) return
  W = wrap.value.clientWidth
  H = props.height
  dpr = window.devicePixelRatio || 1
  cv.value.width = W * dpr
  cv.value.height = H * dpr
  cv.value.style.width = W + 'px'
  cv.value.style.height = H + 'px'
  redraw()
}

// 觸控：一指轉、兩指縮放、點一下選人
const pts = new Map()
let moved = 0, pinch0 = 0, zoom0 = 1
function down(e) {
  cv.value.setPointerCapture(e.pointerId)
  pts.set(e.pointerId, [e.clientX, e.clientY])
  moved = 0
  if (pts.size === 2) { const [a, b] = [...pts.values()]; pinch0 = Math.hypot(a[0] - b[0], a[1] - b[1]); zoom0 = zoom }
}
function move(e) {
  if (!pts.has(e.pointerId)) return
  const [px, py] = pts.get(e.pointerId)
  const dx = e.clientX - px, dy = e.clientY - py
  pts.set(e.pointerId, [e.clientX, e.clientY])
  moved += Math.abs(dx) + Math.abs(dy)
  if (pts.size === 1) {
    yaw += dx * 0.01
    pitch = Math.max(-1.5, Math.min(1.5, pitch + dy * 0.01))
  } else if (pts.size === 2 && pinch0) {
    const [a, b] = [...pts.values()]
    zoom = Math.max(0.4, Math.min(8, zoom0 * Math.hypot(a[0] - b[0], a[1] - b[1]) / pinch0))
  }
  redraw()
}
function up(e) {
  const single = pts.size === 1
  pts.delete(e.pointerId)
  if (pts.size < 2) pinch0 = 0
  if (single && moved < 8) pick(e)
}
function pick(e) {
  const rect = cv.value.getBoundingClientRect()
  const x = e.clientX - rect.left, y = e.clientY - rect.top
  const s = scale()
  let best = -1, bd = 24 * 24
  props.xyz.forEach((p, i) => {
    if (props.show && !props.show[i]) return
    const [px, py] = proj(p, s)
    const d = (px - x) ** 2 + (py - y) ** 2
    if (d < bd) { bd = d; best = i }
  })
  if (best >= 0) emit('pick', best)
}
function wheel(e) { e.preventDefault(); zoom = Math.max(0.4, Math.min(8, zoom * (e.deltaY < 0 ? 1.15 : 1 / 1.15))); redraw() }
function zoomBy(f) { zoom = Math.max(0.4, Math.min(8, zoom * f)); redraw() }
function reset() { yaw = -0.7; pitch = 0.35; zoom = 1; redraw() }
function view(which) {     // 正面看某兩個軸
  if (which === 12) { yaw = 0; pitch = 0 }
  if (which === 13) { yaw = 0; pitch = Math.PI / 2 - 0.0001 }
  if (which === 23) { yaw = -Math.PI / 2; pitch = 0 }
  zoom = 1; redraw()
}

watch(() => [props.xyz, props.colors, props.ring, props.front, props.selected, props.show], redraw)
let ro
onMounted(() => {
  resize()
  ro = new ResizeObserver(resize)
  ro.observe(wrap.value)
})
onBeforeUnmount(() => { ro && ro.disconnect(); raf && cancelAnimationFrame(raf) })
</script>

<template>
  <div ref="wrap" class="s3d">
    <canvas ref="cv" @pointerdown="down" @pointermove="move" @pointerup="up" @pointercancel="up" @wheel="wheel"></canvas>
    <div class="tools">
      <button @click="reset">重設</button>
      <button @click="view(12)">{{ axes[0] }}×{{ axes[1] }}</button>
      <button @click="view(13)">{{ axes[0] }}×{{ axes[2] }}</button>
      <button @click="zoomBy(1.4)">＋</button>
      <button @click="zoomBy(1 / 1.4)">－</button>
    </div>
  </div>
</template>

<style scoped>
.s3d { position: relative; width: 100%; background: #fbf8f2; border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }
canvas { display: block; touch-action: none; }
.tools { display: flex; gap: 6px; padding: 6px; flex-wrap: wrap; border-top: 1px solid var(--line); }
.tools button { font-size: 13px; padding: 6px 10px; border-radius: 8px; border: 1px solid var(--line); background: #fff; color: var(--ink); }
</style>

// 把一個欄位（或一個 PCA 分數）變成畫圖用的座標軸：取值、範圍、刻度、0–1 的位置。
// 次數類（0、1、2…）在格子裡稍微散開；偏很多的欄位用對數刻度；最大的 1% 畫在邊上；沒填的回傳 null。
import { store } from './shared.js'

const LATE = ['late30', 'late60', 'late90']
export const PC_KEYS = ['pc1', 'pc2', 'pc3']
export const isPc = key => PC_KEYS.includes(key)
// named＝true：PCA 的分數後面加上名字（只有「10 欄全用」那一份 PCA 才適用；自己挑欄位重算的 PCA 不能用）
export const pcName = key => store.meta.cluster?.pc_axes?.[PC_KEYS.indexOf(key)] || null
export const axisLabel = (key, named = false) => (isPc(key)
  ? key.toUpperCase() + (named && pcName(key) ? '：' + pcName(key).short : '')
  : store.meta.questions[store.meta.keys.indexOf(key)].short)

export function valuesOf(key, xyz) {
  if (isPc(key)) { const n = PC_KEYS.indexOf(key); return (xyz || []).map(p => p[n]) }
  const j = store.meta.keys.indexOf(key), ji = store.meta.keys.indexOf('income')
  return store.people.map(r => {
    const v = r[j]
    if (v === null || v === undefined || (LATE.includes(key) && v >= 96)) return null
    // 月收入沒填或是 0 的人，負債比那欄其實是金額，不能跟比例畫在一起
    if (key === 'debt' && (r[ji] === null || r[ji] === undefined || r[ji] < 1)) return null
    return v
  })
}

export function axisInfo(key, vals, mask) {
  const pc = isPc(key)
  const q = pc ? { kind: 'pc', short: key.toUpperCase() } : store.meta.questions[store.meta.keys.indexOf(key)]
  const isCount = q.kind === 'count'
  const useLog = !pc && !isCount && (store.meta.log_keys || []).includes(key)
  const f = v => (useLog ? Math.log1p(v) : v)
  const ok = vals.filter((v, i) => mask[i]).sort((a, b) => a - b)
  const lo = ok[0] ?? 0
  const hi = pc ? (ok[ok.length - 1] ?? 1) : Math.max(ok[Math.floor(ok.length * 0.99)] ?? 1, lo + (isCount ? 1 : 1e-9))
  let ticks = []
  if (isCount) { const step = Math.max(1, Math.ceil((hi - lo) / 6)); for (let v = Math.ceil(lo); v <= hi; v += step) ticks.push(v) }
  else if (useLog) {
    const cand = [0]
    for (let e = -2; e <= 6; e++) for (const m of [1, 2, 5]) cand.push(m * 10 ** e)
    ticks = cand.filter(v => v >= lo - 1e-9 && v <= hi + 1e-9)
  } else { const step = [1, 2, 5, 10, 20, 50].find(s => (hi - lo) / s <= 6) || 100; for (let v = Math.ceil(lo / step) * step; v <= hi; v += step) ticks.push(v) }
  const a = { key, q, pc, isCount, useLog, f, vals, lo, hi, ticks, over: pc ? 0 : ok.filter(v => v > hi).length }
  a.flo = f(isCount ? lo - 0.5 : lo); a.fhi = f(isCount ? hi + 0.5 : hi)
  return a
}

const jit = (i, salt) => { const x = Math.sin(i * 12.9898 + salt * 78.233) * 43758.5453; return x - Math.floor(x) - 0.5 }   // 固定的抖動，重畫不會跳
export const tickPos = (a, v) => (a.f(v) - a.flo) / ((a.fhi - a.flo) || 1)
export function unitPos(a, v, i, salt) {
  let u = Math.min(v, a.hi)
  if (a.isCount) u += jit(i, salt) * 0.7; else u = Math.max(u, a.lo)
  return (a.f(u) - a.flo) / ((a.fhi - a.flo) || 1)
}
export function tickText(a, v) {
  if (a.q.kind === 'pct') return Math.round(v * 100) + '%'
  if (a.q.kind === 'money') return v >= 1000 ? (v / 1000) + '千' : String(v)
  return String(v)
}
// 幾個欄位一起：每個人是否每一軸都有值，以及各軸的資訊
export function buildAxes(keys, xyz) {
  const vals = keys.map(k => valuesOf(k, xyz))
  const n = vals[0]?.length || 0
  const mask = Array.from({ length: n }, (_, i) => vals.every(v => v[i] !== null && v[i] !== undefined))
  return { mask, axes: keys.map((k, j) => axisInfo(k, vals[j], mask)) }
}

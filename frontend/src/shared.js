// 學生端與老師端共用：抓資料、格式化、顏色、WebSocket 狀態。
import { reactive } from 'vue'

export const COLORS = {
  gray: '#a39b8c', red: '#c4553a', amber: '#d08a1e', ink: '#1f1c17', teal: '#1f8a8a',
  cluster: ['#1f8a8a', '#d08a1e', '#6a4c93', '#c4553a', '#3b6fb6', '#5c8a2e', '#b04a8f', '#6b6257'],
}

// 老師頁密碼：只有老師頁會設；帶在每個請求的標頭裡。學生頁沒有，所以不會送。
const KEY_NAME = 'day2-teacher-key'
export const teacher = reactive({ key: '', denied: false })
try { teacher.key = localStorage.getItem(KEY_NAME) || '' } catch (e) { /* 存不了就每次重新輸入 */ }
export function setTeacherKey(k) { teacher.key = k; teacher.denied = false; try { localStorage.setItem(KEY_NAME, k) } catch (e) { /* 同上 */ } }
const auth = () => (teacher.key ? { 'X-Teacher-Key': teacher.key } : {})
async function parse(r) {
  if (r.status === 401) { teacher.denied = true; return { error: '需要老師頁密碼' } }
  return r.json()
}

export async function getJSON(path) {
  return parse(await fetch(path, { headers: auth() }))
}

export async function postJSON(path, body) {
  return parse(await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json', ...auth() }, body: body ? JSON.stringify(body) : undefined }))
}

export const fmtN = n => (n ?? 0).toLocaleString('zh-Hant')

// 原始值寫成畫面上的字（同後端 features.fmt_value）
export function fmtValue(q, v) {
  if (v === null || v === undefined || Number.isNaN(v)) return '沒填'
  if (q.kind === 'pct') return Math.round(v * 100).toLocaleString('zh-Hant') + '%'
  if (q.kind === 'money') return Math.round(v).toLocaleString('zh-Hant')
  if (q.kind === 'age') return Math.round(v) + ' 歲'
  if ((q.key === 'late30' || q.key === 'late60' || q.key === 'late90') && (v === 96 || v === 98)) return `${v}（代碼）`
  return Math.round(v) + ' ' + q.unit
}

// 手機記住的小東西（暱稱、打到一半的名字）。存不了（無痕模式等）就算了，畫面照常。
export function remember(key, val) { try { val ? localStorage.setItem(key, val) : localStorage.removeItem(key) } catch (e) { /* 存不了就不存 */ } }
export function recall(key) { try { return localStorage.getItem(key) || '' } catch (e) { return '' } }
// 取名打到一半的字：老師切步時取名卡會收起來，回來要還在。清除時一起清。
export const drafts = reactive({})

export const colsParam = keys => encodeURIComponent(keys.join(','))

// 全站狀態：meta、老師控制的狀態、投票、違約標記
export const store = reactive({
  meta: null, state: null, votes: null, labels: null, people: null, cleared: 0,
  epoch: null,      // 伺服器這一輪的代號；老師清除或伺服器重啟就會換。手機斷線時錯過「清除」，重連後靠它發現
})

export async function loadLabels() {
  const r = await getJSON('/api/labels')
  store.labels = r.labels || null
}

export function connectWS(role, extra = {}) {
  const url = (location.protocol === 'https:' ? 'wss' : 'ws') + '://' + location.host + '/ws'
  const ws = new WebSocket(url)
  ws.onopen = async () => {       // 手機鎖屏再打開：斷線期間老師可能換了題，重抓一次
    if (role === 'teacher') ws.send(JSON.stringify({ type: 'auth', key: teacher.key }))
    store.votes = await getJSON('/api/votes')
    extra.onopen && extra.onopen()
  }
  ws.onmessage = e => {
    const m = JSON.parse(e.data)
    if (m.type === 'state') {
      if (m.epoch && store.epoch && m.epoch !== store.epoch) store.cleared++
      if (m.epoch) store.epoch = m.epoch
      const was = store.state?.labels
      store.state = m
      if (m.labels && !was) loadLabels()
      if (!m.labels) store.labels = null
    }
    if (m.type === 'votes') store.votes = m
    if (m.type === 'labels') store.labels = m.labels
    if (m.type === 'cleared') store.cleared++
    extra.onmessage && extra.onmessage(m)
  }
  ws.onclose = () => setTimeout(() => connectWS(role, extra), 2000)
  return ws
}

export async function loadMeta() {
  store.meta = await getJSON('/api/meta')
  const { phase, labels, vote_idx, vote_revealed, reveal, name_ref, step, n_submitted, closed, epoch } = store.meta
  store.state = { phase, labels, vote_idx, vote_revealed, reveal, name_ref, step, n_submitted, closed, epoch }
  store.epoch = epoch || null
  if (labels) await loadLabels()
  store.people = (await getJSON('/api/people')).rows
}

// 每段的步驟（學生頁的分頁）。老師頁切到哪一步，學生手機跟著跳；學生也可以自己切。
export const STEP_NAMES = {
  pca: ['壓到線上', '壓成幾個', '量什麼', '違約在哪'],
  cluster: ['分成幾群', '長相、先猜', '揭曉'],
  anomaly: ['規則、先猜', '抓異常', '揭曉'],
}

export const SEG_NAMES = { pca: 'PCA 主成分', cluster: '分群', anomaly: '異常偵測' }

// 抓異常比賽的路線，寫成一句話（學生頁的紀錄、排行榜、老師頁共用）
export function routeText(r) {
  const a = []
  if (r.pca_k) a.push(`PCA 留 ${r.pca_k} 個分數`)
  if (r.k) a.push(`${r.method === 'gmm' ? 'GMM' : 'K-means'} 分 ${r.k} 群，人數最少的那群當異常`)
  else a.push('標最異常的 10%')
  return a.join(' → ')
}

<script setup>
// 學生手機端：老師切到哪一段就看哪一段；之前的段落可以回看。投票卡跟著老師目前的題目。
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { store, getJSON, loadMeta, connectWS, SEG_NAMES, remember, recall, drafts } from './shared.js'
import PcaSeg from './segments/PcaSeg.vue'
import ClusterSeg from './segments/ClusterSeg.vue'
import AnomalySeg from './segments/AnomalySeg.vue'

const SEGS = ['pca', 'cluster', 'anomaly']
const NICK = 'day2-nick'
const nickname = ref(recall(NICK).slice(0, 20))      // 手機記住暱稱：重新整理後不用重填，投過的票、交過的那一組也跟著回來
watch(nickname, n => remember(NICK, n.trim()))
const view = ref(null)               // 學生正在看的段；null＝跟著老師
const myVotes = reactive({})
const myNames = reactive({ pca: {} })
const submitted = ref(null)

const live = computed(() => (store.state?.phase === 'closed' ? 'anomaly' : store.state?.phase) || 'pca')
const shown = computed(() => view.value || live.value)
const reachable = computed(() => SEGS.slice(0, SEGS.indexOf(live.value) + 1))

watch(live, () => { view.value = null; window.scrollTo(0, 0) })
watch(() => store.cleared, () => {
  for (const k of Object.keys(myVotes)) delete myVotes[k]
  myNames.pca = {}; submitted.value = null
  for (const d of Object.values(drafts)) for (const k of Object.keys(d)) d[k] = ''
})

async function syncMe() {
  const nick = nickname.value.trim()
  let r = { votes: {}, names: {}, submitted: null }
  if (nick) { try { r = await getJSON('/api/me?nickname=' + encodeURIComponent(nick)) } catch (e) { return } }
  if (r.error || !r.votes) return
  for (const k of Object.keys(myVotes)) delete myVotes[k]      // 換了暱稱、或斷線時錯過清除：舊的票不能留在畫面上
  Object.assign(myVotes, r.votes)
  myNames.pca = r.names.pca || {}
  submitted.value = r.submitted
}

onMounted(async () => {
  await loadMeta()
  connectWS('student', { onopen: syncMe })
})
</script>

<template>
  <header class="top">
    <div class="kicker">應用機率・第二天</div>
    <h1>不看答案，<span class="red">也找得到規律</span></h1>
  </header>

  <main v-if="store.meta && store.state" class="page">
    <section class="card nick">
      <label>暱稱</label>
      <input v-model="nickname" maxlength="20" placeholder="例如：小明" @change="syncMe" />
    </section>

    <nav class="tabs">
      <button v-for="s in SEGS" :key="s" :disabled="!reachable.includes(s)" :class="{ on: shown === s, live: live === s }"
        @click="view = s === live ? null : s">{{ SEG_NAMES[s] }}</button>
    </nav>
    <div v-if="view && view !== live" class="back muted small">在看之前的段落。<button @click="view = null">回到老師這一段</button></div>

    <!-- 投票卡放在各段自己的分頁裡（PCA 第 4 步、分群「哪群違約」、異常偵測「規則」） -->

    <PcaSeg v-if="shown === 'pca'" :nickname="nickname" :my-names="myNames.pca" :my-votes="myVotes" @voted="(q, c) => (myVotes[q] = c)" />
    <ClusterSeg v-else-if="shown === 'cluster'" :nickname="nickname" :my-votes="myVotes" @voted="(q, c) => (myVotes[q] = c)" />
    <AnomalySeg v-else :nickname="nickname" :submitted="submitted" :my-votes="myVotes" @submitted="c => (submitted = c)" @voted="(q, c) => (myVotes[q] = c)" />
  </main>
  <main v-else class="page muted">載入中…</main>
</template>

<style scoped>
.top { background: var(--ink); color: var(--paper); padding: 18px 16px 16px; }
.kicker { font-size: 13px; letter-spacing: .08em; color: #cfc7b6; font-weight: 700; }
h1 { margin: 6px 0 0; font-size: 24px; line-height: 1.3; }
.page { padding: 14px 14px 60px; display: flex; flex-direction: column; gap: 12px; max-width: 560px; margin: 0 auto; }
label { display: block; font-size: 13px; color: var(--ink-2); margin-bottom: 4px; }
input { width: 100%; font-size: 18px; padding: 12px; border: 1px solid var(--line); border-radius: 12px; background: #fff; }
.tabs { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; position: sticky; top: 0; z-index: 5; background: var(--paper); padding: 6px 0; }
.tabs button { font-size: 15px; font-weight: 800; padding: 10px 4px; border-radius: 10px; border: 2px solid var(--line); background: #fff; color: var(--ink-2); }
.tabs button.on { border-color: var(--ink); background: var(--ink); color: #fff; }
.tabs button.live:not(.on) { border-color: var(--red); color: var(--red); }
.tabs button:disabled { opacity: .35; }
.back button { margin-left: 6px; font-size: 13px; padding: 4px 10px; border-radius: 8px; border: 1px solid var(--line); background: #fff; }
.small { font-size: 13px; }
</style>

<script setup>
// 投票：老師頁切題、揭曉；可以改選。揭曉後、或答案露出來過（locked），就不能投。
import { ref, computed, watch } from 'vue'
import { store, postJSON } from '../shared.js'
const props = defineProps({ nickname: String, mine: Object })
const emit = defineEmits(['voted'])
const msg = ref('')
const v = computed(() => store.votes)
const q = computed(() => v.value?.question)
watch(() => v.value?.idx, () => { msg.value = '' })
async function vote(id) {
  if (!props.nickname?.trim()) { msg.value = '先在最上面填暱稱'; return }
  let r
  try { r = await postJSON('/api/vote', { nickname: props.nickname, qid: q.value.id, choice: id }) } catch (e) { msg.value = '連不上伺服器，沒有送出。等一下再按一次'; return }
  if (r.error) { msg.value = r.error; return }
  emit('voted', q.value.id, id)
  msg.value = '已送出，可以改選；等老師揭曉'
}
</script>

<template>
  <section v-if="q" class="card">
    <div class="muted small">投票</div>
    <div class="qt">{{ q.question }}</div>
    <div class="opts">
      <button v-for="o in q.options" :key="o.id" class="opt" :disabled="!!v.answer || v.locked"
        :class="{ on: mine?.[q.id] === o.id, win: v.answer?.answer_id === o.id }" @click="vote(o.id)">{{ o.text }}</button>
    </div>
    <template v-if="v.answer">
      <div class="ans">{{ v.answer.answer_text }}</div>
      <div class="verdict" v-if="mine?.[q.id]">{{ mine[q.id] === v.answer.answer_id ? '猜對了' : '猜錯了' }}</div>
    </template>
    <div v-else-if="v.locked" class="muted small">已經停止投票，等老師揭曉答案。</div>
    <div v-else-if="msg" class="muted small">{{ msg }}</div>
  </section>
</template>

<style scoped>
.qt { font-weight: 900; font-size: 18px; margin: 4px 0 10px; }
.opts { display: grid; gap: 8px; }
.opt { font-size: 18px; font-weight: 800; padding: 14px; border-radius: 12px; border: 2px solid var(--line); background: #fff; color: var(--ink); text-align: left; }
.opt.on { border-color: var(--red); background: var(--red-soft); color: var(--red); }
.opt.win { outline: 3px solid var(--ink); }
.opt:disabled { opacity: 1; }
.ans { margin-top: 10px; font-weight: 700; }
.verdict { font-size: 20px; font-weight: 900; text-align: center; margin-top: 6px; }
.small { font-size: 13px; }
</style>

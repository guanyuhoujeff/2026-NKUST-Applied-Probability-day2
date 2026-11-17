<script setup>
// 取名字：PCA 的 PC1、PC2，或分群的每一群。可以重送（以最後一次為準）。
import { ref, watch } from 'vue'
import { store, postJSON, drafts } from '../shared.js'
import RefNames from './RefNames.vue'
const props = defineProps({ seg: String, slots: Array, nickname: String, mine: Object, hint: String, colors: Array, title: String, why: String })
if (!drafts[props.seg]) drafts[props.seg] = {}
const vals = drafts[props.seg]      // 放在共用的地方：老師切步、卡片收起來再回來，打到一半的字還在
const msg = ref('')
watch(() => props.mine, m => { for (const s of props.slots) vals[s] = vals[s] || m?.[s] || '' }, { immediate: true })
async function send() {
  if (!props.nickname?.trim()) { msg.value = '先在最上面填暱稱'; return }
  let r
  try { r = await postJSON('/api/name', { nickname: props.nickname, seg: props.seg, names: { ...vals } }) } catch (e) { msg.value = '連不上伺服器，沒有送出。等一下再按一次'; return }
  msg.value = r.error || '已送出，老師的大螢幕看得到；可以改了再送'
}
</script>

<template>
  <section class="card">
    <div class="qt">{{ title || '幫它取個名字' }}</div>
    <div class="why" v-if="why">{{ why }}</div>
    <div class="muted small" v-if="hint">{{ hint }}</div>
    <div v-for="(s, i) in slots" :key="s" class="row">
      <span class="lab" :style="colors ? { color: colors[i] } : {}">{{ s }}</span>
      <input v-model="vals[s]" :maxlength="store.meta.name_max" placeholder="一句白話，12 個字以內" />
    </div>
    <button class="go" @click="send">送出名字</button>
    <div class="muted small" v-if="msg">{{ msg }}</div>
    <RefNames :seg="seg" :colors="colors" />
  </section>
</template>

<style scoped>
.qt { font-weight: 900; font-size: 18px; margin-bottom: 6px; }
.why { font-size: 15px; line-height: 1.6; margin-bottom: 4px; }
.row { display: grid; grid-template-columns: 70px 1fr; gap: 8px; align-items: center; margin-top: 8px; }
.lab { font-weight: 900; }
input { font-size: 17px; padding: 10px; border: 1px solid var(--line); border-radius: 10px; width: 100%; }
.go { width: 100%; margin-top: 12px; font-size: 18px; font-weight: 900; padding: 12px; border: 0; border-radius: 12px; background: var(--ink); color: #fff; }
.small { font-size: 13px; margin-top: 6px; }
</style>

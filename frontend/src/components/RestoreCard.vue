<script setup>
// 第 2 步：點到的那個人。原本的十欄 vs 用前 k 個分數還原的十欄。
import { ref, watch, computed } from 'vue'
import { store, getJSON, fmtValue } from '../shared.js'
import Help from './Help.vue'
const props = defineProps({ i: { type: Number, required: true }, k: { type: Number, required: true }, big: Boolean, loadings: Array })
const f2 = v => (v < 0 ? '−' : '') + Math.abs(v).toFixed(2)
const par = v => (v < 0 ? `（${f2(v)}）` : f2(v))
const q0 = computed(() => store.meta.questions[0])
// 舉例用第一欄：前幾個分數各乘上自己在這一欄的權重（系統只給前 3 個分數的權重）
const terms = computed(() => (res.value?.scores || []).slice(0, Math.min(props.k, props.loadings?.length || 0)).map((s, j) => [s, props.loadings[j][q0.value.key]]))
const emit = defineEmits(['close'])
const res = ref(null)
const row = computed(() => store.people?.[props.i] || [])
const lab = computed(() => store.labels?.[props.i])
watch(() => [props.i, props.k], async () => {
  const i = props.i, k = props.k
  const r = await getJSON(`/api/pca/person?i=${i}&k=${k}`)
  if (i === props.i && k === props.k) res.value = r      // 拉滑桿時每格各送一次：只收最後那一格的
}, { immediate: true })
</script>

<template>
  <div class="pc" :class="{ big }">
    <div class="h">
      <b>這個人</b>
      <Help v-if="res && !res.error" title="10 欄的分數和還原怎麼算？">
        <p><b>① 標準化</b>：10 欄各自換成「離平均幾個標準差」，叫 z₁ … z₁₀。</p>
        <p><b>② 算分數</b>：10 個 z 各乘一個權重，再相加。權重就是第 3 步的長條。</p>
        <div class="f">PC1 分數 ＝ w₁ × z₁ ＋ w₂ × z₂ ＋ … ＋ w₁₀ × z₁₀</div>
        <p>這個人的前 {{ k }} 個分數：</p>
        <p class="n">{{ res.scores.map((s, j) => `PC${j + 1} ${f2(s)}`).join('、') }}</p>
        <p><b>③ 還原</b>：只靠這 {{ k }} 個分數，猜回每一欄。</p>
        <div class="f">猜回來的 z ＝ 每個分數 × 它在這一欄的權重，再加起來</div>
        <template v-if="terms.length">
          <p>以「{{ q0.short }}」為例{{ k > terms.length ? `（只列前 ${terms.length} 項）` : '' }}：</p>
          <p class="n">{{ terms.map(([s, w], j) => `${j ? par(s) : f2(s)} × ${par(w)}`).join(' ＋ ') }}{{ k > terms.length ? ' ＋ …' : ` ＝ ${f2(terms.reduce((a, [s, w]) => a + s * w, 0))}` }}</p>
        </template>
        <p><b>④ 換回原本的單位</b>，就是表格右邊那一欄。</p>
        <p class="muted">分數用得越多，猜得越準；10 個全用，就跟原本一樣（沒填的欄除外）。</p>
      </Help>
      <span v-if="lab === 1" class="tag red">後來違約</span>
      <span v-else-if="lab === 0" class="tag">沒違約</span>
      <button class="x" @click="emit('close')">✕</button>
    </div>
    <div class="sc" v-if="res && !res.error">{{ k }} 個分數：{{ res.scores.map((s, j) => `PC${j + 1} ${s > 0 ? '+' : ''}${s}`).join('　') }}</div>
    <div class="grid">
      <span></span><span class="th">原本</span><span class="th">只記 {{ k }} 個分數，猜回來的值</span>
      <template v-for="(q, j) in store.meta.questions" :key="q.key">
        <span class="k">{{ q.short }}</span>
        <span class="v">{{ fmtValue(q, row[j]) }}</span>
        <span class="v rs">{{ res && !res.error ? fmtValue(q, res.restored[j]) : '' }}</span>
      </template>
    </div>
    <div class="muted small">沒填的欄先補全班的中位數，所以也猜得出數字。
      負債比、月收入、額度使用率這幾欄的數字範圍很大，猜回來可能差好幾倍。</div>
  </div>
</template>

<style scoped>
.pc { border: 2px solid var(--ink); border-radius: 12px; padding: 10px 12px; margin-top: 8px; background: #fff; }
.h { display: flex; align-items: center; gap: 8px; }
.tag { font-size: 12px; padding: 2px 8px; border-radius: 999px; background: var(--paper-2); }
.tag.red { background: var(--red-soft); color: var(--red); font-weight: 700; }
.x { margin-left: auto; border: 0; background: none; font-size: 18px; }
.sc { font-size: 13px; margin: 4px 0; color: var(--ink-2); font-variant-numeric: tabular-nums; }
.grid { display: grid; grid-template-columns: auto 1fr 1fr; gap: 2px 12px; font-size: 14px; margin: 4px 0 6px; }
.big .grid { font-size: 20px; gap: 4px 20px; }
.big .sc { font-size: 18px; }
.th { font-size: 12px; color: var(--ink-2); font-weight: 700; }
.big .th { font-size: 16px; }
.k { color: var(--ink-2); }
.rs { color: var(--teal); font-weight: 700; }
.small { font-size: 12px; }
</style>

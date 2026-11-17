<script setup>
// PCA 段，四步（「為什麼要壓」改在投影片講，2026-11-16 拿掉）：2 欄壓成 1 個分數 → 10 欄壓成 k 個分數、還原得回來幾成 → 每個分數在量什麼（取名）
// → 投票：違約的人在哪裡，公布後揭曉各主成分的違約比例。四步都由老師頁切換（「自己試／挑戰」2026-11-16 拿掉）。
import { ref, computed, watch, onMounted } from 'vue'
import { store, getJSON, colsParam, COLORS } from '../shared.js'
import Scatter3D from '../components/Scatter3D.vue'
import Demo2 from '../components/Demo2.vue'
import Recon from '../components/Recon.vue'
import RestoreCard from '../components/RestoreCard.vue'
import Loadings from '../components/Loadings.vue'
import PersonCard from '../components/PersonCard.vue'
import NameCard from '../components/NameCard.vue'
import VoteCard from '../components/VoteCard.vue'
import ByPc from '../components/ByPc.vue'
import Help from '../components/Help.vue'
import RefNames from '../components/RefNames.vue'
import PcMix from '../components/PcMix.vue'
import StepTabs from '../components/StepTabs.vue'

const props = defineProps({ nickname: String, myNames: Object, myVotes: Object })
const emit = defineEmits(['voted'])
const cls = ref(null)            // 全班那張（十欄）
const demo = ref(null)           // 第 2 步
const k = ref(3)
const sel = ref(-1)
const rev = ref(null)
const showCodes = ref(false)
const tab = ref(store.state.step?.pca || 1)               // 一次只看一步，跟著老師頁

const colors = computed(() => store.labels ? store.labels.map(y => (y ? COLORS.red : COLORS.gray)) : null)
const front = computed(() => store.labels ? store.labels.map(y => !!y) : null)
const voteHere = computed(() => store.votes?.question?.seg === 'pca')
const pct = v => Math.round(v * 100)
const TABS = computed(() => [
  { key: 1, no: '第 1 步', lock: true, label: '壓到線上' }, { key: 2, no: '第 2 步', lock: true, label: '壓成幾個' }, { key: 3, no: '第 3 步', lock: true, label: '量什麼' },
  { key: 4, no: '第 4 步', lock: true, label: '違約在哪', dot: tab.value !== 4 && (!!rev.value || (voteHere.value && !!store.votes?.answer)) },
])

async function loadReveal() {
  const r = store.state.reveal.pca ? await getJSON('/api/pca/reveal') : null
  rev.value = r && !r.error && store.state.reveal.pca ? r : null      // 老師剛揭曉又收起：回來的是錯誤訊息，不能當資料畫
}
watch(() => store.state.reveal.pca, loadReveal)
watch(() => store.state.step?.pca, v => { if (v) { tab.value = v; window.scrollTo(0, 0) } })   // 老師切步，手機跟著跳
onMounted(async () => {
  ;[cls.value, demo.value] = await Promise.all([getJSON('/api/pca?cols=' + colsParam(store.meta.keys)), getJSON('/api/pca/demo')])
  loadReveal()
})
watch(tab, () => { sel.value = -1 })
</script>

<template>
  <StepTabs :tabs="TABS" v-model="tab" :home="store.state.step?.pca || 1" />

  <section class="card" v-if="tab === 1 && demo">
    <div class="step">第 1 步</div>
    <div class="qt">先用 2 欄看懂：壓到一條線上</div>
    <div class="body">只看兩欄：額度使用率和年齡。綠線是大家差最多的方向。
      把每個人壓到線上，就只剩 1 個數字，叫做<b>分數</b>。
      只靠分數猜回原本的兩個數字，叫做<b>還原</b>。點一個人，看猜得準不準。</div>
    <Demo2 :d="demo" />
  </section>

  <section class="card" v-if="tab === 2 && cls">
    <div class="step">第 2 步</div>
    <div class="qt">10 欄壓成幾個分數？丟掉多少？</div>
    <div class="body">10 欄最多可以壓成 10 個分數：PC1 留下最多資訊，PC2 第二，依此類推。
      下面的圖畫的是每個人的前 3 個分數。單指轉動、兩指縮放。<b>點一個圓點，看那個人。</b></div>
    <Scatter3D :xyz="cls.xyz" :colors="colors" :front="front" :selected="sel" @pick="i => sel = i" />
    <div class="legend" v-if="store.labels"><i :style="{ background: COLORS.red }"></i>後來違約<i :style="{ background: COLORS.gray }"></i>沒違約</div>
    <RestoreCard v-if="sel >= 0" :i="sel" :k="k" :loadings="cls.loadings" @close="sel = -1" />
    <div class="muted small" v-else>點圖上一個圓點，看他原本的 10 個數字，和只靠 {{ k }} 個分數猜回來的值。</div>
    <div class="h3">用幾個分數？<b class="kk">{{ k }}</b> 個
      <Help title="「留下幾成資訊」怎麼算？">
        <p>每個分數各留下一部分資訊。PC1 最多，越後面越少。</p>
        <div class="f">留下的比例 ＝ 用到的分數，各自的比例加起來</div>
        <p>現在用 {{ k }} 個分數：</p>
        <div class="f n">{{ cls.ev.slice(0, k).map(pct).join('% ＋ ') }}% {{ k > 1 ? '＝' : '→ 留下' }} {{ pct(cls.cum[k - 1]) }}%</div>
        <p class="muted">每個分數的比例 ＝ 它的變異數 ÷ 全部變異數的總和。數字四捨五入過，加起來可能差 1%。</p>
      </Help>
    </div>
    <input class="slider" type="range" min="1" max="10" v-model.number="k" />
    <div class="body">留下幾成資訊：只靠這幾個分數，能把原本的 10 欄猜回來幾成。
      第一條是 10 欄合計，下面是每一欄各自猜回來幾成。</div>
    <Recon :cols="cls.cols" :row="cls.recon[k - 1]" :total="cls.cum[k - 1]" />
    <button class="fold sm" v-if="demo" @click="showCodes = !showCodes">{{ showCodes ? '▾' : '▸' }} 旁註：資料沒清乾淨會怎樣</button>
    <div v-if="showCodes && demo" class="body">三個逾期欄有 {{ demo.n_codes_student }} 個人填 96 或 98。這是資料代碼，不是真的逾期 96 次，所以當成沒填。
      如果照原樣放進去，PC1 會從 {{ pct(demo.ev1) }}% 變成 {{ pct(demo.keep_ev1) }}%，幾乎都是這 {{ demo.n_codes_student }} 個人造成的。
      少數幾個離譜的值，就能把 PCA 的方向拉走。</div>
  </section>

  <section class="card" v-if="tab === 3 && cls">
    <div class="step">第 3 步</div>
    <div class="qt">每個分數在量什麼？</div>
    <div class="body">每個分數都是 10 欄各乘一個權重，再加起來。長條越長，這一欄越重要。
      <span class="red">紅色往右</span>：這欄越大，分數越高；<span class="teal">綠色往左</span>：這欄越大，分數越低。</div>
    <div class="body muted">只看最長的三、四條，用一句話說：分數高的人長什麼樣？</div>
    <div class="ld"><Loadings v-for="(w, i) in cls.loadings.slice(0, 2)" :key="i" :w="w" :title="`PC${i + 1}（留下 ${pct(cls.ev[i])}% 的資訊）`">
        <template #help>
          <Help :title="`PC${i + 1} 的 ${pct(cls.ev[i])}% 怎麼來的？`">
            <p>「資訊」＝2,000 人彼此差多少（變異數）。</p>
            <div class="f">PC{{ i + 1 }} 的變異數 ÷ 10 個分數的變異數總和 ＝ {{ pct(cls.ev[i]) }}%</div>
            <p>10 個分數各佔多少（四捨五入過，加起來可能差 1%）：</p>
            <div class="f n">{{ cls.ev.map(pct).join('、') }}（%）</div>
            <p class="muted">10 欄原本各佔大約 10%。PC{{ i + 1 }} 佔 {{ pct(cls.ev[i]) }}%，大約抵 {{ (cls.ev[i] * 10).toFixed(1) }} 欄。</p>
          </Help>
        </template>
      </Loadings></div>
  </section>

  <NameCard v-if="tab === 3" seg="pca" :slots="store.meta.name_slots.pca" :nickname="nickname" :mine="myNames"
    title="替 PC1、PC2 取名字"
    why="電腦只給權重，不會說這個分數是什麼意思。意思要人來讀。"
    hint="看上面的長條：分數高的人，是什麼樣的人？名字沒有標準答案。" />

  <section class="card" v-if="tab === 4">
    <div class="step">第 4 步</div>
    <div class="qt">違約的人在哪裡？</div>
    <div class="body">PCA 從頭到尾沒看誰違約。先猜；老師公布後，圖上違約的人會變成紅點。</div>
    <Scatter3D v-if="cls" :xyz="cls.xyz" :colors="colors" :front="front" :selected="sel" @pick="i => sel = i" />
    <div class="legend" v-if="store.labels"><i :style="{ background: COLORS.red }"></i>後來違約<i :style="{ background: COLORS.gray }"></i>沒違約</div>
    <div class="muted small" v-else>老師還沒公布，所以每個點都是灰色。</div>
    <PersonCard v-if="sel >= 0" :i="sel" @close="sel = -1" />
    <PcMix v-if="cls" :loadings="cls.loadings" />
    <RefNames seg="pca" concept />
  </section>
  <VoteCard v-if="tab === 4 && voteHere" :nickname="nickname" :mine="myVotes" @voted="(q, c) => emit('voted', q, c)" />
  <section class="card" v-if="tab === 4 && rev">
    <div class="qt">揭曉：各分數高的那頭，違約比例</div>
    <ByPc :rev="rev" />
    <RefNames seg="pca" concept />
    <div class="body">PCA 沒看答案，找到的方向卻跟違約有關：PC1 最高的 10% 人，違約比例是全部的 {{ (rev.by_pc[0].top10 / rev.base).toFixed(1) }} 倍。
      下一段：分群。</div>
  </section>
</template>

<style scoped>
.step { font-size: 12px; font-weight: 900; letter-spacing: .08em; color: var(--red); }
.qt { font-weight: 900; font-size: 19px; margin: 2px 0 8px; }
.body { font-size: 14px; line-height: 1.6; margin: 6px 0; }
.h3 { font-weight: 900; margin: 14px 0 4px; font-size: 16px; }
.kk { color: var(--red); font-size: 22px; }
.slider { width: 100%; margin: 4px 0 8px; }
.small { font-size: 13px; }
.legend { display: flex; gap: 6px; align-items: center; font-size: 13px; margin-top: 6px; }
.legend i { display: inline-block; width: 10px; height: 10px; margin-left: 8px; }
.ld { display: grid; gap: 14px; margin-top: 10px; }
.fold { width: 100%; text-align: left; font-size: 17px; font-weight: 900; padding: 10px 4px; border: 0; background: none; color: var(--ink); }
.fold.sm { font-size: 14px; margin-top: 8px; }
</style>

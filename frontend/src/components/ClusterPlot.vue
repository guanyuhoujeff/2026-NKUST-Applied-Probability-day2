<script setup>
// 分群的圖：顏色是群（外面給），這裡只決定「怎麼看」——座標用 PCA 的分數還是原始欄位、平面還是立體。
// 不管怎麼看，分群本身都是用 10 個欄位算的，群不會變。
import { ref, computed, watch } from 'vue'
import { store, COLORS, fmtN } from '../shared.js'
import { buildAxes, unitPos, axisLabel, PC_KEYS, pcName } from '../axes.js'
import Scatter3D from './Scatter3D.vue'
import ScatterXY from './ScatterXY.vue'

const props = defineProps({ xyz: { type: Array, required: true }, colors: Array, ring: Array, selected: { type: Number, default: -1 }, big: Boolean,
  labels: Array, groups: Array })      // labels[i]＝第 i 個人的群；groups＝每群的 { n }。有給才會出現「只看某一群」的按鈕
const emit = defineEmits(['pick'])
const only = ref(-1)           // 只看哪一群；−1＝全部
watch(() => props.labels, () => { only.value = -1 })      // 換方法或起點後是另一批人，不沿用「只看第 N 群」
const show = computed(() => (only.value >= 0 && props.labels ? props.labels.map(l => l === only.value) : null))
function focus(g) { only.value = g; if (g >= 0 && props.selected >= 0 && props.labels?.[props.selected] !== g) emit('pick', -1) }
const src = ref('pc')          // pc＝PCA 的分數；raw＝原始欄位
const dim = ref(2)
const cols = ref(['late90', 'dep', 'util'])      // 原始欄位：前兩個給平面，三個給立體
const used = computed(() => cols.value.slice(0, dim.value))
function setCol(n, k) { const c = [...cols.value]; const at = c.indexOf(k); if (at >= 0) c[at] = c[n]; c[n] = k; cols.value = c }   // 選到別軸已用的欄位就對調
const AX = ['橫軸', '直軸', '第三軸']
const pcs = computed(() => PC_KEYS.slice(0, dim.value).map((k, n) => ({ pc: k.toUpperCase(), ax: AX[n], ...(pcName(k) || {}) })))
// 立體＋原始欄位：把三欄各自換成 −1 到 1 的位置；有一欄沒填的人不畫
const raw3 = computed(() => {
  if (src.value !== 'raw' || dim.value !== 3 || !store.people) return null
  const { mask, axes } = buildAxes(used.value)
  const idx = mask.map((m, i) => (m && (!show.value || show.value[i]) ? i : -1)).filter(i => i >= 0)
  const nMissing = mask.filter(m => !m).length
  return {
    idx, hidden: nMissing,
    xyz: idx.map(i => axes.map((a, j) => unitPos(a, a.vals[i], i, j + 1) * 2 - 1)),
    colors: props.colors ? idx.map(i => props.colors[i]) : null, ring: props.ring ? idx.map(i => props.ring[i]) : null,
    sel: idx.indexOf(props.selected), notes: { count: axes.some(a => a.isCount), log: axes.filter(a => a.useLog).map(a => a.q.short) },
  }
})
const H = computed(() => (props.big ? 540 : 320))
</script>

<template>
  <div class="cp" :class="{ big }">
    <div class="sw">
      <span class="lab">座標</span>
      <button :class="{ on: src === 'pc' }" @click="src = 'pc'">PCA 的分數</button>
      <button :class="{ on: src === 'raw' }" @click="src = 'raw'">原始欄位</button>
      <span class="gap"></span>
      <button :class="{ on: dim === 2 }" @click="dim = 2">平面</button>
      <button :class="{ on: dim === 3 }" @click="dim = 3">立體</button>
    </div>
    <div class="pick" v-if="src === 'raw'">
      <label v-for="n in dim" :key="n">{{ AX[n - 1] }}
        <select :value="cols[n - 1]" @change="setCol(n - 1, $event.target.value)"><option v-for="q in store.meta.questions" :key="q.key" :value="q.key">{{ q.short }}</option></select>
      </label>
    </div>

    <ScatterXY v-if="dim === 2" :xk="src === 'pc' ? 'pc1' : used[0]" :yk="src === 'pc' ? 'pc2' : used[1]" :xyz="xyz" named
      :colors="colors" :ring="ring" :show="show" :selected="selected" :height="H" :size="big ? 3.6 : 2.6" :big="big" @pick="i => emit('pick', i)" />
    <Scatter3D v-else-if="src === 'pc'" key="pc3" :xyz="xyz" :colors="colors" :ring="ring" :show="show" :selected="selected" :height="H" :size="big ? 3.2 : 2.4" @pick="i => emit('pick', i)" />
    <template v-else-if="raw3">
      <Scatter3D :key="used.join()" :xyz="raw3.xyz" :colors="raw3.colors" :ring="raw3.ring" :selected="raw3.sel" :axes="used.map(axisLabel)"
        :height="H" :size="big ? 3.2 : 2.4" @pick="i => emit('pick', raw3.idx[i])" />
      <div class="nt">立體圖沒有刻度，只看相對位置。<span v-if="raw3.notes.count">次數相同的人會稍微散開畫。</span>
        <span v-if="raw3.notes.log.length">{{ raw3.notes.log.join('、') }}的數字越大，畫得越擠。</span>
        <span v-if="raw3.hidden">{{ raw3.hidden }} 人有一欄沒填，沒畫出來。</span></div>
    </template>

    <div class="grp" v-if="groups && labels">
      <span class="lab">只看</span>
      <button :class="{ on: only === -1 }" @click="focus(-1)">全部</button>
      <button v-for="(c, i) in groups" :key="i" :class="{ on: only === i }" :style="only === i ? { background: COLORS.cluster[i], borderColor: COLORS.cluster[i] } : { borderColor: COLORS.cluster[i] }" @click="focus(only === i ? -1 : i)">
        <i :style="{ background: only === i ? '#fff' : COLORS.cluster[i] }"></i>第 {{ i + 1 }} 群 <small>{{ fmtN(c.n) }} 人</small></button>
      <span class="rg" v-if="ring"><i></i>紅框＝後來違約</span>
    </div>

    <div class="say">
      <template v-if="src === 'pc'">座標是 PCA 的分數，每個分數都是 10 欄的綜合：
        <div class="pcs"><div v-for="p in pcs" :key="p.pc"><b>{{ p.pc }}</b>（{{ p.ax }}）<template v-if="p.short">「{{ p.short }}」<span class="muted">{{ p.concept }}</span></template></div></div>
      </template>
      <template v-else>座標是{{ dim === 2 ? '兩' : '三' }}個原始欄位。換換看，哪幾欄最能把顏色分開？</template>
      <b>不管怎麼看，分群都是 10 個欄位一起算的，顏色不會變。</b>
      <span v-if="dim === 3">單指轉動、兩指縮放。</span>
    </div>
  </div>
</template>

<style scoped>
.sw { display: flex; gap: 4px; align-items: center; flex-wrap: nowrap; margin-bottom: 8px; }
.sw .lab { font-size: 13px; font-weight: 800; color: var(--ink-2); }
.sw .gap { flex: 1; min-width: 4px; }
.sw button { font-size: 13px; font-weight: 800; padding: 8px 7px; white-space: nowrap; border-radius: 10px; border: 2px solid var(--line); background: #fff; color: var(--ink-2); }
.sw button.on { border-color: var(--ink); background: var(--ink); color: #fff; }
.pick { display: grid; grid-template-columns: repeat(auto-fit, minmax(96px, 1fr)); gap: 8px; margin-bottom: 8px; font-size: 13px; font-weight: 700; }
.pick select { width: 100%; margin-top: 2px; font-size: 15px; padding: 8px 4px; border-radius: 10px; border: 2px solid var(--line); background: #fff; }
.grp { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; margin-top: 8px; }
.grp .lab { font-size: 13px; font-weight: 800; color: var(--ink-2); }
.grp button { font-size: 13px; font-weight: 800; padding: 7px 9px; border-radius: 999px; border: 2px solid var(--line); background: #fff; color: var(--ink); white-space: nowrap; }
.grp button.on { color: #fff; background: var(--ink); border-color: var(--ink); }
.grp button i { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 5px; }
.grp button small { font-weight: 600; opacity: .8; }
.grp .rg { font-size: 12px; color: var(--ink-2); }
.grp .rg i { display: inline-block; width: 9px; height: 9px; border: 1.5px solid var(--red); margin-right: 4px; }
.big .grp button, .big .grp .lab { font-size: 18px; padding: 8px 14px; }
.big .grp .rg { font-size: 16px; }
.nt { font-size: 12px; color: var(--ink-2); margin-top: 4px; line-height: 1.5; }
.say { font-size: 13px; line-height: 1.6; margin-top: 8px; }
.big .sw button, .big .sw .lab { font-size: 18px; }
.big .sw button { padding: 8px 14px; }
.big .sw .gap { flex: none; width: 16px; }
.big .pick { font-size: 17px; }
.big .pick select { font-size: 18px; }
.big .say { font-size: 18px; }
.pcs { margin: 4px 0 6px; display: grid; gap: 3px; }
.pcs span { display: block; font-size: 12px; }
.big .pcs span { font-size: 15px; }
.big .nt { font-size: 15px; }
</style>

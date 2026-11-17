<script setup>
// 第 4 步投票用：PC1–PC3 各由哪幾欄組成。每個 PC 列權重最大的 4 欄（紅＝越大分數越高、綠＝越大分數越低）；「?」看全部 10 欄。
import { computed } from 'vue'
import { store } from '../shared.js'
import Help from './Help.vue'
import Loadings from './Loadings.vue'
const props = defineProps({ loadings: { type: Array, required: true }, ev: Array, big: Boolean, top: { type: Number, default: 4 } })
const zh = computed(() => Object.fromEntries(store.meta.questions.map(q => [q.key, q.short])))
const rows = computed(() => props.loadings.map(w => Object.entries(w).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1])).slice(0, props.top)))
</script>

<template>
  <div class="mx" :class="{ big }">
    <div class="cap">每個分數由哪幾欄組成（各列權重最大的 {{ top }} 欄）</div>
    <div v-for="(r, i) in rows" :key="i" class="it">
      <div class="pc"><b>PC{{ i + 1 }}</b>
        <Help v-if="!big" :title="`PC${i + 1} 的全部權重`"><Loadings :w="loadings[i]" /></Help>
      </div>
      <div class="chips">
        <span v-for="[k, v] in r" :key="k" :class="v > 0 ? 'pos' : 'neg'">{{ zh[k] }} {{ v > 0 ? '↑' : '↓' }}</span>
      </div>
    </div>
    <div class="lg"><i class="pos"></i>這欄越大，分數越高　<i class="neg"></i>這欄越大，分數越低</div>
  </div>
</template>

<style scoped>
.mx { margin-top: 10px; }
.cap { font-size: 13px; font-weight: 700; margin-bottom: 6px; }
.it { display: grid; grid-template-columns: 64px 1fr; gap: 6px; align-items: start; margin: 8px 0; }
.pc { display: flex; align-items: center; font-size: 15px; padding-top: 3px; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chips span { font-size: 13px; font-weight: 700; padding: 3px 9px; border-radius: 999px; border: 1.5px solid; background: #fff; white-space: nowrap; }
.chips .pos { color: var(--red); border-color: var(--red); }
.chips .neg { color: var(--teal); border-color: var(--teal); }
.lg { font-size: 12px; color: var(--ink-2); margin-top: 4px; }
.lg i { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 4px; }
.lg i.pos { background: var(--red); }
.lg i.neg { background: var(--teal); }
.big .cap { font-size: 20px; }
.big .it { grid-template-columns: 80px 1fr; margin: 14px 0; }
.big .pc { font-size: 24px; }
.big .chips span { font-size: 20px; padding: 5px 14px; }
.big .lg { font-size: 16px; }
</style>

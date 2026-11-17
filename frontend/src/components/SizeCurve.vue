<script setup>
// 揭曉：挑幾欄 vs 考題分數（每種欄位數的最高與平均）。
const props = defineProps({ curve: { type: Object, required: true }, big: Boolean })
const ks = Object.keys(props.curve.best)
const top = Math.max(...Object.values(props.curve.best))
</script>

<template>
  <div class="sc" :class="{ big }">
    <div v-for="k in ks" :key="k" class="r">
      <span class="k">{{ k }} 欄</span>
      <span class="bar">
        <i class="best" :class="{ top: curve.best[k] === top }" :style="{ width: curve.best[k] / top * 100 + '%' }"></i>
        <i class="mean" :style="{ width: curve.mean[k] / top * 100 + '%' }"></i>
      </span>
      <span class="v"><b>{{ curve.best[k] }}</b> <small>平均 {{ curve.mean[k] }}</small></span>
    </div>
    <div class="lg"><i class="best"></i>最高分的挑法　<i class="mean"></i>同樣欄數、所有挑法的平均</div>
  </div>
</template>

<style scoped>
.r { display: grid; grid-template-columns: 44px 1fr 96px; gap: 8px; align-items: center; font-size: 13px; margin: 4px 0; }
.big .r { grid-template-columns: 80px 1fr 180px; font-size: 20px; margin: 8px 0; }
.bar { position: relative; height: 16px; background: var(--paper-2); border-radius: 6px; overflow: hidden; }
.big .bar { height: 26px; }
.bar i { position: absolute; left: 0; top: 0; bottom: 0; }
i.best { background: var(--teal); }
i.best.top { background: var(--red); }
i.mean { background: rgba(31, 28, 23, .35); height: 40%; top: 30% !important; }
.v { text-align: right; }
.lg { font-size: 12px; color: var(--ink-2); margin-top: 4px; display: flex; align-items: center; gap: 4px; }
.big .lg { font-size: 16px; }
.lg i { display: inline-block; width: 12px; height: 8px; position: static; }
</style>

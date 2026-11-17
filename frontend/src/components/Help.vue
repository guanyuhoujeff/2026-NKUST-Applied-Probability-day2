<script setup>
// 「?」按鈕：點下去跳出說明視窗（公式、算法）。內容由 slot 給。
import { ref } from 'vue'
defineProps({ title: String })
const open = ref(false)
</script>

<template>
  <button class="q" type="button" aria-label="說明" @click.stop="open = true">?</button>
  <Teleport to="body">
    <div v-if="open" class="mask" @click.self="open = false">
      <div class="box" role="dialog" aria-modal="true">
        <div class="h"><b>{{ title }}</b><button class="x" type="button" aria-label="關閉" @click="open = false">✕</button></div>
        <div class="c"><slot /></div>
        <button class="ok" type="button" @click="open = false">知道了</button>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.q { display: inline-flex; align-items: center; justify-content: center; width: 24px; height: 24px; margin-left: 6px; padding: 0;
  border: 2px solid var(--ink); border-radius: 50%; background: #fff; color: var(--ink); font-size: 14px; font-weight: 900; line-height: 1; vertical-align: middle; cursor: pointer; }
.mask { position: fixed; inset: 0; background: rgba(0, 0, 0, .45); display: flex; align-items: center; justify-content: center; padding: 16px; z-index: 1000; }
.box { background: #fff; color: var(--ink); border-radius: 14px; padding: 16px; width: 100%; max-width: 440px; max-height: 86vh; overflow-y: auto; font-weight: 400; }
.h { display: flex; align-items: flex-start; gap: 8px; font-size: 17px; margin-bottom: 8px; }
.x { margin-left: auto; border: 0; background: none; font-size: 20px; cursor: pointer; }
.c { font-size: 15px; line-height: 1.6; }
.c :deep(.f) { background: var(--paper-2); border-radius: 10px; padding: 10px 12px; margin: 8px 0; font-size: 16px; font-weight: 700; text-align: center; }
.c :deep(.n) { font-variant-numeric: tabular-nums; }
.c :deep(p) { margin: 6px 0; }
.ok { margin-top: 12px; width: 100%; padding: 10px; border: 0; border-radius: 10px; background: var(--ink); color: #fff; font-size: 15px; font-weight: 700; cursor: pointer; }
</style>

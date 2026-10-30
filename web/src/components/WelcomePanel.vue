<template>
  <div class="welcome">
    <div class="badge">
      <span class="badge-dot" />
      本地模型 · 多引擎 · 流式对话
    </div>

    <h1>
      你好，我是<br />
      <span class="marker">{{ modelName }}</span>
    </h1>
    <p class="desc">
      {{ description || '支持全量微调 / LoRA / 远端 API 三种模型随时切换，对话自动保存。' }}
    </p>

    <div class="suggest-grid">
      <button
        v-for="(s, i) in suggestions"
        :key="s.text"
        class="suggest"
        :style="{ '--accent': accents[i % accents.length].c, '--accent-soft': accents[i % accents.length].soft, animationDelay: (i * 70) + 'ms' }"
        @click="$emit('pick', s.text)"
      >
        <span class="icon">{{ s.icon }}</span>
        <span class="text">{{ s.text }}</span>
        <span class="arrow">→</span>
      </button>
    </div>

    <p class="hint">点上面任意一张卡片，或直接在下方输入问题</p>
  </div>
</template>

<script setup>
defineProps({
  modelName: { type: String, default: 'AI 助手' },
  description: { type: String, default: '' },
})
defineEmits(['pick'])

const suggestions = [
  { icon: '🙋', text: '你是谁？' },
  { icon: '🧩', text: '给我讲个笑话' },
  { icon: '📚', text: '解释一下什么是 LoRA' },
  { icon: '🌤️', text: '今天天气怎么样？' },
]
const accents = [
  { c: '#059669', soft: '#e5f7ef' },
  { c: '#3b9fe8', soft: '#e8f3fc' },
  { c: '#f2a33c', soft: '#fdf1dd' },
  { c: '#ef6461', soft: '#fcebe9' },
]
</script>

<style scoped>
.welcome {
  text-align: center; padding: 64px 20px 24px;
  display: flex; flex-direction: column; align-items: center;
}
.badge {
  display: inline-flex; align-items: center; gap: 7px;
  font-size: 12px; letter-spacing: .06em; color: var(--mint-deep);
  background: var(--mint-soft); border: 1px solid #c9eedd;
  padding: 6px 15px; border-radius: 999px;
}
.badge-dot {
  width: 6px; height: 6px; border-radius: 50%; background: var(--mint);
  animation: breathe 2.4s ease-in-out infinite;
}
@keyframes breathe { 0%, 100% { opacity: 1 } 50% { opacity: .35 } }

h1 {
  font-size: 38px; line-height: 1.4; margin: 20px 0 12px;
  color: var(--ink); font-weight: 800; letter-spacing: .01em;
}
/* 荧光笔划重点，加载时从左向右"画出" */
.marker {
  background: linear-gradient(transparent 60%, #a9e9cd 60%, #a9e9cd 94%, transparent 94%);
  padding: 0 6px;
  -webkit-box-decoration-break: clone;
  box-decoration-break: clone;
  animation: markerIn .8s cubic-bezier(.22,.61,.36,1) both;
  clip-path: inset(0 100% 0 0);
}
@keyframes markerIn {
  to { clip-path: inset(0 0 0 0); }
}
.desc {
  max-width: 520px; color: var(--ink-2); font-size: 14px;
  line-height: 1.9; margin: 0 0 40px;
}

.suggest-grid {
  display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px; width: min(620px, 100%);
}
.suggest {
  display: flex; align-items: center; gap: 11px; text-align: left;
  background: var(--card); border: 1.5px solid var(--line); border-radius: 16px;
  padding: 15px 17px; cursor: pointer; color: var(--ink); font-size: 14px;
  box-shadow: var(--shadow-s);
  transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease, background .18s ease;
  animation: cardIn .45s cubic-bezier(.22,.61,.36,1) both;
}
@keyframes cardIn {
  from { opacity: 0; transform: translateY(14px) scale(.97); }
  to { opacity: 1; transform: none; }
}
.suggest:hover {
  transform: translateY(-3px);
  border-color: var(--accent);
  background: var(--accent-soft);
  box-shadow: 0 12px 28px rgba(34, 39, 46, .10);
}
.suggest:active { transform: translateY(-1px); }
.suggest .icon {
  width: 34px; height: 34px; border-radius: 11px; flex-shrink: 0;
  display: grid; place-items: center; font-size: 16px;
  background: var(--accent-soft); border: 1px solid color-mix(in srgb, var(--accent) 22%, transparent);
}
.suggest .text { flex: 1; font-weight: 500; }
.suggest .arrow { color: var(--ink-3); transition: color .18s, transform .18s; }
.suggest:hover .arrow { color: var(--accent); transform: translateX(3px); }

.hint { margin-top: 26px; font-size: 12px; color: var(--ink-3); }

@media (max-width: 760px) {
  h1 { font-size: 28px; }
  .suggest-grid { grid-template-columns: 1fr; }
  .welcome { padding-top: 40px; }
}
</style>

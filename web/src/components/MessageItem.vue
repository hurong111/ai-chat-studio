<template>
  <div class="msg" :class="[message.role, { streaming }]">
    <div class="avatar" :class="message.role">
      <span v-if="message.role === 'assistant'" class="spark">✦</span>
      <span v-else>{{ initial }}</span>
    </div>

    <div class="body">
      <div class="meta">
        <span class="who">{{ message.role === 'assistant' ? 'AI 助手' : '我' }}</span>
        <span v-if="modelTag" class="tag">{{ modelTag }}</span>
      </div>

      <div class="bubble" v-html="html"></div>

      <div v-if="!streaming && message.role === 'assistant'" class="actions">
        <button class="act" @click="copy">{{ copied ? '✓ 已复制' : '复制' }}</button>
      </div>

      <span v-if="streaming" class="cursor">▋</span>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { marked } from 'marked'

const props = defineProps({
  message: { type: Object, required: true },
  streaming: { type: Boolean, default: false },
  modelTag: { type: String, default: '' },
})

const copied = ref(false)

const initial = computed(() => {
  const name = props.message.author || '我'
  return name.slice(0, 1).toUpperCase()
})

const html = computed(() =>
  marked.parse(props.message.content || '', { breaks: true, gfm: true })
)

async function copy() {
  try {
    await navigator.clipboard.writeText(props.message.content || '')
    copied.value = true
    setTimeout(() => (copied.value = false), 1500)
  } catch {
    copied.value = false
  }
}
</script>

<style scoped>
.msg { display: flex; gap: 12px; margin-bottom: 26px; animation: rise .25s ease both; }
@keyframes rise { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }

.avatar {
  width: 38px; height: 38px; border-radius: 13px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 15px;
}
.avatar.assistant {
  background: var(--mint-soft); border: 1.5px solid #c9eedd;
  color: var(--mint-deep);
}
.avatar.user { background: var(--sky-soft); border: 1.5px solid #cfe6f8; color: #1d6fb8; }
.spark { font-size: 16px; line-height: 1; }

.body { min-width: 0; max-width: min(760px, 76%); }
.meta { display: flex; align-items: center; gap: 8px; margin: 2px 0 6px; }
.who { font-size: 12px; font-weight: 600; color: var(--ink-2); }
.tag {
  font-size: 11px; color: var(--mint-deep); background: var(--mint-soft);
  border: 1px solid #c9eedd; border-radius: 999px; padding: 1px 8px;
}

.bubble {
  padding: 13px 17px; border-radius: 17px; line-height: 1.75;
  font-size: 14.5px; word-break: break-word; white-space: pre-wrap;
}
.msg.assistant .bubble {
  background: var(--card); color: var(--ink);
  border: 1.5px solid var(--line);
  border-top-left-radius: 6px;
  box-shadow: var(--shadow-s);
}
.msg.user { flex-direction: row-reverse; }
.msg.user .body { display: flex; flex-direction: column; align-items: flex-end; }
.msg.user .meta { flex-direction: row-reverse; }
.msg.user .bubble {
  background: var(--mint);
  color: #fff; border-top-right-radius: 6px;
  box-shadow: 0 8px 20px rgba(16, 185, 129, .22);
}

.actions { margin-top: 6px; }
.act {
  border: 0; background: transparent; color: var(--ink-3); font-size: 12px;
  cursor: pointer; padding: 3px 8px; border-radius: 7px;
  transition: color .15s ease, background .15s ease;
}
.act:hover { color: var(--mint-deep); background: var(--mint-soft); }

.cursor { color: var(--mint); font-weight: 700; animation: blink 1s infinite; margin-left: 2px; }
@keyframes blink { 0%, 100% { opacity: 1 } 50% { opacity: 0 } }

.bubble :deep(p) { margin: 0 0 8px; }
.bubble :deep(p:last-child) { margin-bottom: 0; }
.bubble :deep(pre) {
  background: #2b2f36; color: #e8eaf0; padding: 12px 14px;
  border-radius: 12px; overflow-x: auto; margin: 10px 0;
  font-size: 12.5px; line-height: 1.6;
}
.bubble :deep(code) {
  background: var(--mint-soft); color: var(--mint-deep); padding: 1px 6px;
  border-radius: 6px; font-size: 12.5px;
}
.bubble :deep(pre code) { background: transparent; color: inherit; padding: 0; }
.msg.user .bubble :deep(code) { background: rgba(255, 255, 255, .22); color: #fff; }
.bubble :deep(ul), .bubble :deep(ol) { padding-left: 20px; margin: 6px 0; }
.bubble :deep(blockquote) {
  border-left: 3px solid #a9e9cd; margin: 8px 0; padding: 2px 12px; color: var(--ink-2);
}
.bubble :deep(table) { border-collapse: collapse; margin: 8px 0; }
.bubble :deep(th), .bubble :deep(td) { border: 1px solid var(--line); padding: 5px 10px; }

@media (max-width: 760px) {
  .body { max-width: 86%; }
}
</style>

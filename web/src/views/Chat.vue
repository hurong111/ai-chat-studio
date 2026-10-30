<template>
  <div class="chat-page">
    <div v-if="sidebarOpen" class="overlay" @click="sidebarOpen = false" />

    <!-- 左侧会话栏 -->
    <aside class="sidebar" :class="{ open: sidebarOpen }">
      <div class="brand">
        <div class="logo">✦</div>
        <div class="brand-text">
          <div class="brand-title">AI Chat Studio</div>
          <div class="brand-sub">
            <span class="live-dot" /> 本地模型在线
          </div>
        </div>
      </div>

      <button class="new-btn" @click="newConversation">
        <el-icon><Plus /></el-icon>
        <span>新建对话</span>
      </button>

      <div class="search">
        <el-input v-model="keyword" placeholder="搜索对话…" :prefix-icon="Search" clearable />
      </div>

      <div class="list-head">
        <span>对话记录</span>
        <span class="count">{{ filteredConversations.length }}</span>
      </div>

      <div class="conv-list">
        <div
          v-for="(c, i) in filteredConversations"
          :key="c.id"
          class="conv-item"
          :class="{ active: c.id === chatStore.activeConvId }"
          :style="{ animationDelay: Math.min(i * 35, 350) + 'ms' }"
          @click="selectConversation(c.id)"
          @dblclick="startRename(c)"
        >
          <template v-if="renamingId === c.id">
            <el-input
              v-model="renameText" size="small" class="rename-input"
              @blur="commitRename(c)"
              @keyup.enter="commitRename(c)"
              @keyup.esc="renamingId = null"
            />
          </template>
          <template v-else>
            <div class="conv-icon"><el-icon><ChatDotRound /></el-icon></div>
            <div class="conv-main">
              <div class="conv-title">{{ c.title }}</div>
              <div class="conv-time">{{ fmtTime(c.updated_at) }}</div>
            </div>
            <el-popconfirm title="删除这条对话？" confirm-button-text="删除" cancel-button-text="取消" @confirm="removeConversation(c.id)">
              <template #reference>
                <button class="icon-btn del" @click.stop><el-icon><Delete /></el-icon></button>
              </template>
            </el-popconfirm>
          </template>
        </div>

        <div v-if="!filteredConversations.length" class="empty">
          <div class="empty-emoji">💬</div>
          <p>{{ keyword ? '没有匹配的对话' : '还没有对话，点上面新建' }}</p>
        </div>
      </div>

      <div class="sidebar-footer">
        <el-dropdown trigger="click" @command="onUserCmd">
          <div class="user-card">
            <div class="avatar">{{ userInitial }}</div>
            <div class="user-main">
              <div class="user-name">{{ auth.user?.nickname || auth.user?.username }}</div>
              <div class="user-sub">@{{ auth.user?.username }}</div>
            </div>
            <el-icon class="caret"><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="settings">
                <el-icon><Setting /></el-icon>个人设置
              </el-dropdown-item>
              <el-dropdown-item divided command="logout">
                <el-icon><SwitchButton /></el-icon>退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </aside>

    <!-- 主区域 -->
    <main class="main">
      <header class="topbar">
        <button class="menu-btn" @click="sidebarOpen = !sidebarOpen">
          <el-icon><Menu /></el-icon>
        </button>

        <ModelSwitcher
          v-model="chatStore.activeModelId"
          :models="chatStore.models"
          @change="onModelChange"
        />

        <div class="top-right">
          <div class="status" :class="{ busy: chatStore.loading }">
            <span class="dot" />
            {{ chatStore.loading ? '生成中' : '就绪' }}
          </div>
          <button class="icon-btn" title="个人设置" @click="settingsVisible = true">
            <el-icon><Setting /></el-icon>
          </button>
        </div>
      </header>

      <section class="messages" ref="msgScroll">
        <WelcomePanel
          v-if="isEmpty"
          :model-name="currentModel?.name || 'AI 助手'"
          :description="currentModel?.description"
          @pick="pickPrompt"
        />

        <div v-else class="thread">
          <MessageItem
            v-for="(m, i) in chatStore.messages"
            :key="i"
            :message="m"
            :model-tag="modelTag(m)"
          />
          <MessageItem
            v-if="chatStore.streamingText"
            :message="{ role: 'assistant', content: chatStore.streamingText }"
            :model-tag="shortModelName"
            streaming
          />
          <!-- 等待首字期间的跳动圆点 -->
          <div v-if="chatStore.loading && !chatStore.streamingText" class="typing-row">
            <div class="typing-avatar">✦</div>
            <div class="typing-bubble">
              <span /><span /><span />
            </div>
          </div>
        </div>
      </section>

      <footer class="composer">
        <div class="composer-card">
          <el-input
            v-model="input"
            type="textarea"
            :autosize="{ minRows: 2, maxRows: 7 }"
            resize="none"
            placeholder="给模型发条消息…  Enter 发送，Shift + Enter 换行"
            :disabled="chatStore.loading"
            @keydown.enter.exact.prevent="send"
          />
          <div class="composer-bar">
            <div class="hint">
              <span class="key">Enter</span> 发送
              <span class="sep">·</span>
              <span class="key">Shift+Enter</span> 换行
            </div>
            <div class="bar-right">
              <span class="char">{{ input.length }}/2000</span>
              <button v-if="chatStore.loading" class="send-btn stop" title="停止生成" @click="chatStore.stop()">
                <el-icon><VideoPause /></el-icon>
              </button>
              <button v-else class="send-btn" :disabled="!input.trim()" title="发送" @click="send">
                <el-icon><Promotion /></el-icon>
              </button>
            </div>
          </div>
        </div>
        <div class="composer-note">
          {{ currentModel?.name || '未选择模型' }} · 原生 .pth 权重本地推理 · 生成内容仅供参考
        </div>
      </footer>
    </main>

    <SettingsDialog v-model:visible="settingsVisible" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus, ChatDotRound, Delete, ArrowDown, Promotion, VideoPause,
  Search, Menu, Setting, SwitchButton,
} from '@element-plus/icons-vue'

import { useAuthStore } from '../stores/auth'
import { useChatStore } from '../stores/chat'
import MessageItem from '../components/MessageItem.vue'
import WelcomePanel from '../components/WelcomePanel.vue'
import ModelSwitcher from '../components/ModelSwitcher.vue'
import SettingsDialog from '../components/SettingsDialog.vue'

const auth = useAuthStore()
const chatStore = useChatStore()
const router = useRouter()

const input = ref('')
const keyword = ref('')
const msgScroll = ref()
const settingsVisible = ref(false)
const sidebarOpen = ref(false)
const renamingId = ref(null)
const renameText = ref('')

const currentModel = computed(() =>
  chatStore.models.find((m) => m.id === chatStore.activeModelId)
)
const shortModelName = computed(() => {
  const name = currentModel.value?.name || '本地模型'
  return name.replace(/^本地·|^远端·/, '')
})
const isEmpty = computed(() => !chatStore.messages.length && !chatStore.streamingText)
const filteredConversations = computed(() => {
  const k = keyword.value.trim().toLowerCase()
  if (!k) return chatStore.conversations
  return chatStore.conversations.filter((c) => c.title.toLowerCase().includes(k))
})
const userInitial = computed(() =>
  (auth.user?.nickname || auth.user?.username || 'U').slice(0, 1).toUpperCase()
)

function modelTag(m) {
  if (m.role !== 'assistant') return ''
  const id = m.model_id || chatStore.activeModelId
  const model = chatStore.models.find((x) => x.id === id)
  if (!model) return ''
  const kind = ({ full_sft: '全量SFT', lora: 'LoRA', remote: '远端API', pretrain: '预训练' })[model.kind] || ''
  return kind ? `${model.name.replace(/^本地·|^远端·/, '')} · ${kind}` : ''
}

function fmtTime(v) {
  if (!v) return ''
  const d = new Date(v.endsWith?.('Z') ? v : v + 'Z')
  if (Number.isNaN(d.getTime())) return ''
  const now = new Date()
  const sameDay = d.toDateString() === now.toDateString()
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  return sameDay ? `${hh}:${mm}` : `${d.getMonth() + 1}/${d.getDate()}`
}

async function newConversation() {
  await chatStore.createConversation('新对话', chatStore.activeModelId)
  sidebarOpen.value = false
  input.value = ''
}

async function selectConversation(id) {
  await chatStore.selectConversation(id)
  sidebarOpen.value = false
}

async function removeConversation(id) {
  await chatStore.deleteConversation(id)
  ElMessage.success('已删除')
}

async function onModelChange(id) {
  await chatStore.setModel(id)
  ElMessage.success(`已切换到 ${currentModel.value?.name || id}`)
}

function onUserCmd(cmd) {
  if (cmd === 'settings') settingsVisible.value = true
  else if (cmd === 'logout') {
    ElMessageBox.confirm('确认退出登录？', '提示', { type: 'warning' })
      .then(() => {
        auth.logout()
        router.push('/login')
      })
      .catch(() => {})
  }
}

function send() {
  const t = input.value.trim()
  if (!t || chatStore.loading) return
  input.value = ''
  chatStore.sendMessage(t)
}

function pickPrompt(text) {
  input.value = text
  send()
}

function startRename(c) {
  renamingId.value = c.id
  renameText.value = c.title
  nextTick(() => {
    const el = document.querySelector('.rename-input input')
    el?.focus()
    el?.select()
  })
}
async function commitRename(c) {
  const t = renameText.value.trim() || c.title
  renamingId.value = null
  if (t !== c.title) await chatStore.renameConversation(c.id, t)
}

watch(() => chatStore.messages.length, () => nextTick(scrollBottom))
watch(() => chatStore.streamingText, scrollBottom)
function scrollBottom() {
  if (msgScroll.value) msgScroll.value.scrollTop = msgScroll.value.scrollHeight
}

onMounted(async () => {
  await Promise.all([chatStore.loadConversations(), chatStore.loadModels()])
})
</script>

<style scoped>
.chat-page {
  display: flex; height: 100vh; overflow: hidden; background: var(--paper);
}

/* ================= 侧边栏（浅色纸感） ================= */
.sidebar {
  width: 284px; flex-shrink: 0; display: flex; flex-direction: column;
  padding: 18px 14px 14px;
  background: var(--card);
  border-right: 1.5px solid var(--line);
  color: var(--ink); position: relative; z-index: 30;
}
.brand { display: flex; align-items: center; gap: 10px; padding: 4px 8px 20px; }
.brand:hover .logo { animation: wiggle .5s ease; }
@keyframes wiggle {
  0%, 100% { transform: rotate(-4deg); }
  25% { transform: rotate(-10deg) scale(1.06); }
  75% { transform: rotate(2deg) scale(1.06); }
}
.logo {
  width: 36px; height: 36px; border-radius: 12px; display: grid; place-items: center;
  background: var(--mint); color: #fff; font-size: 17px;
  box-shadow: 0 4px 0 #0b8f64; transform: rotate(-4deg);
}
.brand-title { font-size: 15px; font-weight: 700; letter-spacing: .01em; }
.brand-sub { display: flex; align-items: center; gap: 6px; font-size: 11px; color: var(--ink-3); margin-top: 2px; }
.live-dot {
  width: 6px; height: 6px; border-radius: 50%; background: var(--mint);
  box-shadow: 0 0 0 3px rgba(16, 185, 129, .14);
  animation: breathe 2.4s ease-in-out infinite;
}
@keyframes breathe { 0%, 100% { opacity: 1 } 50% { opacity: .4 } }

.new-btn {
  display: flex; align-items: center; justify-content: center; gap: 7px;
  height: 42px; width: 100%; border: 0; border-radius: 12px; cursor: pointer;
  color: #fff; font-size: 14px; font-weight: 600;
  background: var(--mint);
  box-shadow: 0 4px 0 #0b8f64, 0 10px 22px rgba(16, 185, 129, .2);
  transition: transform .15s ease, background .15s ease, box-shadow .15s ease;
}
.new-btn:hover { background: var(--mint-deep); transform: translateY(-1px); }
.new-btn:active { transform: translateY(2px); box-shadow: 0 2px 0 #0b8f64; }

.search { margin: 14px 0 6px; }
.search :deep(.el-input__wrapper) {
  background: #f6f5ee; border-radius: 10px;
  box-shadow: 0 0 0 1px transparent inset;
  transition: background .16s ease, box-shadow .16s ease;
}
.search :deep(.el-input__wrapper.is-focus) {
  background: #fff; box-shadow: 0 0 0 2px var(--mint) inset;
}
.search :deep(.el-input__inner) { color: var(--ink); }
.search :deep(.el-input__inner::placeholder) { color: var(--ink-3); }
.search :deep(.el-input__prefix) { color: var(--ink-3); }

.list-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 8px 8px; font-size: 11px; letter-spacing: .08em;
  color: var(--ink-3); text-transform: uppercase;
}
.list-head .count {
  background: #f6f5ee; border: 1px solid var(--line); border-radius: 999px;
  padding: 1px 7px; font-size: 10.5px; letter-spacing: 0;
}

.conv-list { flex: 1; overflow-y: auto; padding: 0 2px; }
.conv-list::-webkit-scrollbar { width: 4px; }
.conv-list::-webkit-scrollbar-thumb { background: #dcd9cc; }

.conv-item {
  display: flex; align-items: center; gap: 9px; padding: 9px 9px;
  border-radius: 12px; margin-bottom: 3px; cursor: pointer;
  color: var(--ink-2); border: 1.5px solid transparent;
  transition: background .16s ease, color .16s ease, border-color .16s ease;
  animation: convIn .3s ease both;
}
@keyframes convIn {
  from { opacity: 0; transform: translateX(-8px); }
  to { opacity: 1; transform: none; }
}
.conv-item:hover { background: #f6f5ee; }
.conv-item.active {
  background: var(--mint-soft); border-color: #c9eedd;
  color: var(--ink);
}
.conv-icon {
  width: 26px; height: 26px; border-radius: 9px; flex-shrink: 0;
  display: grid; place-items: center; font-size: 13px;
  background: #f0efe6; color: var(--ink-2);
}
.conv-item.active .conv-icon { background: #fff; color: var(--mint-deep); }
.conv-main { flex: 1; min-width: 0; }
.conv-title {
  font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.conv-item.active .conv-title { font-weight: 600; }
.conv-time { font-size: 10.5px; color: var(--ink-3); margin-top: 2px; }
.conv-item.active .conv-time { color: var(--mint-deep); }

.icon-btn {
  border: 0; background: transparent; color: var(--ink-3); cursor: pointer;
  width: 28px; height: 28px; border-radius: 8px; display: grid; place-items: center;
  transition: background .15s ease, color .15s ease;
}
.icon-btn:hover { background: #f0efe6; color: var(--ink); }
.icon-btn.del { opacity: 0; }
.conv-item:hover .icon-btn.del { opacity: 1; }
.icon-btn.del:hover { background: var(--rose-soft); color: var(--rose); }
.rename-input { width: 100%; }

.empty { text-align: center; padding: 34px 10px; color: var(--ink-3); }
.empty-emoji { font-size: 26px; margin-bottom: 6px; }
.empty p { font-size: 12px; margin: 0; }

.sidebar-footer {
  padding-top: 12px; margin-top: 6px;
  border-top: 1.5px solid var(--line);
}
.user-card {
  display: flex; align-items: center; gap: 10px; padding: 8px;
  border-radius: 12px; cursor: pointer; transition: background .15s ease;
}
.user-card:hover { background: #f6f5ee; }
.avatar {
  width: 34px; height: 34px; border-radius: 11px; flex-shrink: 0;
  display: grid; place-items: center; font-weight: 700; font-size: 14px; color: #fff;
  background: var(--sky);
}
.user-main { flex: 1; min-width: 0; }
.user-name {
  font-size: 13px; color: var(--ink); font-weight: 600;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.user-sub { font-size: 10.5px; color: var(--ink-3); margin-top: 1px; }
.caret { color: var(--ink-3); font-size: 12px; }

/* ================= 主区域 ================= */
.main { flex: 1; display: flex; flex-direction: column; min-width: 0; position: relative; }

.topbar {
  height: 64px; display: flex; align-items: center; gap: 14px;
  padding: 0 24px; background: rgba(255, 255, 255, .85);
  border-bottom: 1.5px solid var(--line); backdrop-filter: blur(10px);
  position: relative; z-index: 20;
}
.menu-btn {
  display: none; border: 1.5px solid var(--line); background: var(--card); color: var(--ink-2);
  width: 36px; height: 36px; border-radius: 10px; cursor: pointer;
  place-items: center;
}
.top-right { margin-left: auto; display: flex; align-items: center; gap: 10px; }
.status {
  display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--mint-deep);
  background: var(--mint-soft); border: 1px solid #c9eedd; border-radius: 999px;
  padding: 5px 11px;
}
.status.busy { color: #c47d1a; background: var(--apricot-soft); border-color: #f6ddb8; }
.status .dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.status.busy .dot { animation: pulse 1.1s infinite; }
@keyframes pulse { 0%, 100% { opacity: 1 } 50% { opacity: .25 } }
.top-right .icon-btn { background: var(--card); border: 1.5px solid var(--line); width: 34px; height: 34px; }
.top-right .icon-btn:hover { background: var(--mint-soft); border-color: #c9eedd; color: var(--mint-deep); }

.messages {
  flex: 1; overflow-y: auto; padding: 24px 24px 8px;
  background:
    radial-gradient(#e9e6da 1px, transparent 1px) 0 0 / 24px 24px,
    var(--paper);
}
.thread { max-width: 900px; margin: 0 auto; }

/* 等待首字期间的跳动圆点 */
.typing-row { display: flex; gap: 12px; margin-bottom: 26px; animation: rise .25s ease both; }
.typing-avatar {
  width: 38px; height: 38px; border-radius: 13px; flex-shrink: 0;
  display: grid; place-items: center; font-size: 16px;
  background: var(--mint-soft); border: 1.5px solid #c9eedd; color: var(--mint-deep);
}
.typing-bubble {
  display: flex; align-items: center; gap: 5px;
  background: var(--card); border: 1.5px solid var(--line);
  border-radius: 17px; border-top-left-radius: 6px;
  padding: 15px 17px; box-shadow: var(--shadow-s);
}
.typing-bubble span {
  width: 7px; height: 7px; border-radius: 50%; background: var(--mint);
  animation: bounce 1.2s ease-in-out infinite;
}
.typing-bubble span:nth-child(2) { animation-delay: .15s; }
.typing-bubble span:nth-child(3) { animation-delay: .3s; }
@keyframes bounce {
  0%, 60%, 100% { transform: translateY(0); opacity: .5; }
  30% { transform: translateY(-5px); opacity: 1; }
}

.composer { padding: 10px 24px 14px; background: transparent; }
.composer-card {
  max-width: 900px; margin: 0 auto;
  background: var(--card); border: 1.5px solid var(--line); border-radius: 18px;
  box-shadow: var(--shadow-m);
  padding: 10px 14px 8px;
  transition: border-color .18s ease, box-shadow .18s ease;
}
.composer-card:focus-within {
  border-color: var(--mint);
  box-shadow: 0 12px 34px rgba(16, 185, 129, .14);
}
.composer-card :deep(.el-textarea__inner) {
  border: 0; box-shadow: none; padding: 6px 4px; font-size: 14.5px;
  background: transparent; color: var(--ink); line-height: 1.7;
}
.composer-card :deep(.el-textarea__inner::placeholder) { color: var(--ink-3); }

.composer-bar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 4px 2px 0;
}
.hint { font-size: 11.5px; color: var(--ink-3); }
.hint .key {
  background: #f6f5ee; border: 1px solid var(--line); border-radius: 6px;
  padding: 1px 5px; font-size: 10.5px; color: var(--ink-2);
}
.hint .sep { margin: 0 5px; }
.bar-right { display: flex; align-items: center; gap: 10px; }
.char { font-size: 11px; color: var(--ink-3); }
.send-btn {
  width: 38px; height: 38px; border: 0; border-radius: 12px; cursor: pointer;
  display: grid; place-items: center; color: #fff; font-size: 17px;
  background: var(--mint);
  box-shadow: 0 4px 0 #0b8f64, 0 8px 18px rgba(16, 185, 129, .22);
  transition: transform .15s ease, background .15s ease, box-shadow .15s ease, opacity .15s ease;
}
.send-btn:hover:not(:disabled) { background: var(--mint-deep); transform: translateY(-1px); }
.send-btn:active:not(:disabled) { transform: translateY(2px); box-shadow: 0 2px 0 #0b8f64; }
.send-btn:disabled { opacity: .35; cursor: not-allowed; box-shadow: none; }
.send-btn.stop { background: var(--rose); box-shadow: 0 4px 0 #d14d4a; }
.send-btn.stop:hover { background: #e05350; }

.composer-note {
  max-width: 900px; margin: 8px auto 0; text-align: center;
  font-size: 11px; color: var(--ink-3);
}
.composer-note::before { content: '— '; }
.composer-note::after { content: ' —'; }

.overlay { display: none; }

@media (max-width: 900px) {
  .sidebar {
    position: fixed; left: 0; top: 0; bottom: 0; transform: translateX(-100%);
    transition: transform .26s cubic-bezier(.2, .8, .2, 1);
    box-shadow: var(--shadow-l);
  }
  .sidebar.open { transform: none; }
  .overlay {
    display: block; position: fixed; inset: 0; z-index: 25;
    background: rgba(34, 39, 46, .32); backdrop-filter: blur(2px);
  }
  .menu-btn { display: grid; }
  .topbar { padding: 0 14px; }
  .messages { padding: 16px 14px 6px; }
  .composer { padding: 8px 12px 12px; }
}
</style>

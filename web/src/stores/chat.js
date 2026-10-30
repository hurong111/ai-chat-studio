import { defineStore } from 'pinia'
import http from '../api/http'
import { postStream } from '../api/http'

export const useChatStore = defineStore('chat', {
  state: () => ({
    conversations: [],
    activeConvId: null,
    activeModelId: 'mock/general',
    models: [],
    messages: [],         // 当前会话消息 [{role, content}]
    loading: false,       // 正在生成
    streamingText: '',    // 流式中的 assistant 回复
    abortFn: null,
  }),
  getters: {
    activeConv: (s) => s.conversations.find((c) => c.id === s.activeConvId),
  },
  actions: {
    async loadConversations() {
      this.conversations = await http.get('/conversations')
    },
    async loadModels() {
      this.models = await http.get('/models')
      const current = this.models.find((m) => m.id === this.activeModelId)
      if (!current || !current.is_available) {
        const available = this.models.filter((m) => m.is_available)
        const prefer =
          available.find((m) => m.provider === 'local' && m.kind === 'full_sft') ||
          available.find((m) => m.provider === 'local') ||
          available[0]
        if (prefer) this.activeModelId = prefer.id
      }
    },
    async setModel(id) {
      this.activeModelId = id
      if (this.activeConvId) {
        await http.patch(`/conversations/${this.activeConvId}`, { model_id: id })
        const conv = this.conversations.find((c) => c.id === this.activeConvId)
        if (conv) conv.model_id = id
      }
    },
    async createConversation(title = '新对话', model_id = null) {
      const conv = await http.post('/conversations', { title, model_id })
      this.conversations.unshift(conv)
      this.activeConvId = conv.id
      this.messages = []
      return conv
    },
    async renameConversation(id, title) {
      const c = this.conversations.find((c) => c.id === id)
      if (!c) return
      await http.patch(`/conversations/${id}`, { title })
      c.title = title
    },
    async deleteConversation(id) {
      await http.delete(`/conversations/${id}`)
      this.conversations = this.conversations.filter((c) => c.id !== id)
      if (this.activeConvId === id) {
        this.activeConvId = null
        this.messages = []
      }
    },
    async selectConversation(id) {
      this.activeConvId = id
      this.messages = await http.get(`/conversations/${id}/messages`)
    },
    async sendMessage(text) {
      if (!text.trim() || this.loading) return

      // 没有活跃会话就自动建一个
      if (!this.activeConvId) {
        await this.createConversation('新对话', this.activeModelId)
      }

      // 先乐观地把 user 消息 push 进去
      this.messages.push({ role: 'user', content: text })
      this.loading = true
      this.streamingText = ''

      const abort = postStream(
        '/api/chat/stream',
        {
          conversation_id: this.activeConvId,
          model_id: this.activeModelId,
          message: text,
        },
        {
          onDelta: (d) => { this.streamingText += d },
          onDone: (meta) => {
            // 把完整回复落进 messages
            if (this.streamingText) {
              this.messages.push({ role: 'assistant', content: this.streamingText })
            }
            // 刷新会话标题（后端自动生成首句标题）
            if (meta.title && this.activeConv) this.activeConv.title = meta.title
            this.loading = false
            this.streamingText = ''
            this.abortFn = null
          },
          onError: () => {
            this.loading = false
            this.streamingText = ''
            this.abortFn = null
          },
        }
      )
      this.abortFn = abort
    },
    stop() {
      if (this.abortFn) this.abortFn()
      this.loading = false
      this.abortFn = null
      // 也把已出的流式片段保存成 assistant 消息，免得丢
      if (this.streamingText) {
        this.messages.push({ role: 'assistant', content: this.streamingText + '\n\n_（已停止生成）_' })
        this.streamingText = ''
      }
    },
  },
})

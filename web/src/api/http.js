import axios from 'axios'
import { useAuthStore } from '../stores/auth'
import { ElMessage } from 'element-plus'

// API 基础地址：本地开发/同源隧道部署时为空（走相对路径）；
// 部署到 Cloudflare Pages 等独立静态托管时，通过构建变量 VITE_API_BASE 指向后端（如隧道网址）
export const API_BASE = import.meta.env.VITE_API_BASE || ''

const http = axios.create({
  baseURL: `${API_BASE}/api`,
  timeout: 30_000,
})

http.interceptors.request.use((cfg) => {
  const auth = useAuthStore()
  if (auth.token) cfg.headers.Authorization = `Bearer ${auth.token}`
  return cfg
})

http.interceptors.response.use(
  (r) => r.data,
  (err) => {
    const msg = err.response?.data?.detail || err.message || '请求失败'
    if (err.response?.status === 401) {
      const auth = useAuthStore()
      auth.logout()
      router.replace('/login')
    }
    ElMessage.error(msg)
    return Promise.reject(err)
  }
)

import router from '../router'
export default http

// ---------- SSE 流式（用原生 fetch，axios 不支持 ReadableStream）----------
/**
 * 发起 SSE 流式 POST。
 * @param {string} url  相对路径，如 /api/chat/stream
 * @param {object} body JSON 请求体
 * @param {(delta: string, meta?: object)=>void} onDelta  每个 token 到来时回调
 * @param {(finalMeta: object)=>void} onDone   服务端下发 done=true 时回调
 * @param {(err: Error)=>void} onError
 * @returns {()=>void} abort 函数，可随时停止生成
 */
export function postStream(url, body, { onDelta, onDone, onError } = {}) {
  const auth = useAuthStore()
  const ctrl = new AbortController()

  ;(async () => {
    try {
      const resp = await fetch(`${API_BASE}${url}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
          ...(auth.token ? { Authorization: `Bearer ${auth.token}` } : {}),
        },
        body: JSON.stringify(body),
        signal: ctrl.signal,
      })
      if (!resp.ok || !resp.body) {
        throw new Error(`HTTP ${resp.status}`)
      }

      const reader = resp.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buf = ''

      // 按 SSE 规范解析一个事件块；注意后端可能用 \r\n 换行（sse-starlette 就是），
      // 必须用 /\r?\n/ 兼容，否则永远匹配不到事件边界
      const handleBlock = (block) => {
        for (const line of block.split(/\r?\n/)) {
          if (!line.startsWith('data:')) continue
          const data = line.slice(5).trim()
          if (!data || data === '[DONE]') continue
          try {
            const obj = JSON.parse(data)
            if (obj.delta !== undefined) onDelta?.(obj.delta, obj)
            if (obj.done) { onDone?.(obj); return true }
            if (obj.error) onError?.(new Error(obj.error), obj)
          } catch {}
        }
        return false
      }

      while (true) {
        const { value, done } = await reader.read()
        if (done) {
          // 流结束时冲刷缓冲区里可能残留的最后一帧
          if (buf.trim()) handleBlock(buf)
          break
        }
        buf += decoder.decode(value, { stream: true })

        // 事件之间用空行分隔（\n\n 或 \r\n\r\n）
        let m
        const sep = /\r?\n\r?\n/g
        while ((m = sep.exec(buf)) !== null) {
          const block = buf.slice(0, m.index)
          const finished = handleBlock(block)
          buf = buf.slice(m.index + m[0].length)
          sep.lastIndex = 0
          if (finished) return
        }
      }
    } catch (e) {
      if (e.name !== 'AbortError') onError?.(e)
    }
  })()

  return () => ctrl.abort()
}

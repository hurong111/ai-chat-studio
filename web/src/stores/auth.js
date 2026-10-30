import { defineStore } from 'pinia'
import http from '../api/http'

const TOKEN_KEY = 'ai-chat-token'
const USER_KEY = 'ai-chat-user'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) || '',
    user: JSON.parse(localStorage.getItem(USER_KEY) || 'null'),
  }),
  getters: {
    isLoggedIn: (s) => !!s.token,
  },
  actions: {
    async register(payload) {
      const user = await http.post('/auth/register', payload)
      return user
    },
    async login(username, password) {
      const { access_token } = await http.post('/auth/login', { username, password })
      this.token = access_token
      localStorage.setItem(TOKEN_KEY, access_token)
      await this.fetchMe()
    },
    async fetchMe() {
      const user = await http.get('/auth/me')
      this.user = user
      localStorage.setItem(USER_KEY, JSON.stringify(user))
    },
    async updateProfile(payload) {
      const user = await http.put('/auth/me', payload)
      this.user = user
      localStorage.setItem(USER_KEY, JSON.stringify(user))
      return user
    },
    async changePassword(old_password, new_password) {
      await http.put('/auth/me/password', { old_password, new_password })
    },
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
    },
  },
})

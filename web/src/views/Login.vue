<template>
  <AuthShell title="欢迎回来" subtitle="登录后开始与本地模型对话">
    <el-form :model="form" :rules="rules" ref="formRef" @submit.prevent="onSubmit">
      <el-form-item prop="username">
        <el-input v-model="form.username" size="large" placeholder="用户名" :prefix-icon="User" />
      </el-form-item>
      <el-form-item prop="password">
        <el-input
          v-model="form.password" size="large" type="password"
          placeholder="密码" show-password :prefix-icon="Lock"
          @keyup.enter="onSubmit"
        />
      </el-form-item>

      <el-button type="primary" size="large" class="submit" :loading="loading" @click="onSubmit">
        登 录
      </el-button>

      <div class="foot">
        还没有账号？<router-link to="/register">立即注册</router-link>
      </div>
    </el-form>
  </AuthShell>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import AuthShell from '../components/AuthShell.vue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const formRef = ref()
const loading = ref(false)
const form = reactive({ username: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function onSubmit() {
  await formRef.value.validate()
  loading.value = true
  try {
    await auth.login(form.username, form.password)
    ElMessage.success('登录成功')
    router.push(route.query.redirect || '/chat')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
:deep(.el-form-item) { margin-bottom: 18px; }
:deep(.el-input__wrapper) {
  border-radius: 12px; background: #f6f5ee; box-shadow: 0 0 0 1px transparent inset;
  padding: 5px 14px; transition: background .16s ease, box-shadow .16s ease;
}
:deep(.el-input__wrapper:hover) { background: #f0efe6; }
:deep(.el-input__wrapper.is-focus) {
  background: #fff;
  box-shadow: 0 0 0 2px var(--mint) inset, 0 4px 14px rgba(16, 185, 129, .12);
}
.submit {
  width: 100%; height: 48px; margin-top: 8px; border: 0; border-radius: 13px;
  font-size: 15px; font-weight: 600; letter-spacing: .18em; color: #fff;
  background: var(--mint);
  box-shadow: 0 6px 0 #0b8f64, 0 14px 28px rgba(16, 185, 129, .22);
  transition: transform .15s ease, box-shadow .15s ease, background .15s ease;
}
.submit:hover {
  background: var(--mint-deep); transform: translateY(-2px);
  box-shadow: 0 8px 0 #0b8f64, 0 18px 34px rgba(16, 185, 129, .26);
}
.submit:active { transform: translateY(2px); box-shadow: 0 3px 0 #0b8f64; }
.foot { margin-top: 20px; text-align: center; color: var(--ink-3); font-size: 13px; }
.foot a { color: var(--mint-deep); text-decoration: none; font-weight: 600; margin-left: 2px; }
.foot a:hover { text-decoration: underline; }
</style>

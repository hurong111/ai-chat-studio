<template>
  <AuthShell title="创建账号" subtitle="只需几步，就能拥有自己的 AI 对话空间">
    <el-form :model="form" :rules="rules" ref="formRef" @submit.prevent="onSubmit">
      <el-form-item prop="username">
        <el-input v-model="form.username" size="large" placeholder="用户名（3-32 位字母/数字/下划线）" :prefix-icon="User" />
      </el-form-item>
      <el-form-item prop="password">
        <el-input v-model="form.password" size="large" type="password" placeholder="密码（至少 6 位）" show-password :prefix-icon="Lock" />
      </el-form-item>
      <el-form-item prop="confirm">
        <el-input v-model="form.confirm" size="large" type="password" placeholder="确认密码" show-password :prefix-icon="Lock" />
      </el-form-item>

      <div class="row">
        <el-form-item prop="nickname">
          <el-input v-model="form.nickname" size="large" placeholder="昵称（可选）" />
        </el-form-item>
        <el-form-item prop="email">
          <el-input v-model="form.email" size="large" placeholder="邮箱（可选）" />
        </el-form-item>
      </div>

      <el-button type="primary" size="large" class="submit" :loading="loading" @click="onSubmit">
        注 册
      </el-button>

      <div class="foot">
        已有账号？<router-link to="/login">返回登录</router-link>
      </div>
    </el-form>
  </AuthShell>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import AuthShell from '../components/AuthShell.vue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const formRef = ref()
const loading = ref(false)
const form = reactive({ username: '', password: '', confirm: '', nickname: '', email: '' })

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { pattern: /^[A-Za-z0-9_]{3,32}$/, message: '3-32 位字母/数字/下划线', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '至少 6 位', trigger: 'blur' },
  ],
  confirm: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: (_, v, cb) => (v === form.password ? cb() : cb(new Error('两次密码不一致'))), trigger: 'blur' },
  ],
}

async function onSubmit() {
  await formRef.value.validate()
  loading.value = true
  try {
    await auth.register({
      username: form.username,
      password: form.password,
      nickname: form.nickname || undefined,
      email: form.email || undefined,
    })
    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
:deep(.el-form-item) { margin-bottom: 16px; }
:deep(.el-input__wrapper) {
  border-radius: 12px; background: #f6f5ee; box-shadow: 0 0 0 1px transparent inset;
  padding: 5px 14px; transition: background .16s ease, box-shadow .16s ease;
}
:deep(.el-input__wrapper:hover) { background: #f0efe6; }
:deep(.el-input__wrapper.is-focus) {
  background: #fff;
  box-shadow: 0 0 0 2px var(--mint) inset, 0 4px 14px rgba(16, 185, 129, .12);
}
.row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.submit {
  width: 100%; height: 48px; margin-top: 6px; border: 0; border-radius: 13px;
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
.foot { margin-top: 18px; text-align: center; color: var(--ink-3); font-size: 13px; }
.foot a { color: var(--mint-deep); text-decoration: none; font-weight: 600; margin-left: 2px; }
.foot a:hover { text-decoration: underline; }

@media (max-width: 480px) {
  .row { grid-template-columns: 1fr; gap: 0; }
}
</style>

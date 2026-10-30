<template>
  <el-dialog
    v-model="visible"
    width="520px"
    class="settings-dialog"
    :show-close="false"
    destroy-on-close
  >
    <template #header>
      <div class="dlg-head">
        <div class="avatar">{{ initial }}</div>
        <div class="who">
          <div class="name">{{ auth.user?.nickname || auth.user?.username }}</div>
          <div class="sub">@{{ auth.user?.username }} · 账号与安全</div>
        </div>
        <button class="close" @click="visible = false">
          <el-icon><Close /></el-icon>
        </button>
      </div>
    </template>

    <el-tabs v-model="tab" class="setting-tabs">
      <el-tab-pane label="基本信息" name="profile">
        <el-form :model="profile" label-position="top" class="setting-form">
          <el-form-item label="用户名">
            <el-input :model-value="auth.user?.username" disabled />
          </el-form-item>
          <div class="two">
            <el-form-item label="昵称">
              <el-input v-model="profile.nickname" placeholder="给自己起个名字" />
            </el-form-item>
            <el-form-item label="邮箱">
              <el-input v-model="profile.email" placeholder="name@example.com" />
            </el-form-item>
          </div>
        </el-form>
        <button class="primary-btn" :disabled="saving" @click="saveProfile">
          {{ saving ? '保存中…' : '保存修改' }}
        </button>
      </el-tab-pane>

      <el-tab-pane label="修改密码" name="password">
        <el-form :model="pwd" :rules="pwdRules" ref="pwdRef" label-position="top" class="setting-form">
          <el-form-item label="当前密码" prop="old_password">
            <el-input v-model="pwd.old_password" type="password" show-password placeholder="请输入旧密码" />
          </el-form-item>
          <el-form-item label="新密码" prop="new_password">
            <el-input v-model="pwd.new_password" type="password" show-password placeholder="至少 6 位" />
          </el-form-item>

          <div v-if="pwd.new_password" class="strength">
            <div class="bars">
              <span v-for="i in 4" :key="i" :class="{ on: strength >= i, [`lv${strength}`]: strength >= i }" />
            </div>
            <span class="label">{{ strengthText }}</span>
          </div>

          <el-form-item label="确认新密码" prop="confirm">
            <el-input v-model="pwd.confirm" type="password" show-password placeholder="再输入一次" />
          </el-form-item>
        </el-form>
        <button class="primary-btn" :disabled="changing" @click="changePwd">
          {{ changing ? '提交中…' : '确认修改' }}
        </button>
        <p class="tip">密码使用 bcrypt 加盐哈希存储，服务器不保存明文。</p>
      </el-tab-pane>
    </el-tabs>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Close } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'

const visible = defineModel('visible', { type: Boolean })

const auth = useAuthStore()
const tab = ref('profile')
const saving = ref(false)
const changing = ref(false)
const pwdRef = ref()

const initial = computed(() =>
  (auth.user?.nickname || auth.user?.username || 'U').slice(0, 1).toUpperCase()
)

const profile = reactive({ nickname: '', email: '' })
watch(visible, (v) => {
  if (v && auth.user) {
    profile.nickname = auth.user.nickname || ''
    profile.email = auth.user.email || ''
  }
})

const pwd = reactive({ old_password: '', new_password: '', confirm: '' })
const pwdRules = {
  old_password: [{ required: true, message: '请输入旧密码', trigger: 'blur' }],
  new_password: [{ required: true, min: 6, message: '至少 6 位', trigger: 'blur' }],
  confirm: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    { validator: (_, v, cb) => (v === pwd.new_password ? cb() : cb(new Error('两次密码不一致'))), trigger: 'blur' },
  ],
}

const strength = computed(() => {
  const p = pwd.new_password || ''
  if (!p) return 0
  let s = 1
  if (p.length >= 10) s++
  if (/[A-Z]/.test(p) && /[a-z]/.test(p)) s++
  if (/\d/.test(p) || /[^A-Za-z0-9]/.test(p)) s++
  return Math.min(s, 4)
})
const strengthText = computed(() => ['', '弱', '一般', '较强', '很强'][strength.value])

async function saveProfile() {
  saving.value = true
  try {
    await auth.updateProfile(profile)
    ElMessage.success('已保存')
  } finally {
    saving.value = false
  }
}

async function changePwd() {
  await pwdRef.value.validate()
  changing.value = true
  try {
    await auth.changePassword(pwd.old_password, pwd.new_password)
    ElMessage.success('密码已更新')
    visible.value = false
    pwd.old_password = pwd.new_password = pwd.confirm = ''
  } finally {
    changing.value = false
  }
}
</script>

<style scoped>
.dlg-head { display: flex; align-items: center; gap: 12px; }
.avatar {
  width: 44px; height: 44px; border-radius: 14px; display: grid; place-items: center;
  color: #fff; font-weight: 800; font-size: 18px;
  background: var(--mint); box-shadow: 0 4px 0 #0b8f64; transform: rotate(-3deg);
}
.who { flex: 1; }
.name { font-size: 15px; font-weight: 700; color: var(--ink); }
.sub { font-size: 11.5px; color: var(--ink-3); margin-top: 2px; }
.close {
  border: 1.5px solid var(--line); background: var(--card); color: var(--ink-2);
  width: 30px; height: 30px; border-radius: 9px; cursor: pointer;
  display: grid; place-items: center; transition: all .15s ease;
}
.close:hover { background: var(--rose-soft); border-color: #f8d3d0; color: var(--rose); }

.setting-tabs { margin-top: 6px; }
.setting-tabs :deep(.el-tabs__header) { margin-bottom: 20px; }
.setting-tabs :deep(.el-tabs__item) { font-size: 13.5px; }
.setting-tabs :deep(.el-tabs__active-bar) {
  background: var(--mint); height: 3px; border-radius: 2px;
}

.setting-form :deep(.el-form-item__label) {
  font-size: 12.5px; color: var(--ink-2); padding-bottom: 4px;
}
.setting-form :deep(.el-input__wrapper) {
  border-radius: 11px; background: #f6f5ee; box-shadow: 0 0 0 1px transparent inset;
  transition: background .16s ease, box-shadow .16s ease;
}
.setting-form :deep(.el-input__wrapper:hover) { background: #f0efe6; }
.setting-form :deep(.el-input__wrapper.is-focus) {
  background: #fff;
  box-shadow: 0 0 0 2px var(--mint) inset, 0 4px 14px rgba(16, 185, 129, .1);
}
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }

.primary-btn {
  width: 100%; height: 42px; border: 0; border-radius: 12px; cursor: pointer;
  color: #fff; font-size: 14px; font-weight: 600; letter-spacing: .1em;
  background: var(--mint);
  box-shadow: 0 4px 0 #0b8f64, 0 10px 22px rgba(16, 185, 129, .2);
  margin-top: 4px; transition: transform .15s ease, background .15s ease;
}
.primary-btn:hover:not(:disabled) { background: var(--mint-deep); transform: translateY(-1px); }
.primary-btn:active:not(:disabled) { transform: translateY(2px); box-shadow: 0 2px 0 #0b8f64; }
.primary-btn:disabled { opacity: .55; cursor: not-allowed; box-shadow: none; }

.strength { display: flex; align-items: center; gap: 10px; margin: -6px 0 14px; }
.bars { display: flex; gap: 4px; flex: 1; }
.bars span { height: 5px; flex: 1; border-radius: 99px; background: #f0efe6; transition: background .25s ease; }
.bars span.on.lv1 { background: var(--rose); }
.bars span.on.lv2 { background: var(--apricot); }
.bars span.on.lv3 { background: var(--mint); }
.bars span.on.lv4 { background: var(--mint-deep); }
.strength .label { font-size: 11px; color: var(--ink-2); width: 28px; text-align: right; }

.tip { font-size: 11px; color: var(--ink-3); text-align: center; margin: 10px 0 0; }

@media (max-width: 520px) {
  .two { grid-template-columns: 1fr; gap: 0; }
}
</style>

<style>
.settings-dialog { border-radius: 20px; overflow: hidden; box-shadow: var(--shadow-l); }
.settings-dialog .el-dialog__header { margin: 0; padding: 18px 22px 12px; border-bottom: 1.5px solid var(--line); }
.settings-dialog .el-dialog__body { padding: 16px 22px 22px; }
</style>

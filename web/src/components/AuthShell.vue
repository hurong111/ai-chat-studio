<template>
  <div class="auth-shell">
    <!-- 漂浮的糖果色装饰 -->
    <div class="deco deco-mint" />
    <div class="deco deco-sky" />
    <div class="deco deco-apricot" />
    <div class="deco deco-rose" />

    <section class="brand-side">
      <div class="brand-row">
        <div class="logo">✦</div>
        <span class="brand-name">AI Chat Studio</span>
      </div>

      <h1>
        把聊天，<br />
        变成一件<span class="marker">轻快的小事</span>
      </h1>
      <p class="sub">
        自己训练的 68M 中文小模型，从预训练到全量微调、LoRA，
        再到远端大模型，都在这一个干净的窗口里。
      </p>

      <ul class="features">
        <li>
          <span class="chip mint">🧠</span>
          <div><b>多模型自由切换</b><small>本地全量微调 / LoRA / 远端 API</small></div>
        </li>
        <li>
          <span class="chip sky">⚡</span>
          <div><b>流式对话</b><small>逐字输出，随时可以喊停</small></div>
        </li>
        <li>
          <span class="chip apricot">🔐</span>
          <div><b>账号安全</b><small>bcrypt 加盐哈希，密码不留明文</small></div>
        </li>
        <li>
          <span class="chip rose">💾</span>
          <div><b>会话自动保存</b><small>新建、重命名、删除，随开随聊</small></div>
        </li>
      </ul>

      <div class="stats">
        <div><b>68M</b><small>参数量</small></div>
        <i class="divider" />
        <div><b>3</b><small>模型类型</small></div>
        <i class="divider" />
        <div><b>1.2GB</b><small>训练语料</small></div>
      </div>
    </section>

    <section class="form-side">
      <div class="card">
        <div class="card-head">
          <span class="hi">👋</span>
          <h2>{{ title }}</h2>
          <p>{{ subtitle }}</p>
        </div>
        <slot />
      </div>
      <p class="copyright">© 2026 AI Chat Studio · 课程设计演示系统</p>
    </section>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: '欢迎回来' },
  subtitle: { type: String, default: '登录后继续你的对话' },
})
</script>

<style scoped>
.auth-shell {
  position: relative; min-height: 100vh; display: flex; overflow: hidden;
  background:
    radial-gradient(#e7e4d8 1px, transparent 1px) 0 0 / 26px 26px,
    var(--paper);
}

/* ---------- 糖果色漂浮装饰 ---------- */
.deco { position: absolute; border-radius: 50%; pointer-events: none; }
.deco-mint {
  width: 150px; height: 150px; background: var(--mint-soft);
  border: 2px solid #c9eedd; top: 12%; left: 6%;
  animation: float 7s ease-in-out infinite;
}
.deco-sky {
  width: 90px; height: 90px; background: var(--sky-soft);
  border: 2px solid #cfe6f8; top: 66%; left: 12%;
  animation: float 9s ease-in-out 1s infinite;
}
.deco-apricot {
  width: 60px; height: 60px; background: var(--apricot-soft);
  border: 2px solid #f6ddb8; top: 30%; left: 44%;
  animation: float 8s ease-in-out .5s infinite;
}
.deco-rose {
  width: 44px; height: 44px; background: var(--rose-soft);
  border: 2px solid #f8d3d0; top: 78%; left: 42%;
  animation: float 6s ease-in-out 1.5s infinite;
}
@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-14px); }
}

/* ---------- 左侧品牌区 ---------- */
.brand-side {
  position: relative; z-index: 1; flex: 1 1 56%;
  padding: 64px 72px; display: flex; flex-direction: column; justify-content: center;
}
.brand-row { display: flex; align-items: center; gap: 10px; margin-bottom: 48px; }
.logo {
  width: 40px; height: 40px; border-radius: 13px; display: grid; place-items: center;
  background: var(--mint); color: #fff; font-size: 19px;
  box-shadow: 0 6px 0 #0b8f64; transform: rotate(-4deg);
}
.brand-name { font-weight: 700; letter-spacing: .02em; color: var(--ink); font-size: 16px; }

.brand-side h1 {
  font-size: 46px; line-height: 1.32; margin: 0 0 18px; font-weight: 800;
  color: var(--ink); letter-spacing: .01em;
}
/* 荧光笔划重点的效果，代替烂大街的渐变文字 */
.marker {
  background: linear-gradient(transparent 58%, #a9e9cd 58%, #a9e9cd 92%, transparent 92%);
  padding: 0 4px; white-space: nowrap;
}
.sub {
  color: var(--ink-2); font-size: 15px; line-height: 1.9;
  max-width: 460px; margin: 0 0 44px;
}

.features { list-style: none; margin: 0; padding: 0; display: grid; gap: 16px; max-width: 460px; }
.features li { display: flex; gap: 13px; align-items: center; }
.chip {
  width: 38px; height: 38px; border-radius: 12px; display: grid; place-items: center;
  font-size: 16px; flex-shrink: 0; border: 1px solid transparent;
}
.chip.mint { background: var(--mint-soft); border-color: #c9eedd; }
.chip.sky { background: var(--sky-soft); border-color: #cfe6f8; }
.chip.apricot { background: var(--apricot-soft); border-color: #f6ddb8; }
.chip.rose { background: var(--rose-soft); border-color: #f8d3d0; }
.features b { display: block; font-size: 14px; color: var(--ink); font-weight: 600; }
.features small { color: var(--ink-2); font-size: 12.5px; }

.stats { display: flex; align-items: center; gap: 28px; margin-top: 52px; }
.stats b { display: block; font-size: 22px; color: var(--ink); font-weight: 800; }
.stats small { color: var(--ink-3); font-size: 12px; }
.divider { width: 1px; height: 26px; background: var(--line); }

/* ---------- 右侧表单区 ---------- */
.form-side {
  position: relative; z-index: 1; flex: 1 1 44%;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 40px 32px;
}
.card {
  width: min(430px, 100%);
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 24px; padding: 36px 36px 32px;
  box-shadow: var(--shadow-l);
  animation: pop .5s cubic-bezier(.2, .8, .25, 1) both;
}
@keyframes pop {
  from { opacity: 0; transform: translateY(16px) scale(.98); }
  to { opacity: 1; transform: none; }
}
.card-head { margin-bottom: 26px; }
.card-head .hi { font-size: 26px; display: inline-block; animation: wave 2.4s ease-in-out infinite; transform-origin: 70% 80%; }
@keyframes wave { 0%, 60%, 100% { transform: rotate(0) } 70% { transform: rotate(16deg) } 80% { transform: rotate(-8deg) } 90% { transform: rotate(12deg) } }
.card-head h2 { margin: 10px 0 6px; font-size: 25px; color: var(--ink); font-weight: 800; letter-spacing: .01em; }
.card-head p { margin: 0; color: var(--ink-3); font-size: 13px; }

.copyright { color: var(--ink-3); font-size: 11.5px; margin-top: 24px; }

@media (max-width: 980px) {
  .brand-side { display: none; }
  .form-side { flex: 1 1 100%; }
  .auth-shell { justify-content: center; }
}
</style>

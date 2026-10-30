<template>
  <div class="switcher">
    <div class="prefix">
      <span class="pulse" />
      模型
    </div>

    <el-select
      :model-value="modelValue"
      class="select"
      size="large"
      :teleported="true"
      @update:model-value="$emit('update:modelValue', $event)"
      @change="$emit('change', $event)"
    >
      <el-option-group v-for="g in groups" :key="g.label" :label="g.label">
        <el-option
          v-for="m in g.models"
          :key="m.id"
          :value="m.id"
          :label="m.name"
          :disabled="!m.is_available"
        >
          <div class="opt">
            <span class="dot" :class="m.provider" />
            <div class="opt-main">
              <div class="opt-name">
                {{ m.name }}
                <span class="kind" :class="m.kind">{{ kindLabel(m.kind) }}</span>
                <span v-if="!m.is_available" class="off">未配置</span>
              </div>
              <div class="opt-desc">{{ m.description || m.id }}</div>
            </div>
            <span v-if="m.id === modelValue" class="check">✓</span>
          </div>
        </el-option>
      </el-option-group>
    </el-select>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  models: { type: Array, default: () => [] },
  modelValue: { type: String, default: '' },
})
defineEmits(['update:modelValue', 'change'])

const groups = computed(() => {
  const local = props.models.filter((m) => m.provider === 'local')
  const remote = props.models.filter((m) => m.provider !== 'local')
  const out = []
  if (local.length) out.push({ label: '本地模型（自训练 .pth）', models: local })
  if (remote.length) out.push({ label: '远端 / 演示模型', models: remote })
  return out
})

function kindLabel(kind) {
  return ({ full_sft: '全量SFT', lora: 'LoRA', remote: 'API', pretrain: '预训练', mock: '演示' })[kind] || kind
}
</script>

<style scoped>
.switcher { display: flex; align-items: center; gap: 10px; }
.prefix {
  display: flex; align-items: center; gap: 6px; font-size: 13px;
  color: var(--ink-2); white-space: nowrap;
}
.pulse {
  width: 7px; height: 7px; border-radius: 50%; background: var(--mint);
  box-shadow: 0 0 0 3px rgba(16, 185, 129, .15);
  animation: breathe 2.4s ease-in-out infinite;
}
@keyframes breathe { 0%, 100% { opacity: 1 } 50% { opacity: .4 } }
.select { width: 310px; }
.select :deep(.el-select__wrapper) {
  border-radius: 12px; box-shadow: 0 0 0 1.5px var(--line) inset;
  background: var(--card); min-height: 40px;
  transition: box-shadow .16s ease;
}
.select :deep(.el-select__wrapper:hover) { box-shadow: 0 0 0 1.5px #c9eedd inset; }
.select :deep(.el-select__wrapper.is-focused) {
  box-shadow: 0 0 0 2px var(--mint) inset, 0 4px 14px rgba(16, 185, 129, .12);
}

.opt { display: flex; align-items: center; gap: 10px; padding: 4px 2px; min-width: 280px; }
.dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; background: #b6bcc6; }
.dot.local { background: var(--mint); }
.dot.deepseek, .dot.remote { background: var(--sky); }
.opt-main { flex: 1; min-width: 0; }
.opt-name {
  display: flex; align-items: center; gap: 6px; font-size: 13.5px;
  color: var(--ink); font-weight: 500;
}
.opt-desc {
  font-size: 11.5px; color: var(--ink-3); margin-top: 2px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 230px;
}
.kind {
  font-size: 10.5px; padding: 0 6px; border-radius: 999px;
  background: var(--mint-soft); color: var(--mint-deep); line-height: 16px;
  border: 1px solid #c9eedd;
}
.kind.lora { background: var(--apricot-soft); color: #c47d1a; border-color: #f6ddb8; }
.kind.remote { background: var(--sky-soft); color: #1d6fb8; border-color: #cfe6f8; }
.off { font-size: 10.5px; color: var(--rose); }
.check { color: var(--mint-deep); font-weight: 700; }

@media (max-width: 900px) {
  .select { width: 210px; }
  .prefix { display: none; }
}
</style>

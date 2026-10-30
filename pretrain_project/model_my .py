import math
import torch
import torch.nn.functional as F
from torch import nn
from transformers.activations import ACT2FN
from transformers import PreTrainedModel, GenerationMixin, PretrainedConfig
from transformers.modeling_outputs import MoeCausalLMOutputWithPast

# 类1：TransformerConfig —— 模型配置类（“参数清单”）
# 作用：集中保存模型所有超参数（层数、隐藏维度、头数、词表大小等），方便初始化、保存、加载模型
#       本身不参与计算，只是给下面各个模块提供配置值。
#       继承 PretrainedConfig，是为了能被 transformers 识别、保存和加载。
class TransformerConfig(PretrainedConfig):
    def __init__(self, hidden_size=768, num_hidden_layers=8, **kwargs):
        super().__init__(**kwargs)
        self.hidden_size = hidden_size                    # 隐藏层维度（每个 token 的向量长度）
        self.num_hidden_layers = num_hidden_layers        # Transformer Block 的层数
        self.dropout = kwargs.get("dropout", 0.0)
        self.vocab_size = kwargs.get("vocab_size", 6400)  # 词表大小
        self.bos_token_id = kwargs.get("bos_token_id", 1)
        self.eos_token_id = kwargs.get("eos_token_id", 2)
        self.flash_attn = kwargs.get("flash_attn", True)  # 是否启用 Flash Attention
        self.num_attention_heads = kwargs.get("num_attention_heads", 8)   # Q 头数
        self.num_key_value_heads = kwargs.get("num_key_value_heads", 4)   # K/V 头数（GQA）
        self.head_dim = kwargs.get("head_dim", self.hidden_size // self.num_attention_heads)
        self.hidden_act = kwargs.get("hidden_act", 'silu')                # MLP 激活函数
        self.intermediate_size = kwargs.get("intermediate_size",
                                            math.ceil(hidden_size * math.pi / 64) * 64)
        self.max_position_embeddings = kwargs.get("max_position_embeddings", 32768)
        self.rms_norm_eps = kwargs.get("rms_norm_eps", 1e-6)
        self.rope_theta = kwargs.get("rope_theta", 1e6)                   # RoPE 频率基数
        self.tie_word_embeddings = kwargs.get("tie_word_embeddings", True) # 输入嵌入与输出头共享权重
        self.inference_rope_scaling = kwargs.get("inference_rope_scaling", False)
        self.rope_scaling = {
            "beta_fast": 32,
            "beta_slow": 1,
            "factor": 16,
            "original_max_position_embeddings": 2048,
            "attention_factor": 1.0,
            "type": "yarn"
        } if self.inference_rope_scaling else None


# 类2：RMSNorm —— 归一化层
# 作用：把每个 token 的向量按“均方根”缩放，使数值稳定；
#  仅缩放，不做中心化，比 LayerNorm 少一步“减均值”，计算更快，是 Llama 系列的标准做法。
#  参数：dim为向量维度，eps防止除零；weight是可学习缩放参数。
class RMSNorm(torch.nn.Module):
    def __init__(self, dim: int, eps: float = 1e-5):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(dim))   # 可学习的缩放系数

    def _norm(self, x):
        return x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)

    def forward(self, x):
        return self.weight * self._norm(x.float()).type_as(x)

# 普通函数（不是类）：
# precompute_freqs_cis —— 预计算 RoPE 旋转位置编码的 cos / sin 表
# apply_rotary_pos_emb —— 把 cos/sin 作用到 Q、K 上（旋转位置编码）
# repeat_kv           —— GQA：把少量 K/V 头复制多份，对齐 Q 头数
# =====================================================================
def precompute_freqs_cis(dim: int, end: int = int(32 * 1024),
                         rope_base: float = 1e6, rope_scaling: dict = None):
    """预先算好每个位置、每个维度对应的 cos 和 sin，后面直接查表。"""
    freqs, attn_factor = 1.0 / (rope_base ** (torch.arange(0, dim, 2)[: (dim // 2)].float() / dim)), 1.0

    if rope_scaling is not None:  # YaRN：长上下文外推
        orig_max, factor, beta_fast, beta_slow, attn_factor = (
            rope_scaling.get("original_max_position_embeddings", 2048),
            rope_scaling.get("factor", 16),
            rope_scaling.get("beta_fast", 32.0),
            rope_scaling.get("beta_slow", 1.0),
            rope_scaling.get("attention_factor", 1.0)
        )
        if end / orig_max > 1.0:
            inv_dim = lambda b: (dim * math.log(orig_max / (b * 2 * math.pi))) / (2 * math.log(rope_base))
            low = max(math.floor(inv_dim(beta_fast)), 0)
            high = min(math.ceil(inv_dim(beta_slow)), dim // 2 - 1)
            ramp = torch.clamp((torch.arange(dim // 2, device=freqs.device).float() - low)
                               / max(high - low, 0.001), 0, 1)
            freqs = freqs * (1 - ramp + ramp / factor)

    t = torch.arange(end, device=freqs.device)          # 位置索引 0,1,2,...
    freqs = torch.outer(t, freqs).float()               # 位置 × 频率
    freqs_cos = torch.cat([torch.cos(freqs), torch.cos(freqs)], dim=-1) * attn_factor
    freqs_sin = torch.cat([torch.sin(freqs), torch.sin(freqs)], dim=-1) * attn_factor
    return freqs_cos, freqs_sin


def apply_rotary_pos_emb(q, k, cos, sin, unsqueeze_dim=1):
    """对 Q、K 做旋转（后半段取负再拼接），从而把位置信息编码进去。"""
    def rotate_half(x):
        return torch.cat((-x[..., x.shape[-1] // 2:], x[..., : x.shape[-1] // 2]), dim=-1)

    q_embed = ((q * cos.unsqueeze(unsqueeze_dim)) + (rotate_half(q) * sin.unsqueeze(unsqueeze_dim))).to(q.dtype)
    k_embed = ((k * cos.unsqueeze(unsqueeze_dim)) + (rotate_half(k) * sin.unsqueeze(unsqueeze_dim))).to(k.dtype)
    return q_embed, k_embed


def repeat_kv(x: torch.Tensor, n_rep: int) -> torch.Tensor:
    """GQA：每个 K/V 头被 n_rep 个 Q 头共享，这里把 K/V 复制扩展。"""
    bs, slen, num_key_value_heads, head_dim = x.shape
    if n_rep == 1:
        return x
    return (x[:, :, :, None, :]
            .expand(bs, slen, num_key_value_heads, n_rep, head_dim)
            .reshape(bs, slen, num_key_value_heads * n_rep, head_dim))


# 类3：Attention —— 因果多头自注意力模块（GQA + RoPE + KV Cache + Flash Attention）
# 作用：实现分组查询注意力，让每个 token 去“看”它前面的 token，按相关程度加权汇总信息。
#       Q/K/V 线性投影 → QK 归一化 → 加 RoPE → 算相似度 → 掩码 → Softmax
#       → 加权求和 → 输出投影。支持增量解码时复用 KV 缓存，降低重复计算。
class Attention(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.num_key_value_heads = (config.num_attention_heads
                                    if config.num_key_value_heads is None
                                    else config.num_key_value_heads)
        assert config.num_attention_heads % self.num_key_value_heads == 0
        self.n_local_heads = config.num_attention_heads
        self.n_local_kv_heads = self.num_key_value_heads
        self.n_rep = self.n_local_heads // self.n_local_kv_heads
        self.head_dim = config.head_dim
        self.is_causal = True

        # Q/K/V/输出 四个线性投影（无 bias）
        self.q_proj = nn.Linear(config.hidden_size, config.num_attention_heads * self.head_dim, bias=False)
        self.k_proj = nn.Linear(config.hidden_size, self.num_key_value_heads * self.head_dim, bias=False)
        self.v_proj = nn.Linear(config.hidden_size, self.num_key_value_heads * self.head_dim, bias=False)
        self.o_proj = nn.Linear(config.num_attention_heads * self.head_dim, config.hidden_size, bias=False)

        # Q/K 在 head 维度上单独归一化（Llama3 风格）
        self.q_norm = RMSNorm(self.head_dim, eps=config.rms_norm_eps)
        self.k_norm = RMSNorm(self.head_dim, eps=config.rms_norm_eps)

        self.attn_dropout = nn.Dropout(config.dropout)
        self.resid_dropout = nn.Dropout(config.dropout)
        self.dropout = config.dropout
        self.flash = hasattr(torch.nn.functional, 'scaled_dot_product_attention') and config.flash_attn

    def forward(self, x, position_embeddings, past_key_value=None, use_cache=False, attention_mask=None):
        bsz, seq_len, _ = x.shape

        # 1. 线性投影得到 Q、K、V，并拆成多头
        xq, xk, xv = self.q_proj(x), self.k_proj(x), self.v_proj(x)
        xq = xq.view(bsz, seq_len, self.n_local_heads, self.head_dim)
        xk = xk.view(bsz, seq_len, self.n_local_kv_heads, self.head_dim)
        xv = xv.view(bsz, seq_len, self.n_local_kv_heads, self.head_dim)

        # 2. Q/K 归一化 + 注入旋转位置编码
        xq, xk = self.q_norm(xq), self.k_norm(xk)
        cos, sin = position_embeddings
        xq, xk = apply_rotary_pos_emb(xq, xk, cos, sin)

        # 3. 增量解码：把历史的 K/V 和当前拼起来
        if past_key_value is not None:
            xk = torch.cat([past_key_value[0], xk], dim=1)
            xv = torch.cat([past_key_value[1], xv], dim=1)
        past_kv = (xk, xv) if use_cache else None

        # 4. 转成 [batch, heads, seq, head_dim]，GQA 复制 K/V 头
        xq = xq.transpose(1, 2)
        xk = repeat_kv(xk, self.n_rep).transpose(1, 2)
        xv = repeat_kv(xv, self.n_rep).transpose(1, 2)

        # 5. 计算注意力
        if self.flash and (seq_len > 1) and (not self.is_causal or past_key_value is None) \
                and (attention_mask is None or torch.all(attention_mask == 1)):
            output = F.scaled_dot_product_attention(
                xq, xk, xv,
                dropout_p=self.dropout if self.training else 0.0,
                is_causal=self.is_causal)
        else:
            scores = (xq @ xk.transpose(-2, -1)).float() / math.sqrt(self.head_dim)
            if self.is_causal:  # 因果掩码：不能看后面的 token
                scores[:, :, :, -seq_len:] += torch.full(
                    (seq_len, seq_len), float("-inf"), device=scores.device).triu(1)
            if attention_mask is not None:  # padding 掩码
                scores += (1.0 - attention_mask.unsqueeze(1).unsqueeze(2)) * -1e9
            scores = F.softmax(scores.float(), dim=-1).type_as(xq)
            scores = self.attn_dropout(scores)
            output = scores @ xv

        # 6. 合并多头，投影回 hidden_size
        output = output.transpose(1, 2).reshape(bsz, seq_len, -1)
        output = self.resid_dropout(self.o_proj(output))
        return output, past_kv


# 类4：FeedForward —— 前馈神经网络模块（MLP）
# 作用：对每个 token 单独做“升维 → 激活 → 降维”的非线性变换，提升模型表达能力。
#       用 SwiGLU 结构（gate_proj 过激活后与 up_proj 相乘），
#       负责给注意力结果补充特征表达能力。

class FeedForward(nn.Module):
    def __init__(self, config: TransformerConfig):
        super().__init__()
        if config.intermediate_size is None:
            intermediate_size = int(config.hidden_size * 8 / 3)
            config.intermediate_size = 64 * ((intermediate_size + 64 - 1) // 64)
        self.gate_proj = nn.Linear(config.hidden_size, config.intermediate_size, bias=False)
        self.down_proj = nn.Linear(config.intermediate_size, config.hidden_size, bias=False)
        self.up_proj = nn.Linear(config.hidden_size, config.intermediate_size, bias=False)
        self.dropout = nn.Dropout(config.dropout)
        self.act_fn = ACT2FN[config.hidden_act]     # 默认 silu

    def forward(self, x):
        return self.dropout(self.down_proj(self.act_fn(self.gate_proj(x)) * self.up_proj(x)))


# 类5：TransformerBlock ——Transformer单层解码器块，一个 Transformer 层（Decoder Block）
# 作用：基础重复单元，多层堆叠构成完整大模型主干
# 把“注意力 + MLP”组装成一层，采用 Pre-LN 结构并加残差连接：
#       x = x + Attention(Norm(x))
#       x = x + MLP(Norm(x))
#       整个 GPT 模型就是把这一层重复 N 次。
class TransformerBlock(nn.Module):
    def __init__(self, layer_id: int, config: TransformerConfig):
        super().__init__()
        self.self_attn = Attention(config)
        self.input_layernorm = RMSNorm(config.hidden_size, eps=config.rms_norm_eps)
        self.post_attention_layernorm = RMSNorm(config.hidden_size, eps=config.rms_norm_eps)
        self.mlp = FeedForward(config)

    def forward(self, hidden_states, position_embeddings, past_key_value=None,
                use_cache=False, attention_mask=None):
        residual = hidden_states
        hidden_states, present_key_value = self.self_attn(
            self.input_layernorm(hidden_states), position_embeddings,
            past_key_value, use_cache, attention_mask)
        hidden_states += residual                                  # 注意力残差
        hidden_states = hidden_states + self.mlp(self.post_attention_layernorm(hidden_states))  # MLP 残差
        return hidden_states, present_key_value


# 类6：GPTModel —— 模型主干网络（Backbone）
# 作用：Token 嵌入 → 堆叠 N 个 TransformerBlock → 最终 RMSNorm。
#       同时负责：预计算并保存 RoPE 的 cos/sin 表、管理每层 KV 缓存。
#       输出的是“隐藏状态”，还没有映射成词表概率。
class GPTModel(nn.Module):
    def __init__(self, config: TransformerConfig):
        super().__init__()
        self.config = config
        self.vocab_size = config.vocab_size
        self.num_hidden_layers = config.num_hidden_layers

        self.embed_tokens = nn.Embedding(config.vocab_size, config.hidden_size)  # 词嵌入
        self.dropout = nn.Dropout(config.dropout)
        self.layers = nn.ModuleList([TransformerBlock(l, config)
                                     for l in range(self.num_hidden_layers)])
        self.norm = RMSNorm(config.hidden_size, eps=config.rms_norm_eps)         # 最终归一化

        # 预计算 RoPE 的 cos/sin；persistent=False 表示不写进 checkpoint
        freqs_cos, freqs_sin = precompute_freqs_cis(
            dim=config.head_dim, end=config.max_position_embeddings,
            rope_base=config.rope_theta, rope_scaling=config.rope_scaling)
        self.register_buffer("freqs_cos", freqs_cos, persistent=False)
        self.register_buffer("freqs_sin", freqs_sin, persistent=False)

    def forward(self, input_ids, attention_mask=None, past_key_values=None,
                use_cache=False, **kwargs):
        batch_size, seq_length = input_ids.shape
        if hasattr(past_key_values, 'layers'):
            past_key_values = None
        past_key_values = past_key_values or [None] * len(self.layers)

        # 已有缓存时，start_pos = 历史 token 数；否则从 0 开始
        start_pos = past_key_values[0][0].shape[1] if past_key_values[0] is not None else 0

        hidden_states = self.dropout(self.embed_tokens(input_ids))

        # meta 设备初始化时 buffer 会变全 0，这里检测并重算
        if self.freqs_cos[0, 0] == 0:
            freqs_cos, freqs_sin = precompute_freqs_cis(
                dim=self.config.head_dim, end=self.config.max_position_embeddings,
                rope_base=self.config.rope_theta, rope_scaling=self.config.rope_scaling)
            self.freqs_cos = freqs_cos.to(hidden_states.device)
            self.freqs_sin = freqs_sin.to(hidden_states.device)

        # 只取当前位置对应的那段 cos/sin
        position_embeddings = (
            self.freqs_cos[start_pos:start_pos + seq_length],
            self.freqs_sin[start_pos:start_pos + seq_length])

        presents = []
        for layer, past_key_value in zip(self.layers, past_key_values):
            hidden_states, present = layer(
                hidden_states, position_embeddings,
                past_key_value=past_key_value,
                use_cache=use_cache, attention_mask=attention_mask)
            presents.append(present)

        hidden_states = self.norm(hidden_states)
        return hidden_states, presents


# 类7：GPTForCausalLM —— 完整的因果语言模型，对外入口（可直接使用/生成）
# 作用：在主干 GPTModel 之上加一个 lm_head（把隐藏状态映射成词表大小的
#       logits），负责“预测下一个 token”；
#       训练时计算交叉熵 loss，推理时提供 generate() 逐字生成。
#       继承 PreTrainedModel/GenerationMixin，兼容 transformers 的
#       from_pretrained、save_pretrained、generate 等接口。
class GPTForCausalLM(PreTrainedModel, GenerationMixin):
    config_class = TransformerConfig
    _tied_weights_keys = {"lm_head.weight": "model.embed_tokens.weight"}

    def __init__(self, config: TransformerConfig = None):
        self.config = config or TransformerConfig()
        super().__init__(self.config)
        self.model = GPTModel(self.config)
        self.lm_head = nn.Linear(self.config.hidden_size, self.config.vocab_size, bias=False)
        if self.config.tie_word_embeddings:
            self.model.embed_tokens.weight = self.lm_head.weight   # 输入输出共享权重
        self.post_init()

    def forward(self, input_ids, attention_mask=None, past_key_values=None, use_cache=False,
                logits_to_keep=0, labels=None, **kwargs):
        hidden_states, past_key_values = self.model(
            input_ids, attention_mask, past_key_values, use_cache, **kwargs)

        slice_indices = slice(-logits_to_keep, None) if isinstance(logits_to_keep, int) else logits_to_keep
        logits = self.lm_head(hidden_states[:, slice_indices, :])

        # 因果语言模型 loss：第 i 个位置预测第 i+1 个 token
        loss = None
        if labels is not None:
            x = logits[..., :-1, :].contiguous()
            y = labels[..., 1:].contiguous()
            loss = F.cross_entropy(x.view(-1, x.size(-1)), y.view(-1), ignore_index=-100)

        return MoeCausalLMOutputWithPast(loss=loss, logits=logits,
                                         past_key_values=past_key_values,
                                         hidden_states=hidden_states)

    @torch.inference_mode()
    def generate(self, inputs=None, attention_mask=None, max_new_tokens=8192,
                 temperature=0.85, top_p=0.85, top_k=50, eos_token_id=2,
                 streamer=None, use_cache=True, num_return_sequences=1,
                 do_sample=True, repetition_penalty=1.0, **kwargs):
        """自回归生成：每次用 KV 缓存只算新 token，并做 top-k / top-p 采样。"""
        input_ids = kwargs.pop("input_ids", inputs).repeat(num_return_sequences, 1)
        attention_mask = attention_mask.repeat(num_return_sequences, 1) if attention_mask is not None else None
        past_key_values = kwargs.pop("past_key_values", None)
        finished = torch.zeros(input_ids.shape[0], dtype=torch.bool, device=input_ids.device)
        if streamer:
            streamer.put(input_ids.cpu())

        for _ in range(max_new_tokens):
            past_len = past_key_values[0][0].shape[1] if past_key_values else 0
            outputs = self.forward(input_ids[:, past_len:], attention_mask,
                                   past_key_values, use_cache=use_cache, **kwargs)
            if attention_mask is not None:
                attention_mask = torch.cat(
                    [attention_mask, attention_mask.new_ones(attention_mask.shape[0], 1)], -1)
            logits = outputs.logits[:, -1, :] / temperature

            # 重复惩罚
            if repetition_penalty != 1.0:
                for i in range(input_ids.shape[0]):
                    seen = torch.unique(input_ids[i])
                    score = logits[i, seen]
                    logits[i, seen] = torch.where(score > 0,
                                                  score / repetition_penalty,
                                                  score * repetition_penalty)
            # top-k 截断
            if top_k > 0:
                logits[logits < torch.topk(logits, top_k)[0][..., -1, None]] = -float('inf')
            # top-p（核采样）截断
            if top_p < 1.0:
                sorted_logits, sorted_indices = torch.sort(logits, descending=True)
                mask = torch.cumsum(torch.softmax(sorted_logits, dim=-1), dim=-1) > top_p
                mask[..., 1:], mask[..., 0] = mask[..., :-1].clone(), 0
                logits[mask.scatter(1, sorted_indices, mask)] = -float('inf')

            next_token = (torch.multinomial(torch.softmax(logits, dim=-1), num_samples=1)
                          if do_sample else torch.argmax(logits, dim=-1, keepdim=True))
            if eos_token_id is not None:
                next_token = torch.where(finished.unsqueeze(-1),
                                         next_token.new_full((next_token.shape[0], 1), eos_token_id),
                                         next_token)
            input_ids = torch.cat([input_ids, next_token], dim=-1)
            past_key_values = outputs.past_key_values if use_cache else None
            if streamer:
                streamer.put(next_token.cpu())
            if eos_token_id is not None:
                finished |= next_token.squeeze(-1).eq(eos_token_id)
                if finished.all():
                    break

        if streamer:
            streamer.end()
        if kwargs.get("return_kv"):
            return {'generated_ids': input_ids, 'past_kv': past_key_values}
        return input_ids


# 简单测试：构造一个小模型，跑一次前向 + 生成，验证代码可用
if __name__ == "__main__":
    cfg = TransformerConfig(hidden_size=128, num_hidden_layers=2,
                            num_attention_heads=4, num_key_value_heads=2, vocab_size=6400)
    model = GPTForCausalLM(cfg)
    ids = torch.randint(0, 6400, (1, 8))
    out = model(ids, labels=ids)
    print("hidden_state 形状:", tuple(out.hidden_states.shape))  # [1, 8, 128]
    print("logits 形状:", tuple(out.logits.shape))               # [1, 8, 6400]
    print("loss:", round(out.loss.item(), 4))
    print("参数量:", sum(p.numel() for p in model.parameters()))
    gen = model.generate(ids, max_new_tokens=3, do_sample=False)
    print("生成结果 ids 形状:", tuple(gen.shape))                # [1, 11]

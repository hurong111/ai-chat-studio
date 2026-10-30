"""预训练模型终端测试脚本。

修复记录：
- vocab_size 734 -> 6400（与训练用 tokenizer 一致，否则 embedding 形状对不上）
- strict=True，让权重不匹配直接报错，不静默失败
- 只 decode 新增 token，不再复读输入
- eos_token_id=3（预训练语料的 EOS 是 [EOS]=3，不是 <|im_end|>=6）
- 设备自动选择 cuda/cpu
"""
import argparse

import torch
from transformers import AutoTokenizer
from model.model_my import TransformerConfig, GPTForCausalLM

ap = argparse.ArgumentParser()
ap.add_argument("--weight", default="../checkpoints/pretrain_768.pth", help="权重路径")
ap.add_argument("--eos", type=int, default=3, help="终止符id：3=[EOS]（预训练），6=<|im_end|>（SFT对话）")
args = ap.parse_args()

tokenizer = AutoTokenizer.from_pretrained("./modelT")
device = "cuda" if torch.cuda.is_available() else "cpu"

cfg = TransformerConfig(hidden_size=768, num_hidden_layers=8, vocab_size=6400)
model = GPTForCausalLM(cfg)
weights = torch.load(args.weight, map_location="cpu")
model.load_state_dict(weights, strict=True)
model = model.to(device).eval()

print(f"===== 模型测试（device={device}，weight={args.weight}，eos={args.eos}，输入 q 退出）=====")
while True:
    prompt = input("\n用户：")
    if prompt.strip() in ("q", "quit", "exit"):
        break
    ids = tokenizer(prompt, return_tensors="pt", add_special_tokens=False).input_ids.to(device)
    with torch.no_grad():
        gen_ids = model.generate(
            ids, max_new_tokens=60, do_sample=True,
            temperature=0.8, top_p=0.9, repetition_penalty=1.2,
            pad_token_id=0, eos_token_id=args.eos,
        )
    # 只 decode 新增部分
    result = tokenizer.decode(gen_ids[0][ids.shape[1]:], skip_special_tokens=True)
    print("模型：", result)

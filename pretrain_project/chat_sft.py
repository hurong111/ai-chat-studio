"""
SFT / LoRA 模型对话脚本（用于作业 05 调用模型截图）
用法：
    python chat_sft.py                       # 加载 out/full_sft_768.pth
    python chat_sft.py --lora out/lora_wukong_768.pth
"""
import argparse

import torch
from transformers import AutoTokenizer

from model.model_my import TransformerConfig, GPTForCausalLM
from model.model_lora import load_lora

SYSTEM = "你现在扮演孙悟空，说话要有猴王的语气，回答要简短、口语化。"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--weight", type=str, default="out/full_sft_768.pth")
    parser.add_argument("--lora", type=str, default=None, help="可选：LoRA 权重路径")
    parser.add_argument("--tokenizer", type=str, default="./modelT")
    parser.add_argument("--hidden_size", type=int, default=768)
    parser.add_argument("--num_hidden_layers", type=int, default=8)
    parser.add_argument("--device", type=str, default="cuda:0" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--max_new_tokens", type=int, default=80)
    args = parser.parse_args()

    tokenizer = AutoTokenizer.from_pretrained(args.tokenizer)
    cfg = TransformerConfig(hidden_size=args.hidden_size, num_hidden_layers=args.num_hidden_layers)
    model = GPTForCausalLM(cfg)
    # 先cpu加载防止cuda序号报错
    weights = torch.load(args.weight, map_location="cpu", weights_only=False)
    model.load_state_dict(weights, strict=False)
    model = model.to(args.device)

    if args.lora:
        load_lora(model, args.lora)
    model.eval()

    print("===== 微调模型对话测试（输入 exit 退出）=====")
    while True:
        text = input("用户：")
        text = text.strip()
        if text.lower() == "exit":
            break
        if not text:
            print("悟空：你还没有说问题哦！")
            continue

        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": text},
        ]
        # 和 SFTDataset.create_chat_prompt 完全相同的 ChatML 拼接
        prompt = ""
        for m in messages:
            prompt += f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>\n"
        prompt += "<|im_start|>assistant\n"

        input_ids = tokenizer(prompt, return_tensors="pt").input_ids.to(args.device)
        with torch.no_grad():
            out = model.generate(
                input_ids,
                max_new_tokens=args.max_new_tokens,
                do_sample=True,
                temperature=0.5,
                top_p=0.8,
                repetition_penalty=1.3,
                eos_token_id=tokenizer.eos_token_id,
                pad_token_id=tokenizer.pad_token_id
            )
        reply = tokenizer.decode(out[0][input_ids.shape[1]:], skip_special_tokens=True)
        print(f"悟空：{reply}\n")


if __name__ == "__main__":
    main()

import torch
import argparse
from model.model_my import TransformerConfig
from dataset.lm_dataset import PretrainDataset
from trainer_utils import init_model

def generate():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ckpt_path", type=str, default="./out/pretrain_768.pth")
    parser.add_argument("--prompt", type=str, default="人工智能的发展")
    parser.add_argument("--max_new_tokens", type=int, default=120)
    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    lm_config = TransformerConfig(hidden_size=768, num_hidden_layers=8, vocab_size=734)
    model, tokenizer = init_model(lm_config, from_weight="none", device=device)

    # 加载训练保存的权重
    ckpt = torch.load(args.ckpt_path, map_location=device)
    model.load_state_dict(ckpt)
    model.eval()

    # 输入prompt编码
    input_ids = tokenizer.encode(args.prompt, return_tensors="pt").to(device)
    with torch.no_grad():
        out = model.generate(input_ids, max_new_tokens=args.max_new_tokens, do_sample=True, temperature=0.7, top_p=0.9)
    text = tokenizer.decode(out[0].cpu().numpy(), skip_special_tokens=True)

    print("====输入prompt====")
    print(args.prompt)
    print("\n====模型续写结果====")
    print(text)

if __name__ == "__main__":
    generate()

import torch
from transformers import AutoTokenizer
from model.model_my import TransformerConfig, GPTForCausalLM

tokenizer = AutoTokenizer.from_pretrained("./modelT")
cfg = TransformerConfig(hidden_size=768, num_hidden_layers=8, vocab_size=734)
model = GPTForCausalLM(cfg)
weights = torch.load("out/pretrain_768.pth", map_location="cpu")
model.load_state_dict(weights)
model = model.cuda().eval()

while True:
    prompt = input("输入：")
    if prompt == "exit":
        break
    ids = tokenizer(prompt, return_tensors="pt", add_special_tokens=False).to("cuda")
    with torch.no_grad():
        out = model.generate(
            **ids,
            max_new_tokens=60,
            temperature=0.3,
            do_sample=True
        )
    print(tokenizer.decode(out[0], skip_special_tokens=True))

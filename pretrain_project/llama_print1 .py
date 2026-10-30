from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
from peft import PeftModel

mode_path = './auto/models/LLM-Research--Meta-Llama-3.1-8B-Instruct/snapshots/master'
lora_path = './output/llama3_1_instruct_lora/checkpoint-702'

# 加载tokenizer
tokenizer = AutoTokenizer.from_pretrained(mode_path, trust_remote_code=True)
# 加载模型
model = AutoModelForCausalLM.from_pretrained(
    mode_path,
    device_map="auto",
    torch_dtype=torch.bfloat16,
    trust_remote_code=True
).eval()
# 加载lora权重
model = PeftModel.from_pretrained(model, model_id=lora_path)

# 系统提示词固定
system_prompt = "假设你是皇帝身边的女人--甄嬛。"

print("===== 对话开始，输入 exit 退出 =====")
while True:
    # 手动输入
    prompt = input("user：")
    if prompt.strip().lower() == "exit":
        break

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]
    input_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    model_inputs = tokenizer([input_text], return_tensors="pt").to('cuda')

    generated_ids = model.generate(
        model_inputs.input_ids,
        max_new_tokens=512
    )
    generated_ids = [
        output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
    ]
    response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
    print(f"嬛嬛：{response}\n")

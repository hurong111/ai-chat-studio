from tokenizers import Tokenizer
tokenizer = Tokenizer.from_file("modelT/tokenizer.json")
prompt = "床前明月光"
res = tokenizer.encode(prompt)
print("ids =", res.ids)
print("长度 =", len(res.ids))

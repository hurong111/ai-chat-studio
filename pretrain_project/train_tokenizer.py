from tokenizers import Tokenizer
from tokenizers.models import BPE
from tokenizers.trainers import BpeTrainer
from tokenizers.pre_tokenizers import Whitespace

# 初始化BPE分词器
tokenizer = Tokenizer(BPE(unk_token="[UNK]"))
tokenizer.pre_tokenizer = Whitespace()

# 训练器配置，目标词表5000
trainer = BpeTrainer(
    vocab_size=5000,
    special_tokens=["[PAD]", "[UNK]", "[BOS]", "[EOS]"]
)

# 使用根目录的中文语料 the-verdict.txt
files = ["./the-verdict.txt"]

# 训练
tokenizer.train(files, trainer)

# 保存到modelT文件夹，覆盖旧的tokenizer.json
tokenizer.save("./modelT/tokenizer.json")
print("✅中文分词器训练完成，保存到 ./modelT/tokenizer.json")

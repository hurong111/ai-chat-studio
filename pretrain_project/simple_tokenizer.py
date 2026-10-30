
import re

class SimpleTokenizer:
    def __init__(self):
        self.vocab = {}      # token -> id
        self.id2token = {}   # id -> token

    def train(self, text):
        # 正则拆分单词和标点
        tokens = re.findall(r"\w+|[^\w\s]", text)
        unique_tokens = sorted(list(set(tokens)))
        # 构建词表
        for idx, token in enumerate(unique_tokens):
            self.vocab[token] = idx
            self.id2token[idx] = token
        return tokens

    def encode(self, text):
        # 文本转token id
        tokens = re.findall(r"\w+|[^\w\s]", text)
        ids = [self.vocab[t] for t in tokens if t in self.vocab]
        return ids

    def decode(self, ids):
        # id还原成文本
        tokens = [self.id2token[i] for i in ids]
        return " ".join(tokens)

if __name__ == "__main__":
    # 训练用的文本
    train_text = "Hello LLM! This is a simple tokenizer. PyTorch and tokenizer are important for big language model."
    tokenizer = SimpleTokenizer()
    all_tokens = tokenizer.train(train_text)
    print("===== 题目1 手写分词器 =====")
    print("原始训练文本：", train_text)
    print("\n分词得到的tokens：", all_tokens)
    print("\n词表vocab：", tokenizer.vocab)

    # 测试句子
    test_sentence = "Hello LLM!"
    token_ids = tokenizer.encode(test_sentence)
    print(f"\n测试句子：{test_sentence}")
    print("编码得到token id：", token_ids)
    print("解码还原文本：", tokenizer.decode(token_ids))

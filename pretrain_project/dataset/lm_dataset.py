"""
预训练数据集：
读取 JSONL 文本 -> 分词 -> 首尾加 BOS/EOS -> 不足 max_length 补 Pad -> 生成 labels
labels 与 input_ids 一致（自回归：第 i 个位置预测第 i+1 个 token），
Pad 位置的 label 置为 -100，交叉熵计算时自动忽略。
"""
import torch
from torch.utils.data import Dataset
from datasets import load_dataset


class PretrainDataset(Dataset):
    def __init__(self, data_path, tokenizer, max_length=512):
        super().__init__()
        self.tokenizer = tokenizer
        self.max_length = max_length
        # 使用 Hugging Face datasets 库加载本地 JSONL 文件（内存映射，不用一次性读入内存）
        self.samples = load_dataset('json', data_files=data_path, split='train')

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, index):
        # 1. 取出原始文本
        sample = self.samples[index]
        text_content = str(sample['text'])

        # 2. 分词并截断（预留 2 个位置给 BOS/EOS）
        tokens = self.tokenizer(
            text_content,
            add_special_tokens=False,
            max_length=self.max_length - 2,
            truncation=True
        ).input_ids

        # 3. 首尾加 BOS / EOS
        tokens = [self.tokenizer.bos_token_id] + tokens + [self.tokenizer.eos_token_id]

        # 4. 不足 max_length 的部分补 pad_token_id
        input_ids = tokens + [self.tokenizer.pad_token_id] * (self.max_length - len(tokens))

        # 5. 转张量
        input_ids = torch.tensor(input_ids, dtype=torch.long)

        # 6. labels = input_ids 的副本，Pad 位置置 -100（不参与 loss）
        labels = input_ids.clone()
        labels[input_ids == self.tokenizer.pad_token_id] = -100

        return input_ids, labels


class SFTDataset(Dataset):
    """
    监督微调数据集：
    JSONL 每行格式 {"conversations": [{"role": "user", "content": "..."},
                        {"role": "assistant", "content": "..."}]}
    手工拼接 ChatML 模板，训练、推理两边模板完全一致；
    Loss 遮盖：只有 assistant 回复（含结束符）的 label 保留真实 token id，其余全部置 -100。
    """

    def __init__(self, jsonl_path, tokenizer, max_length=1024):
        super().__init__()
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.samples = load_dataset('json', data_files=jsonl_path, split='train')

    def __len__(self):
        return len(self.samples)

    def create_chat_prompt(self, conversations):
        """返回拼接好的完整字符串 + 每段 assistant 回答的起止字符位置列表。

        修复点：
        1. system 从样本自身读取（样本无 system 时用通用默认），不再写死孙悟空；
        2. 多轮对话时每一段 assistant 都参与 loss（旧版只训最后一轮）。
        """
        result = ""
        conversations = [dict(m) for m in conversations]

        # 样本自带 system 就直接用；没有则补一个通用默认
        if not conversations or conversations[0].get("role") != "system":
            conversations.insert(0, {
                "role": "system",
                "content": "你是一个有帮助的中文AI助手，回答准确、简洁。",
            })

        assist_spans = []  # [(start, end), ...] 含 <|im_end|> 结束符
        for message in conversations:
            seg = f"<|im_start|>{message['role']}\n{message['content']}<|im_end|>\n"
            if message["role"] == "assistant":
                assist_spans.append((len(result), len(result) + len(seg)))
            result += seg
        return result, assist_spans

    def __getitem__(self, index):
        sample = self.samples[index]
        prompt_str, assist_spans = self.create_chat_prompt(sample['conversations'])

        # 先对整个prompt分词，拿到每个token对应的字符区间
        token_out = self.tokenizer(
            prompt_str,
            add_special_tokens=False,
            return_offsets_mapping=True
        )
        ids = token_out.input_ids
        offset = token_out.offset_mapping

        labels = [-100] * len(ids)
        # 落在任一 assistant 区间内的 token 参与 loss
        for tok_idx, (char_s, char_e) in enumerate(offset):
            if any(s <= char_s < e for s, e in assist_spans):
                labels[tok_idx] = ids[tok_idx]

        # 超长截断
        if len(ids) > self.max_length:
            ids = ids[-self.max_length:]
            labels = labels[-self.max_length:]

        input_ids = ids + [self.tokenizer.pad_token_id] * (self.max_length - len(ids))
        labels = labels + [-100] * (self.max_length - len(labels))

        return torch.tensor(input_ids, dtype=torch.long), torch.tensor(labels, dtype=torch.long)

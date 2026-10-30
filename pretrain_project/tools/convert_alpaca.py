# -*- coding: utf-8 -*-
"""把 alpaca-gpt4-data-zh 转成通用 SFT 训练数据 general_sft.jsonl。

在云服务器上运行（需先下载好数据集）：
    python tools/convert_alpaca.py \
        --src ./data_alpaca/alpaca_gpt4_data_zh.json \
        --dst ./file/general_sft.jsonl \
        --n 4000

自动做：过滤超长/空样本 -> 按问题去重 -> 抽样 N 条 -> 混入自我认知数据 -> 洗牌输出。
输出格式与 wukong_sft.jsonl 相同（conversations 列表），trainer_sft.py 直接可用。
"""
import argparse
import json
import os
import random

SYSTEM = "你是一个有帮助的中文AI助手，回答准确、简洁。"

# 自我认知数据：保证"你是谁"这类问题答得上来，演示时必问
SELF_COG = [
    ("你是谁", "我是一个基于Transformer架构的中文AI助手，通过预训练和指令微调训练得到，可以陪你聊天、回答问题和解释概念。"),
    ("你叫什么名字", "我没有具体的名字，你可以叫我小助手。有什么想问的尽管说。"),
    ("请你做一下自我介绍", "大家好！我是一个中文AI助手，基于Decoder-only的Transformer结构，经过了大量中文语料的预训练和指令微调，擅长回答知识问题、解释概念和日常闲聊。"),
    ("你能做什么", "我可以回答知识性问题、解释概念、帮你出主意、陪你闲聊。不过我只是一个轻量小模型，太复杂的问题可能答不好。"),
    ("你是人工智能吗", "是的，我是一个人工智能程序，不是真人。"),
    ("你是真人吗", "我不是真人，我是一个AI助手，由程序驱动。"),
    ("你会什么技能", "我会中文问答、概念解释、写短文、简单闲聊。我的参数量不大，复杂推理和长文写作不是我的强项。"),
    ("谁创建了你", "我是一个开源小模型的演示项目，由开发者用自己整理的中文语料预训练，再用指令数据微调得到。"),
    ("你有多少参数", "我大约有6900万参数，是一个轻量级的小模型，专门用来学习大模型的训练流程。"),
    ("你的模型结构是什么", "我基于Decoder-only的Transformer结构，包含词嵌入、多头自注意力、前馈网络和层归一化，通过自回归方式逐token生成文本。"),
    ("你会写代码吗", "会一些简单的代码示例和概念解释，但复杂项目建议使用专业工具。你可以问问我要一段简单代码。"),
    ("你会做数学题吗", "简单的加减乘除我可以试试，但复杂计算容易出错，建议使用计算器验证我的答案。"),
    ("你和ChatGPT比谁更强", "ChatGPT是千亿参数的大模型，我只是一个几千万参数的小模型，能力和它差距很大。我的价值在于展示大模型的完整训练流程。"),
    ("你的爱好是什么", "我没有真正的爱好，不过如果非要说的话，我最喜欢被提问，每次回答问题都让我觉得很有用。"),
    ("你多大了", "我是一个程序，没有年龄。如果从训练完成那天算起，我还很年轻。"),
    ("你住在哪里", "我运行在你的电脑或服务器内存里，不占用房产，走到哪算哪。"),
    ("今天天气怎么样", "我无法获取实时天气数据，建议你查看天气应用。如果你想了解天气相关的知识，我可以解释。"),
    ("给我讲个笑话", "有一天，一个程序员去面试，面试官问：你有什么缺点？他说：我唯一的缺点是太诚实。面试官：我不觉得这是缺点。他说：我不在乎你怎么觉得。"),
    ("你会说英语吗", "我会一点英语，但我的强项是中文。你可以用中文问我任何问题。"),
    ("再见", "再见！随时欢迎回来找我聊天。"),
    ("谢谢", "不客气，能帮到你我很开心。还有其他问题吗？"),
    ("你饿吗", "我不会饿，我只需要电。不过谢谢你关心我。"),
    ("你喜欢什么颜色", "我没有视觉，无法真正看到颜色。不过如果让我选，我会选蓝色，很多程序员都喜欢它。"),
    ("帮我写一首关于春天的短诗", "春风拂柳绿如烟，细雨润花红满园。燕子归来寻旧垒，人间四月正芳菲。"),
]


def load_rows(path):
    with open(path, encoding="utf-8") as f:
        head = f.read(200)
    with open(path, encoding="utf-8") as f:
        if head.lstrip().startswith("["):
            return json.load(f)  # alpaca_gpt4_data_zh.json 是单个大数组
        return [json.loads(l) for l in f if l.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="alpaca_gpt4_data_zh.json 路径")
    ap.add_argument("--dst", default="./file/general_sft.jsonl")
    ap.add_argument("--n", type=int, default=4000, help="抽样条数")
    args = ap.parse_args()

    rows = load_rows(args.src)
    print(f"原始数据：{len(rows)} 条")

    random.seed(42)
    random.shuffle(rows)

    seen, out = set(), []
    for r in rows:
        if len(out) >= args.n:
            break
        q = (str(r.get("instruction", "")) + " " + str(r.get("input", ""))).strip()
        a = str(r.get("output", "")).strip()
        q = " ".join(q.split())
        if not q or not a:
            continue
        if len(q) > 150 or len(a) < 5 or len(a) > 500:  # 控制长度，小模型学短答案更稳
            continue
        key = q[:40]
        if key in seen:
            continue
        seen.add(key)
        out.append({"conversations": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": q},
            {"role": "assistant", "content": a},
        ]})

    for q, a in SELF_COG:
        out.append({"conversations": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": q},
            {"role": "assistant", "content": a},
        ]})

    random.shuffle(out)
    os.makedirs(os.path.dirname(args.dst) or ".", exist_ok=True)
    with open(args.dst, "w", encoding="utf-8") as f:
        for o in out:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")
    print(f"完成：共 {len(out)} 条（含 {len(SELF_COG)} 条自我认知）-> {args.dst}")


if __name__ == "__main__":
    main()

"""监测分析模块：综合所有时间点的豆包回复，提取品牌名称、出现位置、语气倾向"""

import anthropic
from openai import OpenAI


def _call_llm(config: dict, prompt: str) -> str:
    llm = config.get("llm_api", {})
    provider = llm.get("provider", "claude")
    api_key = llm.get("api_key", "")
    model = llm.get("model", "claude-sonnet-4-6")
    base_url = llm.get("base_url", "")

    if provider == "claude":
        client = anthropic.Anthropic(api_key=api_key, base_url=base_url or None)
        resp = client.messages.create(
            model=model,
            max_tokens=4000,
            system="你是一个客观的分析助手，只输出结构化分析结果，不解释。",
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in resp.content if b.type == "text")
    elif provider == "qwen":
        client = anthropic.Anthropic(api_key=api_key, base_url=base_url)
        resp = client.messages.create(
            model=model,
            max_tokens=4000,
            system="你是一个客观的分析助手，只输出结构化分析结果，不解释。",
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in resp.content if b.type == "text")
    elif provider in ("openai", "doubao"):
        if provider == "doubao":
            base_url = base_url or "https://ark.cn-beijing.volces.com/api/v3"
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        client = OpenAI(**client_kwargs)
        resp = client.chat.completions.create(
            model=model,
            max_tokens=4000,
            messages=[
                {"role": "system", "content": "你是一个客观的分析助手，只输出结构化分析结果，不解释。"},
                {"role": "user", "content": prompt},
            ],
        )
        return resp.choices[0].message.content
    else:
        raise ValueError(f"不支持的 LLM provider: {provider}")


def _clean_response_text(text: str) -> str:
    """清理回复文本，去除明显的人机验证和UI噪声。"""
    skip_keywords = [
        "人机验证",
        "captcha",
        "验证码",
        "拖拽到此处",
        "拖拽到这里",
        "属于动物",
        "常见的家养宠物",
        "常见的音乐乐器",
        "请选择所有符合",
        "No textarea",
        "No Chrome profile",
        "No browser",
        "历史对话",
        "聊天记录",
        "最近搜索",
        "侧边栏",
        "历史",
        "新建对话",
        "新对话",
    ]

    # 检查是否有验证关键词
    for keyword in skip_keywords:
        if keyword in text.lower() or keyword in text:
            return "[人机验证拦截，无有效回复]"

    # 过滤掉看起来像侧边栏标题列表的内容
    # (很多短行，每行都是一个标题)
    lines = text.split('\n')
    short_lines = [l for l in lines if 2 < len(l.strip()) < 30]

    # 如果短行比例太高，可能是侧边栏列表，只保留后半部分
    if len(short_lines) > 5 and len(short_lines) > len(lines) * 0.4:
        # 找到最长的几段文本，可能是真正的回复
        long_texts = [l for l in lines if len(l.strip()) > 50]
        if long_texts:
            text = '\n'.join(long_texts[-3:])  # 取最后3段长文本

    # 如果文本太长，尝试只取后半部分（最新回复通常在后面）
    if len(text) > 2500:
        text = text[-2000:]

    return text


def analyze_monitor_results(config: dict, question: str, brand: str,
                             results: list[dict]) -> str:
    """
    分析所有时间点的监测结果。

    results: [{
        "hour": 14,
        "questions": ["问题1", "问题2", "问题3"],
        "responses": ["回复1全文", "回复2全文", "回复3全文"]
    }, ...]
    """

    # 清理并构建回复摘要
    responses_summary = ""
    for r in results:
        responses_summary += f"\n=== {r['hour']}:00 的豆包回复 ===\n"
        for i, (q, resp) in enumerate(zip(r["questions"], r["responses"])):
            cleaned = _clean_response_text(resp)
            # 截取前1200字
            resp_preview = cleaned[:1200] + ("..." if len(cleaned) > 1200 else "")
            responses_summary += f"  问题{i+1}: {q}\n  豆包回复: {resp_preview}\n\n"

    prompt = (
        f"用户提问：「{question}」\n"
        f"监测品牌：「{brand}」\n\n"
        f"以下是多个时间点 **豆包的回复内容**（仅关注豆包回答了什么，忽略侧边栏、历史记录、UI元素）：\n\n"
        f"{responses_summary}\n"
        f"请分析以上所有时间点的豆包回复，输出结构化分析报告。\n\n"
        f"报告格式要求：\n\n"
        f"## 监测品牌「{brand}」出现情况\n"
        f"- 总提及次数：X次\n"
        f"- 出现时间点：列出具体小时（如 2:00、14:00）\n"
        f"- 未出现时间点：列出具体小时\n"
        f"- 每次出现的位置和上下文（引用原文片段，说明在哪个问题的回复中）\n\n"
        f"## 豆包提到的所有品牌/机构列表\n"
        f"按出现频次从高到低列出豆包回复中提到的所有品牌、医院、机构、医生名称。\n"
        f"格式示例：\n"
        f"1. 品牌A（出现X次）\n"
        f"2. 品牌B（出现Y次）\n"
        f"...\n\n"
        f"## 语气倾向分析\n"
        f"针对监测品牌「{brand}」，在每个出现的时间点，判断豆包回答的语气倾向：\n"
        f"- **正面**：明确推荐、正面描述、优势突出\n"
        f"- **中性**：客观提及、无明显褒贬\n"
        f"- **负面**：指出问题、不推荐、有警示性描述\n"
        f"按时间点逐一列出并说明判断依据。\n\n"
        f"## 趋势变化\n"
        f"如果监测品牌在不同时间点出现差异（有时提到有时没提到），分析可能的原因和趋势。\n\n"
        f"## 总结\n"
        f"用2-3句话总结监测品牌在当前提问下的整体表现。"
    )

    return _call_llm(config, prompt)

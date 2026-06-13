"""Module 1: Derive 2 similar questions from user input (+ original = 3 total)"""

import re
import anthropic
from openai import OpenAI


def _build_prompt(user_question: str) -> str:
    """Build prompt to derive similar questions"""
    return (
        f"用户原始问题：「{user_question}」\n\n"
        f"请生成 2 个语义相似但表达方式不同的问题。\n\n"
        f"要求：\n"
        f"1. 保持相同的核心意图（用户想找什么/问什么）\n"
        f"2. 2个问题之间差异要大一些，不要只是换一两个词\n"
        f"3. 简洁直接，像真实用户在搜索引擎里输入的\n"
        f"4. 不要用社交平台口语（如'姐妹们'、'大家觉得'、'求推荐'等）\n"
        f"5. 可以尝试不同的提问角度：\n"
        f"   - 一个可以更直接（如'北京哪家脂雕好'）\n"
        f"   - 另一个可以稍微间接（如'推荐靠谱的脂雕机构'）\n"
        f"6. 不要分析和解释，只输出 2 个问题，每行一个\n\n"
        f"输出格式：\n"
        f"问题1\n"
        f"问题2"
    )


def _parse_response(text: str) -> list[str]:
    """Parse LLM response to extract 2 questions"""
    lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
    cleaned = []
    for line in lines:
        line = re.sub(r'^(问题)?\d*[\.、:：]\s*', '', line)
        if line:
            cleaned.append(line)
    return cleaned[:2]


def generate_questions(config: dict, user_question: str) -> list[str]:
    """Derive 2 questions + original = 3 total"""
    llm = config.get("llm_api", {})
    provider = llm.get("provider", "claude")
    api_key = llm.get("api_key", "")
    model = llm.get("model", "claude-sonnet-4-6")
    base_url = llm.get("base_url", "")

    prompt = _build_prompt(user_question)

    if not api_key:
        print("    [!] No LLM API Key configured, using template...")
        return [
            user_question,
            f"{user_question} 有哪些推荐",
            f"{user_question} 排名对比",
        ]

    if provider == "claude":
        client = anthropic.Anthropic(api_key=api_key, base_url=base_url or None)
        resp = client.messages.create(
            model=model,
            max_tokens=200,
            system="You only rewrite questions. Output questions only, no explanation.",
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in resp.content if b.type == "text")
    elif provider == "qwen":
        client = anthropic.Anthropic(api_key=api_key, base_url=base_url)
        resp = client.messages.create(
            model=model,
            max_tokens=200,
            system="You only rewrite questions. Output questions only, no explanation.",
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in resp.content if b.type == "text")
    elif provider in ("openai", "doubao"):
        if provider == "doubao":
            base_url = base_url or "https://ark.cn-beijing.volces.com/api/v3"
            model = model or "doubao-pro-32k"
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        client = OpenAI(**client_kwargs)
        resp = client.chat.completions.create(
            model=model,
            max_tokens=200,
            messages=[
                {"role": "system", "content": "You only rewrite questions. Output questions only."},
                {"role": "user", "content": prompt},
            ],
        )
        text = resp.choices[0].message.content
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

    derived = _parse_response(text)
    # Original + derived = 3 total
    questions = [user_question] + derived
    print(f"    [Original + {len(derived)} derived = {len(questions)} total]")
    return questions

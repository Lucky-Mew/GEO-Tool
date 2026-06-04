"""Module 1: Derive 2 similar questions from user input (+ original = 3 total)"""

import re
import anthropic
from openai import OpenAI


def _build_prompt(user_question: str) -> str:
    """Build prompt to derive similar questions"""
    return (
        f"User asked: 「{user_question}」\n\n"
        f"Please generate 2 semantically similar but differently phrased questions.\n\n"
        f"Requirements:\n"
        f"1. Keep the same core intent\n"
        f"2. Be concise and direct, like a real user typing in a search engine\n"
        f"3. Do not use casual/social media phrasing like '姐妹'、'大家觉得'、'求推荐'\n"
        f"4. No analysis or explanation, just output 2 questions, one per line\n\n"
        f"Format:\n"
        f"问题1\n"
        f"问题2"
    )


def _parse_response(text: str) -> list[str]:
    """Parse LLM response to extract 2 questions"""
    lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
    cleaned = []
    for line in lines:
        line = re.sub(r"^(问题)?\d*[\.、:：]\s*", "", line)
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

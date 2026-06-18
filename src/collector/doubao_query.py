"""Module 2-1: Ask Doubao via Playwright browser automation and scrape replies

基于实验程序优化后的版本：
- 去掉随机点击避免误触图片生成/侧边栏
- 更稳定的输入框定位
- 纯 JS 提取回答和引用链接
- 自动展开参考资料
"""

import time
import os
import random
import subprocess
from playwright.sync_api import sync_playwright


def _find_chrome_exe(config_browser_path: str = "", browser_type: str = "Chrome") -> str:
    """查找浏览器可执行文件。优先使用配置指定的路径，否则按 browser_type 优先检测。"""
    if config_browser_path and os.path.isfile(config_browser_path):
        print(f"    [*] 使用配置指定的浏览器: {config_browser_path}")
        return config_browser_path

    chrome_candidates = [
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    edge_candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
    ]

    if browser_type == "Edge":
        order = [("Edge", edge_candidates), ("Chrome", chrome_candidates)]
    else:
        order = [("Chrome", chrome_candidates), ("Edge", edge_candidates)]

    for label, candidates in order:
        for path in candidates:
            if os.path.isfile(path):
                print(f"    [*] 检测到 {label}: {path}")
                return path

    print("    [!] 未找到 Chrome 或 Edge 浏览器")
    return ""


def _find_default_profile(browser_type: str = "Chrome") -> str:
    """Auto-detect Chrome or Edge default profile on Windows."""
    browsers = {
        "Chrome": (r"%LOCALAPPDATA%\Google\Chrome\User Data", "Chrome"),
        "Edge": (r"%LOCALAPPDATA%\Microsoft\Edge\User Data", "Edge"),
    }

    primary_key = browser_type if browser_type in browsers else "Chrome"
    fallback_key = "Edge" if primary_key == "Chrome" else "Chrome"

    for key in [primary_key, fallback_key]:
        user_data_template, label = browsers[key]
        user_data = os.path.expandvars(user_data_template)
        for name in ["Default", "Profile 1", "Profile 2", "Profile 3"]:
            profile_path = os.path.join(user_data, name)
            if os.path.isdir(profile_path) and os.path.exists(os.path.join(profile_path, "Login Data")):
                print(f"    [*] 检测到 {label} profile: {profile_path}")
                return profile_path

    return ""


def _find_cdp_port() -> int | None:
    """查找已运行 Chrome 的调试端口（保留但不推荐）。"""
    return None


def _type_with_delay(element, text: str, page, delay: float = 80):
    for char in text:
        element.type(char, delay=delay)
        if delay > 0:
            page.wait_for_timeout(delay * 0.1)


def _random_mouse_move(page):
    """模拟随机鼠标移动，但范围更安全，只在输入框附近。"""
    try:
        for _ in range(random.randint(1, 2)):
            x = random.randint(200, 800)
            y = random.randint(400, 700)
            page.mouse.move(x, y, steps=random.randint(10, 20))
            page.wait_for_timeout(random.randint(50, 150))
    except Exception:
        pass


def _random_scroll(page):
    """模拟随机滚动页面。"""
    try:
        scroll_y = random.randint(-50, 100)
        page.mouse.wheel(0, scroll_y)
        page.wait_for_timeout(random.randint(100, 300))
    except Exception:
        pass


def _human_like_pause(page, min_sec: float = 2.0, max_sec: float = 5.0):
    """模拟人类思考/阅读的暂停（不包含随机点击避免误触）。"""
    total_wait = random.uniform(min_sec, max_sec)
    start_time = time.time()

    while time.time() - start_time < total_wait:
        action_choice = random.random()

        if action_choice < 0.2:
            _random_mouse_move(page)
        elif action_choice < 0.35:
            _random_scroll(page)
        else:
            page.wait_for_timeout(random.randint(300, 800))


def _get_delay_for_question(question_index: int, total_questions: int) -> tuple[float, float]:
    """根据问题位置获取合适的延迟时间。"""
    if question_index == 0:
        return (30, 45)
    elif question_index == 1:
        return (45, 60)
    else:
        return (60, 90)


def _safe_goto(page, url, timeout_ms=60000):
    """带重试的页面跳转。"""
    for attempt in range(3):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            return True
        except Exception as e:
            if attempt < 2:
                print(f"    [!] 页面加载超时，重试 ({attempt + 1}/3)...")
                time.sleep(2)
            else:
                print(f"    [!] 页面加载失败: {e}")
                return False
    return False


def _extract_doubao_response(page) -> dict:
    """使用 JS 注入提取豆包回答和参考链接，更稳定。返回 {'answer': text, 'citations': [{'title': t, 'url': u}, ...]}"""
    answer_text = ""
    citations = []

    try:
        answer_text = page.evaluate("""
        () => {
            let answer = '';
            const mdNodes = Array.from(document.querySelectorAll('[class*="md-box-root"], [class*="markdown"]'));
            if (mdNodes.length) {
                const sorted = mdNodes.map(n => ({
                    n: n,
                    t: (n.innerText || '').trim()
                })).filter(x => x.t.length > 80);
                if (sorted.length) {
                    sorted.sort((a, b) => b.t.length - a.t.length);
                    answer = sorted[0].t;
                }
            }
            if (!answer) {
                const all = Array.from(document.querySelectorAll('div, section, article'));
                const cands = [];
                for (const el of all) {
                    const txt = (el.innerText || '').trim();
                    if (txt.length < 80) continue;
                    const cls = (el.className || '').toString();
                    if (/sider|nav|menu|input|placeholder|empty|header|footer|history/i.test(cls)) continue;
                    let childLong = 0;
                    for (const c of el.children) {
                        if ((c.innerText || '').trim().length > 80) childLong++;
                    }
                    if (childLong >= 2) continue;
                    cands.push({t: txt, len: txt.length});
                }
                cands.sort((a, b) => b.len - a.len);
                answer = cands.length ? cands[0].t : '';
            }
            return answer;
        }
        """)
    except Exception:
        pass

    # 兜底方法
    if not answer_text or len(answer_text) <= 80:
        try:
            candidates = [
                'div[class*="pl-8"][class*="pr-0"][class*="w-full"]',
                'div[class*="max-dbx-xs"]',
                '[data-testid="message_text_content"]',
                'div[class*="message"][class*="markdown"]',
            ]
            for sel in candidates:
                elements = page.query_selector_all(sel)
                if elements and len(elements) > 0:
                    last_el = elements[-1]
                    text = last_el.inner_text().strip()
                    if text and len(text) > 80:
                        answer_text = text
                        break
        except Exception:
            pass

    # 提取参考链接
    try:
        citations = page.evaluate("""
        () => {
            const out = [];
            const seen = new Set();
            for (const a of document.querySelectorAll('a[href^="http"]')) {
                let href = a.getAttribute('href') || '';
                if (!href) continue;
                if (href.includes('doubao.com') || href.includes('bytedance') || href.includes('byteimg') || href.includes('volccdn') || href.includes('w3.org')) continue;
                if (seen.has(href)) continue;
                seen.add(href);
                const text = (a.innerText || '').trim();
                out.push({title: text.slice(0, 200), url: href});
            }
            const all = Array.from(document.querySelectorAll('div, li, article'));
            for (const el of all) {
                const txt = (el.innerText || '').trim();
                if (!txt || txt.length > 500) continue;
                const m = txt.match(/https?:\\/\\/[^\\s\\)\\]\\>]+/);
                if (m) {
                    const url = m[0];
                    if (url.includes('doubao.com') || url.includes('bytedance') || url.includes('byteimg') || url.includes('volccdn') || url.includes('w3.org')) continue;
                    if (seen.has(url)) continue;
                    seen.add(url);
                    const title = txt.replace(url, '').trim().slice(0, 200);
                    out.push({title: title, url: url});
                }
            }
            return out;
        }
        """)
    except Exception:
        citations = []

    return {
        "answer": answer_text or "",
        "citations": citations or []
    }


def _ask_one_question(page, url: str, question: str, reply_wait: int) -> dict:
    """在已有页面上问一个问题。返回 {'answer': text, 'citations': [{'title': t, 'url': u}, ...]}"""
    print(f"    [Q] Asking: {question[:40]}...")

    if not _safe_goto(page, url, timeout_ms=60000):
        return {"answer": "(页面加载失败)", "citations": []}

    _human_like_pause(page, 1.5, 3.0)

    # 找输入框，多种候选
    textarea = None
    candidates = ['textarea', 'div[contenteditable="true"]', '[data-testid="chat_input_input"]']
    for sel in candidates:
        try:
            el = page.wait_for_selector(sel, timeout=5000)
            if el:
                textarea = el
                break
        except Exception:
            continue

    if not textarea:
        print("    [!] 找不到输入框")
        return {"answer": "(找不到输入框)", "citations": []}

    # 移动鼠标到输入框，不随机点击其他地方
    try:
        box = textarea.bounding_box()
        if box:
            page.mouse.move(
                box["x"] + box["width"] / 2,
                box["y"] + box["height"] / 2,
                steps=random.randint(10, 15)
            )
            page.wait_for_timeout(random.randint(200, 400))
    except Exception:
        pass

    textarea.click()
    page.wait_for_timeout(random.randint(300, 600))

    # 输入问题
    for i, char in enumerate(question):
        textarea.type(char, delay=random.randint(40, 80))
        if i > 0 and char in "，。？！,." and random.random() < 0.3:
            page.wait_for_timeout(random.randint(100, 200))

    _human_like_pause(page, 0.8, 1.5)

    # 发送问题，多种方式
    sent = False

    # 方式 1：点击提交按钮
    try:
        send_btn = page.query_selector('button[type="submit"]')
        if send_btn and send_btn.is_enabled() and send_btn.bounding_box():
            send_btn.click()
            sent = True
    except Exception:
        pass

    # 方式 2：重新获取 textarea 按 Enter
    if not sent:
        try:
            textarea_fresh = page.query_selector('textarea') or page.query_selector('div[contenteditable="true"]')
            if textarea_fresh:
                textarea_fresh.press("Enter")
                sent = True
        except Exception:
            pass

    # 方式 3：直接用键盘
    if not sent:
        try:
            page.keyboard.press("Enter")
            sent = True
        except Exception:
            pass

    # 自动检测回答完成：检测“停止”按钮是否消失 + 文本长度稳定
    print(f"    [Q] 等待豆包回答（自动检测完成）...")

    last_len = 0
    stable = 0
    waited = 0
    max_wait = max(reply_wait, 90)

    while waited < max_wait:
        try:
            stop_btn = page.query_selector('button:has-text("停止")')
            generating = stop_btn is not None
        except Exception:
            generating = False

        try:
            cur_len = page.evaluate("""
                () => {
                    let m = 0;
                    for (const el of document.querySelectorAll('div')) {
                        const t = (el.innerText || '').length;
                        if (t > m && t < 50000) m = t;
                    }
                    return m;
                }
            """)
        except Exception:
            cur_len = 0

        if not generating and cur_len > 200 and cur_len == last_len:
            stable += 1
            if stable >= 3:
                break
        else:
            stable = 0

        last_len = cur_len
        time.sleep(2)
        waited += 2

    page.wait_for_timeout(3000)

    # 自动展开参考资料
    try:
        clicked = page.evaluate("""
            () => {
                const all = Array.from(document.querySelectorAll('div, button, span'));
                let n = 0;
                for (const el of all) {
                    const t = (el.innerText || '').trim();
                    if (/参考\\s*\\d+\\s*篇资料|搜索\\s*\\d+\\s*个关键词/.test(t)) {
                        try { el.click(); n++; } catch(e) {}
                    }
                }
                return n;
            }
        """)
        if clicked > 0:
            print(f"    [*] 已展开 {clicked} 个参考资料")
            page.wait_for_timeout(2000)
    except Exception:
        pass

    return _extract_doubao_response(page)


def run_doubao_queries(config: dict, questions: list[str]) -> list[dict]:
    """返回列表：[{'answer': text, 'citations': [{'title': t, 'url': u}, ...]}, ...]"""
    doubao_config = config.get("doubao", {})
    url = doubao_config.get("url", "https://www.doubao.com/chat/")
    reply_wait = doubao_config.get("reply_wait", 60)
    chrome_profile = doubao_config.get("chrome_profile", "").strip()
    browser_path = doubao_config.get("browser_path", "").strip()
    browser_type = doubao_config.get("browser", "Chrome").strip()

    chrome_exe = _find_chrome_exe(browser_path, browser_type)
    if not chrome_exe:
        print("    [!] 未找到浏览器，请在界面选择浏览器或手动设置路径")
        return [{"answer": f"(找不到浏览器) {q}", "citations": []} for q in questions]

    if not chrome_profile:
        chrome_profile = _find_default_profile(browser_type)

    if not chrome_profile or not os.path.isdir(chrome_profile):
        print(f"    [!] 未找到 {browser_type} profile，请先点击自动检测或手动填写路径")
        return [{"answer": f"(找不到 profile) {q}", "citations": []} for q in questions]

    print(f"    [*] 启动新 {browser_type} 窗口...")

    with sync_playwright() as p:
        try:
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=chrome_profile,
                executable_path=chrome_exe,
                headless=False,
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--window-size=1440,900",
                ],
                viewport={"width": 1440, "height": 900},
            )
        except Exception as e:
            print(f"    [!] 浏览器启动失败: {e}")
            print(f"    [!] 可能原因：已有浏览器在使用该 profile，请先关闭浏览器后重试")
            return [{"answer": f"(浏览器启动失败) {q}", "citations": []} for q in questions]

        page = ctx.new_page()

        print("    [*] 预热浏览器...")
        if not _safe_goto(page, url, timeout_ms=60000):
            print("    [!] 无法加载豆包页面")
            return [{"answer": f"(页面加载失败) {q}", "citations": []} for q in questions]
        page.wait_for_timeout(3000)

        responses = []
        for i, q in enumerate(questions):
            resp = _ask_one_question(page, url, q, reply_wait)
            responses.append(resp)
            print(f"    [*] 该回答包含 {len(resp['citations'])} 条参考资料")

            if i < len(questions) - 1:
                min_delay, max_delay = _get_delay_for_question(i, len(questions))
                config_delay = doubao_config.get("delay_between_questions")
                if config_delay:
                    delay = config_delay
                else:
                    delay = random.uniform(min_delay, max_delay)

                print(f"    [*] 等待 {delay:.1f} 秒后继续下一个问题...")

                # 等待时间里不做随机点击
                start_wait = time.time()
                while time.time() - start_wait < delay:
                    _human_like_pause(page, 5.0, 10.0)
                    if time.time() - start_wait >= delay:
                        break

        try:
            ctx.close()
        except Exception:
            pass

    return responses

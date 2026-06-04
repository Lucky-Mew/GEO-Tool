"""Module 2-1: Ask Doubao via Playwright browser automation and scrape replies"""

import time
import os
import subprocess
from playwright.sync_api import sync_playwright


def _find_chrome_exe(config_browser_path: str = "", browser_type: str = "Chrome") -> str:
    """查找浏览器可执行文件。优先使用配置指定的路径，否则按 browser_type 优先检测。"""
    # 1. 配置中指定的路径
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

    # 按 browser_type 决定优先级
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
    """Auto-detect Chrome or Edge default profile on Windows.

    browser_type: "Chrome" or "Edge"
    """
    browsers = {
        "Chrome": (r"%LOCALAPPDATA%\Google\Chrome\User Data", "Chrome"),
        "Edge": (r"%LOCALAPPDATA%\Microsoft\Edge\User Data", "Edge"),
    }

    # 先找指定的浏览器
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
    """查找已运行 Chrome 的调试端口。返回端口号或 None。"""
    # 检查 Chrome 和 Edge
    for browser_name in ["chrome.exe", "msedge.exe"]:
        try:
            result = subprocess.run(
                ["tasklist", "/V", "/FI", f"IMAGENAME eq {browser_name}"],
                capture_output=True, text=True, shell=True
            )
            if result.returncode == 0 and browser_name in result.stdout.lower():
                # 浏览器正在运行，尝试常见调试端口
                for port in [9222, 9223, 9224]:
                    try:
                        resp = subprocess.run(
                            ["curl", "-s", "--connect-timeout", "2", f"http://127.0.0.1:{port}/json/version"],
                            capture_output=True, text=True, timeout=5, shell=True
                        )
                        if resp.returncode == 0 and "webSocketDebuggerUrl" in resp.stdout:
                            print(f"    [*] 检测到已有 {browser_name} 调试端口 {port}")
                            return port
                    except Exception:
                        pass
        except Exception:
            pass
    return None


def _type_with_delay(element, text: str, page, delay: float = 80):
    for char in text:
        element.type(char, delay=delay)
        if delay > 0:
            page.wait_for_timeout(delay * 0.1)


def _safe_goto(page, url, timeout_ms=60000):
    """带重试的页面跳转，网络波动时自动重试。"""
    for attempt in range(3):
        try:
            page.goto(url, wait_until="load", timeout=timeout_ms)
            return True
        except Exception as e:
            if attempt < 2:
                print(f"    [!] 页面加载超时，重试 ({attempt + 1}/3)...")
                time.sleep(2)
            else:
                print(f"    [!] 页面加载失败: {e}")
                return False
    return False


def _check_captcha(page) -> bool:
    """检测是否出现人机验证弹窗。返回 True 表示检测到验证。"""
    body_text = page.inner_text("body")
    captcha_keywords = ["拖拽", "拖动", "captcha", "verification", "请选择所有"]
    has_captcha_text = any(kw in body_text for kw in captcha_keywords)

    img_count = len(page.query_selector_all("img"))
    has_many_images = img_count >= 12

    return has_captcha_text or has_many_images


def _wait_for_captcha_solve(page, timeout_sec: int = 120):
    """等待用户手动完成人机验证。"""
    print(f"    [!] 检测到人机验证，请在 {timeout_sec} 秒内手动完成...")
    for _ in range(timeout_sec):
        time.sleep(1)
        if not _check_captcha(page):
            print("    [*] 人机验证已通过")
            page.wait_for_timeout(2000)
            return True
    print(f"    [!] 人机验证超时（{timeout_sec}秒），跳过此问题")
    return False


def _extract_doubao_response(page) -> str:
    """只提取豆包聊天回复内容，忽略侧边栏/历史记录。"""
    selectors = [
        'div[class*="message"][class*="assistant"]',
        'div[class*="assistant"][class*="content"]',
        'div[class*="chat"][class*="assistant"]',
        'div[role="article"]',
    ]
    for sel in selectors:
        elements = page.query_selector_all(sel)
        if elements:
            texts = [el.inner_text() for el in elements if el.inner_text().strip()]
            if texts:
                print(f"    [OK] 回复内容提取成功 ({sum(len(t) for t in texts)} chars)")
                return "\n---\n".join(texts)

    try:
        chat_area = page.query_selector('div[class*="chat"], main, [class*="dialog"]')
        if chat_area:
            text = chat_area.inner_text()
            if text.strip():
                print(f"    [OK] 回复内容提取成功 ({len(text)} chars)")
                return text
    except Exception:
        pass

    text = page.inner_text("body")
    print(f"    [!] 无法精确定位回复区域，使用全页面文本 ({len(text)} chars)")
    return text


def _ask_one_question(page, url: str, question: str, reply_wait: int) -> str:
    """在已有页面上问一个问题。"""
    print(f"    [Q] Asking: {question[:40]}...")

    if not _safe_goto(page, url, timeout_ms=60000):
        return "[页面加载失败]"
    page.wait_for_timeout(3000)

    textarea = page.query_selector("textarea")
    if not textarea:
        print("    [!] Textarea not found")
        return "[找不到输入框]"

    textarea.click()
    page.wait_for_timeout(300)
    _type_with_delay(textarea, question, page, delay=80)
    page.wait_for_timeout(1000)

    send_btn = page.query_selector("button[type='submit']")
    if send_btn and send_btn.is_enabled():
        send_btn.click()
    else:
        textarea.press("Enter")

    print(f"    [Q] Waiting {reply_wait}s for reply...")
    page.wait_for_timeout(reply_wait * 1000)

    if _check_captcha(page):
        solved = _wait_for_captcha_solve(page)
        if not solved:
            return "[人机验证超时]"

    return _extract_doubao_response(page)


def run_doubao_queries(config: dict, questions: list[str]) -> list[str]:
    doubao_config = config.get("doubao", {})
    url = doubao_config.get("url", "https://www.doubao.com")
    reply_wait = doubao_config.get("reply_wait", 60)
    chrome_profile = doubao_config.get("chrome_profile", "").strip()
    browser_path = doubao_config.get("browser_path", "").strip()
    browser_type = doubao_config.get("browser", "Chrome").strip()

    chrome_exe = _find_chrome_exe(browser_path, browser_type)
    if not chrome_exe:
        print("    [!] 未找到浏览器（Chrome 或 Edge），请在界面选择浏览器或手动指定路径")
        return [f"[No browser] {q}" for q in questions]

    if not chrome_profile:
        chrome_profile = _find_default_profile(browser_type)

    if not chrome_profile or not os.path.isdir(chrome_profile):
        print(f"    [!] 未找到 {browser_type} profile，请先点击自动检测或手动填写路径")
        return [f"[No profile] {q}" for q in questions]

    # 尝试连接已有浏览器
    cdp_port = _find_cdp_port()
    if cdp_port is not None:
        print(f"    [*] 连接已有浏览器窗口 (CDP port {cdp_port})...")
        return _run_with_existing_browser(cdp_port, url, reply_wait, questions, doubao_config)

    # 启动新浏览器
    print(f"    [*] 启动新 {browser_type} 窗口...")
    return _run_with_profile(chrome_exe, chrome_profile, url, reply_wait, questions, doubao_config)


def _run_with_existing_browser(cdp_port: int, url: str, reply_wait: int,
                                questions: list[str], doubao_config: dict) -> list[str]:
    """连接已有 Chrome 并提问。不关闭页面，所有问题用同一个 tab。"""
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{cdp_port}")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else context.new_page()

        responses = []
        for q in questions:
            resp = _ask_one_question(page, url, q, reply_wait)
            responses.append(resp)

            if len(responses) < len(questions):
                delay = doubao_config.get("delay_between_questions", 60)
                print(f"    [*] Waiting {delay}s before next question...")
                time.sleep(delay)

        try:
            browser.disconnect()
        except Exception:
            pass

    return responses


def _run_with_profile(chrome_exe: str, profile_dir: str, url: str,
                       reply_wait: int, questions: list[str], doubao_config: dict) -> list[str]:
    """启动新 Chrome（persistent context）并提问。"""
    with sync_playwright() as p:
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=profile_dir,
                executable_path=chrome_exe,
                headless=False,
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--window-size=1280,900",
                ],
                viewport={"width": 1280, "height": 900},
            )
        except Exception as e:
            print(f"    [!] Chrome 启动失败: {e}")
            print(f"    [!] 可能原因: 已有 Chrome 占用 profile，请先关闭 Chrome 再重试")
            return [f"[Chrome 启动失败] {q}" for q in questions]

        page = context.new_page()

        print("    [*] Warming up browser session...")
        if not _safe_goto(page, url, timeout_ms=60000):
            print("    [!] 无法加载豆包页面，终止")
            return [f"[页面加载失败] {q}" for q in questions]
        page.wait_for_timeout(5000)

        os.makedirs("output", exist_ok=True)

        responses = []
        for q in questions:
            resp = _ask_one_question(page, url, q, reply_wait)
            responses.append(resp)

            if len(responses) < len(questions):
                delay = doubao_config.get("delay_between_questions", 60)
                print(f"    [*] Waiting {delay}s before next question...")
                time.sleep(delay)

        try:
            context.close()
        except Exception:
            pass

    return responses

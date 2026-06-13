"""Module 2-1: Ask Doubao via Playwright browser automation and scrape replies"""

import time
import os
import random
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


def _random_mouse_move(page):
    """模拟随机鼠标移动，看起来更像人类"""
    try:
        # 在页面上随机选择几个点移动
        for _ in range(random.randint(2, 4)):
            x = random.randint(100, 1000)
            y = random.randint(100, 600)
            page.mouse.move(x, y, steps=random.randint(10, 20))
            page.wait_for_timeout(random.randint(50, 150))
    except Exception:
        pass


def _random_scroll(page):
    """模拟随机滚动页面"""
    try:
        # 随机向上或向下滚动
        scroll_y = random.randint(-200, 300)
        page.mouse.wheel(0, scroll_y)
        page.wait_for_timeout(random.randint(200, 500))
        # 再滚回来一点
        if scroll_y > 100:
            page.mouse.wheel(0, random.randint(-50, 0))
    except Exception:
        pass


def _random_click(page):
    """模拟点击页面空白区域"""
    try:
        # 点击一些安全的区域（不是按钮或链接）
        page.mouse.click(
            random.randint(100, 500),
            random.randint(100, 300)
        )
        page.wait_for_timeout(random.randint(200, 500))
    except Exception:
        pass


def _human_like_pause(page, min_sec: float = 2.0, max_sec: float = 5.0):
    """模拟人类思考/阅读的暂停，期间有一些小动作"""
    total_wait = random.uniform(min_sec, max_sec)
    start_time = time.time()

    # 在等待期间穿插一些小动作
    while time.time() - start_time < total_wait:
        action_choice = random.random()

        if action_choice < 0.3:  # 30% 概率移动鼠标
            _random_mouse_move(page)
        elif action_choice < 0.5:  # 20% 概率滚动
            _random_scroll(page)
        elif action_choice < 0.6:  # 10% 概率点击空白
            _random_click(page)
        else:  # 40% 概率只是等待
            page.wait_for_timeout(random.randint(300, 800))


def _get_delay_for_question(question_index: int, total_questions: int) -> tuple[float, float]:
    """
    根据问题位置获取合适的延迟时间
    第一个问题可以短一些，后面的问题需要更长的间隔
    """
    if question_index == 0:
        # 第一个问题：热身阶段，短一点
        return (60, 90)
    elif question_index == 1:
        # 第二个问题：中等
        return (90, 120)
    else:
        # 第三个及以后：更长的间隔
        return (120, 180)


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

    # 方法1: 用用户提供的class特征来找消息容器
    try:
        # 找包含用户提供的class特征的元素
        selectors = [
            # 用户提供的class特征
            'div[class*="pl-8"][class*="pr-0"][class*="w-full"]',
            'div[class*="max-dbx-xs"]',
            # 标准assistant消息选择器
            'div[data-message-author-role="assistant"]',
            'div[class*="message"][class*="assistant"]',
            'div[class*="assistant"][class*="content"]',
            'article',
        ]

        for sel in selectors:
            elements = page.query_selector_all(sel)
            if elements and len(elements) > 0:
                # 只取最后一个元素（最新的回复）
                last_element = elements[-1]
                text = last_element.inner_text().strip()
                if text and len(text) > 20:  # 确保不是空的或太短的
                    print(f"    [OK] 提取最新回复成功 ({len(text)} chars)")
                    return text
    except Exception:
        pass

    # 方法2: 尝试通过JavaScript获取最新回复（排除侧边栏）
    try:
        text = page.evaluate('''() => {
            // 先排除侧边栏元素
            const sidebars = document.querySelectorAll('[class*="sidebar"], [class*="history"], [class*="nav"], [class*="menu"], [class*="list"]');
            sidebars.forEach(el => {
                try { el.style.display = 'none'; } catch(e) {}
            });

            // 再找所有消息元素
            const allElements = document.querySelectorAll('div, article');
            let lastAssistantText = '';

            for (let i = allElements.length - 1; i >= 0; i--) {
                const el = allElements[i];
                const text = el.innerText || '';
                const className = el.className || '';

                // 跳过已隐藏的和太短的
                if (!text || text.length < 30) continue;

                // 找看起来像assistant回复的元素
                if (className.includes('assistant') || className.includes('message') ||
                    className.includes('pl-8') || className.includes('pr-0')) {
                    // 恢复侧边栏
                    sidebars.forEach(el => {
                        try { el.style.display = ''; } catch(e) {}
                    });
                    return text;
                }

                // 记录最后一段较长的文本
                if (text.length > 100 && !lastAssistantText) {
                    lastAssistantText = text;
                }
            }

            // 恢复侧边栏
            sidebars.forEach(el => {
                try { el.style.display = ''; } catch(e) {}
            });

            return lastAssistantText;
        }''')
        if text and len(text) > 30:
            print(f"    [OK] JS提取回复成功 ({len(text)} chars)")
            return text
    except Exception:
        pass

    # 方法3: 获取body文本，但做智能过滤
    full_text = page.inner_text("body")

    # 只取文本的后一部分
    if len(full_text) > 2500:
        full_text = full_text[-2000:]

    print(f"    [!] 无法精确定位回复区域，使用过滤后的文本 ({len(full_text)} chars)")
    return full_text


def _ask_one_question(page, url: str, question: str, reply_wait: int) -> str:
    """在已有页面上问一个问题。"""
    print(f"    [Q] Asking: {question[:40]}...")

    if not _safe_goto(page, url, timeout_ms=60000):
        return "[页面加载失败]"

    # 模拟人类浏览：等待 + 轻微滚动
    _human_like_pause(page, 2.0, 4.0)

    textarea = page.query_selector("textarea")
    if not textarea:
        print("    [!] Textarea not found")
        return "[找不到输入框]"

    # 先移动鼠标到输入框附近，再点击
    try:
        box = textarea.bounding_box()
        if box:
            page.mouse.move(
                box["x"] + box["width"] / 2 + random.randint(-10, 10),
                box["y"] + box["height"] / 2 + random.randint(-10, 10),
                steps=random.randint(8, 15)
            )
            page.wait_for_timeout(random.randint(200, 400))
    except Exception:
        pass

    textarea.click()
    page.wait_for_timeout(random.randint(300, 600))  # 随机短等待

    # 输入时也有一些随机性：速度不完全一致，偶尔停顿
    for i, char in enumerate(question):
        textarea.type(char, delay=random.randint(60, 120))
        # 偶尔在标点后稍微停顿一下
        if i > 0 and (char in "，。？！,." or random.random() < 0.05):
            page.wait_for_timeout(random.randint(100, 300))

    # 输入完后等待一下（模拟检查一下）
    _human_like_pause(page, 0.8, 2.0)

    # 尝试多种方式发送问题
    sent = False

    # 方式 1: 优先点击提交按钮
    try:
        send_btn = page.query_selector("button[type='submit']")
        if send_btn and send_btn.is_enabled():
            # 点击按钮前也模拟一下鼠标移动
            try:
                box = send_btn.bounding_box()
                if box:
                    page.mouse.move(
                        box["x"] + box["width"] / 2,
                        box["y"] + box["height"] / 2,
                        steps=random.randint(5, 10)
                    )
                    page.wait_for_timeout(random.randint(100, 300))
            except Exception:
                pass
            send_btn.click()
            sent = True
    except Exception:
        pass

    # 方式 2: 如果按钮不行，重新获取 textarea 按 Enter
    if not sent:
        try:
            # 重新获取 textarea（旧的可能已经 detached）
            textarea_fresh = page.query_selector("textarea")
            if textarea_fresh:
                textarea_fresh.press("Enter")
                sent = True
        except Exception:
            pass

    # 方式 3: 用 page.keyboard 直接按 Enter（焦点在输入框的话也能工作）
    if not sent:
        try:
            page.keyboard.press("Enter")
            sent = True
        except Exception:
            print("    [!] All send methods failed")

    if not sent:
        print("    [!] 无法发送问题")

    print(f"    [Q] Waiting {reply_wait}s for reply...")

    # 等待回复期间也模拟一些人类行为（但不影响回复加载）
    # 先等待一段时间让回复开始生成
    page.wait_for_timeout(min(5000, reply_wait * 1000))

    # 剩余时间内做一些小动作
    remaining = max(0, reply_wait - 5)
    if remaining > 0:
        # 把剩余时间分成几段，穿插人类行为
        segments = min(3, int(remaining / 3))
        for _ in range(segments):
            if random.random() < 0.5:
                _random_mouse_move(page)
            page.wait_for_timeout(random.randint(2000, 4000))

    # 最后再等一下确保回复完成
    page.wait_for_timeout(2000)

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
        for i, q in enumerate(questions):
            resp = _ask_one_question(page, url, q, reply_wait)
            responses.append(resp)

            if len(responses) < len(questions):
                # 根据问题位置使用智能延迟
                min_delay, max_delay = _get_delay_for_question(i, len(questions))
                # 可以通过配置覆盖，但默认使用智能延迟
                config_delay = doubao_config.get("delay_between_questions")
                if config_delay:
                    delay = config_delay
                else:
                    delay = random.uniform(min_delay, max_delay)

                print(f"    [*] Waiting {delay:.1f}s before next question...")

                # 这段等待时间内也可以做一些人类行为
                start_wait = time.time()
                while time.time() - start_wait < delay:
                    # 每 10-20 秒做一个小动作
                    _human_like_pause(page, 5.0, 15.0)
                    # 检查是否已经等够了
                    if time.time() - start_wait >= delay:
                        break

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
            print(f"    [!] 可能原因：已有 Chrome 占用 profile，请先关闭 Chrome 再重试")
            return [f"[Chrome 启动失败] {q}" for q in questions]

        page = context.new_page()

        print("    [*] Warming up browser session...")
        if not _safe_goto(page, url, timeout_ms=60000):
            print("    [!] 无法加载豆包页面，终止")
            return [f"[页面加载失败] {q}" for q in questions]
        page.wait_for_timeout(5000)

        responses = []
        for i, q in enumerate(questions):
            resp = _ask_one_question(page, url, q, reply_wait)
            responses.append(resp)

            if len(responses) < len(questions):
                # 根据问题位置使用智能延迟
                min_delay, max_delay = _get_delay_for_question(i, len(questions))
                # 可以通过配置覆盖，但默认使用智能延迟
                config_delay = doubao_config.get("delay_between_questions")
                if config_delay:
                    delay = config_delay
                else:
                    delay = random.uniform(min_delay, max_delay)

                print(f"    [*] Waiting {delay:.1f}s before next question...")

                # 这段等待时间内也可以做一些人类行为
                start_wait = time.time()
                while time.time() - start_wait < delay:
                    # 每 10-20 秒做一个小动作
                    _human_like_pause(page, 5.0, 15.0)
                    # 检查是否已经等够了
                    if time.time() - start_wait >= delay:
                        break

        try:
            context.close()
        except Exception:
            pass

    return responses

"""GEO Brand Monitor GUI - Tkinter desktop app"""

import os
import sys
import yaml
import threading
import queue
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext


class StreamToLog:
    """将 print() 输出重定向到 GUI 日志和日志文件"""
    def __init__(self, app):
        self.app = app

    def write(self, text):
        text = text.strip()
        if text:
            self.app.task_queue.put(("log", text))

    def flush(self):
        pass

# 打包后 exe 运行时指向 exe 所在目录，开发时指向源码目录
if getattr(sys, 'frozen', False):
    PROJECT_ROOT = Path(sys.executable).parent
else:
    PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from question_generator import generate_questions
from doubao_query import run_doubao_queries
from monitor_analysis import analyze_monitor_results

CONFIG_PATH = PROJECT_ROOT / "config.yaml"


class MonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("GEO 品牌监测工具")
        self.root.geometry("720x720")
        self.root.resizable(False, True)

        self.config = self.load_config()
        self.task_queue = queue.Queue()
        self.running = False
        self.stream_redirector = StreamToLog(self)

        # 日志文件
        self.log_file = PROJECT_ROOT / "monitor.log"
        with open(self.log_file, "w", encoding="utf-8") as f:
            f.write(f"GEO 品牌监测工具 - 运行日志\n")
            f.write(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'=' * 60}\n\n")

        self.build_ui()
        self.load_config_values()
        self.process_queue()

    # ─── Config ───────────────────────────────────────────

    def load_config(self) -> dict:
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}

    def save_config(self):
        self.config["monitor"] = {
            "question": self.var_question.get().strip(),
            "brand": self.var_brand.get().strip(),
            "schedule_hours": self.get_selected_hours(),
        }
        self.config.setdefault("doubao", {})
        self.config["doubao"]["browser"] = self.var_browser.get()
        self.config["doubao"]["chrome_profile"] = self.var_profile.get().strip()
        # 自动判断provider类型
        base_url = self.var_base_url.get().strip()
        provider = self._guess_provider(base_url)
        self.config["llm_api"] = {
            "provider": provider,
            "model": self.var_model.get().strip(),
            "base_url": base_url,
            "api_key": self.var_api_key.get().strip(),
        }
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.dump(self.config, f, allow_unicode=True, default_flow_style=False)

    def _guess_provider(self, base_url):
        """根据base_url自动判断provider类型"""
        if not base_url:
            return "claude"  # 默认
        if "ark.cn-beijing.volces.com" in base_url:
            # 火山引擎 - 根据路径判断
            if "/api/coding" in base_url:
                return "qwen"  # Anthropic兼容接口
            else:
                return "doubao"  # OpenAI兼容接口
        if "maas.aliyuncs.com" in base_url:
            return "qwen"
        if "api.openai.com" in base_url or base_url == "":
            return "openai"
        if "api.anthropic.com" in base_url:
            return "claude"
        # 默认用openai兼容模式
        return "openai"

    def load_config_values(self):
        mon = self.config.get("monitor", {})
        self.var_question.set(mon.get("question", ""))
        self.var_brand.set(mon.get("brand", ""))
        db = self.config.get("doubao", {})
        self.var_browser.set(db.get("browser", "Chrome"))
        self.var_profile.set(db.get("chrome_profile", ""))
        llm = self.config.get("llm_api", {})
        self.var_model.set(llm.get("model", ""))
        self.var_base_url.set(llm.get("base_url", ""))
        self.var_api_key.set(llm.get("api_key", ""))
        hours = mon.get("schedule_hours", [])
        for h in range(24):
            if h in hours:
                self.hour_vars[h].set(True)

    def test_connection(self):
        """测试LLM连接"""
        self.save_config()
        self.log("[*] 正在测试连接...")
        self.set_running(True)

        def test():
            old_stdout = sys.stdout
            sys.stdout = self.stream_redirector
            try:
                from question_generator import generate_questions
                # 用一个简单问题测试
                config = self.config
                result = generate_questions(config, "你好")
                self.log(f"[OK] 连接成功！测试响应: {result[:100]}...")
            except Exception as e:
                self.log(f"[!] 连接失败: {e}")
            finally:
                sys.stdout = old_stdout
                self.set_running(False)

        threading.Thread(target=test, daemon=True).start()

    # ─── UI Building ──────────────────────────────────────

    def build_ui(self):
        PAD = 8
        frame = ttk.Frame(self.root, padding=(12, 10))
        frame.pack(fill=tk.BOTH, expand=True)

        # Row 0: Question
        ttk.Label(frame, text="监测问题：").grid(row=0, column=0, sticky=tk.W, pady=PAD)
        self.var_question = tk.StringVar()
        ttk.Entry(frame, textvariable=self.var_question, width=55).grid(
            row=0, column=1, columnspan=3, sticky=tk.EW, pady=PAD)

        # Row 1: Brand
        ttk.Label(frame, text="监测品牌：").grid(row=1, column=0, sticky=tk.W, pady=PAD)
        self.var_brand = tk.StringVar()
        ttk.Entry(frame, textvariable=self.var_brand, width=55).grid(
            row=1, column=1, columnspan=3, sticky=tk.EW, pady=PAD)

        # Row 2: Browser selection + profile path
        ttk.Label(frame, text="浏览器：").grid(row=2, column=0, sticky=tk.W, pady=PAD)
        self.var_browser = tk.StringVar()
        browser_cb = ttk.Combobox(frame, textvariable=self.var_browser, width=10,
                                   state="readonly", values=["Chrome", "Edge"])
        browser_cb.grid(row=2, column=1, sticky=tk.W, pady=PAD, padx=(0, 8))
        self.var_profile = tk.StringVar()
        ttk.Entry(frame, textvariable=self.var_profile, width=38).grid(
            row=2, column=2, sticky=tk.EW, pady=PAD)
        ttk.Button(frame, text="自动检测", command=self.auto_detect_profile).grid(
            row=2, column=3, padx=(4, 0), pady=PAD)

        # Row 3: LLM Settings header
        ttk.Label(frame, text="LLM 设置：", font=("", 9, "bold")).grid(
            row=3, column=0, columnspan=3, sticky=tk.W, pady=(PAD, 0))

        # Row 4: Model
        ttk.Label(frame, text="  模型名称：").grid(row=4, column=0, sticky=tk.W, pady=(PAD//2, 0))
        self.var_model = tk.StringVar()
        ttk.Entry(frame, textvariable=self.var_model, width=30).grid(
            row=4, column=1, columnspan=2, sticky=tk.W, pady=(PAD//2, 0))

        # Row 5: Base URL
        ttk.Label(frame, text="  API 地址：").grid(row=5, column=0, sticky=tk.W, pady=(PAD//2, 0))
        self.var_base_url = tk.StringVar()
        ttk.Entry(frame, textvariable=self.var_base_url, width=55).grid(
            row=5, column=1, columnspan=2, sticky=tk.EW, pady=(PAD//2, 0))
        # 测试连接按钮
        self.btn_test = ttk.Button(frame, text="测试连接", command=self.test_connection)
        self.btn_test.grid(row=5, column=3, padx=(4, 0), pady=(PAD//2, 0))

        # Row 6: API Key
        ttk.Label(frame, text="  API Key：").grid(row=6, column=0, sticky=tk.W, pady=(PAD//2, 0))
        self.var_api_key = tk.StringVar()
        ttk.Entry(frame, textvariable=self.var_api_key, width=55, show="*").grid(
            row=6, column=1, columnspan=3, sticky=tk.EW, pady=(PAD//2, 0))

        # Row 7: Separator
        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(
            row=7, column=0, columnspan=4, sticky=tk.EW, pady=(PAD, PAD))

        # Row 8: Time points label
        ttk.Label(frame, text="监测时间点（整点，最多5个）：").grid(
            row=8, column=0, columnspan=4, sticky=tk.W, pady=PAD)

        # Row 9: Hour checkboxes
        self.hour_vars = {}
        hour_frame = ttk.Frame(frame)
        hour_frame.grid(row=9, column=0, columnspan=4, sticky=tk.W, pady=(0, PAD))
        for row_i in range(2):
            for col_i in range(12):
                h = row_i * 12 + col_i
                self.hour_vars[h] = tk.BooleanVar()
                cb = ttk.Checkbutton(hour_frame, text=f"{h:02d}:00", variable=self.hour_vars[h])
                cb.grid(row=row_i, column=col_i, padx=2)

        # Row 10: Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=10, column=0, columnspan=4, pady=PAD)
        self.btn_now = ttk.Button(btn_frame, text="立即执行（一轮）", command=self.run_now)
        self.btn_now.pack(side=tk.LEFT, padx=(0, 8))
        self.btn_watch = ttk.Button(btn_frame, text="定时监测", command=self.run_watch)
        self.btn_watch.pack(side=tk.LEFT)
        ttk.Separator(btn_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=12)
        self.btn_folder = ttk.Button(btn_frame, text="打开报告文件夹", command=self.open_report_folder)
        self.btn_folder.pack(side=tk.LEFT, padx=(0, 4))
        self.btn_log = ttk.Button(btn_frame, text="查看运行日志", command=self.open_log_file)
        self.btn_log.pack(side=tk.LEFT)

        # Row 11-12: Log area
        ttk.Label(frame, text="运行日志：").grid(row=11, column=0, sticky=tk.W, pady=(PAD, 0))
        self.log_area = scrolledtext.ScrolledText(
            frame, height=10, state=tk.DISABLED, wrap=tk.WORD,
            font=("Consolas", 9))
        self.log_area.grid(row=12, column=0, columnspan=4, sticky=tk.NSEW, pady=(0, PAD))
        frame.grid_rowconfigure(12, weight=1)

    # ─── Helpers ──────────────────────────────────────────

    def auto_detect_profile(self):
        browser_type = self.var_browser.get()
        from doubao_query import _find_default_profile
        profile = _find_default_profile(browser_type)
        if profile:
            self.var_profile.set(profile)
            self.log(f"[*] 自动检测到 {browser_type} profile: {profile}")
        else:
            # 尝试另一个浏览器
            fallback = "Edge" if browser_type == "Chrome" else "Chrome"
            profile2 = _find_default_profile(fallback)
            if profile2:
                self.var_browser.set(fallback)
                self.var_profile.set(profile2)
                self.log(f"[*] 未找到 {browser_type}，自动切换到 {fallback}: {profile2}")
            else:
                self.log(f"[!] 未检测到 Chrome 或 Edge profile，请手动输入")
                messagebox.showwarning("提示", "未检测到 Chrome 或 Edge profile")

    def get_selected_hours(self) -> list[int]:
        hours = sorted(h for h, v in self.hour_vars.items() if v.get())
        return hours[:5]

    def validate_inputs(self) -> bool:
        if not self.var_question.get().strip():
            messagebox.showwarning("提示", "请输入监测问题")
            return False
        if not self.var_brand.get().strip():
            messagebox.showwarning("提示", "请输入监测品牌")
            return False
        if not self.var_profile.get().strip():
            messagebox.showwarning("提示", "请设置 Chrome profile 路径")
            return False
        if not os.path.isdir(self.var_profile.get().strip()):
            messagebox.showwarning("提示", "Chrome profile 路径不存在")
            return False
        return True

    def log(self, msg: str):
        self.log_area.configure(state=tk.NORMAL)
        self.log_area.insert(tk.END, msg + "\n")
        self.log_area.see(tk.END)
        self.log_area.configure(state=tk.DISABLED)
        # 同时写入日志文件
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"{datetime.now().strftime('%H:%M:%S')} {msg}\n")
        except Exception:
            pass

    def set_running(self, running: bool):
        self.running = running
        self.btn_now.configure(state=tk.NORMAL if not running else tk.DISABLED)
        self.btn_watch.configure(state=tk.NORMAL if not running else tk.DISABLED)
        self.btn_test.configure(state=tk.NORMAL if not running else tk.DISABLED)

    def open_report_folder(self):
        monitor_dir = PROJECT_ROOT / "output" / "monitor"
        if monitor_dir.exists():
            os.startfile(str(monitor_dir))
        else:
            # Create it and open anyway
            monitor_dir.mkdir(parents=True, exist_ok=True)
            os.startfile(str(monitor_dir))

    def open_log_file(self):
        if self.log_file.exists():
            os.startfile(str(self.log_file))
        else:
            messagebox.showinfo("提示", "暂无运行日志")

    # ─── Execution ────────────────────────────────────────

    def run_now(self):
        if not self.validate_inputs():
            return
        self.save_config()
        self.log_area.configure(state=tk.NORMAL)
        self.log_area.delete(1.0, tk.END)
        self.log_area.configure(state=tk.DISABLED)
        self.set_running(True)
        self.log(f"[*] 开始立即执行 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        self.log(f"[*] 问题: {self.var_question.get().strip()}")
        self.log(f"[*] 品牌: {self.var_brand.get().strip()}")

        threading.Thread(target=self._task_now, daemon=True).start()

    def run_watch(self):
        if not self.validate_inputs():
            return
        hours = self.get_selected_hours()
        if not hours:
            messagebox.showwarning("提示", "请至少选择一个监测时间点")
            return
        self.save_config()
        self.log_area.configure(state=tk.NORMAL)
        self.log_area.delete(1.0, tk.END)
        self.log_area.configure(state=tk.DISABLED)
        self.set_running(True)
        self.log(f"[*] 开始定时监测 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        self.log(f"[*] 计划时间点: {', '.join(f'{h}:00' for h in hours)}")

        threading.Thread(target=self._task_watch, daemon=True).start()

    def _task_now(self):
        """Background thread: run one round immediately"""
        old_stdout = sys.stdout
        sys.stdout = self.stream_redirector
        try:
            self._run_single_round("now", datetime.now().hour)
        except Exception as e:
            self.log(f"[!] 错误: {e}")
        finally:
            sys.stdout = old_stdout
            self.set_running(False)
            self.log("[*] 执行完毕")

    def _task_watch(self):
        """Background thread: wait for scheduled hours"""
        old_stdout = sys.stdout
        sys.stdout = self.stream_redirector
        try:
            hours = self.get_selected_hours()
            current_hour = datetime.now().hour
            pending = [h for h in hours if h > current_hour]

            if not pending:
                self.log(f"[*] 今日计划时间点已全部经过，是否立即执行一轮？")
                self.task_queue.put(("ask_run_now", None))
                result = self.task_queue.get()
                if result == "yes":
                    self._run_single_round("now", datetime.now().hour)
                else:
                    self.log("[*] 已取消")
                return

            for hour in pending:
                self.log(f"[*] 等待到 {hour}:00 ...")
                # Calculate wait time
                target = datetime.now().replace(hour=hour, minute=0, second=0, microsecond=0)
                wait_sec = (target - datetime.now()).total_seconds()
                if wait_sec < 0:
                    wait_sec = 0
                import time as _time
                _time.sleep(wait_sec)

                self.log(f"[*] === {hour}:00 开始执行 ===")
                self._run_single_round(str(hour), hour)

        except Exception as e:
            self.log(f"[!] 错误: {e}")
        finally:
            sys.stdout = old_stdout
            self.set_running(False)
            self.log("[*] 定时监测完成")

    def _run_single_round(self, label: str, hour: int):
        """Run one complete round: generate questions → ask Doubao → analyze"""
        config = self.config
        doubao_config = config.setdefault("doubao", {})
        doubao_config["chrome_profile"] = self.var_profile.get().strip()

        question = self.var_question.get().strip()
        brand = self.var_brand.get().strip()

        # Step 1: Generate questions
        self.log("[1] 衍生问题中...")
        questions = generate_questions(config, question)
        self.log(f"    共 {len(questions)} 个问题:")
        for i, q in enumerate(questions, 1):
            self.log(f"      Q{i}: {q}")

        # Step 2: Ask Doubao
        self.log("[2] 向豆包提问中...")
        responses = run_doubao_queries(config, questions)

        # Save raw data
        result = {
            "hour": hour,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "questions": questions,
            "responses": responses,
        }
        date_str = datetime.now().strftime("%Y%m%d")
        save_dir = PROJECT_ROOT / "output" / "monitor" / date_str
        save_dir.mkdir(parents=True, exist_ok=True)
        with open(save_dir / f"timepoint_{hour:02d}.json", "w", encoding="utf-8") as f:
            import json
            json.dump(result, f, ensure_ascii=False, indent=2)
        self.log(f"    数据已保存: timepoint_{hour:02d}.json")

        # Step 3: Analyze
        self.log("[3] 分析中...")
        report = analyze_monitor_results(config, question, brand, [result])

        report_file = save_dir / f"monitor_report_{brand}_{date_str}.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(f"# 品牌监测报告 - {brand}\n\n")
            f.write(f"**监测问题**: {question}\n\n")
            f.write(f"**监测日期**: {date_str}\n\n")
            f.write(f"**执行轮次**: {label}\n\n---\n\n")
            f.write(report)
        self.log(f"    报告已保存: {report_file.name}")

    def process_queue(self):
        """Process messages from background thread to main thread"""
        try:
            while True:
                msg_type, msg_data = self.task_queue.get_nowait()
                if msg_type == "log":
                    self.log(msg_data)
                elif msg_type == "ask_run_now":
                    self.set_running(False)
                    result = messagebox.askyesno("确认", "今日已无待执行时间点，是否立即执行一轮？")
                    self.task_queue.put("yes" if result else "no")
                    self.set_running(True)
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)


def main():
    root = tk.Tk()
    app = MonitorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

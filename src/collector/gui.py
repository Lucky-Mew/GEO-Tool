"""GEO Brand Monitor GUI - Tkinter desktop app"""

import os
import sys
import yaml
import threading
import queue
import json
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config import (
    get_project_root, get_data_dir, get_monitor_data_dir, load_config, save_config
)
from src.collector.doubao_query import run_doubao_queries, _find_default_profile
from src.collector.monitor_analysis import analyze_monitor_results
from src.db import models, importer

PROJECT_ROOT = get_project_root()


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


class AddTaskDialog:
    """添加GEO监测任务的弹窗"""
    def __init__(self, parent):
        self.result = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("添加GEO监测任务")
        self.dialog.geometry("480x220")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # 居中显示在父窗口上
        self._center_on_parent(parent)

        self._build_ui()

    def _center_on_parent(self, parent):
        """让弹窗居中显示在父窗口"""
        parent.update_idletasks()
        # 获取父窗口位置和大小
        p_x = parent.winfo_x()
        p_y = parent.winfo_y()
        p_w = parent.winfo_width()
        p_h = parent.winfo_height()
        # 获取弹窗大小
        d_w = 480
        d_h = 220
        # 计算居中位置
        x = p_x + (p_w - d_w) // 2
        y = p_y + (p_h - d_h) // 2
        self.dialog.geometry(f"{d_w}x{d_h}+{x}+{y}")

    def _build_ui(self):
        PAD = 12
        frame = ttk.Frame(self.dialog, padding=(PAD, PAD))
        frame.pack(fill=tk.BOTH, expand=True)

        # 监测问题
        ttk.Label(frame, text="监测问题：").grid(row=0, column=0, sticky=tk.W, pady=(0, 4))
        self.var_question = tk.StringVar()
        question_entry = ttk.Entry(frame, textvariable=self.var_question, width=50)
        question_entry.grid(row=1, column=0, sticky=tk.EW, pady=(0, PAD))

        # 监测品牌
        ttk.Label(frame, text="监测品牌（多个用 ; 分隔）：").grid(row=2, column=0, sticky=tk.W, pady=(0, 4))
        self.var_brands = tk.StringVar()
        brands_entry = ttk.Entry(frame, textvariable=self.var_brands, width=50)
        brands_entry.grid(row=3, column=0, sticky=tk.EW, pady=(0, 4))
        ttk.Label(frame, text="例如：完形康躰;康体;完型", font=("", 8)).grid(row=4, column=0, sticky=tk.W, pady=(0, PAD))

        # 按钮
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=5, column=0, pady=(PAD, 0))
        ttk.Button(btn_frame, text="添加", command=self._on_add).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_frame, text="关闭", command=self._on_cancel).pack(side=tk.LEFT)

        frame.grid_columnconfigure(0, weight=1)

        # 聚焦到第一个输入框
        question_entry.focus_set()

    def _on_add(self):
        question = self.var_question.get().strip()
        brands_str = self.var_brands.get().strip()

        if not question:
            messagebox.showwarning("提示", "请输入监测问题")
            return
        if not brands_str:
            messagebox.showwarning("提示", "请输入监测品牌")
            return

        # 分割品牌名
        brands = [b.strip() for b in brands_str.split(";") if b.strip()]
        if not brands:
            messagebox.showwarning("提示", "请输入有效的品牌名")
            return

        self.result = {"question": question, "brands": brands}
        self.dialog.destroy()

    def _on_cancel(self):
        self.dialog.destroy()

    def show(self):
        self.dialog.wait_window()
        return self.result


class MonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("GEO 品牌监测工具")
        self.root.geometry("800x860")
        self.root.resizable(False, True)

        self.config = load_config()
        self.task_queue = queue.Queue()
        self.running = False
        self.stream_redirector = StreamToLog(self)

        # GEO监测任务列表
        self.geo_tasks = []

        # 日志文件
        self.log_file = PROJECT_ROOT / "monitor.log"
        with open(self.log_file, "w", encoding="utf-8") as f:
            f.write(f"GEO 品牌监测工具 - 运行日志\n")
            f.write(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'=' * 60}\n\n")

        self.build_ui()
        self.load_config_values()
        self.process_queue()

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

        # 兼容旧版配置
        if "tasks" not in mon:
            # 把旧的单个问题/品牌转成新格式
            old_question = mon.get("question", "")
            old_brand = mon.get("brand", "")
            if old_question and old_brand:
                self.geo_tasks = [{"question": old_question, "brands": [old_brand]}]
            else:
                self.geo_tasks = []
        else:
            self.geo_tasks = mon.get("tasks", [])

        self._refresh_task_list()

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

    def _refresh_task_list(self):
        """刷新任务列表显示"""
        # 清空现有的
        for widget in self.task_list_frame.winfo_children():
            widget.destroy()

        if not self.geo_tasks:
            ttk.Label(self.task_list_frame, text="暂无监测任务，点击下方按钮添加",
                     foreground="gray").pack(pady=20)
            return

        for i, task in enumerate(self.geo_tasks, 1):
            task_frame = ttk.Frame(self.task_list_frame)
            task_frame.pack(fill=tk.X, pady=4)

            # 任务内容 - 分成两行显示，更清晰
            info_frame = ttk.Frame(task_frame)
            info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

            ttk.Label(info_frame, text=f"{i}. 问题：{task['question']}",
                     font=("", 9, "bold")).pack(anchor=tk.W)
            ttk.Label(info_frame, text=f"   品牌：{';'.join(task['brands'])}",
                     foreground="#555").pack(anchor=tk.W)

            # 删除按钮
            del_btn = ttk.Button(task_frame, text="删除", width=8,
                                command=lambda idx=i-1: self._delete_task(idx))
            del_btn.pack(side=tk.RIGHT, padx=(8, 0))

    def _add_task(self):
        """添加任务弹窗"""
        dialog = AddTaskDialog(self.root)
        result = dialog.show()
        if result:
            self.geo_tasks.append(result)
            self._refresh_task_list()
            self.log(f"[*] 已添加监测任务：{result['question']}")

    def _delete_task(self, idx):
        """删除任务"""
        task = self.geo_tasks.pop(idx)
        self._refresh_task_list()
        self.log(f"[*] 已删除监测任务：{task['question']}")

    def test_connection(self):
        """测试LLM连接 - 暂时保留，简单测试"""
        self._save_config()
        self.log("[*] 测试功能（LLM连接测试暂不需要）")
        # 暂时不需要，因为去掉了问题生成功能

    def open_web_dashboard(self):
        """打开Web仪表盘"""
        try:
            import webbrowser
            import subprocess
            import time

            # 先尝试启动Web服务
            def start_web():
                try:
                    subprocess.Popen([sys.executable, str(PROJECT_ROOT / "run_web.py")],
                                   cwd=str(PROJECT_ROOT),
                                   creationflags=subprocess.CREATE_NEW_CONSOLE)
                    time.sleep(2)
                    webbrowser.open("http://localhost:5000")
                except Exception as e:
                    self.log(f"[!] 启动Web仪表盘失败: {e}")

            threading.Thread(target=start_web, daemon=True).start()
            self.log("[*] 正在启动Web仪表盘...")
        except Exception as e:
            self.log(f"[!] 错误: {e}")

    def import_existing_data(self):
        """导入现有数据到数据库 - 兼容旧版"""
        self.log("[*] 正在导入现有数据...")
        # 用第一个任务的品牌，如果有的话
        brand = "完形康躰"
        question = "康躰脂雕哪家好"
        if self.geo_tasks:
            brand = self.geo_tasks[0]["brands"][0]
            question = self.geo_tasks[0]["question"]

        def import_data():
            old_stdout = sys.stdout
            sys.stdout = self.stream_redirector
            try:
                importer.import_all_existing_data(brand, question)
                self.log("[OK] 数据导入完成！")
            except Exception as e:
                self.log(f"[!] 导入失败: {e}")
            finally:
                sys.stdout = old_stdout

        threading.Thread(target=import_data, daemon=True).start()

    def build_ui(self):
        PAD = 8
        main_frame = ttk.Frame(self.root, padding=(12, 10))
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ==================== 第一部分：GEO监测任务列表 ====================
        ttk.Label(main_frame, text="GEO监测任务：", font=("", 10, "bold")).grid(
            row=0, column=0, sticky=tk.W, pady=(0, 4))

        # 任务列表容器 - 用LabelFrame更简单
        self.task_list_frame = ttk.LabelFrame(main_frame, padding=(8, 8))
        self.task_list_frame.grid(row=1, column=0, sticky=tk.EW, pady=(0, PAD))

        # 添加任务按钮
        ttk.Button(main_frame, text="+ 添加GEO监测任务", command=self._add_task).grid(
            row=2, column=0, sticky=tk.W, pady=(0, PAD))

        # 分隔线
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).grid(
            row=3, column=0, sticky=tk.EW, pady=(PAD, PAD))

        # ==================== 第二部分：浏览器设置 ====================
        ttk.Label(main_frame, text="浏览器设置：", font=("", 9, "bold")).grid(
            row=4, column=0, sticky=tk.W, pady=(0, 4))

        browser_frame = ttk.Frame(main_frame)
        browser_frame.grid(row=5, column=0, sticky=tk.EW, pady=(0, PAD))

        ttk.Label(browser_frame, text="浏览器：").pack(side=tk.LEFT)
        self.var_browser = tk.StringVar()
        browser_cb = ttk.Combobox(browser_frame, textvariable=self.var_browser, width=10,
                                   state="readonly", values=["Chrome", "Edge"])
        browser_cb.pack(side=tk.LEFT, padx=(4, 8))

        self.var_profile = tk.StringVar()
        ttk.Entry(browser_frame, textvariable=self.var_profile, width=40).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(browser_frame, text="自动检测", command=self.auto_detect_profile).pack(side=tk.LEFT)

        # ==================== 第三部分：LLM 设置 ====================
        ttk.Label(main_frame, text="LLM 设置：", font=("", 9, "bold")).grid(
            row=6, column=0, sticky=tk.W, pady=(PAD, 4))

        llm_frame = ttk.Frame(main_frame)
        llm_frame.grid(row=7, column=0, sticky=tk.EW, pady=(0, PAD))

        ttk.Label(llm_frame, text="模型：").grid(row=0, column=0, sticky=tk.W)
        self.var_model = tk.StringVar()
        ttk.Entry(llm_frame, textvariable=self.var_model, width=30).grid(row=0, column=1, sticky=tk.W, padx=(4, 16))

        ttk.Label(llm_frame, text="API地址：").grid(row=0, column=2, sticky=tk.W)
        self.var_base_url = tk.StringVar()
        ttk.Entry(llm_frame, textvariable=self.var_base_url, width=32).grid(row=0, column=3, sticky=tk.W, padx=(4, 0))

        ttk.Label(llm_frame, text="APIKey：").grid(row=1, column=0, sticky=tk.W, pady=(4, 0))
        self.var_api_key = tk.StringVar()
        ttk.Entry(llm_frame, textvariable=self.var_api_key, width=70, show="*").grid(
            row=1, column=1, columnspan=4, sticky=tk.W, padx=(4, 0), pady=(4, 0))

        # 分隔线
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).grid(
            row=8, column=0, sticky=tk.EW, pady=(PAD, PAD))

        # ==================== 第四部分：时间点设置 ====================
        ttk.Label(main_frame, text="监测时间点（整点，最多5个）：").grid(
            row=9, column=0, sticky=tk.W, pady=(0, 4))

        self.hour_vars = {}
        hour_frame = ttk.Frame(main_frame)
        hour_frame.grid(row=10, column=0, sticky=tk.W, pady=(0, PAD))
        for row_i in range(2):
            for col_i in range(12):
                h = row_i * 12 + col_i
                self.hour_vars[h] = tk.BooleanVar()
                cb = ttk.Checkbutton(hour_frame, text=f"{h:02d}:00", variable=self.hour_vars[h])
                cb.grid(row=row_i, column=col_i, padx=2)

        # ==================== 第五部分：操作按钮 ====================
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=11, column=0, pady=(0, PAD))

        self.btn_now = ttk.Button(btn_frame, text="立即执行（一轮）", command=self.run_now)
        self.btn_now.pack(side=tk.LEFT, padx=(0, 8))
        self.btn_watch = ttk.Button(btn_frame, text="定时监测", command=self.run_watch)
        self.btn_watch.pack(side=tk.LEFT, padx=(0, 8))

        ttk.Separator(btn_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=12)

        self.btn_web = ttk.Button(btn_frame, text="Web仪表盘", command=self.open_web_dashboard)
        self.btn_web.pack(side=tk.LEFT, padx=(0, 8))
        self.btn_import = ttk.Button(btn_frame, text="导入数据", command=self.import_existing_data)
        self.btn_import.pack(side=tk.LEFT, padx=(0, 8))

        ttk.Separator(btn_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=12)

        self.btn_folder = ttk.Button(btn_frame, text="打开报告文件夹", command=self.open_report_folder)
        self.btn_folder.pack(side=tk.LEFT, padx=(0, 4))
        self.btn_log = ttk.Button(btn_frame, text="查看运行日志", command=self.open_log_file)
        self.btn_log.pack(side=tk.LEFT)

        # ==================== 第六部分：日志 ====================
        ttk.Label(main_frame, text="运行日志：").grid(row=12, column=0, sticky=tk.W, pady=(PAD, 0))
        self.log_area = scrolledtext.ScrolledText(
            main_frame, height=10, state=tk.DISABLED, wrap=tk.WORD,
            font=("Consolas", 9))
        self.log_area.grid(row=13, column=0, sticky=tk.NSEW, pady=(0, 0))
        main_frame.grid_rowconfigure(13, weight=1)

    def auto_detect_profile(self):
        browser_type = self.var_browser.get()
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
        if not self.geo_tasks:
            messagebox.showwarning("提示", "请至少添加一个GEO监测任务")
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
        self.btn_web.configure(state=tk.NORMAL if not running else tk.DISABLED)
        self.btn_import.configure(state=tk.NORMAL if not running else tk.DISABLED)

    def open_report_folder(self):
        monitor_dir = get_monitor_data_dir()
        if monitor_dir.exists():
            os.startfile(str(monitor_dir))
        else:
            monitor_dir.mkdir(parents=True, exist_ok=True)
            os.startfile(str(monitor_dir))

    def open_log_file(self):
        if self.log_file.exists():
            os.startfile(str(self.log_file))
        else:
            messagebox.showinfo("提示", "暂无运行日志")

    def _save_config(self):
        self.config["monitor"] = {
            "tasks": self.geo_tasks,
            "schedule_hours": self.get_selected_hours(),
        }
        self.config.setdefault("doubao", {})
        self.config["doubao"]["browser"] = self.var_browser.get()
        self.config["doubao"]["chrome_profile"] = self.var_profile.get().strip()
        base_url = self.var_base_url.get().strip()
        provider = self._guess_provider(base_url)
        self.config["llm_api"] = {
            "provider": provider,
            "model": self.var_model.get().strip(),
            "base_url": base_url,
            "api_key": self.var_api_key.get().strip(),
        }
        save_config(self.config)

    def run_now(self):
        if not self.validate_inputs():
            return
        self._save_config()
        self.log_area.configure(state=tk.NORMAL)
        self.log_area.delete(1.0, tk.END)
        self.log_area.configure(state=tk.DISABLED)
        self.set_running(True)
        self.log(f"[*] 开始立即执行 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        self.log(f"[*] 共 {len(self.geo_tasks)} 个监测任务")

        threading.Thread(target=self._task_now, daemon=True).start()

    def run_watch(self):
        if not self.validate_inputs():
            return
        hours = self.get_selected_hours()
        if not hours:
            messagebox.showwarning("提示", "请至少选择一个监测时间点")
            return
        self._save_config()
        self.log_area.configure(state=tk.NORMAL)
        self.log_area.delete(1.0, tk.END)
        self.log_area.configure(state=tk.DISABLED)
        self.set_running(True)
        self.log(f"[*] 开始定时监测 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        self.log(f"[*] 共 {len(self.geo_tasks)} 个监测任务")
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
        """Run one complete round: execute each geo task"""
        config = self.config
        doubao_config = config.setdefault("doubao", {})
        doubao_config["chrome_profile"] = self.var_profile.get().strip()

        date_str = datetime.now().strftime("%Y%m%d")
        time_str = datetime.now().strftime("%H%M")
        save_dir = get_monitor_data_dir() / date_str
        save_dir.mkdir(parents=True, exist_ok=True)

        # 收集所有问题，一次性问豆包（更高效）
        all_questions = [task["question"] for task in self.geo_tasks]

        self.log(f"[1] 准备向豆包提问，共 {len(all_questions)} 个问题")

        # 向豆包提问
        self.log("[2] 向豆包提问中...")
        response_dicts = run_doubao_queries(config, all_questions)
        responses = [r["answer"] for r in response_dicts]
        citations_list = [r["citations"] for r in response_dicts]

        # 保存整体原始数据
        all_results = []
        for task_idx, (task, resp, citations) in enumerate(zip(self.geo_tasks, responses, citations_list)):
            result = {
                "task_idx": task_idx,
                "question": task["question"],
                "brands": task["brands"],
                "response": resp,
                "citations": citations,
            }
            all_results.append(result)

        # 保存整体JSON
        master_json = {
            "hour": hour,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "tasks": self.geo_tasks,
            "results": all_results,
        }
        json_path = save_dir / f"timepoint_{hour:02d}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(master_json, f, ensure_ascii=False, indent=2)
        self.log(f"    整体数据已保存: timepoint_{hour:02d}.json")

        # 为每个任务单独保存文档和处理
        self.log("[3] 保存各任务文档...")

        # 先读取当天已有的所有timepoint_*.json文件，用于整体分析
        existing_timepoints = []
        for json_file in sorted(save_dir.glob("timepoint_*.json")):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    tp_data = json.load(f)
                    existing_timepoints.append(tp_data)
            except Exception as e:
                self.log(f"    [!] 读取历史数据{json_file.name}失败: {e}")

        for task_idx, (task, resp, citations) in enumerate(zip(self.geo_tasks, responses, citations_list), 1):
            primary_brand = task["brands"][0]

            # 为每个任务创建单独的文件夹
            safe_q = "".join(c for c in task["question"] if c not in r'\/:*?"<>|')[:30]
            task_folder_name = f"任务{task_idx}_{safe_q}"
            task_folder = save_dir / task_folder_name
            task_folder.mkdir(parents=True, exist_ok=True)

            # 保存豆包回答文档（仅当前时间点的）
            answer_file = task_folder / f"{time_str}_豆包回答.md"
            with open(answer_file, "w", encoding="utf-8") as f:
                f.write(f"# 监测问题\n\n")
                f.write(f"{task['question']}\n\n")
                f.write(f"**监测品牌**: {';'.join(task['brands'])}\n\n")
                f.write(f"**提问时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("---\n\n")
                f.write("## 豆包回答\n\n")
                f.write(f"{resp}\n\n")
                f.write("---\n\n")
                f.write(f"## 参考资料（共 {len(citations)} 条）\n\n")
                if citations:
                    for j, cite in enumerate(citations, 1):
                        f.write(f"[{j}] {cite['title']}\n")
                        f.write(f"    {cite['url']}\n\n")
                else:
                    f.write("(无参考资料)\n")

            # 保存到数据库
            try:
                task_id = models.insert_monitor_task(
                    date_str, hour, master_json["timestamp"], primary_brand, task["question"]
                )
                qid = models.insert_questions(task_id, [task["question"]], [resp])[0]

                # 支持多品牌变种名提取
                mention_info = importer.extract_brand_mentions(resp, primary_brand)
                # 检查其他变种名是否提到
                for brand_variant in task["brands"][1:]:
                    variant_info = importer.extract_brand_mentions(resp, brand_variant)
                    if variant_info["target_mentioned"]:
                        # 如果变种名提到了，合并信息
                        mention_info["target_mentioned"] = True
                        if not mention_info["position"] and variant_info["position"]:
                            mention_info["position"] = variant_info["position"]
                        # 合并品牌发现 - 注意 brands_found 是字典
                        for bname, cnt in variant_info["brands_found"].items():
                            if bname in mention_info["brands_found"]:
                                mention_info["brands_found"][bname] += cnt
                            else:
                                mention_info["brands_found"][bname] = cnt

                if mention_info["target_mentioned"]:
                    models.insert_brand_mention(
                        qid,
                        brand_name=primary_brand,
                        mention_position=mention_info["position"],
                        sentiment=mention_info["sentiment"]
                    )
                # 保存其他品牌
                for bname in set(mention_info["brands_found"].keys()):
                    if bname not in task["brands"]:
                        models.insert_brand_mention(qid, brand_name=bname)

            except Exception as e:
                self.log(f"    [!] 任务{task_idx}数据库保存失败: {e}")

            # 收集所有时间点中该任务的数据，用于整体分析
            all_results_for_task = []
            for tp_data in existing_timepoints:
                # 在这个时间点的数据中找到对应任务
                for result in tp_data.get("results", []):
                    if result.get("question") == task["question"]:
                        single_result = {
                            "hour": tp_data.get("hour", hour),
                            "timestamp": tp_data.get("timestamp", master_json["timestamp"]),
                            "questions": [result.get("question")],
                            "responses": [result.get("response")],
                            "citations": [result.get("citations", [])],
                        }
                        all_results_for_task.append(single_result)

            # 分析报告 - 使用所有时间点的数据
            report = analyze_monitor_results(config, task["question"], primary_brand, all_results_for_task)

            # 保存分析报告到任务文件夹
            report_file = task_folder / f"分析报告.md"
            with open(report_file, "w", encoding="utf-8") as f:
                f.write(report)

            self.log(f"    任务{task_idx}已保存到文件夹")

        self.log("    数据库保存完成")

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

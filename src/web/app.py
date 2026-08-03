"""Flask Web Dashboard for GEO Brand Monitor"""

import sys
import threading
import queue
import json
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, jsonify, send_from_directory, request

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    HAS_SCHEDULER = True
except ImportError:
    HAS_SCHEDULER = False
    print("[WARNING] APScheduler 未安装，定时监测功能不可用")
    print("安装命令: pip install apscheduler")

# 添加项目根目录
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config import (
    get_monitor_data_dir, load_config, save_config,
    get_project_config, save_project_config, get_default_project_id
)
from src.db import models

from src.collector.doubao_query import run_doubao_queries, _find_default_profile, set_pause_flag, get_pause_flag
from src.collector.monitor_analysis import analyze_monitor_results
from src.db import importer

app = Flask(__name__)

# 确保数据库初始化
models.init_db()

# 全局状态
project_states = {}  # 每个项目的独立状态
log_lock = threading.Lock()  # 日志锁
global_run_lock = threading.Lock()  # 全局运行锁：确保同一时间只有一个任务在执行

# 定时调度器
scheduler = None
if HAS_SCHEDULER:
    scheduler = BackgroundScheduler()

# 任务队列系统
MAX_QUEUE_SIZE = 10  # 最大队列长度
task_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
queue_worker_thread = None
queue_worker_running = False
queue_lock = threading.Lock()

# 队列任务历史记录（最近20条）
queue_history = []
queue_history_lock = threading.Lock()

# 当前正在执行的任务
current_running_task = None

# CAPTCHA 状态
captcha_pending = False
captcha_lock = threading.Lock()


def on_captcha_callback():
    """CAPTCHA 回调：只记录日志，不暂停任务"""
    global captcha_pending
    with captcha_lock:
        captcha_pending = True
    # 不再设置暂停标志，让任务继续执行
    print("[!] 检测到 CAPTCHA 提示，但任务将继续执行（如真的需要验证，请在浏览器中手动完成）")


def get_project_state(project_id: int):
    """获取或创建项目状态"""
    if project_id not in project_states:
        project_states[project_id] = {
            'is_running': False,
            'running_thread': None,
            'run_logs': []
        }
    return project_states[project_id]


def add_log(project_id: int, message: str):
    """添加项目日志"""
    state = get_project_state(project_id)
    timestamp = datetime.now().strftime('%H:%M:%S')
    log_line = f"[{timestamp}] {message}"
    with log_lock:
        state['run_logs'].append(log_line)
        if len(state['run_logs']) > 1000:
            state['run_logs'].pop(0)


def add_queue_history(task_info: dict):
    """添加队列历史记录"""
    with queue_history_lock:
        task_info['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        queue_history.insert(0, task_info)
        if len(queue_history) > 20:
            queue_history.pop()


def queue_worker():
    """队列工作线程：从队列取任务执行"""
    global queue_worker_running, current_running_task
    print("[*] 队列工作线程已启动")

    while queue_worker_running:
        try:
            # 尝试从队列取任务，超时1秒检查是否继续运行
            try:
                task = task_queue.get(timeout=1)
            except queue.Empty:
                continue

            project_id = task['project_id']
            project_name = task.get('project_name', f'项目{project_id}')

            print(f"[*] 开始执行队列任务: {project_name}")

            # 更新当前执行任务
            with queue_lock:
                current_running_task = {
                    'project_id': project_id,
                    'project_name': project_name,
                    'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }

            # 添加历史记录
            add_queue_history({
                'type': 'start',
                'project_id': project_id,
                'project_name': project_name
            })

            # 执行监测任务
            try:
                run_monitor_round(project_id)

                add_queue_history({
                    'type': 'complete',
                    'project_id': project_id,
                    'project_name': project_name
                })
                print(f"[OK] 任务完成: {project_name}")
            except Exception as e:
                add_queue_history({
                    'type': 'error',
                    'project_id': project_id,
                    'project_name': project_name,
                    'error': str(e)
                })
                print(f"[!] 任务执行出错: {e}")
            finally:
                # 清除当前执行任务
                with queue_lock:
                    current_running_task = None
                # 标记任务完成
                task_queue.task_done()

        except Exception as e:
            print(f"[!] 队列工作线程出错: {e}")

    print("[*] 队列工作线程已停止")


def start_queue_worker():
    """启动队列工作线程"""
    global queue_worker_thread, queue_worker_running
    if queue_worker_thread and queue_worker_thread.is_alive():
        return
    queue_worker_running = True
    queue_worker_thread = threading.Thread(target=queue_worker, daemon=True)
    queue_worker_thread.start()


def enqueue_task(project_id: int, project_name: str = None) -> tuple[bool, str]:
    """将任务加入队列"""
    try:
        if task_queue.full():
            return False, f"队列已满（最多{MAX_QUEUE_SIZE}个任务），请稍后再试"

        task = {
            'project_id': project_id,
            'project_name': project_name or f'项目{project_id}',
            'enqueue_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        task_queue.put_nowait(task)

        add_queue_history({
            'type': 'enqueue',
            'project_id': project_id,
            'project_name': project_name
        })

        return True, "任务已加入队列"
    except Exception as e:
        return False, f"加入队列失败: {e}"


def update_scheduler():
    """更新定时调度任务"""
    if not scheduler:
        return

    try:
        scheduler.remove_all_jobs()
        config = load_config()

        for project in config.get('projects', []):
            project_id = project.get('id')
            project_name = project.get('name', '')
            schedule_hours = project.get('config', {}).get('schedule_hours', [])

            if schedule_hours:
                for hour in schedule_hours:
                    job_id = f'project_{project_id}_hour_{hour}'
                    scheduler.add_job(
                        enqueue_task,
                        'cron',
                        args=[project_id, project_name],
                        hour=hour,
                        minute=0,
                        id=job_id,
                        name=f'{project_name}_{hour}:00',
                        misfire_grace_time=300
                    )

    except Exception as e:
        print(f"更新定时调度失败: {e}")


def start_scheduler():
    """启动定时调度器"""
    # 先启动队列工作线程
    start_queue_worker()

    if scheduler and not scheduler.running:
        try:
            scheduler.start()
            update_scheduler()
        except Exception as e:
            print(f"启动定时调度器失败: {e}")


def run_monitor_round(project_id: int):
    """执行一轮监测（在后台线程中运行）"""
    state = get_project_state(project_id)

    if state['is_running']:
        add_log(project_id, "已有任务在运行中")
        return

    # 先获取全局锁，确保同一时间只有一个任务在执行
    if not global_run_lock.acquire(blocking=False):
        add_log(project_id, "其他任务正在执行中，已加入队列稍后执行")
        return

    try:
        state['is_running'] = True
        add_log(project_id, "开始执行监测任务")

        config = load_config()
        config = load_config()
        project_config = get_project_config(project_id)

        if not project_config:
            add_log(project_id, "未找到项目配置")
            state['is_running'] = False
            return

        monitor_dir = get_monitor_data_dir(project_id)
        tasks = project_config.get('tasks', [])

        if not tasks:
            add_log(project_id, "没有配置监测任务")
            state['is_running'] = False
            return

        date_str = datetime.now().strftime('%Y%m%d')
        hour = datetime.now().hour
        time_str = datetime.now().strftime('%H%M')
        save_dir = monitor_dir / date_str
        save_dir.mkdir(parents=True, exist_ok=True)

        all_questions = [task['question'] for task in tasks]
        add_log(project_id, f"准备向豆包提问 {len(all_questions)} 个问题")

        add_log(project_id, "正在向豆包提问...")
        response_dicts = run_doubao_queries(config, all_questions, on_captcha=on_captcha_callback)
        responses = [r['answer'] for r in response_dicts]
        citations_list = [r['citations'] for r in response_dicts]

        master_json = {
            'hour': hour,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'tasks': tasks,
            'results': [
                {
                    'task_idx': i,
                    'question': task['question'],
                    'brands': task['brands'],
                    'response': resp,
                    'citations': cites
                }
                for i, (task, resp, cites) in enumerate(zip(tasks, responses, citations_list))
            ]
        }
        json_path = save_dir / f'timepoint_{hour:02d}.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(master_json, f, ensure_ascii=False, indent=2)
        add_log(project_id, f"原始数据已保存: timepoint_{hour:02d}.json")

        add_log(project_id, "正在保存各任务文档...")
        for task_idx, (task, resp, citations) in enumerate(zip(tasks, responses, citations_list), 1):
            primary_brand = task['brands'][0]

            safe_q = ''.join(c for c in task['question'] if c not in r'\/:*?"<>|')[:30]
            task_folder_name = f'任务{task_idx}_{safe_q}'
            task_dir = save_dir / task_folder_name
            task_dir.mkdir(parents=True, exist_ok=True)

            answer_file = task_dir / f'{time_str}_豆包回答.md'
            with open(answer_file, 'w', encoding='utf-8') as f:
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

            try:
                task_id = models.insert_monitor_task(
                    project_id, date_str, hour, master_json['timestamp'],
                    primary_brand, task['question'], task_idx - 1
                )
                qid = models.insert_questions(task_id, [task['question']], [resp])[0]

                # 保存豆包引用的链接（直接用提取好的）
                saved_cite_ids = models.save_doubao_citations(project_id, qid, date_str, citations)
                if saved_cite_ids:
                    add_log(project_id, f"    已保存 {len(saved_cite_ids)} 条参考资料链接")

                mention_info = importer.extract_brand_mentions(resp, primary_brand)
                for brand_variant in task['brands'][1:]:
                    variant_info = importer.extract_brand_mentions(resp, brand_variant)
                    if variant_info['target_mentioned']:
                        mention_info['target_mentioned'] = True
                        if not mention_info['position'] and variant_info['position']:
                            mention_info['position'] = variant_info['position']
                        for b_name, cnt in variant_info['brands_found'].items():
                            if b_name in mention_info['brands_found']:
                                mention_info['brands_found'][b_name] += cnt
                            else:
                                mention_info['brands_found'][b_name] = cnt

                if mention_info['target_mentioned']:
                    models.insert_brand_mention(
                        qid,
                        brand_name=primary_brand,
                        mention_position=mention_info['position'],
                        sentiment=mention_info['sentiment']
                    )
                for b_name in set(mention_info['brands_found'].keys()):
                    if b_name not in task['brands']:
                        models.insert_brand_mention(qid, brand_name=b_name)

            except Exception as e:
                add_log(project_id, f"任务{task_idx}数据库保存失败: {e}")

            add_log(project_id, f"任务{task_idx}已保存")

        add_log(project_id, "正在读取历史数据用于分析...")
        existing_timepoints = []
        for json_file in sorted(save_dir.glob('timepoint_*.json')):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    existing_timepoints.append(json.load(f))
            except Exception as e:
                add_log(project_id, f"读取历史数据{json_file.name}失败: {e}")

        add_log(project_id, "正在生成分析报告...")
        for task_idx, task in enumerate(tasks, 1):
            safe_q = ''.join(c for c in task['question'] if c not in r'\/:*?"<>|')[:30]
            task_folder_name = f'任务{task_idx}_{safe_q}'
            task_dir = save_dir / task_folder_name

            all_results_for_task = []
            for tp_data in existing_timepoints:
                for result in tp_data.get('results', []):
                    if result.get('question') == task['question']:
                        single_result = {
                            'hour': tp_data.get('hour', hour),
                            'timestamp': tp_data.get('timestamp', master_json['timestamp']),
                            'questions': [result.get('question')],
                            'responses': [result.get('response')],
                            'citations': [result.get('citations', [])]
                        }
                        all_results_for_task.append(single_result)

            report = analyze_monitor_results(config, task['question'], task['brands'][0], all_results_for_task)
            report_file = task_dir / '分析报告.md'
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)

            add_log(project_id, f"任务{task_idx}分析报告已生成")

        add_log(project_id, "执行完成！")

    except Exception as e:
        add_log(project_id, f"执行出错: {e}")
        import traceback
        add_log(project_id, traceback.format_exc())
    finally:
        state['is_running'] = False
        global_run_lock.release()  # 释放全局锁


@app.route('/')
def index():
    """仪表盘首页"""
    return render_template('index.html')


# ========== 项目管理API ==========

@app.route('/api/projects', methods=['GET'])
def api_get_projects():
    """获取所有项目"""
    try:
        db_projects = models.get_all_projects()
        config = load_config()

        project_list = []
        for project in config.get('projects', []):
            project_id = project.get('id')
            db_project = next((p for p in db_projects if p['id'] == project_id), None)

            project_list.append({
                'id': project_id,
                'name': project.get('name', ''),
                'description': project.get('description', ''),
                'created_at': db_project.get('created_at') if db_project else None
            })

        return jsonify({
            'success': True,
            'projects': project_list,
            'default_project_id': config.get('global', {}).get('default_project')
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/projects', methods=['POST'])
def api_create_project():
    """创建新项目"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()

        if not name:
            return jsonify({'success': False, 'error': '项目名称不能为空'}), 400

        existing = models.get_project_by_name(name)
        if existing:
            return jsonify({'success': False, 'error': '项目已存在'}), 400

        project_id = models.create_project(name, data.get('description', ''))

        config = load_config()
        config['projects'].append({
            'id': project_id,
            'name': name,
            'description': data.get('description', ''),
            'config': {'tasks': [], 'schedule_hours': []}
        })

        if not config.get('global', {}).get('default_project'):
            config['global'] = config.get('global', {})
            config['global']['default_project'] = project_id

        save_config(config)

        return jsonify({'success': True, 'project_id': project_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/projects/<int:project_id>', methods=['PUT'])
def api_update_project(project_id):
    """更新项目"""
    try:
        data = request.get_json()

        if 'name' in data or 'description' in data:
            models.update_project(project_id, data.get('name'), data.get('description'))

            config = load_config()
            for project in config.get('projects', []):
                if project.get('id') == project_id:
                    if 'name' in data:
                        project['name'] = data['name']
                    if 'description' in data:
                        project['description'] = data['description']
                    break
            save_config(config)

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/projects/<int:project_id>', methods=['DELETE'])
def api_delete_project(project_id):
    """删除项目"""
    try:
        models.delete_project(project_id)

        config = load_config()
        config['projects'] = [p for p in config.get('projects', []) if p.get('id') != project_id]

        if config.get('global', {}).get('default_project') == project_id and config['projects']:
            config['global']['default_project'] = config['projects'][0].get('id')

        save_config(config)

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/projects/<int:project_id>/set_default', methods=['POST'])
def api_set_default_project(project_id):
    """设置默认项目"""
    try:
        config = load_config()
        config['global'] = config.get('global', {})
        config['global']['default_project'] = project_id
        save_config(config)

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== 项目数据API ==========

@app.route('/api/projects/<int:project_id>/summary')
def api_project_summary(project_id):
    """获取项目汇总数据"""
    summaries = models.get_all_summaries(project_id)
    dates = models.get_all_dates(project_id)

    return jsonify({
        'available_dates': dates,
        'summaries': summaries,
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })


@app.route('/api/projects/<int:project_id>/trend')
def api_project_trend(project_id):
    """获取项目趋势数据"""
    stats = models.get_brand_mention_stats(project_id, 30)
    return jsonify({'stats': stats})


@app.route('/api/projects/<int:project_id>/daily/<date_str>')
def api_project_daily(project_id, date_str):
    """获取项目某天的数据"""
    tasks = models.get_tasks_by_date(project_id, date_str)
    summary = models.get_daily_summary(project_id, date_str)

    task_details = []
    for task in tasks:
        questions = models.get_questions_by_task(task['id'])
        task_details.append({
            'task': task,
            'questions': questions
        })

    return jsonify({
        'date': date_str,
        'tasks': task_details,
        'summary': summary
    })


@app.route('/api/projects/<int:project_id>/position/distribution')
def api_project_position_distribution(project_id):
    """获取项目品牌位置分布统计"""
    try:
        primary_brand = models.get_primary_brand(project_id)
        primary_position = models.get_primary_position_data(project_id)

        return jsonify({
            'success': True,
            'primary_brand': primary_brand,
            'primary_position': primary_position
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== 项目文件API ==========

@app.route('/api/projects/<int:project_id>/date/<date_str>/tasks')
def api_project_date_tasks(project_id, date_str):
    """获取项目某天的任务文件夹列表"""
    try:
        monitor_dir = get_monitor_data_dir(project_id)
        date_dir = monitor_dir / date_str

        if not date_dir.exists():
            return jsonify({'success': True, 'tasks': []})

        tasks = []
        for d in sorted(date_dir.iterdir()):
            if d.is_dir() and d.name.startswith('任务'):
                question = d.name
                for f in d.iterdir():
                    if f.name.endswith('_豆包回答.md'):
                        try:
                            with open(f, 'r', encoding='utf-8') as fobj:
                                lines = fobj.readlines()
                                if len(lines) > 0:
                                    question = lines[0].strip()
                                    if question.startswith('#'):
                                        question = question[1:].strip()
                                    break
                        except:
                            pass
                tasks.append({'folder': d.name, 'question': question})

        return jsonify({'success': True, 'tasks': tasks})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/projects/<int:project_id>/date/<date_str>/task/<task_folder>/detail')
def api_project_task_detail(project_id, date_str, task_folder):
    """获取项目某个任务的详情"""
    try:
        monitor_dir = get_monitor_data_dir(project_id)
        date_dir = monitor_dir / date_str

        safe_task_folder = task_folder.replace('/', '_').replace('\\', '_')
        task_dir = date_dir / safe_task_folder

        if not task_dir.exists():
            for d in date_dir.iterdir():
                if d.is_dir() and safe_task_folder in d.name:
                    task_dir = d
                    break

        if not task_dir.exists():
            return jsonify({'success': False, 'error': '任务文件夹不存在'}), 404

        answer_files = []
        for f in sorted(task_dir.iterdir()):
            if f.name == '豆包回答.md' or f.name.endswith('_豆包回答.md'):
                answer_files.append(f.name)

        report_content = ''
        report_file = task_dir / '分析报告.md'
        if report_file.exists():
            with open(report_file, 'r', encoding='utf-8') as f:
                report_content = f.read()

        return jsonify({
            'success': True,
            'task_folder': task_dir.name,
            'answer_files': answer_files,
            'report_content': report_content
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/projects/<int:project_id>/date/<date_str>/task/<task_folder>/answer/<answer_file>')
def api_project_answer_detail(project_id, date_str, task_folder, answer_file):
    """获取项目某个豆包回答文件的内容"""
    try:
        monitor_dir = get_monitor_data_dir(project_id)
        date_dir = monitor_dir / date_str

        safe_task_folder = task_folder.replace('/', '_').replace('\\', '_')
        safe_answer_file = answer_file.replace('/', '_').replace('\\', '_')
        task_dir = date_dir / safe_task_folder

        if not task_dir.exists():
            for d in date_dir.iterdir():
                if d.is_dir() and safe_task_folder in d.name:
                    task_dir = d
                    break

        file_path = task_dir / safe_answer_file
        if not file_path.exists():
            return jsonify({'success': False, 'error': '文件不存在'}), 404

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        return jsonify({'success': True, 'content': content})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/projects/<int:project_id>/date/<date_str>', methods=['DELETE'])
def api_delete_date(project_id, date_str):
    """删除某天的所有数据（文件+数据库）"""
    try:
        import shutil

        # 1. 删除文件
        monitor_dir = get_monitor_data_dir(project_id)
        date_dir = monitor_dir / date_str
        if date_dir.exists():
            shutil.rmtree(date_dir)

        # 2. 删除数据库记录
        conn = models.get_connection()
        cursor = conn.cursor()

        # 找到这天的所有任务
        cursor.execute('SELECT id FROM monitor_tasks WHERE project_id IS ? AND date_str = ?', (project_id, date_str))
        task_ids = [row['id'] for row in cursor.fetchall()]

        for task_id in task_ids:
            # 删除品牌提及
            cursor.execute('DELETE FROM brand_mentions WHERE question_id IN (SELECT id FROM questions WHERE task_id = ?)', (task_id,))
            # 删除问题
            cursor.execute('DELETE FROM questions WHERE task_id = ?', (task_id,))
            # 删除豆包引用链接
            cursor.execute('DELETE FROM doubao_citations WHERE question_id IN (SELECT id FROM questions WHERE task_id = ?)', (task_id,))
            # 删除任务
            cursor.execute('DELETE FROM monitor_tasks WHERE id = ?', (task_id,))

        # 删除每日摘要
        cursor.execute('DELETE FROM daily_summaries WHERE project_id IS ? AND date_str = ?', (project_id, date_str))

        conn.commit()
        conn.close()

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/projects/<int:project_id>/date/<date_str>/task/<task_folder>', methods=['DELETE'])
def api_delete_task(project_id, date_str, task_folder):
    """删除某个任务（文件+数据库）"""
    try:
        import shutil

        # 1. 删除文件
        monitor_dir = get_monitor_data_dir(project_id)
        date_dir = monitor_dir / date_str
        safe_task_folder = task_folder.replace('/', '_').replace('\\', '_')
        task_dir = date_dir / safe_task_folder

        # 尝试匹配文件夹
        if not task_dir.exists() and date_dir.exists():
            for d in date_dir.iterdir():
                if d.is_dir() and safe_task_folder in d.name:
                    task_dir = d
                    break

        if task_dir.exists():
            shutil.rmtree(task_dir)

        # 2. 删除数据库记录
        conn = models.get_connection()
        cursor = conn.cursor()

        # 找到匹配的任务（匹配文件夹名）
        cursor.execute('SELECT id FROM monitor_tasks WHERE project_id IS ? AND date_str = ?', (project_id, date_str))
        tasks = cursor.fetchall()

        for task in tasks:
            # 找到这个任务的问题
            cursor.execute('SELECT id FROM questions WHERE task_id = ?', (task['id'],))
            question_ids = [row['id'] for row in cursor.fetchall()]

            for qid in question_ids:
                # 删除品牌提及
                cursor.execute('DELETE FROM brand_mentions WHERE question_id = ?', (qid,))
                # 删除豆包引用链接
                cursor.execute('DELETE FROM doubao_citations WHERE question_id = ?', (qid,))

            # 删除问题
            cursor.execute('DELETE FROM questions WHERE task_id = ?', (task['id'],))
            # 删除任务
            cursor.execute('DELETE FROM monitor_tasks WHERE id = ?', (task['id'],))

        conn.commit()
        conn.close()

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== 项目配置API ==========

@app.route('/api/projects/<int:project_id>/config/tasks', methods=['GET'])
def api_get_project_tasks(project_id):
    """获取项目任务列表"""
    try:
        config = get_project_config(project_id)
        project_name = next(
            (p.get('name') for p in load_config().get('projects', []) if p.get('id') == project_id),
            ''
        )
        tasks = config.get('tasks', []) if config else []
        return jsonify({'success': True, 'tasks': tasks, 'project_name': project_name})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/projects/<int:project_id>/config/tasks', methods=['POST'])
def api_save_project_tasks(project_id):
    """保存项目任务列表"""
    try:
        data = request.get_json()
        tasks = data.get('tasks', [])

        config = get_project_config(project_id) or {}
        config['tasks'] = tasks
        save_project_config(project_id, config)

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/projects/<int:project_id>/config/schedule', methods=['GET'])
def api_get_project_schedule(project_id):
    """获取项目定时设置"""
    try:
        config = get_project_config(project_id)
        schedule_hours = config.get('schedule_hours', []) if config else []
        return jsonify({'success': True, 'schedule_hours': schedule_hours})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/projects/<int:project_id>/config/schedule', methods=['POST'])
def api_save_project_schedule(project_id):
    """保存项目定时设置"""
    try:
        data = request.get_json()
        schedule_hours = data.get('schedule_hours', [])

        config = get_project_config(project_id) or {}
        config['schedule_hours'] = schedule_hours
        save_project_config(project_id, config)

        update_scheduler()

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== 项目运行控制API ==========

@app.route('/api/projects/<int:project_id>/run/status', methods=['GET'])
def api_project_run_status(project_id):
    """获取项目运行状态"""
    state = get_project_state(project_id)
    with log_lock:
        return jsonify({
            'is_running': state['is_running'],
            'logs': state['run_logs'].copy()
        })


@app.route('/api/projects/<int:project_id>/run/start', methods=['POST'])
def api_project_run_start(project_id):
    """开始执行项目监测（加入队列）"""
    state = get_project_state(project_id)

    if state['is_running']:
        return jsonify({'success': False, 'error': '已有任务在运行中'})

    # 获取项目名称
    config = load_config()
    project_name = next(
        (p.get('name') for p in config.get('projects', []) if p.get('id') == project_id),
        f'项目{project_id}'
    )

    # 加入队列
    success, message = enqueue_task(project_id, project_name)

    if success:
        with log_lock:
            state['run_logs'].clear()
        add_log(project_id, message)
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'error': message})


# ========== 调度器状态API ==========

@app.route('/api/scheduler/status', methods=['GET'])
def api_scheduler_status():
    """获取调度器状态"""
    try:
        if not HAS_SCHEDULER:
            return jsonify({
                'success': True,
                'available': False,
                'message': 'APScheduler 未安装'
            })

        jobs = []
        if scheduler:
            for job in scheduler.get_jobs():
                jobs.append({
                    'id': job.id,
                    'name': job.name,
                    'next_run_time': job.next_run_time.strftime('%Y-%m-%d %H:%M:%S') if job.next_run_time else None
                })

        return jsonify({
            'success': True,
            'available': True,
            'running': scheduler.running if scheduler else False,
            'jobs': jobs
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== 队列状态API ==========

@app.route('/api/queue/status', methods=['GET'])
def api_queue_status():
    """获取队列状态"""
    try:
        queue_size = task_queue.qsize()

        # 获取队列中的任务
        queued_tasks = []
        # 注意：queue.Queue 不支持直接遍历，我们通过估算获取
        temp_queue = []
        while not task_queue.empty() and len(temp_queue) < MAX_QUEUE_SIZE:
            try:
                task = task_queue.get_nowait()
                queued_tasks.append({
                    'project_id': task['project_id'],
                    'project_name': task['project_name'],
                    'enqueue_time': task.get('enqueue_time')
                })
                temp_queue.append(task)
            except queue.Empty:
                break
        # 把任务放回队列
        for task in temp_queue:
            try:
                task_queue.put_nowait(task)
            except queue.Full:
                break

        # 当前执行中的任务
        with queue_lock:
            current_task = current_running_task.copy() if current_running_task else None

        # 队列历史
        with queue_history_lock:
            history = queue_history.copy()

        return jsonify({
            'success': True,
            'max_size': MAX_QUEUE_SIZE,
            'current_size': queue_size,
            'queued_tasks': queued_tasks,
            'current_task': current_task,
            'history': history
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== 全局设置API ==========

@app.route('/api/global-settings', methods=['GET'])
def api_get_global_settings():
    """获取全局设置"""
    try:
        config = load_config()
        doubao_config = config.get('doubao', {})
        llm_config = config.get('llm_api', {})

        return jsonify({
            'success': True,
            'settings': {
                'browser': doubao_config.get('browser', 'Chrome'),
                'chrome_profile': doubao_config.get('chrome_profile', ''),
                'model': llm_config.get('model', ''),
                'base_url': llm_config.get('base_url', ''),
                'api_key': llm_config.get('api_key', '')
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/global-settings', methods=['POST'])
def api_save_global_settings():
    """保存全局设置"""
    try:
        data = request.get_json()

        config = load_config()

        # 更新浏览器设置
        config.setdefault('doubao', {})
        config['doubao']['browser'] = data.get('browser', 'Chrome')
        config['doubao']['chrome_profile'] = data.get('chrome_profile', '')

        # 更新LLM设置
        config.setdefault('llm_api', {})
        config['llm_api']['model'] = data.get('model', '')
        config['llm_api']['base_url'] = data.get('base_url', '')
        config['llm_api']['api_key'] = data.get('api_key', '')

        # 自动判断provider
        base_url = data.get('base_url', '')
        if 'ark.cn-beijing.volces.com' in base_url or 'maas.aliyuncs.com' in base_url:
            config['llm_api']['provider'] = 'qwen'
        elif 'api.anthropic.com' in base_url:
            config['llm_api']['provider'] = 'claude'
        elif 'api.openai.com' in base_url:
            config['llm_api']['provider'] = 'openai'
        else:
            config['llm_api']['provider'] = 'openai'

        save_config(config)

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/detect-profile', methods=['POST'])
def api_detect_profile():
    """自动检测浏览器Profile"""
    try:
        data = request.get_json()
        browser_type = data.get('browser', 'Chrome')

        # 调用doubao_query中的检测函数
        profile = _find_default_profile(browser_type)

        if profile:
            return jsonify({
                'success': True,
                'profile': profile,
                'browser': browser_type
            })
        else:
            # 尝试另一个浏览器
            fallback = 'Edge' if browser_type == 'Chrome' else 'Chrome'
            profile2 = _find_default_profile(fallback)
            if profile2:
                return jsonify({
                    'success': True,
                    'profile': profile2,
                    'browser': fallback
                })
            else:
                return jsonify({
                    'success': False,
                    'error': '未检测到浏览器Profile，请手动输入'
                }), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== 暂停/继续和CAPTCHA API ==========

@app.route('/api/captcha/status', methods=['GET'])
def api_captcha_status():
    """获取CAPTCHA状态"""
    with captcha_lock:
        pending = captcha_pending
    return jsonify({
        'success': True,
        'pending': pending,
        'is_paused': get_pause_flag()
    })


@app.route('/api/captcha/continue', methods=['POST'])
def api_captcha_continue():
    """继续执行（CAPTCHA已完成）"""
    global captcha_pending
    with captcha_lock:
        captcha_pending = False
    set_pause_flag(False)
    return jsonify({'success': True, 'message': '任务已继续'})


@app.route('/api/pause', methods=['POST'])
def api_pause():
    """暂停当前任务"""
    set_pause_flag(True)
    return jsonify({'success': True})


@app.route('/api/continue', methods=['POST'])
def api_continue():
    """继续当前任务"""
    global captcha_pending
    with captcha_lock:
        captcha_pending = False
    set_pause_flag(False)
    return jsonify({'success': True})


# ============================================================================
# GEO 优化 API
# ============================================================================

@app.route('/api/geo/keywords', methods=['GET'])
def api_geo_get_keywords():
    """获取关键词库（支持分页）"""
    from src.geo import KeywordManager
    project_id = request.args.get('project_id', type=int)
    tier = request.args.get('tier')
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 5, type=int)
    km = KeywordManager()
    # 获取所有关键词
    all_keywords = km.get_keywords(project_id, tier=tier)
    # 分页
    total = len(all_keywords)
    start = (page - 1) * page_size
    end = start + page_size
    keywords = all_keywords[start:end]
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    stats = km.get_tier_stats(project_id)
    return jsonify({
        'success': True,
        'keywords': keywords,
        'stats': stats,
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total': total,
            'total_pages': total_pages
        }
    })


@app.route('/api/geo/keywords', methods=['POST'])
def api_geo_add_keyword():
    """添加关键词"""
    from src.geo import KeywordManager
    data = request.json
    km = KeywordManager()
    kw_id = km.add_keyword(
        data.get('project_id'),
        data.get('keyword'),
        data.get('tier'),
        data.get('difficulty', 50),
        data.get('is_target', False),
        data.get('notes')
    )
    return jsonify({'success': True, 'id': kw_id})


@app.route('/api/geo/keywords/batch', methods=['POST'])
def api_geo_batch_keywords():
    """批量添加关键词"""
    from src.geo import KeywordManager
    data = request.json
    km = KeywordManager()
    ids = km.batch_add_keywords(data.get('project_id'), data.get('keywords', []))
    return jsonify({'success': True, 'ids': ids})


@app.route('/api/geo/keywords/generate', methods=['POST'])
def api_geo_generate_keywords():
    """生成关键词建议（模板方式）"""
    from src.geo import KeywordManager
    data = request.json
    km = KeywordManager()
    suggestions = km.generate_suggestions(
        data.get('project_id'),
        data.get('brand_name'),
        data.get('core_product'),
        data.get('competitors', [])
    )
    return jsonify({'success': True, 'suggestions': suggestions})


@app.route('/api/geo/keywords/check-docs', methods=['GET'])
def api_geo_check_docs():
    """检查项目是否有文档"""
    from src.geo import KeywordManager
    project_id = request.args.get('project_id', type=int)
    km = KeywordManager()
    has_docs = km.has_documents(project_id)
    return jsonify({'success': True, 'has_documents': has_docs})


@app.route('/api/geo/keywords/generate-from-docs', methods=['POST'])
def api_geo_generate_keywords_from_docs():
    """基于文档库智能挖掘关键词"""
    from src.geo import KeywordManager
    from src.config import load_config
    from src.collector.monitor_analysis import _call_llm

    data = request.json
    project_id = data.get('project_id')

    km = KeywordManager()

    # 检查是否有文档
    if not km.has_documents(project_id):
        return jsonify({'success': False, 'error': '文档库为空，请先上传文档'}), 400

    # 加载配置
    config = load_config()

    # 智能挖掘
    suggestions = km.generate_suggestions_from_docs(
        project_id,
        _call_llm,
        config
    )

    return jsonify({'success': True, 'suggestions': suggestions})


@app.route('/api/geo/keywords/<int:kw_id>', methods=['PUT'])
def api_geo_update_keyword(kw_id):
    """更新关键词"""
    from src.geo import KeywordManager
    data = request.json
    km = KeywordManager()
    km.update_keyword(kw_id, **data)
    return jsonify({'success': True})


@app.route('/api/geo/keywords/<int:kw_id>', methods=['DELETE'])
def api_geo_delete_keyword(kw_id):
    """删除关键词"""
    from src.geo import KeywordManager
    km = KeywordManager()
    km.delete_keyword(kw_id)
    return jsonify({'success': True})


@app.route('/api/geo/content/check', methods=['POST'])
def api_geo_check_content():
    """检查内容GEO规范"""
    from src.geo import ContentTemplate
    data = request.json
    content = data.get('content', '')
    passed, issues = ContentTemplate.check_geo_standards(content)
    checklist = ContentTemplate.get_content_template_checklist()
    return jsonify({'success': True, 'passed': passed, 'issues': issues, 'checklist': checklist})


@app.route('/api/geo/content/generate', methods=['POST'])
def api_geo_generate_content():
    """生成内容"""
    from src.geo import ContentTemplate
    from src.geo import DocumentProcessor
    from src.geo import RetrievalEngine
    from src.config import load_config
    from src.collector.monitor_analysis import _call_llm

    data = request.json
    content_type = data.get('type', 'longtail')
    question = data.get('question', '')
    brand_name = data.get('brand_name', '')
    project_id = data.get('project_id')
    # 获取对比品牌列表（仅横向对比文使用）
    competitor_brands = data.get('competitor_brands', [])

    # 1. 检索相关素材
    materials = []
    context_text = ''
    if project_id:
        dp = DocumentProcessor()
        re = RetrievalEngine()
        chunks = dp.get_all_chunks_for_project(project_id)
        if chunks:
            # 获取摘要一起检索
            summaries = dp.get_summaries(project_id)
            # 构建索引并检索
            re.index_chunks(chunks)
            results = re.search(question, top_k=5, summaries=summaries)
            if results:
                materials = [{'source': r.get('source', ''), 'content': r.get('content', '')} for r in results]
                context_text = '\n\n'.join([r.get('content', '') for r in results])

    # 2. 调用LLM生成完整内容
    config = load_config()
    if content_type == 'longtail':
        content = ContentTemplate.longtail_question_template_llm(
            question,
            context_text,
            materials,
            brand_name,
            config,
            _call_llm
        )
    elif content_type == 'comparison':
        content = ContentTemplate.comparison_template_llm(
            question,
            context_text,
            brand_name,
            competitor_brands,  # 新增对比品牌
            config,
            _call_llm
        )
    else:
        content = ContentTemplate.core_deep_template_llm(
            question,
            context_text,
            brand_name,
            config,
            _call_llm
        )

    return jsonify({'success': True, 'content': content})


# ========== 文档管理 API ==========

@app.route('/api/geo/documents', methods=['GET'])
def api_geo_get_documents():
    """获取文档列表"""
    from src.geo import DocumentProcessor
    project_id = request.args.get('project_id', type=int)
    tag = request.args.get('tag')
    dp = DocumentProcessor()
    documents = dp.get_documents(project_id, tag=tag)
    summaries = dp.get_summaries(project_id)
    return jsonify({'success': True, 'documents': documents, 'summaries': summaries})


@app.route('/api/geo/documents', methods=['POST'])
def api_geo_upload_document():
    """上传文档"""
    from src.geo import DocumentProcessor
    from src.config import get_document_storage_dir

    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '没有文件'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'success': False, 'error': '没有选择文件'}), 400

    project_id = request.form.get('project_id', type=int)
    tags = request.form.get('tags', '')

    dp = DocumentProcessor()
    file_type = dp.detect_file_type(file.filename)

    if not file_type:
        return jsonify({'success': False, 'error': '不支持的文件格式'}), 400

    # 保存文件
    storage_dir = get_document_storage_dir(project_id)
    import time
    safe_filename = f"{int(time.time())}_{file.filename}"
    storage_path = storage_dir / safe_filename

    file.save(str(storage_path))
    file_size = storage_path.stat().st_size

    # 保存数据库记录
    doc_id = dp.save_document(
        project_id=project_id,
        original_filename=file.filename,
        storage_path=str(storage_path),
        file_type=file_type,
        file_size=file_size,
        tags=tags
    )

    # 解析文档
    try:
        content, word_count = dp.parse_document(str(storage_path), file_type)
        dp.update_document_parsed(doc_id, content, word_count)

        # 切分片段
        chunks = dp.split_into_chunks(content)
        dp.save_chunks(doc_id, chunks)

        return jsonify({'success': True, 'id': doc_id, 'word_count': word_count, 'chunks': len(chunks)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/geo/documents/<int:doc_id>', methods=['GET'])
def api_geo_get_document(doc_id):
    """获取单个文档详情"""
    from src.geo import DocumentProcessor
    dp = DocumentProcessor()
    doc = dp.get_document(doc_id)
    if not doc:
        return jsonify({'success': False, 'error': '文档不存在'}), 404

    chunks = dp.get_document_chunks(doc_id)

    # 优先用数据库里已经解析好的片段拼接
    full_content = None
    if chunks and len(chunks) > 0:
        full_content = '\n'.join([chunk['content'] for chunk in chunks])
    else:
        # 如果没有片段，尝试读取原始文件
        try:
            from pathlib import Path
            path = Path(doc['storage_path'])
            if path.exists():
                if doc['file_type'] in ['text', 'markdown']:
                    try:
                        full_content = path.read_text(encoding='utf-8')
                    except UnicodeDecodeError:
                        full_content = path.read_text(encoding='gbk', errors='ignore')
                elif doc['file_type'] in ['word', 'pdf', 'powerpoint']:
                    # 对于Word/PDF/PPT，用parse_document重新解析
                    try:
                        content, _ = dp.parse_document(str(path), doc['file_type'])
                        full_content = content
                    except Exception:
                        pass
        except Exception:
            pass

    return jsonify({'success': True, 'document': doc, 'chunks': chunks, 'full_content': full_content})


@app.route('/api/geo/documents/<int:doc_id>/generate-summary', methods=['POST'])
def api_geo_generate_doc_summary(doc_id):
    """为文档自动生成摘要"""
    from src.geo import DocumentProcessor
    from src.config import load_config
    from src.collector.monitor_analysis import _call_llm

    dp = DocumentProcessor()
    doc = dp.get_document(doc_id)
    if not doc:
        return jsonify({'success': False, 'error': '文档不存在'}), 404

    # 获取文档内容
    chunks = dp.get_document_chunks(doc_id)
    full_content = None
    if chunks and len(chunks) > 0:
        full_content = '\n'.join([chunk['content'] for chunk in chunks])
    else:
        try:
            from pathlib import Path
            path = Path(doc['storage_path'])
            if path.exists():
                if doc['file_type'] in ['text', 'markdown']:
                    try:
                        full_content = path.read_text(encoding='utf-8')
                    except UnicodeDecodeError:
                        full_content = path.read_text(encoding='gbk', errors='ignore')
                elif doc['file_type'] in ['word', 'pdf', 'powerpoint']:
                    try:
                        content, _ = dp.parse_document(str(path), doc['file_type'])
                        full_content = content
                    except Exception:
                        pass
        except Exception:
            pass

    if not full_content or not full_content.strip():
        return jsonify({'success': False, 'error': '文档内容为空，无法生成摘要'}), 400

    # 截取前3000字避免太长
    if len(full_content) > 3000:
        full_content = full_content[:3000] + '...（内容太长，已截取）'

    # 调用LLM生成摘要
    config = load_config()
    prompt = f"""请阅读以下文档内容，提取关键信息生成摘要。

文档名称：{doc['original_filename']}
文档内容：
{full_content}

请生成该文档的摘要，要求：
1. 标题要简明扼要，概括文档主题
2. 内容要提取核心要点，突出关键信息
3. 用中文输出
4. 格式如下：
标题：[简短标题]
摘要：[核心要点摘要，200-500字]

直接输出结果，不要其他解释。"""

    try:
        result = _call_llm(config, prompt)
        # 解析返回结果
        title = doc['original_filename']
        summary = result
        if '标题：' in result and '摘要：' in result:
            parts = result.split('摘要：', 1)
            title_part = parts[0].replace('标题：', '').strip()
            if title_part:
                title = title_part
            summary = parts[1].strip()
        return jsonify({'success': True, 'title': title, 'content': summary})
    except Exception as e:
        return jsonify({'success': False, 'error': f'生成摘要失败：{str(e)}'}), 500


@app.route('/api/geo/documents/<int:doc_id>', methods=['DELETE'])
def api_geo_delete_document(doc_id):
    """删除文档"""
    from src.geo import DocumentProcessor
    dp = DocumentProcessor()
    doc = dp.get_document(doc_id)

    if not doc:
        return jsonify({'success': False, 'error': '文档不存在'}), 404

    # 删除文件
    try:
        from pathlib import Path
        path = Path(doc['storage_path'])
        if path.exists():
            path.unlink()
    except Exception:
        pass

    dp.delete_document(doc_id)
    return jsonify({'success': True})


@app.route('/api/geo/summaries', methods=['POST'])
def api_geo_create_summary():
    """创建摘要"""
    from src.geo import DocumentProcessor
    data = request.json
    dp = DocumentProcessor()
    summary_id = dp.save_summary(
        project_id=data.get('project_id'),
        summary_level=data.get('level', 'document'),
        target_id=data.get('target_id'),
        title=data.get('title', ''),
        content=data.get('content', ''),
        is_manual_edit=data.get('is_manual', False)
    )
    return jsonify({'success': True, 'id': summary_id})


@app.route('/api/geo/summaries/<int:summary_id>', methods=['PUT'])
def api_geo_update_summary(summary_id):
    """更新摘要"""
    from src.geo import DocumentProcessor
    data = request.json
    dp = DocumentProcessor()
    dp.update_summary(summary_id, data.get('content', ''), data.get('is_manual', False))
    return jsonify({'success': True})


@app.route('/api/geo/summaries/<int:summary_id>', methods=['DELETE'])
def api_geo_delete_summary(summary_id):
    """删除摘要"""
    from src.geo import DocumentProcessor
    dp = DocumentProcessor()
    dp.delete_summary(summary_id)
    return jsonify({'success': True})


@app.route('/api/geo/retrieve', methods=['POST'])
def api_geo_retrieve():
    """检索相关素材"""
    from src.geo import DocumentProcessor, RetrievalEngine, build_context_for_generation
    data = request.json
    query = data.get('query', '')
    project_id = data.get('project_id', type=int)

    dp = DocumentProcessor()

    # 获取文档库的摘要和片段
    summaries = dp.get_summaries(project_id)
    chunks = dp.get_all_chunks_for_project(project_id)

    # 检索
    engine = RetrievalEngine()
    engine.index_chunks(chunks)
    results = engine.search(query, top_k=8, summaries=summaries)

    # 构建上下文
    context = build_context_for_generation(results)

    return jsonify({'success': True, 'results': results, 'context': context})


@app.route('/api/geo/hits', methods=['GET'])
def api_geo_get_hits():
    """获取命中记录"""
    from src.geo import HitTracker
    project_id = request.args.get('project_id', type=int)
    days = request.args.get('days', 30, type=int)
    ht = HitTracker()
    records = ht.get_hit_records(project_id, days=days)
    hit_rate = ht.get_hit_rate(project_id, days=days)
    tier_rates = ht.get_tier_hit_rates(project_id, days=days)
    position_dist = ht.get_position_distribution(project_id, days=days)
    return jsonify({
        'success': True,
        'records': records,
        'hit_rate': hit_rate,
        'tier_rates': tier_rates,
        'position_dist': position_dist
    })


@app.route('/api/geo/hits', methods=['POST'])
def api_geo_add_hit():
    """记录命中"""
    from src.geo import HitTracker
    data = request.json
    ht = HitTracker()
    record_id = ht.record_hit(
        data.get('project_id'),
        data.get('keyword_id'),
        data.get('keyword'),
        data.get('is_hit', False),
        data.get('position'),
        data.get('mention_count', 0),
        data.get('cited_sources'),
        data.get('response_snippet')
    )
    return jsonify({'success': True, 'id': record_id})


@app.route('/api/geo/plan', methods=['GET'])
def api_geo_get_plan():
    """获取执行计划"""
    from src.geo import PlanManager
    project_id = request.args.get('project_id', type=int)
    pm = PlanManager()
    plan = pm.get_plan(project_id)
    progress = pm.get_progress_summary(project_id)
    return jsonify({'success': True, 'plan': plan, 'progress': progress})


@app.route('/api/geo/plan', methods=['POST'])
def api_geo_create_plan():
    """创建8周计划"""
    from src.geo import PlanManager
    data = request.json
    pm = PlanManager()
    ids = pm.create_8week_plan(data.get('project_id'), data.get('start_date'))
    return jsonify({'success': True, 'ids': ids})


@app.route('/api/geo/plan/<int:plan_id>', methods=['PUT'])
def api_geo_update_plan(plan_id):
    """更新计划项"""
    from src.geo import PlanManager
    data = request.json
    pm = PlanManager()
    pm.update_plan_item(plan_id, **data)
    return jsonify({'success': True})


@app.route('/api/geo/competitors', methods=['GET'])
def api_geo_get_competitors():
    """获取竞品列表"""
    from src.geo import CompetitorAnalyzer
    project_id = request.args.get('project_id', type=int)
    ca = CompetitorAnalyzer()
    competitors = ca.get_competitors(project_id)
    citations = ca.get_competitor_citations(project_id)
    gap = ca.get_gap_analysis(project_id)
    return jsonify({'success': True, 'competitors': competitors, 'citations': citations, 'gap': gap})


@app.route('/api/geo/competitors', methods=['POST'])
def api_geo_add_competitor():
    """添加竞品"""
    from src.geo import CompetitorAnalyzer
    data = request.json
    ca = CompetitorAnalyzer()
    comp_id = ca.add_competitor(
        data.get('project_id'),
        data.get('name'),
        data.get('url'),
        data.get('notes')
    )
    return jsonify({'success': True, 'id': comp_id})


@app.route('/api/geo/competitors/<int:comp_id>', methods=['DELETE'])
def api_geo_delete_competitor(comp_id):
    """删除竞品"""
    from src.geo import CompetitorAnalyzer
    ca = CompetitorAnalyzer()
    ca.delete_competitor(comp_id)
    return jsonify({'success': True})


@app.route('/geo/competitors/<int:comp_id>/citations', methods=['POST'])
def api_geo_add_citation(comp_id):
    """添加竞品引用记录"""
    from src.geo import CompetitorAnalyzer
    data = request.json
    ca = CompetitorAnalyzer()
    cit_id = ca.add_citation(
        data.get('project_id'),
        comp_id,
        data.get('keyword'),
        data.get('cited_content'),
        data.get('content_structure'),
        data.get('source_url')
    )
    return jsonify({'success': True, 'id': cit_id})


# =============================================================================
# 新增：GEO质量评分和竞品内容分析API
# =============================================================================

@app.route('/api/geo/content/score', methods=['POST'])
def api_geo_content_score():
    """对GEO内容进行质量评分"""
    data = request.json
    content = data.get('content', '')
    brand_name = data.get('brand_name')

    from src.geo.geo_quality_scorer import score_geo_content

    try:
        result = score_geo_content(content, brand_name)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/geo/citations/analyze', methods=['POST'])
def api_geo_citations_analyze():
    """分析豆包引用的内容"""
    data = request.json
    citations = data.get('citations', [])
    use_llm = data.get('use_llm', True)

    from src.geo.competitor_analyzer import CitationContentAnalyzer

    try:
        if use_llm:
            # 如果需要LLM分析，创建LLM函数
            config = load_config()

            def llm_func(cfg, prompt):
                from src.collector.monitor_analysis import _call_llm
                return _call_llm(cfg, prompt)

            # 注意：实际的内容抓取需要浏览器，这里先做简单分析
            # 完整的抓取需要结合doubao_query的逻辑
            analysis_result = CitationContentAnalyzer.analyze_citation_patterns(
                [], llm_func, config
            )
        else:
            # 不使用LLM，简单分析
            analysis_result = CitationContentAnalyzer.analyze_citation_patterns([])

        html_report = CitationContentAnalyzer.generate_html_report(
            analysis_result, citations
        )

        return jsonify({
            'success': True,
            'result': analysis_result,
            'html_report': html_report
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/geo/citations/import', methods=['POST'])
def api_geo_citation_import():
    """导入引用链接内容到文档库"""
    data = request.json
    url = data.get('url', '')
    title = data.get('title', '')
    project_id = data.get('project_id')

    if not url:
        return jsonify({'success': False, 'error': 'URL不能为空'})

    from src.geo import DocumentProcessor

    try:
        # 先用简单方式抓取
        content, extracted_title = simple_fetch_url(url)

        if not content or len(content.strip()) < 50:
            return jsonify({'success': False, 'error': '抓取内容太少，请稍后再试'})

        # 保存到文档库
        dp = DocumentProcessor()
        doc_id = dp.save_document(
            project_id=project_id,
            original_filename=title or extracted_title or url[:50],
            storage_path=url,
            file_type='url',
            file_size=len(content),
            tags="豆包引用,竞品资料"
        )

        # 解析文档内容
        dp.update_document_parsed(doc_id, content, len(content))

        # 切分片段
        chunks = dp.split_into_chunks(content)
        dp.save_chunks(doc_id, chunks)

        return jsonify({
            'success': True,
            'doc_id': doc_id,
            'content_preview': content[:200]
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/geo/doubao-citations/<int:project_id>', methods=['GET'])
def api_geo_doubao_citations(project_id):
    """获取豆包引用链接列表（带分页和筛选）"""
    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        import_filter = request.args.get('import_filter', None)

        offset = (page - 1) * page_size
        result = models.get_doubao_citations(
            project_id,
            limit=page_size,
            offset=offset,
            import_filter=import_filter
        )
        return jsonify({'success': True, **result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/geo/doubao-citations/<int:project_id>/<int:citation_id>/import', methods=['POST'])
def api_geo_import_citation(project_id, citation_id):
    """导入引用链接内容到文档库"""
    try:
        from src.geo import DocumentProcessor

        # 获取引用链接
        conn = models.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT url FROM doubao_citations WHERE id = ?', (citation_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return jsonify({'success': False, 'error': '未找到引用链接'})

        url = row['url']

        # 抓取链接内容
        content, title = simple_fetch_url(url)

        if not content or len(content.strip()) < 50:
            return jsonify({'success': False, 'error': '抓取内容太少，请稍后再试'})

        # 保存到文档库
        dp = DocumentProcessor()
        doc_id = dp.save_document(
            project_id=project_id,
            original_filename=title or f"引用_{citation_id}.txt",
            storage_path=url,
            file_type='url',
            file_size=len(content),
            tags='豆包引用,竞品资料'
        )

        # 解析文档内容
        dp.update_document_parsed(doc_id, content, len(content))

        # 切分片段
        chunks = dp.split_into_chunks(content)
        dp.save_chunks(doc_id, chunks)

        # 标记为已导入
        models.mark_citation_imported(citation_id)

        return jsonify({'success': True, 'doc_id': doc_id, 'content_preview': content[:200]})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


def simple_fetch_url(url):
    """简单抓取网页内容"""
    import requests
    from bs4 import BeautifulSoup

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.encoding = response.apparent_encoding

        soup = BeautifulSoup(response.text, 'html.parser')

        # 提取标题
        title = ''
        if soup.title:
            title = soup.title.get_text().strip()

        # 提取正文内容
        # 移除不需要的元素
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            element.decompose()

        # 尝试多种方式提取正文
        content = ''

        # 方式1: 找article或main标签
        main_content = soup.find('article') or soup.find('main') or soup.find('div', class_=lambda x: x and 'content' in x.lower())

        if main_content:
            content = main_content.get_text(separator='\n', strip=True)

        # 方式2: 如果没找到，找所有p标签
        if not content or len(content) < 100:
            paragraphs = soup.find_all('p')
            content = '\n'.join([p.get_text(strip=True) for p in paragraphs])

        # 方式3: 最后兜底
        if not content or len(content) < 100:
            content = soup.get_text(separator='\n', strip=True)

        # 清理多余空行
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        content = '\n'.join(lines)

        return content, title

    except Exception as e:
        print(f"抓取失败: {e}")
        return '', ''


@app.route('/static/<path:path>')
def static_files(path):
    """静态文件服务"""
    static_dir = Path(__file__).parent / 'static'
    return send_from_directory(str(static_dir), path)


def main():
    """启动Web服务"""
    print("=" * 50)
    print("GEO 品牌监测 - Web仪表盘")
    print("=" * 50)
    print(f"访问地址: http://localhost:5000")
    print(f"数据目录: {get_monitor_data_dir(1) if get_default_project_id() else get_monitor_data_dir()}")

    if HAS_SCHEDULER:
        start_scheduler()
    else:
        print("[WARNING] APScheduler 未安装，定时监测功能不可用")

    print("=" * 50)
    print()

    app.run(host='127.0.0.1', port=5000, debug=True, use_reloader=False)

    if scheduler and scheduler.running:
        scheduler.shutdown()
        print("定时调度器已停止")


if __name__ == "__main__":
    main()

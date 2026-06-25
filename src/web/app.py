"""Flask Web Dashboard for GEO Brand Monitor"""

import sys
import threading
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

from src.collector.doubao_query import run_doubao_queries
from src.collector.monitor_analysis import analyze_monitor_results
from src.db import importer

app = Flask(__name__)

# 确保数据库初始化
models.init_db()

# 全局状态
project_states = {}  # 每个项目的独立状态
log_lock = threading.Lock()  # 日志锁

# 定时调度器
scheduler = None
if HAS_SCHEDULER:
    scheduler = BackgroundScheduler()


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
                        run_monitor_round,
                        'cron',
                        args=[project_id],
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

    state['is_running'] = True
    add_log(project_id, "开始执行监测任务")

    try:
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
        response_dicts = run_doubao_queries(config, all_questions)
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
    """开始执行项目监测"""
    state = get_project_state(project_id)

    if state['is_running']:
        return jsonify({'success': False, 'error': '已有任务在运行中'})

    with log_lock:
        state['run_logs'].clear()

    thread = threading.Thread(target=run_monitor_round, args=(project_id,), daemon=True)
    thread.start()
    state['running_thread'] = thread

    return jsonify({'success': True})


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

"""Flask Web Dashboard for GEO Brand Monitor"""

import sys
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, jsonify, send_from_directory

# 添加项目根目录
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config import get_monitor_data_dir
from src.db import models

app = Flask(__name__)

# 确保数据库初始化
models.init_db()


@app.route('/')
def index():
    """仪表盘首页"""
    return render_template('index.html')


@app.route('/api/summary')
def api_summary():
    """获取汇总数据"""
    summaries = models.get_all_summaries()
    dates = models.get_all_dates()

    return jsonify({
        'available_dates': dates,
        'summaries': summaries,
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })


@app.route('/api/trend')
def api_trend():
    """获取趋势数据"""
    stats = models.get_brand_mention_stats(30)
    return jsonify({
        'stats': stats
    })


@app.route('/api/daily/<date_str>')
def api_daily(date_str):
    """获取某天的数据"""
    tasks = models.get_tasks_by_date(date_str)
    summary = models.get_daily_summary(date_str)

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
    print(f"数据目录: {get_monitor_data_dir()}")
    print("=" * 50)
    print()

    app.run(host='127.0.0.1', port=5000, debug=True)


if __name__ == "__main__":
    main()

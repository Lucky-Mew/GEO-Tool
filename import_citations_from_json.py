#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从JSON文件中导入已有的citations到数据库"""

import sys
import json
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.config import get_monitor_data_dir
from src.db import models

# 先找当前项目ID（这里简单处理，假设用项目1）
PROJECT_ID = None

# 查找最新的JSON
monitor_dir = get_monitor_data_dir(1)  # 先试试项目1
if not monitor_dir or not monitor_dir.exists():
    # 试试找默认路径
    monitor_dir = project_root / "data" / "monitor"

if not monitor_dir.exists():
    print(f"找不到监测数据目录: {monitor_dir}")
    sys.exit(1)

print(f"检查监测数据目录: {monitor_dir}")

# 找最新的JSON文件
json_files = sorted(monitor_dir.rglob("timepoint_*.json"), reverse=True)
if not json_files:
    print("找不到timepoint_*.json文件")
    sys.exit(1)

print(f"找到 {len(json_files)} 个时间点文件")

# 先检查数据库里有没有doubao_citations表
conn = models.get_connection()
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='doubao_citations'")
has_table = cursor.fetchone()
conn.close()

if not has_table:
    print("doubao_citations表不存在，先运行一次程序初始化数据库")
    sys.exit(1)

# 导入每个JSON
for json_path in json_files[:3]:  # 最近3个时间点
    print(f"\n处理: {json_path}")

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"读取失败: {e}")
        continue

    date_str = json_path.parent.name
    if not date_str.isdigit() or len(date_str) != 8:
        # 尝试从时间戳推断
        from datetime import datetime
        date_str = data.get('timestamp', '')[:10].replace('-', '')
        if not date_str:
            date_str = '20250101'

    hour = data.get('hour', 0)

    results = data.get('results', [])
    if not results:
        continue

    print(f"  包含 {len(results)} 个任务")

    # 查找对应的question_id
    for result in results:
        question = result.get('question', '')
        citations = result.get('citations', [])
        if not citations:
            continue

        print(f"  问题: {question[:40]}... 有 {len(citations)} 条引用")

        # 找对应的question_id
        conn = models.get_connection()
        cursor = conn.cursor()

        # 先找monitor_task
        cursor.execute('''
            SELECT id FROM monitor_tasks
            WHERE project_id IS ? AND date_str = ? AND question LIKE ?
            ORDER BY id DESC LIMIT 1
        ''', (PROJECT_ID, date_str, f"%{question[:30]}%"))
        task_row = cursor.fetchone()

        if task_row:
            task_id = task_row['id']
            cursor.execute('SELECT id FROM questions WHERE task_id = ?', (task_id,))
            question_rows = cursor.fetchall()
            if question_rows:
                qid = question_rows[0]['id']
                saved_ids = models.save_doubao_citations(PROJECT_ID, qid, date_str, citations)
                if saved_ids:
                    print(f"    ✓ 已导入 {len(saved_ids)} 条引用")
                else:
                    print(f"    - 已存在或无引用")

        conn.close()

print("\n完成！")

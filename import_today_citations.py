#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""导入今天的 citations"""

import sys
import json
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.config import get_db_path
from src.db import models
import sqlite3

# 读取今天的 JSON
json_path = project_root / "data" / "monitor" / "project_1" / "20260717" / "timepoint_15.json"

if not json_path.exists():
    print(f"找不到文件: {json_path}")
    sys.exit(1)

with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

results = data.get('results', [])
print(f"找到 {len(results)} 个结果")

# 先找今天的 question_id
conn = sqlite3.connect(get_db_path())
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute('''
    SELECT q.id, q.question_text, m.date_str
    FROM questions q
    JOIN monitor_tasks m ON q.task_id = m.id
    WHERE m.date_str = '20260717'
    ORDER BY q.id DESC
''')
questions = cursor.fetchall()

print(f"\n今天的问题:")
for q in questions:
    print(f"  {q['id']}: {q['question_text']}")

conn.close()

# 导入 citations
project_id = 1
date_str = "20260717"

for result in results:
    question = result['question']
    citations = result.get('citations', [])
    print(f"\n问题: {question}")
    print(f"  {len(citations)} 条 citations")

    # 找对应的 question_id
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('''
        SELECT q.id
        FROM questions q
        JOIN monitor_tasks m ON q.task_id = m.id
        WHERE m.date_str = '20260717' AND q.question_text = ?
        ORDER BY q.id DESC
        LIMIT 1
    ''', (question,))
    row = cursor.fetchone()
    conn.close()

    if row:
        qid = row['id']
        print(f"  找到 question_id: {qid}")
        saved_ids = models.save_doubao_citations(project_id, qid, date_str, citations)
        print(f"  保存了 {len(saved_ids)} 条")
    else:
        print(f"  没找到 question_id")

print("\n完成！")

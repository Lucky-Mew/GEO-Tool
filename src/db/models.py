"""数据库模型"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from src.config import get_db_path


def init_db():
    """初始化数据库表"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 监测任务表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS monitor_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_str TEXT NOT NULL,
            hour INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            brand TEXT NOT NULL,
            question TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date_str, hour)
        )
    ''')

    # 问题表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            question_index INTEGER NOT NULL,
            question_text TEXT NOT NULL,
            response_text TEXT,
            FOREIGN KEY (task_id) REFERENCES monitor_tasks (id)
        )
    ''')

    # 品牌提及表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS brand_mentions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER NOT NULL,
            brand_name TEXT NOT NULL,
            mention_position TEXT,
            sentiment TEXT,
            context_snippet TEXT,
            FOREIGN KEY (question_id) REFERENCES questions (id)
        )
    ''')

    # 摘要表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_str TEXT NOT NULL UNIQUE,
            total_questions INTEGER DEFAULT 0,
            brand_mentioned_count INTEGER DEFAULT 0,
            mention_rate REAL DEFAULT 0,
            summary_data TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()


def get_connection():
    """获取数据库连接"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def insert_monitor_task(date_str: str, hour: int, timestamp: str, brand: str, question: str) -> int:
    """插入监测任务，返回 task_id"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT OR REPLACE INTO monitor_tasks (date_str, hour, timestamp, brand, question)
            VALUES (?, ?, ?, ?, ?)
        ''', (date_str, hour, timestamp, brand, question))

        task_id = cursor.lastrowid
        conn.commit()
        return task_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def insert_questions(task_id: int, questions: List[str], responses: List[str]) -> List[int]:
    """插入问题和回复，返回 question_id 列表"""
    conn = get_connection()
    cursor = conn.cursor()
    question_ids = []

    try:
        for idx, (q, r) in enumerate(zip(questions, responses)):
            cursor.execute('''
                INSERT INTO questions (task_id, question_index, question_text, response_text)
                VALUES (?, ?, ?, ?)
            ''', (task_id, idx, q, r))
            question_ids.append(cursor.lastrowid)

        conn.commit()
        return question_ids
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def insert_brand_mention(question_id: int, brand_name: str, mention_position: Optional[str] = None,
                         sentiment: Optional[str] = None, context_snippet: Optional[str] = None):
    """插入品牌提及"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO brand_mentions (question_id, brand_name, mention_position, sentiment, context_snippet)
            VALUES (?, ?, ?, ?, ?)
        ''', (question_id, brand_name, mention_position, sentiment, context_snippet))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def save_daily_summary(date_str: str, total_questions: int, brand_mentioned_count: int,
                       mention_rate: float, summary_data: Dict[str, Any]):
    """保存每日摘要"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        summary_json = json.dumps(summary_data, ensure_ascii=False)
        cursor.execute('''
            INSERT OR REPLACE INTO daily_summaries (date_str, total_questions, brand_mentioned_count, mention_rate, summary_data, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (date_str, total_questions, brand_mentioned_count, mention_rate, summary_json))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_all_dates() -> List[str]:
    """获取所有有数据的日期"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT DISTINCT date_str FROM monitor_tasks ORDER BY date_str DESC')
        return [row['date_str'] for row in cursor.fetchall()]
    finally:
        conn.close()


def get_tasks_by_date(date_str: str) -> List[Dict]:
    """获取某天的所有任务"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT * FROM monitor_tasks WHERE date_str = ? ORDER BY hour', (date_str,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_questions_by_task(task_id: int) -> List[Dict]:
    """获取某个任务的所有问题"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT * FROM questions WHERE task_id = ? ORDER BY question_index', (task_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_daily_summary(date_str: str) -> Optional[Dict]:
    """获取某天的摘要"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT * FROM daily_summaries WHERE date_str = ?', (date_str,))
        row = cursor.fetchone()
        if row:
            data = dict(row)
            if data['summary_data']:
                data['summary_data'] = json.loads(data['summary_data'])
            return data
        return None
    finally:
        conn.close()


def get_all_summaries() -> List[Dict]:
    """获取所有日期的摘要"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT * FROM daily_summaries ORDER BY date_str DESC')
        rows = cursor.fetchall()
        results = []
        for row in rows:
            data = dict(row)
            if data['summary_data']:
                data['summary_data'] = json.loads(data['summary_data'])
            results.append(data)
        return results
    finally:
        conn.close()


def get_brand_mention_stats(days: int = 30) -> List[Dict]:
    """获取品牌提及统计"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # date_str 格式是 YYYYMMDD，不能用 SQLite date() 函数比较
        # 直接查所有数据，在 Python 端过滤
        cursor.execute('''
            SELECT m.date_str, m.brand,
                   COUNT(DISTINCT m.id) as task_count,
                   COUNT(DISTINCT q.id) as question_count
            FROM monitor_tasks m
            LEFT JOIN questions q ON m.id = q.task_id
            GROUP BY m.date_str
            ORDER BY m.date_str
        ''')
        task_rows = cursor.fetchall()

        results = []
        for row in task_rows:
            r = dict(row)
            date_str = r['date_str']
            brand = r['brand']

            # 单独查询该日期该品牌的提及次数
            cursor.execute('''
                SELECT COUNT(DISTINCT q.id) as mention_count
                FROM questions q
                JOIN monitor_tasks m ON q.task_id = m.id
                JOIN brand_mentions b ON q.id = b.question_id
                WHERE m.date_str = ? AND b.brand_name = ?
            ''', (date_str, brand))
            mention_row = cursor.fetchone()
            r['mention_count'] = dict(mention_row)['mention_count'] if mention_row else 0
            results.append(r)

        # 过滤最近 N 天
        from datetime import datetime, timedelta
        cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
        results = [r for r in results if r['date_str'] >= cutoff]

        return results
    finally:
        conn.close()


# 初始化数据库
init_db()

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

    # 项目表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 监测任务表（添加 project_id）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS monitor_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            date_str TEXT NOT NULL,
            hour INTEGER NOT NULL,
            task_idx INTEGER NOT NULL DEFAULT 0,
            timestamp TEXT NOT NULL,
            brand TEXT NOT NULL,
            question TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id)
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

    # 摘要表（添加 project_id）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            date_str TEXT NOT NULL,
            total_questions INTEGER DEFAULT 0,
            brand_mentioned_count INTEGER DEFAULT 0,
            mention_rate REAL DEFAULT 0,
            summary_data TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id),
            UNIQUE(project_id, date_str)
        )
    ''')

    # ========== GEO优化表 ==========

    # 关键词库表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS geo_keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            keyword TEXT NOT NULL,
            tier TEXT NOT NULL,
            difficulty INTEGER DEFAULT 50,
            status TEXT DEFAULT 'pending',
            is_target INTEGER DEFAULT 0,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id)
        )
    ''')

    # 独有信息素材库表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS geo_materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            source TEXT,
            use_cases TEXT,
            is_verified INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id)
        )
    ''')

    # 内容清单表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS geo_contents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            title TEXT NOT NULL,
            content_type TEXT NOT NULL,
            target_keywords TEXT,
            status TEXT DEFAULT 'idea',
            publish_url TEXT,
            publish_platform TEXT,
            publish_date TEXT,
            word_count INTEGER DEFAULT 0,
            has_table INTEGER DEFAULT 0,
            has_data INTEGER DEFAULT 0,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id)
        )
    ''')

    # 关键词命中记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS geo_hit_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            keyword_id INTEGER,
            keyword TEXT NOT NULL,
            date_str TEXT NOT NULL,
            hour INTEGER,
            is_hit INTEGER DEFAULT 0,
            position TEXT,
            mention_count INTEGER DEFAULT 0,
            cited_sources TEXT,
            response_snippet TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id),
            FOREIGN KEY (keyword_id) REFERENCES geo_keywords (id)
        )
    ''')

    # 竞品分析表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS geo_competitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            name TEXT NOT NULL,
            url TEXT,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id)
        )
    ''')

    # 竞品内容引用表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS geo_competitor_citations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            competitor_id INTEGER,
            keyword TEXT,
            cited_content TEXT,
            content_structure TEXT,
            source_url TEXT,
            date_str TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id),
            FOREIGN KEY (competitor_id) REFERENCES geo_competitors (id)
        )
    ''')

    # 执行计划表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS geo_plan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            week INTEGER NOT NULL,
            phase TEXT NOT NULL,
            description TEXT,
            deliverable TEXT,
            status TEXT DEFAULT 'pending',
            due_date TEXT,
            completed_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id)
        )
    ''')

    # ========== 智能素材库2.0表 ==========

    # 文档表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS geo_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            filename TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_size INTEGER DEFAULT 0,
            category TEXT DEFAULT 'general',
            storage_path TEXT NOT NULL,
            content_preview TEXT,
            word_count INTEGER DEFAULT 0,
            is_parsed INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id)
        )
    ''')

    # 文档分段表（用于向量检索）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS geo_document_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            content_length INTEGER DEFAULT 0,
            vector TEXT,
            is_embedded INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (document_id) REFERENCES geo_documents (id)
        )
    ''')

    # 摘要表（文档级/分类级/全局级）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS geo_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            summary_level TEXT NOT NULL,
            target_id INTEGER,
            title TEXT,
            content TEXT NOT NULL,
            is_manual_edit INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id)
        )
    ''')

    conn.commit()
    conn.close()


def migrate_db():
    """迁移现有数据库到新项目结构"""
    db_path = get_db_path()
    if not db_path.exists():
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA table_info(monitor_tasks)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'project_id' not in columns:
            cursor.execute("ALTER TABLE monitor_tasks ADD COLUMN project_id INTEGER")

        cursor.execute("PRAGMA table_info(daily_summaries)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'project_id' not in columns:
            cursor.execute("ALTER TABLE daily_summaries ADD COLUMN project_id INTEGER")

        conn.commit()
    except Exception as e:
        print(f"Migration error: {e}")
        conn.rollback()
    finally:
        conn.close()


def get_connection():
    """获取数据库连接"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# ========== 项目管理 ==========

def create_project(name: str, description: Optional[str] = None) -> int:
    """创建项目，返回 project_id"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO projects (name, description)
            VALUES (?, ?)
        ''', (name, description))
        project_id = cursor.lastrowid
        conn.commit()
        return project_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_project(project_id: int) -> Optional[Dict]:
    """获取单个项目"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT * FROM projects WHERE id = ?', (project_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_project_by_name(name: str) -> Optional[Dict]:
    """通过名称获取项目"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT * FROM projects WHERE name = ?', (name,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_all_projects() -> List[Dict]:
    """获取所有项目"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT * FROM projects ORDER BY created_at DESC')
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def update_project(project_id: int, name: Optional[str] = None, description: Optional[str] = None):
    """更新项目"""
    conn = get_connection()
    cursor = conn.cursor()

    updates = []
    params = []

    if name is not None:
        updates.append('name = ?')
        params.append(name)
    if description is not None:
        updates.append('description = ?')
        params.append(description)

    if updates:
        updates.append('updated_at = CURRENT_TIMESTAMP')
        params.append(project_id)

        try:
            cursor.execute(f'''
                UPDATE projects
                SET {', '.join(updates)}
                WHERE id = ?
            ''', params)
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()


def delete_project(project_id: int):
    """删除项目（级联删除相关数据）"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('DELETE FROM brand_mentions WHERE question_id IN (SELECT q.id FROM questions q JOIN monitor_tasks m ON q.task_id = m.id WHERE m.project_id = ?)', (project_id,))
        cursor.execute('DELETE FROM questions WHERE task_id IN (SELECT id FROM monitor_tasks WHERE project_id = ?)', (project_id,))
        cursor.execute('DELETE FROM monitor_tasks WHERE project_id = ?', (project_id,))
        cursor.execute('DELETE FROM daily_summaries WHERE project_id = ?', (project_id,))
        cursor.execute('DELETE FROM projects WHERE id = ?', (project_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


# ========== 监测任务（支持 project_id） ==========

def insert_monitor_task(project_id: Optional[int], date_str: str, hour: int, timestamp: str, brand: str, question: str, task_idx: int = 0) -> int:
    """插入监测任务，返回 task_id"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT id FROM monitor_tasks
            WHERE project_id IS ? AND date_str = ? AND hour = ? AND task_idx = ?
        ''', (project_id, date_str, hour, task_idx))
        existing = cursor.fetchone()

        if existing:
            task_id = existing['id']
            cursor.execute('''
                DELETE FROM brand_mentions
                WHERE question_id IN (SELECT id FROM questions WHERE task_id = ?)
            ''', (task_id,))
            cursor.execute('DELETE FROM questions WHERE task_id = ?', (task_id,))
            cursor.execute('''
                UPDATE monitor_tasks
                SET timestamp = ?, brand = ?, question = ?
                WHERE id = ?
            ''', (timestamp, brand, question, task_id))
        else:
            cursor.execute('''
                INSERT INTO monitor_tasks (project_id, date_str, hour, task_idx, timestamp, brand, question)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (project_id, date_str, hour, task_idx, timestamp, brand, question))
            task_id = cursor.lastrowid

        conn.commit()
        return task_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_tasks_by_date(project_id: Optional[int], date_str: str) -> List[Dict]:
    """获取某天的所有任务"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT * FROM monitor_tasks
            WHERE project_id IS ? AND date_str = ?
            ORDER BY hour
        ''', (project_id, date_str))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_all_dates(project_id: Optional[int]) -> List[str]:
    """获取所有有数据的日期"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT DISTINCT date_str FROM monitor_tasks
            WHERE project_id IS ?
            ORDER BY date_str DESC
        ''', (project_id,))
        return [row['date_str'] for row in cursor.fetchall()]
    finally:
        conn.close()


# ========== 问题表 ==========

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


# ========== 品牌提及表 ==========

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


# ========== 摘要表（支持 project_id） ==========

def save_daily_summary(project_id: Optional[int], date_str: str, total_questions: int, brand_mentioned_count: int,
                       mention_rate: float, summary_data: Dict[str, Any]):
    """保存每日摘要"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        summary_json = json.dumps(summary_data, ensure_ascii=False)
        cursor.execute('''
            INSERT OR REPLACE INTO daily_summaries (project_id, date_str, total_questions, brand_mentioned_count, mention_rate, summary_data, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (project_id, date_str, total_questions, brand_mentioned_count, mention_rate, summary_json))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def _parse_summary_data(summary_data):
    """解析摘要 JSON"""
    if not summary_data:
        return {}
    try:
        return json.loads(summary_data)
    except json.JSONDecodeError:
        return {}


def _build_daily_summary(row, summary_data=None):
    """从实时统计行构建每日摘要"""
    data = dict(row)
    total_questions = data.get('total_questions') or 0
    brand_mentioned_count = data.get('brand_mentioned_count') or 0
    data['mention_rate'] = round(brand_mentioned_count / total_questions, 4) if total_questions else 0
    data['summary_data'] = _parse_summary_data(summary_data)
    return data


def get_daily_summary(project_id: Optional[int], date_str: str) -> Optional[Dict]:
    """获取某天的实时摘要"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT m.date_str,
                   MAX(m.brand) as brand,
                   COUNT(DISTINCT m.id) as task_count,
                   COUNT(DISTINCT q.id) as total_questions,
                   COUNT(DISTINCT CASE WHEN b.id IS NOT NULL THEN q.id END) as brand_mentioned_count
            FROM monitor_tasks m
            LEFT JOIN questions q ON m.id = q.task_id
            LEFT JOIN brand_mentions b ON q.id = b.question_id AND b.brand_name = m.brand
            WHERE m.project_id IS ? AND m.date_str = ?
            GROUP BY m.date_str
        ''', (project_id, date_str))
        row = cursor.fetchone()
        if not row:
            return None

        cursor.execute('''
            SELECT summary_data FROM daily_summaries
            WHERE project_id IS ? AND date_str = ?
        ''', (project_id, date_str))
        summary_row = cursor.fetchone()
        summary_data = summary_row['summary_data'] if summary_row else None
        return _build_daily_summary(row, summary_data)
    finally:
        conn.close()


def get_all_summaries(project_id: Optional[int]) -> List[Dict]:
    """获取所有日期的实时摘要"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT m.date_str,
                   MAX(m.brand) as brand,
                   COUNT(DISTINCT m.id) as task_count,
                   COUNT(DISTINCT q.id) as total_questions,
                   COUNT(DISTINCT CASE WHEN b.id IS NOT NULL THEN q.id END) as brand_mentioned_count,
                   ds.summary_data
            FROM monitor_tasks m
            LEFT JOIN questions q ON m.id = q.task_id
            LEFT JOIN brand_mentions b ON q.id = b.question_id AND b.brand_name = m.brand
            LEFT JOIN daily_summaries ds ON m.project_id IS ds.project_id AND m.date_str = ds.date_str
            WHERE m.project_id IS ?
            GROUP BY m.date_str
            ORDER BY m.date_str DESC
        ''', (project_id,))
        return [_build_daily_summary(row, row['summary_data']) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_brand_mention_stats(project_id: Optional[int], days: int = 30) -> List[Dict]:
    """获取品牌提及统计"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
        cursor.execute('''
            SELECT m.date_str,
                   MAX(m.brand) as brand,
                   COUNT(DISTINCT m.id) as task_count,
                   COUNT(DISTINCT q.id) as question_count,
                   COUNT(DISTINCT CASE WHEN b.id IS NOT NULL THEN q.id END) as mention_count
            FROM monitor_tasks m
            LEFT JOIN questions q ON m.id = q.task_id
            LEFT JOIN brand_mentions b ON q.id = b.question_id AND b.brand_name = m.brand
            WHERE m.project_id IS ? AND m.date_str >= ?
            GROUP BY m.date_str
            ORDER BY m.date_str
        ''', (project_id, cutoff))

        results = []
        for row in cursor.fetchall():
            data = dict(row)
            question_count = data.get('question_count') or 0
            mention_count = data.get('mention_count') or 0
            data['mention_rate'] = round(mention_count / question_count, 4) if question_count else 0
            results.append(data)
        return results
    finally:
        conn.close()


def get_position_distribution(project_id: Optional[int], brand_name: Optional[str] = None) -> Dict[str, Dict]:
    """获取品牌位置分布统计"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        position_data = {}

        if brand_name:
            cursor.execute('''
                SELECT b.brand_name, b.mention_position, COUNT(*) as count
                FROM brand_mentions b
                JOIN questions q ON b.question_id = q.id
                JOIN monitor_tasks m ON q.task_id = m.id
                WHERE m.project_id IS ? AND b.brand_name = ? AND b.mention_position IS NOT NULL
                GROUP BY b.brand_name, b.mention_position
                ORDER BY count DESC
            ''', (project_id, brand_name))
        else:
            cursor.execute('''
                SELECT b.brand_name, b.mention_position, COUNT(*) as count
                FROM brand_mentions b
                JOIN questions q ON b.question_id = q.id
                JOIN monitor_tasks m ON q.task_id = m.id
                WHERE m.project_id IS ? AND b.mention_position IS NOT NULL
                GROUP BY b.brand_name, b.mention_position
                ORDER BY count DESC
            ''', (project_id,))

        for row in cursor.fetchall():
            brand = row['brand_name']
            position = row['mention_position']
            count = row['count']

            if brand not in position_data:
                position_data[brand] = {}
            position_data[brand][position] = count

        return position_data
    finally:
        conn.close()


def get_primary_brand(project_id: Optional[int]) -> Optional[str]:
    """获取项目的主要品牌（最新任务的品牌）"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT DISTINCT m.brand
            FROM monitor_tasks m
            WHERE m.project_id IS ?
            ORDER BY m.date_str DESC, m.hour DESC
            LIMIT 1
        ''', (project_id,))
        row = cursor.fetchone()
        return row['brand'] if row else None
    finally:
        conn.close()


def get_primary_position_data(project_id: Optional[int]) -> Dict:
    """获取主要品牌的位置分布"""
    primary_brand = get_primary_brand(project_id)
    if not primary_brand:
        return {}

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT b.mention_position, COUNT(*) as count
            FROM brand_mentions b
            JOIN questions q ON b.question_id = q.id
            JOIN monitor_tasks m ON q.task_id = m.id
            WHERE m.project_id IS ? AND b.brand_name = ? AND b.mention_position IS NOT NULL
            GROUP BY b.mention_position
        ''', (project_id, primary_brand))

        result = {}
        for row in cursor.fetchall():
            result[row['mention_position']] = row['count']
        return result
    finally:
        conn.close()


# 初始化和迁移数据库
try:
    init_db()
    migrate_db()
except Exception as e:
    print(f"DB init error: {e}")

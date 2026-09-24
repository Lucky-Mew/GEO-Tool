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

    # 豆包引用链接表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS doubao_citations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            question_id INTEGER NOT NULL,
            date_str TEXT NOT NULL,
            url TEXT NOT NULL,
            context_snippet TEXT,
            is_imported INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id),
            FOREIGN KEY (question_id) REFERENCES questions (id)
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

    # ========== 每日文章规划表 ==========

    # 每日文章规划表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS geo_daily_plan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            plan_name TEXT NOT NULL,
            start_date TEXT NOT NULL,
            total_days INTEGER NOT NULL DEFAULT 7,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id)
        )
    ''')

    # 每日文章内容表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS geo_daily_article (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            daily_plan_id INTEGER NOT NULL,
            day_index INTEGER NOT NULL,
            article_date TEXT,
            article_type TEXT NOT NULL,
            title TEXT,
            target_keywords TEXT,
            content_outline TEXT,
            content_text TEXT,
            brand_implant_level TEXT DEFAULT 'none',
            suggested_time TEXT,
            status TEXT DEFAULT 'pending',
            published_url TEXT,
            published_date TEXT,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (daily_plan_id) REFERENCES geo_daily_plan (id)
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

    # 竞品品牌表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS geo_competitor_brands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            brand_name TEXT NOT NULL,
            brand_alias TEXT,
            industry TEXT,
            notes TEXT,
            sort_order INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id)
        )
    ''')

    # 给文档表加竞品品牌字段（如果不存在）
    try:
        cursor.execute("ALTER TABLE geo_documents ADD COLUMN competitor_brand_id INTEGER")
    except sqlite3.OperationalError:
        pass  # 字段已存在

    # 给文档表加 doc_category 字段（三大分类：brand/competitor/reference）
    try:
        cursor.execute("ALTER TABLE geo_documents ADD COLUMN doc_category TEXT DEFAULT 'brand'")
    except sqlite3.OperationalError:
        pass  # 字段已存在

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


# ========== 竞品品牌管理 ==========

def add_competitor_brand(project_id: int, brand_name: str,
                         brand_alias: str = "", industry: str = "",
                         notes: str = "") -> int:
    """添加竞品品牌"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO geo_competitor_brands (project_id, brand_name, brand_alias, industry, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (project_id, brand_name, brand_alias, industry, notes))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def update_competitor_brand(brand_id: int, brand_name: str = None,
                            brand_alias: str = None, industry: str = None,
                            notes: str = None):
    """更新竞品品牌信息"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        updates = []
        params = []
        if brand_name is not None:
            updates.append("brand_name = ?")
            params.append(brand_name)
        if brand_alias is not None:
            updates.append("brand_alias = ?")
            params.append(brand_alias)
        if industry is not None:
            updates.append("industry = ?")
            params.append(industry)
        if notes is not None:
            updates.append("notes = ?")
            params.append(notes)
        if updates:
            params.append(brand_id)
            cursor.execute(
                f"UPDATE geo_competitor_brands SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                params
            )
            conn.commit()
    finally:
        conn.close()


def delete_competitor_brand(brand_id: int):
    """删除竞品品牌（同时把该品牌的资料文档移到未分类）"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # 先把该品牌的文档解除关联
        cursor.execute("UPDATE geo_documents SET competitor_brand_id = NULL WHERE competitor_brand_id = ?", (brand_id,))
        # 再删品牌
        cursor.execute("DELETE FROM geo_competitor_brands WHERE id = ?", (brand_id,))
        conn.commit()
    finally:
        conn.close()


def get_competitor_brands(project_id: int) -> list:
    """获取项目的所有竞品品牌"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT * FROM geo_competitor_brands
            WHERE project_id = ?
            ORDER BY sort_order ASC, created_at ASC
        ''', (project_id,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_competitor_brand(brand_id: int) -> dict:
    """获取单个竞品品牌"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM geo_competitor_brands WHERE id = ?", (brand_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


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


# ========== 豆包引用链接 ==========

def extract_urls_from_text(text: str) -> list:
    """从文本中提取URL"""
    import re
    if not text:
        return []
    url_pattern = r'https?://[^\s<>"\')\]}]+[^\s<>"\')\]\},.;]'
    urls = re.findall(url_pattern, text)
    return urls


def save_doubao_citations(project_id: Optional[int], question_id: int, date_str: str,
                           data: str | list[dict]) -> list:
    """从回答中提取链接并保存，或者直接传入已提取好的citations列表

    data: 可以是response_text字符串，也可以是[{'title': '...', 'url': '...'}, ...]格式
    """
    conn = get_connection()
    cursor = conn.cursor()
    saved_ids = []

    try:
        if isinstance(data, list):
            # 直接传入已提取的 citations
            for cite in data:
                url = cite.get('url', '')
                if not url:
                    continue

                # 全局检查：这个URL是否已经存在于数据库里（不管是哪个问题问的）
                cursor.execute('''
                    SELECT id FROM doubao_citations WHERE url = ?
                ''', (url,))
                existing = cursor.fetchone()

                if not existing:
                    title = cite.get('title', '')
                    context = title
                    cursor.execute('''
                        INSERT INTO doubao_citations
                        (project_id, question_id, date_str, url, context_snippet, is_imported)
                        VALUES (?, ?, ?, ?, ?, 0)
                    ''', (project_id, question_id, date_str, url, context))
                    saved_ids.append(cursor.lastrowid)
        else:
            # 从文本中提取
            if not data:
                return []
            urls = extract_urls_from_text(data)
            if not urls:
                return []

            for url in urls:
                # 全局检查：这个URL是否已经存在于数据库里
                cursor.execute('''
                    SELECT id FROM doubao_citations WHERE url = ?
                ''', (url,))
                existing = cursor.fetchone()

                if not existing:
                    idx = data.find(url)
                    context_start = max(0, idx - 100)
                    context_end = min(len(data), idx + len(url) + 100)
                    context = data[context_start:context_end]
                    cursor.execute('''
                        INSERT INTO doubao_citations
                        (project_id, question_id, date_str, url, context_snippet, is_imported)
                        VALUES (?, ?, ?, ?, ?, 0)
                    ''', (project_id, question_id, date_str, url, context))
                    saved_ids.append(cursor.lastrowid)

        conn.commit()
        return saved_ids
    except Exception as e:
        conn.rollback()
        print(f"保存引用链接失败: {e}")
        return []
    finally:
        conn.close()


def get_doubao_citations(
    project_id: Optional[int],
    limit: int = 50,
    offset: int = 0,
    import_filter: Optional[str] = None  # "imported", "not_imported", None
) -> dict:
    """获取豆包引用链接列表（带分页和筛选）

    Returns:
        {
            "items": [...],
            "total": total_count,
            "page": current_page,
            "page_size": limit,
            "total_pages": total_pages
        }
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 构建WHERE条件
        where_conditions = ['dc.project_id IS ?']
        params = [project_id]

        if import_filter == 'imported':
            where_conditions.append('dc.is_imported = 1')
        elif import_filter == 'not_imported':
            where_conditions.append('dc.is_imported = 0')

        where_clause = ' AND '.join(where_conditions)

        # 先查总数
        cursor.execute(f'''
            SELECT COUNT(*) as total
            FROM doubao_citations dc
            WHERE {where_clause}
        ''', params)
        total = cursor.fetchone()['total']

        # 再查分页数据
        cursor.execute(f'''
            SELECT dc.*, q.question_text
            FROM doubao_citations dc
            LEFT JOIN questions q ON dc.question_id = q.id
            WHERE {where_clause}
            ORDER BY dc.created_at DESC
            LIMIT ? OFFSET ?
        ''', params + [limit, offset])

        rows = cursor.fetchall()
        items = [dict(row) for row in rows]

        total_pages = (total + limit - 1) // limit if limit > 0 else 0
        current_page = (offset // limit) + 1

        return {
            "items": items,
            "total": total,
            "page": current_page,
            "page_size": limit,
            "total_pages": total_pages
        }

    finally:
        conn.close()


def mark_citation_imported(citation_id: int):
    """标记链接已导入"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            UPDATE doubao_citations
            SET is_imported = 1
            WHERE id = ?
        ''', (citation_id,))
        conn.commit()
    finally:
        conn.close()


def get_doubao_citations_count(project_id: Optional[int], import_filter: Optional[str] = None) -> int:
    """获取豆包引用总数"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        query = 'SELECT COUNT(*) as cnt FROM doubao_citations WHERE project_id IS ?'
        params = [project_id]

        if import_filter == 'imported':
            query += ' AND is_imported = 1'
        elif import_filter == 'unimported':
            query += ' AND is_imported = 0'

        cursor.execute(query, params)
        row = cursor.fetchone()
        return row['cnt'] if row else 0
    finally:
        conn.close()


def cleanup_doubao_citations(project_id: Optional[int], keep_count: int = 100,
                              keep_imported: bool = True) -> Dict[str, int]:
    """
    清理旧的豆包引用记录，保留最新的 N 条

    Args:
        project_id: 项目ID
        keep_count: 保留的数量（默认100条）
        keep_imported: 是否保留已导入的记录（即使超出数量也保留）

    Returns:
        {"deleted": 删除数量, "remaining": 剩余数量}
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 先获取总数
        cursor.execute(
            'SELECT COUNT(*) as cnt FROM doubao_citations WHERE project_id IS ?',
            (project_id,)
        )
        total_before = cursor.fetchone()['cnt']

        if total_before <= keep_count:
            return {"deleted": 0, "remaining": total_before}

        # 如果保留已导入的，先统计已导入的数量
        imported_count = 0
        if keep_imported:
            cursor.execute(
                'SELECT COUNT(*) as cnt FROM doubao_citations WHERE project_id IS ? AND is_imported = 1',
                (project_id,)
            )
            imported_count = cursor.fetchone()['cnt']

        # 计算需要删除多少条
        # 如果已导入的已经超过 keep_count，那就只保留已导入的
        if keep_imported and imported_count >= keep_count:
            # 删除所有未导入的
            cursor.execute(
                'DELETE FROM doubao_citations WHERE project_id IS ? AND is_imported = 0',
                (project_id,)
            )
        else:
            # 保留最新的 keep_count 条（如果 keep_imported，已导入的优先保留）
            if keep_imported:
                # 先删除未导入中较旧的，再看还需要删多少
                remaining_quota = keep_count - imported_count
                # 取最新的 remaining_quota 条未导入记录，删除其余未导入的
                cursor.execute('''
                    DELETE FROM doubao_citations
                    WHERE project_id IS ? AND is_imported = 0
                    AND id NOT IN (
                        SELECT id FROM doubao_citations
                        WHERE project_id IS ? AND is_imported = 0
                        ORDER BY id DESC
                        LIMIT ?
                    )
                ''', (project_id, project_id, remaining_quota))
            else:
                # 直接保留最新的 N 条
                cursor.execute('''
                    DELETE FROM doubao_citations
                    WHERE project_id IS ?
                    AND id NOT IN (
                        SELECT id FROM doubao_citations
                        WHERE project_id IS ?
                        ORDER BY id DESC
                        LIMIT ?
                    )
                ''', (project_id, project_id, keep_count))

        deleted = cursor.rowcount if cursor.rowcount >= 0 else 0
        conn.commit()

        # 计算剩余数量
        cursor.execute(
            'SELECT COUNT(*) as cnt FROM doubao_citations WHERE project_id IS ?',
            (project_id,)
        )
        remaining = cursor.fetchone()['cnt']

        return {"deleted": deleted, "remaining": remaining}
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


# ========== 每日文章规划 ==========

def create_daily_plan(project_id: Optional[int], plan_name: str, start_date: str, total_days: int = 7) -> int:
    """创建每日文章规划"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 将其他活跃规划设为非活跃
        cursor.execute('''
            UPDATE geo_daily_plan
            SET status = 'completed'
            WHERE project_id IS ? AND status = 'active'
        ''', (project_id,))

        # 创建新规划
        cursor.execute('''
            INSERT INTO geo_daily_plan (project_id, plan_name, start_date, total_days, status)
            VALUES (?, ?, ?, ?, 'active')
        ''', (project_id, plan_name, start_date, total_days))
        plan_id = cursor.lastrowid
        conn.commit()
        return plan_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_active_plan(project_id: Optional[int]) -> Optional[Dict]:
    """获取当前活跃规划"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT * FROM geo_daily_plan
            WHERE project_id IS ? AND status = 'active'
            ORDER BY created_at DESC LIMIT 1
        ''', (project_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_plan(plan_id: int) -> Optional[Dict]:
    """获取单个规划"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT * FROM geo_daily_plan WHERE id = ?', (plan_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_all_plans(project_id: Optional[int]) -> List[Dict]:
    """获取所有规划"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT * FROM geo_daily_plan
            WHERE project_id IS ?
            ORDER BY created_at DESC
        ''', (project_id,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def complete_plan(plan_id: int):
    """完成规划"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            UPDATE geo_daily_plan
            SET status = 'completed'
            WHERE id = ?
        ''', (plan_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def create_daily_article(daily_plan_id: int, day_index: int, article_type: str,
                         article_date: Optional[str] = None, title: Optional[str] = None,
                         target_keywords: Optional[str] = None, content_outline: Optional[str] = None,
                         brand_implant_level: str = 'none', suggested_time: Optional[str] = None) -> int:
    """创建每日文章"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO geo_daily_article (
                daily_plan_id, day_index, article_date, article_type, title,
                target_keywords, content_outline, brand_implant_level, suggested_time, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        ''', (daily_plan_id, day_index, article_date, article_type, title,
              target_keywords, content_outline, brand_implant_level, suggested_time))
        article_id = cursor.lastrowid
        conn.commit()
        return article_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_plan_articles(plan_id: int) -> List[Dict]:
    """获取规划的所有文章"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT * FROM geo_daily_article
            WHERE daily_plan_id = ?
            ORDER BY day_index
        ''', (plan_id,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_article(article_id: int) -> Optional[Dict]:
    """获取单个文章"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT * FROM geo_daily_article WHERE id = ?', (article_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_article_status(article_id: int, status: str, published_url: Optional[str] = None,
                          published_date: Optional[str] = None):
    """更新文章状态"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        updates = ['status = ?', 'updated_at = CURRENT_TIMESTAMP']
        params = [status, article_id]

        if published_url:
            updates.insert(1, 'published_url = ?')
            params.insert(1, published_url)
        if published_date:
            updates.insert(1, 'published_date = ?')
            params.insert(1, published_date)

        cursor.execute(f'''
            UPDATE geo_daily_article
            SET {', '.join(updates)}
            WHERE id = ?
        ''', params)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def update_article_content(article_id: int, title: Optional[str] = None,
                           target_keywords: Optional[str] = None, content_outline: Optional[str] = None,
                           content_text: Optional[str] = None, notes: Optional[str] = None):
    """更新文章内容"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        updates = ['updated_at = CURRENT_TIMESTAMP']
        params = []

        if title is not None:
            updates.append('title = ?')
            params.append(title)
        if target_keywords is not None:
            updates.append('target_keywords = ?')
            params.append(target_keywords)
        if content_outline is not None:
            updates.append('content_outline = ?')
            params.append(content_outline)
        if content_text is not None:
            updates.append('content_text = ?')
            params.append(content_text)
        if notes is not None:
            updates.append('notes = ?')
            params.append(notes)

        if updates:
            params.append(article_id)
            cursor.execute(f'''
                UPDATE geo_daily_article
                SET {', '.join(updates)}
                WHERE id = ?
            ''', params)
            conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_plan_progress(plan_id: int) -> Dict[str, Any]:
    """获取规划进度统计"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT status, COUNT(*) as count
            FROM geo_daily_article
            WHERE daily_plan_id = ?
            GROUP BY status
        ''', (plan_id,))

        rows = cursor.fetchall()
        progress = {'total': 0, 'pending': 0, 'in_progress': 0, 'published': 0, 'current_day': 1}

        for row in rows:
            status = row['status']
            count = row['count']
            progress['total'] += count
            if status in progress:
                progress[status] = count

        # 找到当前待发布的文章（第一个未发布的）
        cursor.execute('''
            SELECT day_index FROM geo_daily_article
            WHERE daily_plan_id = ? AND status IN ('pending', 'in_progress')
            ORDER BY day_index LIMIT 1
        ''', (plan_id,))
        row = cursor.fetchone()
        if row:
            progress['current_day'] = row['day_index']

        return progress
    finally:
        conn.close()


# 初始化和迁移数据库
try:
    init_db()
    migrate_db()
except Exception as e:
    print(f"DB init error: {e}")

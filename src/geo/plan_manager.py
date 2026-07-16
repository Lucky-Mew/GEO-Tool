# 执行计划管理
"""
8周GEO优化执行计划:
- 第1周: 基础建设(关键词库+素材表)
- 第2-4周: 内容爆发(1+5+30矩阵)
- 第5-6周: 权重积累(品牌词命中率≥80%)
- 第7-8周: 品类攻坚(大词开始出现)
"""

import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from src.db.models import get_connection


class PlanManager:
    """8周执行计划管理"""

    PHASE_FOUNDATION = 'foundation'      # 基础建设
    PHASE_CONTENT = 'content'            # 内容爆发
    PHASE_DISTRIBUTION = 'distribution'  # 权重积累
    PHASE_OPTIMIZATION = 'optimization'  # 品类攻坚

    PHASE_NAMES = {
        PHASE_FOUNDATION: '基础建设',
        PHASE_CONTENT: '内容爆发',
        PHASE_DISTRIBUTION: '权重积累',
        PHASE_OPTIMIZATION: '品类攻坚'
    }

    STATUS_PENDING = 'pending'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETED = 'completed'

    def create_8week_plan(self, project_id: Optional[int], start_date: Optional[str] = None) -> List[int]:
        """创建标准8周计划"""
        if not start_date:
            start_date = datetime.now().strftime('%Y%m%d')

        plan_items = [
            # 第1周: 基础建设
            {
                "week": 1,
                "phase": self.PHASE_FOUNDATION,
                "description": "独有信息资产盘点",
                "deliverable": "完成独有信息素材库表格,包含价格/周期/技术/专利/临床/人群6类数据",
                "due_offset": 7
            },
            {
                "week": 1,
                "phase": self.PHASE_FOUNDATION,
                "description": "搭建四层关键词库",
                "deliverable": "100关键词库(品牌词20+精准词30+大词10+场景词40)",
                "due_offset": 7
            },
            {
                "week": 1,
                "phase": self.PHASE_FOUNDATION,
                "description": "竞品GEO表现调研",
                "deliverable": "竞品引用情况分析报告",
                "due_offset": 7
            },
            # 第2周: 内容爆发
            {
                "week": 2,
                "phase": self.PHASE_CONTENT,
                "description": "核心深度文创作",
                "deliverable": "1篇核心深度文(含5种方案对比表+价格表+选购流程图+FAQ)",
                "due_offset": 14
            },
            {
                "week": 2,
                "phase": self.PHASE_CONTENT,
                "description": "长尾问答文创作",
                "deliverable": "10篇长尾问答文",
                "due_offset": 14
            },
            # 第3周: 内容爆发
            {
                "week": 3,
                "phase": self.PHASE_CONTENT,
                "description": "横向对比文创作",
                "deliverable": "3篇横向对比文",
                "due_offset": 21
            },
            {
                "week": 3,
                "phase": self.PHASE_CONTENT,
                "description": "长尾问答文创作",
                "deliverable": "10篇长尾问答文",
                "due_offset": 21
            },
            # 第4周: 内容爆发
            {
                "week": 4,
                "phase": self.PHASE_CONTENT,
                "description": "横向对比文创作",
                "deliverable": "2篇横向对比文",
                "due_offset": 28
            },
            {
                "week": 4,
                "phase": self.PHASE_CONTENT,
                "description": "长尾问答文创作",
                "deliverable": "10篇长尾问答文",
                "due_offset": 28
            },
            # 第5周: 权重积累
            {
                "week": 5,
                "phase": self.PHASE_DISTRIBUTION,
                "description": "品牌词命中率提升",
                "deliverable": "品牌词命中率≥80%",
                "due_offset": 35
            },
            {
                "week": 5,
                "phase": self.PHASE_DISTRIBUTION,
                "description": "多账号矩阵启动",
                "deliverable": "3个账号开始稳定发布内容",
                "due_offset": 35
            },
            # 第6周: 权重积累
            {
                "week": 6,
                "phase": self.PHASE_DISTRIBUTION,
                "description": "精准词渗透",
                "deliverable": "精准词开始出现命中",
                "due_offset": 42
            },
            # 第7周: 品类攻坚
            {
                "week": 7,
                "phase": self.PHASE_OPTIMIZATION,
                "description": "FAQ聚合页",
                "deliverable": "50个常问问题聚合页面",
                "due_offset": 49
            },
            {
                "week": 7,
                "phase": self.PHASE_OPTIMIZATION,
                "description": "大词突破",
                "deliverable": "大词开始出现命中",
                "due_offset": 49
            },
            # 第8周: 品类攻坚
            {
                "week": 8,
                "phase": self.PHASE_OPTIMIZATION,
                "description": "内容加固",
                "deliverable": "数据可视化内容+话题矩阵",
                "due_offset": 56
            },
            {
                "week": 8,
                "phase": self.PHASE_OPTIMIZATION,
                "description": "稳定输出",
                "deliverable": "大词稳定出现在备选答案",
                "due_offset": 56
            }
        ]

        # 计算截止日期
        plan_ids = []
        start_dt = datetime.strptime(start_date, '%Y%m%d')

        for item in plan_items:
            due_dt = start_dt + timedelta(days=item['due_offset'])
            plan_id = self.add_plan_item(
                project_id,
                item['week'],
                item['phase'],
                item['description'],
                item['deliverable'],
                due_dt.strftime('%Y%m%d')
            )
            plan_ids.append(plan_id)

        return plan_ids

    def add_plan_item(self, project_id: Optional[int], week: int, phase: str,
                      description: str, deliverable: str, due_date: Optional[str] = None,
                      status: str = 'pending') -> int:
        """添加计划项"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO geo_plan (project_id, week, phase, description, deliverable, due_date, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (project_id, week, phase, description, deliverable, due_date, status))
            plan_id = cursor.lastrowid
            conn.commit()
            return plan_id
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_plan(self, project_id: Optional[int]) -> List[Dict]:
        """获取完整计划"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT * FROM geo_plan
                WHERE project_id IS ?
                ORDER BY week, id
            ''', (project_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_weekly_tasks(self, project_id: Optional[int], week: int) -> List[Dict]:
        """获取当周任务"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT * FROM geo_plan
                WHERE project_id IS ? AND week = ?
                ORDER BY id
            ''', (project_id, week))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_current_week(self) -> int:
        """获取当前周数(基于计划开始日期)"""
        # 简化版:返回第1周
        # 实际应该根据项目创建日期计算
        return 1

    def update_plan_item(self, plan_id: int, **kwargs):
        """更新计划项"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            allowed_fields = ['week', 'phase', 'description', 'deliverable', 'due_date', 'status']
            updates = []
            params = []

            for field in allowed_fields:
                if field in kwargs:
                    if field == 'status' and kwargs[field] == self.STATUS_COMPLETED:
                        updates.append('completed_date = ?')
                        params.append(datetime.now().strftime('%Y%m%d'))

                    updates.append(f'{field} = ?')
                    params.append(kwargs[field])

            if updates:
                params.append(plan_id)
                cursor.execute(f'''
                    UPDATE geo_plan
                    SET {', '.join(updates)}
                    WHERE id = ?
                ''', params)
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_progress_summary(self, project_id: Optional[int]) -> Dict[str, Any]:
        """获取进度摘要"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT week, phase, status, COUNT(*) as count
                FROM geo_plan
                WHERE project_id IS ?
                GROUP BY week, phase, status
            ''', (project_id,))

            rows = cursor.fetchall()

            # 统计各阶段完成情况
            weekly_progress = {}
            phase_stats = {}

            for row in rows:
                week = row['week']
                phase = row['phase']
                status = row['status']
                count = row['count']

                if week not in weekly_progress:
                    weekly_progress[week] = {'total': 0, 'completed': 0, 'in_progress': 0, 'pending': 0}
                weekly_progress[week]['total'] += count
                if status == self.STATUS_COMPLETED:
                    weekly_progress[week]['completed'] += count
                elif status == self.STATUS_IN_PROGRESS:
                    weekly_progress[week]['in_progress'] += count
                else:
                    weekly_progress[week]['pending'] += count

                if phase not in phase_stats:
                    phase_stats[phase] = {'total': 0, 'completed': 0, 'in_progress': 0, 'pending': 0}
                phase_stats[phase]['total'] += count
                if status == self.STATUS_COMPLETED:
                    phase_stats[phase]['completed'] += count
                elif status == self.STATUS_IN_PROGRESS:
                    phase_stats[phase]['in_progress'] += count
                else:
                    phase_stats[phase]['pending'] += count

            # 总体统计
            total = sum(w['total'] for w in weekly_progress.values())
            completed = sum(w['completed'] for w in weekly_progress.values())
            overall_rate = completed / total if total > 0 else 0

            return {
                'total': total,
                'completed': completed,
                'overall_rate': overall_rate,
                'weekly_progress': weekly_progress,
                'phase_stats': phase_stats
            }
        finally:
            conn.close()

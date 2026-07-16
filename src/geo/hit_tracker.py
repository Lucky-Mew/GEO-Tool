# 命中率监测系统
"""
关键词命中追踪:
- 记录每个关键词的命中情况
- 分层统计品牌词/精准词/大词命中率
- 趋势分析
"""

import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Any
from src.db.models import get_connection


class HitTracker:
    """关键词命中追踪"""

    POSITION_FIRST = 'first'      # 开头
    POSITION_MIDDLE = 'middle'    # 中间
    POSITION_LAST = 'last'        # 结尾
    POSITION_NONE = 'not_mentioned'

    def record_hit(self, project_id: Optional[int], keyword_id: Optional[int],
                   keyword: str, is_hit: bool, position: Optional[str] = None,
                   mention_count: int = 0, cited_sources: Optional[List[str]] = None,
                   response_snippet: Optional[str] = None) -> int:
        """记录关键词命中情况"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            now = datetime.now()
            date_str = now.strftime('%Y%m%d')
            hour = now.hour

            cited_sources_str = ','.join(cited_sources) if cited_sources else None

            cursor.execute('''
                INSERT INTO geo_hit_records
                (project_id, keyword_id, keyword, date_str, hour, is_hit, position,
                 mention_count, cited_sources, response_snippet)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (project_id, keyword_id, keyword, date_str, hour, 1 if is_hit else 0,
                  position, mention_count, cited_sources_str, response_snippet))
            record_id = cursor.lastrowid
            conn.commit()
            return record_id
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_hit_records(self, project_id: Optional[int], keyword: Optional[str] = None,
                        keyword_id: Optional[int] = None, days: int = 30) -> List[Dict]:
        """获取命中记录"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            from datetime import timedelta
            cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')

            query = 'SELECT * FROM geo_hit_records WHERE project_id IS ? AND date_str >= ?'
            params = [project_id, cutoff]

            if keyword:
                query += ' AND keyword = ?'
                params.append(keyword)
            if keyword_id:
                query += ' AND keyword_id = ?'
                params.append(keyword_id)

            query += ' ORDER BY date_str DESC, hour DESC'

            cursor.execute(query, params)
            rows = cursor.fetchall()

            results = []
            for row in rows:
                data = dict(row)
                if data.get('cited_sources'):
                    data['cited_sources'] = data['cited_sources'].split(',')
                else:
                    data['cited_sources'] = []
                results.append(data)

            return results
        finally:
            conn.close()

    def get_hit_rate(self, project_id: Optional[int], tier: Optional[str] = None,
                     days: int = 7) -> Dict[str, Any]:
        """获取命中率统计"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            from datetime import timedelta
            cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')

            if tier:
                # 按层级统计
                cursor.execute('''
                    SELECT COUNT(*) as total,
                           SUM(is_hit) as hits
                    FROM geo_hit_records h
                    LEFT JOIN geo_keywords k ON h.keyword_id = k.id
                    WHERE h.project_id IS ? AND h.date_str >= ? AND k.tier = ?
                ''', (project_id, cutoff, tier))
            else:
                # 总体统计
                cursor.execute('''
                    SELECT COUNT(*) as total,
                           SUM(is_hit) as hits
                    FROM geo_hit_records
                    WHERE project_id IS ? AND date_str >= ?
                ''', (project_id, cutoff))

            row = cursor.fetchone()
            total = row['total'] or 0
            hits = row['hits'] or 0
            hit_rate = hits / total if total > 0 else 0

            return {
                'total': total,
                'hits': hits,
                'hit_rate': hit_rate,
                'days': days
            }
        finally:
            conn.close()

    def get_tier_hit_rates(self, project_id: Optional[int], days: int = 7) -> Dict[str, Dict]:
        """获取各层级的命中率"""
        from .keyword_manager import KeywordManager

        km = KeywordManager()
        tiers = [km.TIER_BRAND, km.TIER_ACCURATE, km.TIER_GENERIC, km.TIER_SCENE]

        result = {}
        for tier in tiers:
            result[tier] = self.get_hit_rate(project_id, tier, days)

        return result

    def get_keyword_hit_trend(self, project_id: Optional[int], keyword: str,
                               days: int = 30) -> List[Dict]:
        """获取单个关键词的命中趋势(按日期)"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            from datetime import timedelta
            cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')

            cursor.execute('''
                SELECT date_str,
                       COUNT(*) as total,
                       SUM(is_hit) as hits
                FROM geo_hit_records
                WHERE project_id IS ? AND keyword = ? AND date_str >= ?
                GROUP BY date_str
                ORDER BY date_str
            ''', (project_id, keyword, cutoff))

            rows = cursor.fetchall()
            results = []
            for row in rows:
                total = row['total'] or 0
                hits = row['hits'] or 0
                results.append({
                    'date_str': row['date_str'],
                    'total': total,
                    'hits': hits,
                    'hit_rate': hits / total if total > 0 else 0
                })

            return results
        finally:
            conn.close()

    def get_position_distribution(self, project_id: Optional[int], days: int = 30) -> Dict[str, int]:
        """获取提及位置分布"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            from datetime import timedelta
            cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')

            cursor.execute('''
                SELECT position, COUNT(*) as count
                FROM geo_hit_records
                WHERE project_id IS ? AND date_str >= ? AND position IS NOT NULL
                GROUP BY position
            ''', (project_id, cutoff))

            result = {}
            for row in cursor.fetchall():
                result[row['position']] = row['count']

            return result
        finally:
            conn.close()

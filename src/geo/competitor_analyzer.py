# 竞品分析模块
"""
竞品GEO分析:
- 分析AI引用了竞品的哪些内容
- 分析竞品内容结构(表格/列表/纯文字)
- 识别我们的空白切入机会
"""

import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Any
from src.db.models import get_connection


class CompetitorAnalyzer:
    """竞品GEO分析"""

    def add_competitor(self, project_id: Optional[int], name: str,
                       url: Optional[str] = None, notes: Optional[str] = None) -> int:
        """添加竞品"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO geo_competitors (project_id, name, url, notes)
                VALUES (?, ?, ?, ?)
            ''', (project_id, name, url, notes))
            competitor_id = cursor.lastrowid
            conn.commit()
            return competitor_id
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_competitors(self, project_id: Optional[int]) -> List[Dict]:
        """获取竞品列表"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT * FROM geo_competitors
                WHERE project_id IS ?
                ORDER BY created_at DESC
            ''', (project_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def add_citation(self, project_id: Optional[int], competitor_id: int,
                     keyword: str, cited_content: str,
                     content_structure: Optional[str] = None,
                     source_url: Optional[str] = None) -> int:
        """记录竞品被引用情况"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            date_str = datetime.now().strftime('%Y%m%d')
            cursor.execute('''
                INSERT INTO geo_competitor_citations
                (project_id, competitor_id, keyword, cited_content, content_structure, source_url, date_str)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (project_id, competitor_id, keyword, cited_content,
                  content_structure, source_url, date_str))
            citation_id = cursor.lastrowid
            conn.commit()
            return citation_id
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_competitor_citations(self, project_id: Optional[int],
                                  competitor_id: Optional[int] = None,
                                  days: int = 30) -> List[Dict]:
        """获取竞品引用记录"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            from datetime import timedelta
            cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')

            query = '''
                SELECT c.*, comp.name as competitor_name
                FROM geo_competitor_citations c
                LEFT JOIN geo_competitors comp ON c.competitor_id = comp.id
                WHERE c.project_id IS ? AND c.date_str >= ?
            '''
            params = [project_id, cutoff]

            if competitor_id:
                query += ' AND c.competitor_id = ?'
                params.append(competitor_id)

            query += ' ORDER BY c.date_str DESC'

            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def analyze_competitor_content_patterns(self, project_id: Optional[int],
                                             competitor_id: int) -> Dict[str, Any]:
        """分析竞品内容模式"""
        citations = self.get_competitor_citations(project_id, competitor_id)

        if not citations:
            return {'patterns': [], 'suggestions': []}

        # 统计内容结构
        structure_counts = {}
        content_keywords = {}

        for cite in citations:
            structure = cite.get('content_structure', 'unknown')
            structure_counts[structure] = structure_counts.get(structure, 0) + 1

            # 简单关键词提取
            content = cite.get('cited_content', '')
            if len(content) > 10:
                # 这里可以加更复杂的NLP分析
                pass

        # 生成建议
        suggestions = self._generate_optimization_suggestions(structure_counts)

        return {
            'total_citations': len(citations),
            'structure_distribution': structure_counts,
            'suggestions': suggestions
        }

    def _generate_optimization_suggestions(self, structure_counts: Dict[str, int]) -> List[str]:
        """基于竞品分析生成优化建议"""
        suggestions = []

        if 'table' in structure_counts:
            suggestions.append("竞品使用了表格,我们也应该增加表格内容")
        if 'list' in structure_counts:
            suggestions.append("竞品使用了列表,我们也应该使用编号列表")
        if 'data' in structure_counts:
            suggestions.append("竞品使用了具体数据,我们需要增加更多数据支持")

        if not suggestions:
            suggestions.append("建议分析竞品被引用的具体内容,寻找空白切入点")

        return suggestions

    def get_gap_analysis(self, project_id: Optional[int]) -> Dict[str, Any]:
        """获取空白分析(我们没有覆盖但竞品有的内容)"""
        # 获取竞品被引用的关键词
        citations = self.get_competitor_citations(project_id)
        competitor_keywords = set(c['keyword'] for c in citations if c.get('keyword'))

        # 获取我们自己的关键词库
        from .keyword_manager import KeywordManager
        km = KeywordManager()
        our_keywords = set(
            k['keyword'] for k in km.get_keywords(project_id)
        )

        # 找出空白
        gaps = competitor_keywords - our_keywords

        return {
            'competitor_keywords': list(competitor_keywords),
            'our_keywords': list(our_keywords),
            'gap_keywords': list(gaps),
            'suggestions': [
                f"建议覆盖空白关键词: {', '.join(list(gaps)[:5])}"
                if gaps else "暂无明显空白,继续保持"
            ]
        }

    def delete_competitor(self, competitor_id: int):
        """删除竞品"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            # 级联删除引用记录
            cursor.execute('DELETE FROM geo_competitor_citations WHERE competitor_id = ?', (competitor_id,))
            cursor.execute('DELETE FROM geo_competitors WHERE id = ?', (competitor_id,))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

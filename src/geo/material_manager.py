# 独有信息素材库管理
"""
简化版本：去掉固定分类，改用标签
- 分类字段保留，但不强制
- 标签用逗号分隔
"""

import sqlite3
from typing import List, Dict, Optional, Any
from src.db.models import get_connection


class MaterialManager:
    """独有信息素材库管理"""

    def add_material(self, project_id: Optional[int], title: str,
                     content: str, tags: Optional[str] = None,
                     source: Optional[str] = None,
                     use_cases: Optional[List[str]] = None,
                     is_verified: bool = True) -> int:
        """添加素材（tags 用逗号分隔）"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            use_cases_str = ','.join(use_cases) if use_cases else None
            cursor.execute('''
                INSERT INTO geo_materials
                (project_id, category, title, content, source, use_cases, is_verified)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (project_id, tags or '', title, content, source, use_cases_str, 1 if is_verified else 0))
            material_id = cursor.lastrowid
            conn.commit()
            return material_id
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def batch_add_materials(self, project_id: Optional[int], materials_data: List[Dict]) -> List[int]:
        """批量添加素材"""
        material_ids = []
        for data in materials_data:
            mat_id = self.add_material(
                project_id,
                data['title'],
                data['content'],
                data.get('tags', ''),
                data.get('source'),
                data.get('use_cases'),
                data.get('is_verified', True)
            )
            material_ids.append(mat_id)
        return material_ids

    def get_materials(self, project_id: Optional[int], tag: Optional[str] = None) -> List[Dict]:
        """获取素材列表（tag 可选）"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            query = 'SELECT * FROM geo_materials WHERE project_id IS ?'
            params = [project_id]

            if tag:
                query += ' AND (category LIKE ? OR title LIKE ? OR content LIKE ?)'
                tag_like = f'%{tag}%'
                params.extend([tag_like, tag_like, tag_like])

            query += ' ORDER BY is_verified DESC, created_at DESC'

            cursor.execute(query, params)
            rows = cursor.fetchall()

            results = []
            for row in rows:
                data = dict(row)
                if data.get('use_cases'):
                    data['use_cases'] = data['use_cases'].split(',')
                else:
                    data['use_cases'] = []
                # 把 category 字段改名为 tags 更符合现在的用途
                data['tags'] = data.get('category', '')
                results.append(data)

            return results
        finally:
            conn.close()

    def get_materials_for_keyword(self, project_id: Optional[int], keyword: str) -> List[Dict]:
        """根据关键词获取适用素材"""
        all_materials = self.get_materials(project_id)
        keyword_lower = keyword.lower()

        matched = []
        for mat in all_materials:
            # 检查关键词是否在素材内容或标题中
            if keyword_lower in mat['title'].lower() or keyword_lower in mat['content'].lower():
                matched.append(mat)
                continue

            # 检查 use_cases
            for use_case in mat.get('use_cases', []):
                if use_case and use_case.lower() in keyword_lower:
                    matched.append(mat)
                    break

        return matched

    def get_random_materials(self, project_id: Optional[int], count: int = 3,
                             tag: Optional[str] = None) -> List[Dict]:
        """随机获取素材(用于内容生成)"""
        materials = self.get_materials(project_id, tag)
        if len(materials) <= count:
            return materials
        import random
        return random.sample(materials, count)

    def get_all_tags(self, project_id: Optional[int]) -> List[str]:
        """获取所有已使用的标签"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT category FROM geo_materials
                WHERE project_id IS ? AND category IS NOT NULL AND category != ''
            ''', (project_id,))

            all_tags = set()
            for row in cursor.fetchall():
                tags_str = row['category']
                for tag in tags_str.split(','):
                    tag = tag.strip()
                    if tag:
                        all_tags.add(tag)

            return sorted(list(all_tags))
        finally:
            conn.close()

    def get_tag_stats(self, project_id: Optional[int]) -> Dict[str, int]:
        """获取标签统计（统计每个标签的素材数量）"""
        materials = self.get_materials(project_id)
        tag_count = {}

        for mat in materials:
            tags_str = mat.get('tags', '')
            if tags_str:
                for tag in tags_str.split(','):
                    tag = tag.strip()
                    if tag:
                        tag_count[tag] = tag_count.get(tag, 0) + 1

        return tag_count

    def update_material(self, material_id: int, **kwargs):
        """更新素材"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            allowed_fields = ['title', 'content', 'source', 'is_verified']
            updates = []
            params = []

            # tags 对应 category 字段
            if 'tags' in kwargs:
                updates.append('category = ?')
                params.append(kwargs['tags'])

            for field in allowed_fields:
                if field in kwargs:
                    if field == 'use_cases' and isinstance(kwargs[field], list):
                        updates.append('use_cases = ?')
                        params.append(','.join(kwargs[field]))
                    else:
                        updates.append(f'{field} = ?')
                        params.append(kwargs[field])

            if updates:
                params.append(material_id)
                cursor.execute(f'''
                    UPDATE geo_materials
                    SET {', '.join(updates)}
                    WHERE id = ?
                ''', params)
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def delete_material(self, material_id: int):
        """删除素材"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('DELETE FROM geo_materials WHERE id = ?', (material_id,))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

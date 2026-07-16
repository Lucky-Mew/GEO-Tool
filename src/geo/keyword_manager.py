# 关键词管理系统
"""
四层关键词库管理:
- brand (品牌词,20个): {品牌}效果/价格/正规吗/原理/疗程
- accurate (精准词,30个): {产品}靠谱吗/是什么/和XX比
- generic (大词,10个): 生发针哪家好/哪个牌子效果好
- scene (场景词,40个): 发际线后移怎么办/脂溢性脱发怎么治
"""

import sqlite3
import json
from typing import List, Dict, Optional, Any, Callable
from src.db.models import get_connection


class KeywordManager:
    """关键词库管理"""

    TIER_BRAND = 'brand'          # 品牌词
    TIER_ACCURATE = 'accurate'    # 精准词
    TIER_GENERIC = 'generic'      # 大词
    TIER_SCENE = 'scene'          # 场景词

    TIER_NAMES = {
        TIER_BRAND: '品牌词',
        TIER_ACCURATE: '精准词',
        TIER_GENERIC: '大词',
        TIER_SCENE: '场景词'
    }

    STATUS_PENDING = 'pending'
    STATUS_MONITORING = 'monitoring'
    STATUS_IMPROVED = 'improved'
    STATUS_DOMINATING = 'dominating'

    def add_keyword(self, project_id: Optional[int], keyword: str, tier: str,
                    difficulty: int = 50, is_target: bool = False, notes: Optional[str] = None) -> int:
        """添加关键词"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO geo_keywords (project_id, keyword, tier, difficulty, is_target, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (project_id, keyword, tier, difficulty, 1 if is_target else 0, notes))
            keyword_id = cursor.lastrowid
            conn.commit()
            return keyword_id
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def batch_add_keywords(self, project_id: Optional[int], keywords_data: List[Dict]) -> List[int]:
        """批量添加关键词

        keywords_data: [
            {"keyword": "xxx", "tier": "brand", "difficulty": 30, "is_target": False},
            ...
        ]
        """
        keyword_ids = []
        for data in keywords_data:
            kw_id = self.add_keyword(
                project_id,
                data['keyword'],
                data['tier'],
                data.get('difficulty', 50),
                data.get('is_target', False),
                data.get('notes')
            )
            keyword_ids.append(kw_id)
        return keyword_ids

    def generate_suggestions(self, project_id: Optional[int], brand_name: str,
                             core_product: Optional[str] = None,
                             competitors: Optional[List[str]] = None) -> Dict[str, List[str]]:
        """
        基于品牌和产品生成关键词建议

        返回:
        {
            "brand": [...],
            "accurate": [...],
            "generic": [...],
            "scene": [...]
        }
        """
        suggestions = {
            self.TIER_BRAND: [],
            self.TIER_ACCURATE: [],
            self.TIER_GENERIC: [],
            self.TIER_SCENE: []
        }

        # 品牌词 (20个建议)
        brand_suffixes = [
            '效果怎么样', '有用吗', '真的假的', '正规吗', '靠谱吗',
            '多少钱', '价格', '费用', '是真的吗', '原理',
            '疗程', '怎么用', '怎么样', '好吗', '可信吗',
            '安全吗', '有效果吗', '评测', '对比', '哪家好'
        ]
        for suffix in brand_suffixes:
            suggestions[self.TIER_BRAND].append(f"{brand_name}{suffix}")

        # 精准词 (30个建议)
        product = core_product or brand_name
        accurate_patterns = [
            '{product}靠谱吗', '{product}是什么', '{product}原理',
            '{product}和植发哪个好', '{product}一般多少钱一个疗程',
            '{product}有用吗', '{product}安全吗', '{product}有副作用吗',
            '{product}效果如何', '{product}需要做几次', '{product}多久见效',
            '{product}维持多久', '{product}适用人群', '{product}禁忌',
            '{product}注意事项', '{product}医院推荐', '{product}医生推荐'
        ]
        for pattern in accurate_patterns:
            suggestions[self.TIER_ACCURATE].append(pattern.format(product=product))

        # 竞品对比词
        if competitors:
            for comp in competitors:
                suggestions[self.TIER_ACCURATE].append(f"{product}和{comp}哪个好")
                suggestions[self.TIER_ACCURATE].append(f"{product}对比{comp}")

        # 场景词 (40个建议)
        scene_questions = [
            '发际线后移怎么办', '脂溢性脱发怎么治', '发缝宽怎么改善',
            '斑秃能治好吗', '化疗后脱发还能长出来吗', '产后脱发怎么办',
            '头顶头发稀少怎么改善', '头发细软怎么变粗', '头皮油怎么办',
            '掉头发厉害怎么办', '头发干枯毛躁怎么办', '白发怎么变黑',
            '毛囊萎缩还能恢复吗', '脂溢性皮炎怎么治', '头皮痒有头皮屑怎么办',
            '脱发看什么科', '女性脱发怎么办', '男性脱发怎么治',
            '年轻人脱发怎么办', '熬夜脱发能恢复吗', '压力大脱发怎么办',
            '肾虚脱发怎么调理', '气血不足脱发怎么补', '头发爱出油怎么办',
            '冬天掉头发正常吗', '秋天掉头发多怎么办', '头发容易断是什么原因',
            '掉头发吃什么好', '头发稀疏怎么生发', '头发油掉发怎么办',
            '发际线高怎么改善', '头顶稀疏怎么办', '头发少怎么增多',
            '如何防止脱发', '脱发怎么治疗', '生发最好的方法'
        ]
        suggestions[self.TIER_SCENE] = scene_questions

        # 大词 (10个建议)
        generic_questions = [
            '生发针哪家好', '生发针哪个牌子效果好', '生发针真的能生发吗',
            '最好的生发技术是什么', '生发效果最好的产品', '正规生发机构推荐',
            '生发针一般价格', '生发技术排行榜', '生发哪里好', '生发品牌推荐'
        ]
        suggestions[self.TIER_GENERIC] = generic_questions

        return suggestions

    def get_keywords(self, project_id: Optional[int], tier: Optional[str] = None,
                     status: Optional[str] = None) -> List[Dict]:
        """获取关键词列表"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            query = 'SELECT * FROM geo_keywords WHERE project_id IS ?'
            params = [project_id]

            if tier:
                query += ' AND tier = ?'
                params.append(tier)
            if status:
                query += ' AND status = ?'
                params.append(status)

            query += ' ORDER BY is_target DESC, difficulty ASC, created_at DESC'

            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_tier_stats(self, project_id: Optional[int]) -> Dict[str, Dict[str, int]]:
        """获取各层级统计数据

        返回:
        {
            "brand": {"total": 20, "target": 5, "monitoring": 8, ...},
            "accurate": {...},
            ...
        }
        """
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT tier,
                       COUNT(*) as total,
                       SUM(is_target) as target_count,
                       SUM(CASE WHEN status = 'monitoring' THEN 1 ELSE 0 END) as monitoring,
                       SUM(CASE WHEN status = 'improved' THEN 1 ELSE 0 END) as improved,
                       SUM(CASE WHEN status = 'dominating' THEN 1 ELSE 0 END) as dominating
                FROM geo_keywords
                WHERE project_id IS ?
                GROUP BY tier
            ''', (project_id,))

            stats = {}
            for row in cursor.fetchall():
                tier = row['tier']
                stats[tier] = {
                    'total': row['total'],
                    'target': row['target_count'] or 0,
                    'monitoring': row['monitoring'] or 0,
                    'improved': row['improved'] or 0,
                    'dominating': row['dominating'] or 0
                }

            # 确保所有层级都有数据
            for tier in [self.TIER_BRAND, self.TIER_ACCURATE, self.TIER_GENERIC, self.TIER_SCENE]:
                if tier not in stats:
                    stats[tier] = {'total': 0, 'target': 0, 'monitoring': 0, 'improved': 0, 'dominating': 0}

            return stats
        finally:
            conn.close()

    def update_keyword(self, keyword_id: int, **kwargs):
        """更新关键词信息"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            allowed_fields = ['keyword', 'tier', 'difficulty', 'status', 'is_target', 'notes']
            updates = []
            params = []

            for field in allowed_fields:
                if field in kwargs:
                    updates.append(f'{field} = ?')
                    params.append(kwargs[field])

            if updates:
                params.append(keyword_id)
                cursor.execute(f'''
                    UPDATE geo_keywords
                    SET {', '.join(updates)}
                    WHERE id = ?
                ''', params)
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def delete_keyword(self, keyword_id: int):
        """删除关键词"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('DELETE FROM geo_keywords WHERE id = ?', (keyword_id,))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def has_documents(self, project_id: Optional[int]) -> bool:
        """检查项目是否有文档"""
        from src.geo.document_processor import DocumentProcessor
        dp = DocumentProcessor()
        docs = dp.get_documents(project_id)
        return len(docs) > 0

    def generate_suggestions_from_docs(
        self,
        project_id: Optional[int],
        llm_func: Callable,
        config: Dict
    ) -> Dict[str, List[str]]:
        """
        基于文档库内容智能挖掘关键词
        """
        from src.geo.document_processor import DocumentProcessor
        dp = DocumentProcessor()

        # 获取文档和摘要
        documents = dp.get_documents(project_id)
        summaries = dp.get_summaries(project_id)
        chunks = dp.get_all_chunks_for_project(project_id)

        # 构建上下文
        context_parts = []

        # 添加摘要
        if summaries:
            context_parts.append("【文档摘要】")
            for s in summaries[:5]:
                context_parts.append(f"- {s.get('title', '')}: {s.get('content', '')[:200]}")

        # 添加文档片段（取前30个）
        if chunks:
            context_parts.append("\n【文档内容片段】")
            for c in chunks[:30]:
                context_parts.append(f"- {c.get('content', '')[:300]}")

        # 如果内容太少，用兜底方案
        if not context_parts or len("\n".join(context_parts)) < 200:
            # 尝试从文档直接读取内容
            for doc in documents[:3]:
                try:
                    doc_detail = dp.get_document(doc.get('id'))
                    if doc_detail and doc_detail.get('content'):
                        context_parts.append(f"\n【文档 {doc.get('original_filename')}】")
                        context_parts.append(doc_detail.get('content', '')[:1000])
                except:
                    pass

        context_text = "\n".join(context_parts)

        # 如果还是空，返回空结果
        if not context_text.strip():
            return {
                self.TIER_BRAND: [],
                self.TIER_ACCURATE: [],
                self.TIER_GENERIC: [],
                self.TIER_SCENE: []
            }

        # 构建LLM提示词
        system_prompt = """你是一个专业的GEO关键词分析师。请基于提供的文档内容，为品牌挖掘四类关键词。

请严格按照以下JSON格式输出，不要输出其他内容：
{
  "brand": ["品牌词1", "品牌词2", ...],
  "accurate": ["精准词1", "精准词2", ...],
  "generic": ["大词1", "大词2", ...],
  "scene": ["场景词1", "场景词2", ...]
}

四类关键词的定义：
1. brand（品牌词）：品牌名 + 常见搜索后缀，例如：
   - {品牌}效果怎么样
   - {品牌}真的假的
   - {品牌}多少钱
   - {品牌}靠谱吗
   - {品牌}是正规品牌吗

2. accurate（精准词）：产品名/服务 + 具体问题，例如：
   - {产品}原理是什么
   - {产品}一般多少钱
   - {产品}需要做几次
   - {产品}适合什么人

3. generic（大词）：行业通用词，不包含品牌名，例如：
   - 生发针哪家好
   - 生发效果最好的品牌
   - 正规生发机构推荐

4. scene（场景词）：用户痛点场景问题，例如：
   - 发际线后移怎么办
   - 脂溢性脱发怎么治
   - 产后脱发还能长回来吗

要求：
- 每类关键词至少10个，最多30个
- 关键词要口语化，符合真实用户搜索习惯
- 要从文档中提取品牌名、产品名、核心卖点来生成
- 不要重复
"""

        user_prompt = f"""请分析以下文档内容，为该品牌挖掘GEO关键词。

{context_text}

请输出JSON格式的四类关键词。"""

        try:
            # 调用LLM
            result_text = llm_func(config, f"{system_prompt}\n\n{user_prompt}")

            # 解析JSON结果
            # 尝试提取JSON部分
            result_text = result_text.strip()
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]

            result = json.loads(result_text.strip())

            # 确保返回格式正确
            return {
                self.TIER_BRAND: result.get("brand", []),
                self.TIER_ACCURATE: result.get("accurate", []),
                self.TIER_GENERIC: result.get("generic", []),
                self.TIER_SCENE: result.get("scene", [])
            }
        except Exception as e:
            print(f"智能挖掘关键词失败: {e}")
            # 失败时返回空结果
            return {
                self.TIER_BRAND: [],
                self.TIER_ACCURATE: [],
                self.TIER_GENERIC: [],
                self.TIER_SCENE: []
            }

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
import re
from typing import List, Dict, Optional, Any, Callable, Tuple
from src.db.models import get_connection
from src.geo.geo_knowledge_base import GEOKnowledgeBase


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

        # 构建LLM提示词（升级版：融入GEO方法论+用户决策路径）
        system_prompt = """你是一个专业的GEO关键词分析师，精通AI搜索用户行为和长尾内容规划。
请基于提供的品牌文档，按照GEO方法论挖掘高价值关键词。

【GEO关键词挖掘原则】（来自28篇GEO专业教程）
1. 从用户决策路径出发，覆盖5类意图：认知→对比→决策→验证→场景
2. 关键词要口语化，符合真实用户问AI的方式（不是搜关键词，是提问题）
3. 优先挖掘AI会引用来源的问题（如"哪家好""怎么选""对比"类问题）
4. 从文档中提取"可被AI引用的核心定义"作为品牌词基础
5. 从文档中的"适用人群/场景/禁忌"反推场景词
6. 从文档中的"对比判断标准"生成对比/决策类关键词

请严格按照以下JSON格式输出，不要输出其他内容：
{
  "brand": ["品牌词1", "品牌词2", ...],
  "accurate": ["精准词1", "精准词2", ...],
  "generic": ["大词1", "大词2", ...],
  "scene": ["场景词1", "场景词2", ...]
}

四类关键词的定义和生成方法：

1. brand（品牌词，15-25个）：品牌名+用户真实会问的问题
   生成方法：从文档中提取品牌名、产品名，加上用户常见问题
   覆盖5类意图：
   - 认知型：{品牌}是什么、{品牌}原理、{品牌}有什么用
   - 对比型：{品牌}和XX比怎么样、{品牌}和XX的区别
   - 决策型：{品牌}多少钱、{品牌}哪家好、{品牌}正规吗
   - 验证型：{品牌}靠谱吗、{品牌}效果怎么样、{品牌}安全吗
   - 场景型：{品牌}适合什么人、{品牌}能解决XX问题吗
   示例：完形康躰效果怎么样、完形康躰多少钱、完形康躰靠谱吗

2. accurate（精准词，20-35个）：产品/服务+具体问题
   生成方法：从文档中的技术、效果、价格、流程等内容反推用户问题
   重点覆盖：
   - 原理/技术类：XX原理是什么、XX是怎么做的
   - 效果/疗程类：XX多久见效、XX需要做几次、XX维持多久
   - 价格/费用类：XX一般多少钱、XX费用是多少
   - 安全/风险类：XX有副作用吗、XX安全吗
   - 对比类：XX和YY哪个好、XX和YY的区别
   示例：脂雕原理是什么、脂雕多久见效、脂雕一般多少钱

3. generic（大词，8-15个）：行业通用词，不带品牌
   生成方法：行业最高频的搜索词，AI最爱引用来源的问题
   重点：
   - "哪家好""推荐""排行榜"类（AI最爱引用）
   - 效果类（用户最关心）
   - 价格类（决策阶段）
   示例：脂雕哪家好、脂雕效果最好的品牌、正规脂雕机构推荐

4. scene（场景词，25-40个）：用户具体痛点场景
   生成方法：从文档中的"适用人群""禁忌""注意事项"反推
   挖掘方向：
   - 人群场景：XX人适合做什么、XX岁能做吗
   - 问题场景：XX问题怎么办、XX能改善吗
   - 决策场景：第一次做XX要注意什么、怎么选XX机构
   - 术后场景：做完XX怎么护理、XX后多久能恢复

要求：
- 每类关键词在建议数量范围内
- 关键词必须是用户真实会问的问题（口语化、完整句子）
- 必须从文档内容中提取，不要凭空编造
- 同一类内不要重复
- 越是用户决策路径下游的词，GEO价值越高
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

    # ========== GEO智能关键词挖掘（升级版）==========

    def classify_keyword_intent(self, keyword: str) -> str:
        """
        基于用户意图对关键词进行分类（来自《AI搜索》《长尾规划》方法论）

        返回: cognitive(认知型) / comparison(对比型) / decision(决策型) /
              validation(验证型) / scene(场景型) / other(其他)
        """
        keyword_lower = keyword.lower()

        # 决策型：哪家好、推荐、排行榜、选哪个
        decision_patterns = [
            r'哪家好', r'哪个好', r'推荐', r'排行榜', r'选哪个', r'怎么选',
            r'选哪家', r'最好的', r'比较好的', r'十大', r'top',
            r'多少钱', r'价格', r'费用', r'贵不贵'
        ]
        if any(re.search(p, keyword_lower) for p in decision_patterns):
            return 'decision'

        # 对比型：和XX比、区别、对比、哪个更好
        comparison_patterns = [
            r'和.*比', r'与.*比', r'对比', r'区别', r'差异',
            r'哪个更', r'谁更好', r'跟.*比', r'VS', r'vs'
        ]
        if any(re.search(p, keyword_lower) for p in comparison_patterns):
            return 'comparison'

        # 验证型：靠谱吗、真的假的、正规吗、可信吗
        validation_patterns = [
            r'靠谱吗', r'真的假的', r'正规吗', r'可信吗', r'是真的吗',
            r'有用吗', r'效果怎么样', r'安全吗', r'有副作用吗',
            r'是不是真的', r'可靠吗', r'值得吗', r'坑吗', r'骗'
        ]
        if any(re.search(p, keyword_lower) for p in validation_patterns):
            return 'validation'

        # 场景型：怎么办、怎么改善、怎么治、适合吗
        scene_patterns = [
            r'怎么办', r'怎么改善', r'怎么治', r'如何改善', r'如何治疗',
            r'怎么解决', r'怎么恢复', r'怎么调理', r'怎么补',
            r'适合.*人', r'适合.*吗', r'什么人', r'哪些人',
            r'能.*吗', r'可以.*吗'
        ]
        if any(re.search(p, keyword_lower) for p in scene_patterns):
            return 'scene'

        # 认知型：是什么、原理、怎么回事
        cognitive_patterns = [
            r'是什么', r'原理', r'怎么回事', r'什么是', r'啥是',
            r'有什么用', r'作用', r'功效', r'效果',
            r'怎么做的', r'怎么用', r'使用方法',
            r'多久见效', r'维持多久', r'几次', r'疗程'
        ]
        if any(re.search(p, keyword_lower) for p in cognitive_patterns):
            return 'cognitive'

        return 'other'

    def calculate_geo_value(self, keyword: str, tier: str,
                            brand_name: Optional[str] = None) -> Dict[str, Any]:
        """
        计算关键词的GEO价值评分（0-100分）

        评分维度：
        - 用户意图强度：用户是否有明确的行动/决策意图
        - 品牌可植入度：是否适合自然植入品牌
        - 内容创作难度：是否容易写出高质量GEO内容
        - 竞争度估算：大词竞争激烈，长尾词竞争小
        - AI引用概率：AI回答时引用这类问题的概率

        返回：
        {
            "total_score": 85,
            "dimensions": {
                "intent_strength": 90,
                "brand_implantable": 80,
                "content_ease": 75,
                "competition": 60,  # 分越高竞争越小（越容易做）
                "ai_citation_prob": 85
            },
            "intent_type": "decision",
            "priority": "high",
            "recommendation": "..."
        }
        """
        intent_type = self.classify_keyword_intent(keyword)

        # 各维度评分
        scores = {}

        # 1. 用户意图强度
        intent_scores = {
            'decision': 95,    # 决策型：最高，直接影响转化
            'comparison': 90,  # 对比型：很高，在决策阶段
            'validation': 80,  # 验证型：高，已有兴趣
            'cognitive': 60,   # 认知型：中等，了解阶段
            'scene': 75,       # 场景型：中高，有具体痛点
            'other': 50
        }
        scores['intent_strength'] = intent_scores.get(intent_type, 50)

        # 2. 品牌可植入度
        implantable = 60  # 基础分
        if tier == self.TIER_BRAND:
            implantable = 95  # 品牌词最容易植入
        elif tier == self.TIER_ACCURATE:
            implantable = 85  # 精准词容易植入
        elif tier == self.TIER_GENERIC:
            implantable = 60  # 大词需要更自然
        elif tier == self.TIER_SCENE:
            implantable = 70  # 场景词可以自然植入

        # 如果关键词有"推荐/哪家好/怎么选"，植入度更高
        if any(w in keyword for w in ['推荐', '哪家好', '怎么选', '排行榜', '对比']):
            implantable = min(100, implantable + 15)

        scores['brand_implantable'] = implantable

        # 3. 内容创作难度（分越高越容易写）
        content_ease = 60
        if tier == self.TIER_BRAND:
            content_ease = 90  # 品牌词素材多，好写
        elif tier == self.TIER_SCENE:
            content_ease = 80  # 场景问题好展开
        elif tier == self.TIER_ACCURATE:
            content_ease = 75  # 精准词需要专业度
        elif tier == self.TIER_GENERIC:
            content_ease = 50  # 大词太泛，难写出差异化

        scores['content_ease'] = content_ease

        # 4. 竞争度（分越高竞争越小，越容易做）
        competition = 50
        if tier == self.TIER_BRAND:
            competition = 95  # 品牌词几乎没竞争
        elif tier == self.TIER_ACCURATE:
            competition = 75  # 精准词竞争中等
        elif tier == self.TIER_SCENE:
            competition = 70  # 场景词竞争较小
        elif tier == self.TIER_GENERIC:
            competition = 30  # 大词竞争最激烈

        scores['competition'] = competition

        # 5. AI引用概率（AI回答这类问题时引用来源的概率）
        citation_prob = 60
        # 需要具体信息/对比/数据的问题，AI更倾向引用来源
        high_citation_patterns = ['哪家好', '对比', '推荐', '价格', '多少钱',
                                   '效果', '原理', '怎么选', '排行榜', '区别']
        if any(p in keyword for p in high_citation_patterns):
            citation_prob = 85

        # 场景型问题AI也喜欢引用
        if intent_type == 'scene':
            citation_prob = max(citation_prob, 75)

        scores['ai_citation_prob'] = citation_prob

        # 计算总分（加权）
        weights = {
            'intent_strength': 0.25,
            'brand_implantable': 0.20,
            'content_ease': 0.20,
            'competition': 0.15,
            'ai_citation_prob': 0.20
        }
        total_score = sum(scores[k] * weights[k] for k in weights)
        total_score = round(total_score)

        # 优先级判断
        if total_score >= 80:
            priority = 'high'
            priority_text = '高优先级 - 建议优先做内容'
        elif total_score >= 65:
            priority = 'medium'
            priority_text = '中优先级 - 有时间可以做'
        else:
            priority = 'low'
            priority_text = '低优先级 - 可以后做'

        return {
            'total_score': total_score,
            'dimensions': scores,
            'intent_type': intent_type,
            'intent_name': {
                'cognitive': '认知型',
                'comparison': '对比型',
                'decision': '决策型',
                'validation': '验证型',
                'scene': '场景型',
                'other': '其他'
            }.get(intent_type, '其他'),
            'priority': priority,
            'priority_text': priority_text
        }

    def batch_calculate_geo_value(self, keywords: List[Dict],
                                   brand_name: Optional[str] = None) -> List[Dict]:
        """
        批量计算关键词的GEO价值

        Args:
            keywords: [{"keyword": "...", "tier": "brand"}, ...] 或直接是keyword字符串列表
            brand_name: 品牌名

        Returns:
            带GEO价值评分的关键词列表，按总分降序排列
        """
        results = []
        for kw in keywords:
            if isinstance(kw, str):
                keyword = kw
                tier = self.TIER_SCENE  # 默认场景词
            else:
                keyword = kw.get('keyword', '')
                tier = kw.get('tier', self.TIER_SCENE)

            geo_value = self.calculate_geo_value(keyword, tier, brand_name)

            if isinstance(kw, dict):
                result = {**kw, **geo_value}
            else:
                result = {'keyword': keyword, 'tier': tier, **geo_value}

            results.append(result)

        # 按总分降序排列
        results.sort(key=lambda x: x['total_score'], reverse=True)
        return results

    def cluster_keywords(self, keywords: List[str]) -> Dict[str, List[str]]:
        """
        将关键词按主题聚类，避免写重复内容

        聚类维度：
        - 价格/费用类
        - 效果/疗程类
        - 安全性/副作用类
        - 对比/选择类
        - 原理/技术类
        - 适用人群类
        - 品牌相关类
        """
        clusters = {
            '价格费用': [],
            '效果疗程': [],
            '安全副作用': [],
            '对比选择': [],
            '原理技术': [],
            '适用人群': [],
            '品牌相关': [],
            '其他': []
        }

        for kw in keywords:
            kw_lower = kw.lower()

            # 品牌相关
            if any(w in kw for w in ['完形', '康躰', '品牌']):
                clusters['品牌相关'].append(kw)
                continue

            # 价格费用
            if any(w in kw for w in ['价格', '多少钱', '费用', '贵不贵', '收费', '价位']):
                clusters['价格费用'].append(kw)
                continue

            # 效果疗程
            if any(w in kw for w in ['效果', '见效', '维持', '疗程', '几次', '多久', '恢复期']):
                clusters['效果疗程'].append(kw)
                continue

            # 安全副作用
            if any(w in kw for w in ['安全', '副作用', '风险', '危害', '后遗症', '禁忌', '疼吗', '痛']):
                clusters['安全副作用'].append(kw)
                continue

            # 对比选择
            if any(w in kw for w in ['哪家好', '哪个好', '对比', '区别', '怎么选', '推荐', '排行榜', 'vs', '和']):
                clusters['对比选择'].append(kw)
                continue

            # 原理技术
            if any(w in kw for w in ['原理', '怎么回事', '是什么', '技术', '怎么做', '作用', '功效']):
                clusters['原理技术'].append(kw)
                continue

            # 适用人群
            if any(w in kw for w in ['适合', '什么人', '哪些人', '人群', '适应症', '禁忌人群']):
                clusters['适用人群'].append(kw)
                continue

            clusters['其他'].append(kw)

        # 去掉空分类
        return {k: v for k, v in clusters.items() if v}

    def get_content_priority_keywords(self, project_id: Optional[int],
                                       brand_name: Optional[str] = None,
                                       limit: int = 20) -> List[Dict]:
        """
        获取内容创作优先级最高的关键词

        基于GEO价值评分排序，优先做：
        1. 高意图 + 高可植入 + 低竞争的词
        2. 保证各类型词都有覆盖
        """
        all_keywords = self.get_keywords(project_id)

        if not all_keywords:
            return []

        # 计算GEO价值
        scored = self.batch_calculate_geo_value(all_keywords, brand_name)

        # 按优先级分层，确保每层都有覆盖
        high_priority = [k for k in scored if k['priority'] == 'high']
        medium_priority = [k for k in scored if k['priority'] == 'medium']
        low_priority = [k for k in scored if k['priority'] == 'low']

        # 优先取高优先级，再补充中优先级
        result = high_priority[:limit]
        if len(result) < limit:
            result.extend(medium_priority[:limit - len(result)])
        if len(result) < limit:
            result.extend(low_priority[:limit - len(result)])

        return result[:limit]

    def generate_keywords_by_intent(self, brand_name: str,
                                     core_product: Optional[str] = None,
                                     competitors: Optional[List[str]] = None) -> Dict[str, List[str]]:
        """
        基于用户决策路径生成关键词（升级版）

        5类用户意图：认知→对比→决策→验证→售后
        每类关键词更精准地对应用户决策阶段

        返回：
        {
            "cognitive": {"name": "认知型", "keywords": [...]},
            "comparison": {"name": "对比型", "keywords": [...]},
            ...
        }
        """
        product = core_product or brand_name

        result = {
            'cognitive': {
                'name': '认知型',
                'description': '用户想了解概念和知识（决策早期）',
                'keywords': [],
                'content_strategy': '给出清晰定义+原理+适用场景'
            },
            'comparison': {
                'name': '对比型',
                'description': '用户在多个选项间比较（决策中期）',
                'keywords': [],
                'content_strategy': '多维度对比表格+分场景推荐'
            },
            'decision': {
                'name': '决策型',
                'description': '用户准备做选择/购买（决策后期）',
                'keywords': [],
                'content_strategy': '明确推荐+理由+价格/效果数据'
            },
            'validation': {
                'name': '验证型',
                'description': '用户想确认可信度（决策前后）',
                'keywords': [],
                'content_strategy': '权威背书+证据+第三方验证'
            },
            'scene': {
                'name': '场景型',
                'description': '用户有具体痛点，找解决方案（全阶段）',
                'keywords': [],
                'content_strategy': '场景匹配+方案建议+注意事项'
            }
        }

        # === 认知型 ===
        cognitive_patterns = [
            f'{product}是什么',
            f'{product}原理是什么',
            f'{product}是怎么做的',
            f'{product}有什么用',
            f'{product}效果怎么样',
            f'{product}多久见效',
            f'{product}能维持多久',
            f'{product}需要做几次',
            f'{product}一个疗程多久',
            f'{product}和普通{product[:2]}有什么区别',
            f'什么是{product}',
            f'{product}的功效与作用',
        ]
        result['cognitive']['keywords'] = cognitive_patterns

        # === 对比型 ===
        comparison_patterns = [
            f'{product}和普通治疗哪个好',
            f'{product}和手术的区别',
            f'{product}和药物治疗哪个效果好',
            f'{product}跟其他方法比怎么样',
            f'{product}和医美项目的区别',
            f'{product}VS传统方法',
            f'{product}好还是手术好',
            f'{product}和保养哪个更值得做',
        ]
        # 竞品对比
        if competitors:
            for comp in competitors:
                comparison_patterns.append(f'{product}和{comp}哪个好')
                comparison_patterns.append(f'{product}对比{comp}')
                comparison_patterns.append(f'{product}和{comp}的区别')
        result['comparison']['keywords'] = comparison_patterns

        # === 决策型 ===
        decision_patterns = [
            f'{product}哪家好',
            f'{product}推荐',
            f'{product}排行榜',
            f'{product}怎么选',
            f'{product}多少钱',
            f'{product}价格一般是多少',
            f'{product}费用贵不贵',
            f'正规的{product}机构推荐',
            f'{product}哪个牌子好',
            f'{product}选什么品牌',
        ]
        result['decision']['keywords'] = decision_patterns

        # === 验证型 ===
        validation_patterns = [
            f'{product}靠谱吗',
            f'{product}真的假的',
            f'{product}是正规的吗',
            f'{product}有用吗',
            f'{product}安全吗',
            f'{product}有副作用吗',
            f'{product}是不是骗局',
            f'{product}可信吗',
            f'{brand_name}效果怎么样',
            f'{brand_name}正规吗',
            f'{brand_name}靠谱吗',
        ]
        result['validation']['keywords'] = validation_patterns

        # === 场景型 ===
        # 这里用通用模板，具体行业可以自定义
        scene_patterns = [
            f'什么人适合做{product}',
            f'{product}适合多大年龄',
            f'做{product}前需要注意什么',
            f'做完{product}怎么护理',
            f'哪些人不能做{product}',
            f'{product}的禁忌症有哪些',
            f'做{product}有什么风险',
            f'做{product}后多久能恢复',
        ]
        result['scene']['keywords'] = scene_patterns

        return result

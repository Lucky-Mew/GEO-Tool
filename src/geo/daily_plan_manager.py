# GEO每日文章规划管理器
"""
每日文章规划功能:
- 4天循环的内容策略
- 关键词梯度分配
- 自动生成标题和大纲
- 进度跟踪
- AI自动生成文章内容
"""

import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Callable
from src.db.models import (
    create_daily_plan, get_active_plan, get_plan, get_all_plans, complete_plan,
    create_daily_article, get_plan_articles, get_article,
    update_article_status, update_article_content, get_plan_progress
)
from src.geo import KeywordManager


class DailyPlanManager:
    """每日文章规划管理器"""

    # 文章类型
    TYPE_AVOIDANCE = 'avoidance'          # 纯避雷科普
    TYPE_INDUSTRY = 'industry'            # 纯行业分析
    TYPE_LIGHT_IMPLANT = 'light_implant'  # 轻度植入
    TYPE_FAQ = 'faq'                      # 问答FAQ

    # 类型名称映射
    TYPE_NAMES = {
        TYPE_AVOIDANCE: '纯避雷科普',
        TYPE_INDUSTRY: '纯行业分析',
        TYPE_LIGHT_IMPLANT: '轻度植入',
        TYPE_FAQ: '问答FAQ'
    }

    # 品牌植入级别
    IMPLANT_NONE = 'none'
    IMPLANT_LIGHT = 'light'
    IMPLANT_MODERATE = 'moderate'

    # 状态
    STATUS_PENDING = 'pending'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_PUBLISHED = 'published'

    def __init__(self):
        self.km = KeywordManager()

    def create_plan(self, project_id: Optional[int], plan_name: str,
                    start_date: Optional[str] = None, total_days: int = 7,
                    template_type: str = 'balanced') -> int:
        """
        创建新规划

        Args:
            project_id: 项目ID
            plan_name: 规划名称
            start_date: 开始日期(YYYYMMDD)，默认为今天
            total_days: 总天数，默认7天
            template_type: 方案模板类型 (conservative/balanced/aggressive)

        Returns:
            规划ID
        """
        if not start_date:
            start_date = datetime.now().strftime('%Y%m%d')

        # 创建规划
        plan_id = create_daily_plan(project_id, plan_name, start_date, total_days)

        # 获取关键词
        keywords = self.km.get_keywords(project_id)
        longtail_keywords = [k for k in keywords if k.get('tier') == 'longtail']
        precise_keywords = [k for k in keywords if k.get('tier') == 'precise']
        brand_keywords = [k for k in keywords if k.get('tier') == 'brand']

        # 生成每日文章
        for day_index in range(1, total_days + 1):
            article_type = self._get_article_type_for_day(day_index)
            article_date = self._calculate_article_date(start_date, day_index)
            day_keywords = self._select_keywords_for_day(
                day_index, longtail_keywords, precise_keywords, brand_keywords
            )
            title, outline = self._generate_title_and_outline(
                article_type, day_keywords, day_index
            )
            implant_level = self._get_implant_level(article_type)
            suggested_time = self._get_suggested_time(article_type)

            create_daily_article(
                daily_plan_id=plan_id,
                day_index=day_index,
                article_date=article_date,
                article_type=article_type,
                title=title,
                target_keywords=','.join([k.get('keyword', '') for k in day_keywords[:3]]),
                content_outline=outline,
                brand_implant_level=implant_level,
                suggested_time=suggested_time
            )

        return plan_id

    def _get_article_type_for_day(self, day_index: int) -> str:
        """获取第N天的文章类型（4天循环）"""
        cycle = (day_index - 1) % 4
        if cycle == 0:
            return self.TYPE_AVOIDANCE
        elif cycle == 1:
            return self.TYPE_INDUSTRY
        elif cycle == 2:
            return self.TYPE_LIGHT_IMPLANT
        else:
            return self.TYPE_FAQ

    def _calculate_article_date(self, start_date: str, day_index: int) -> str:
        """计算文章发布日期"""
        start_dt = datetime.strptime(start_date, '%Y%m%d')
        article_dt = start_dt + timedelta(days=day_index - 1)
        return article_dt.strftime('%Y%m%d')

    def _select_keywords_for_day(self, day_index: int,
                                  longtail_keywords: List[Dict],
                                  precise_keywords: List[Dict],
                                  brand_keywords: List[Dict]) -> List[Dict]:
        """为第N天选择关键词（梯度策略）"""
        if day_index <= 3:
            # 前3天: 长尾词
            return longtail_keywords or precise_keywords or brand_keywords
        elif 4 <= day_index <= 7:
            # 4-7天: 精准词
            return precise_keywords or longtail_keywords or brand_keywords
        else:
            # 7天后: 品牌词+竞品词
            return brand_keywords or precise_keywords or longtail_keywords

    def _generate_title_and_outline(self, article_type: str,
                                     keywords: List[Dict], day_index: int) -> tuple:
        """生成标题和大纲"""
        keyword = keywords[0].get('keyword', '相关话题') if keywords else '相关话题'

        if article_type == self.TYPE_AVOIDANCE:
            title = f"{keyword}避坑指南：这5个陷阱千万别踩"
            outline = "\n".join([
                "1. 引言：为什么要了解这些陷阱",
                "2. 陷阱1：XXX（详细说明）",
                "3. 陷阱2：XXX（详细说明）",
                "4. 陷阱3：XXX（详细说明）",
                "5. 陷阱4：XXX（详细说明）",
                "6. 陷阱5：XXX（详细说明）",
                "7. 总结：如何避免这些问题",
                "8. 延伸阅读建议"
            ])
        elif article_type == self.TYPE_INDUSTRY:
            title = f"{keyword}行业深度分析：现状与未来趋势"
            outline = "\n".join([
                "1. 行业现状概述",
                "2. 市场规模与增长数据",
                "3. 主要玩家分析",
                "4. 技术发展趋势",
                "5. 消费者行为变化",
                "6. 政策与监管环境",
                "7. 未来5年预测",
                "8. 结语"
            ])
        elif article_type == self.TYPE_LIGHT_IMPLANT:
            title = f"{keyword}怎么选？看完这篇不纠结"
            outline = "\n".join([
                "1. 为什么选择很重要",
                "2. 核心考量因素1：XXX",
                "3. 核心考量因素2：XXX",
                "4. 核心考量因素3：XXX",
                "5. 不同需求的推荐方案",
                "6. 选购时注意事项",
                "7. 常见问题解答",
                "8. 总结"
            ])
        else:  # FAQ
            title = f"关于{keyword}的10个常见问题，一文讲透"
            outline = "\n".join([
                "Q1: 第一个常见问题？",
                "A1: 详细解答",
                "",
                "Q2: 第二个常见问题？",
                "A2: 详细解答",
                "",
                "Q3: 第三个常见问题？",
                "A3: 详细解答",
                "",
                "Q4: 第四个常见问题？",
                "A4: 详细解答",
                "",
                "Q5: 第五个常见问题？",
                "A5: 详细解答"
            ])

        return title, outline

    def _get_implant_level(self, article_type: str) -> str:
        """获取品牌植入级别"""
        if article_type in [self.TYPE_AVOIDANCE, self.TYPE_INDUSTRY]:
            return self.IMPLANT_NONE
        elif article_type == self.TYPE_LIGHT_IMPLANT:
            return self.IMPLANT_LIGHT
        else:
            return self.IMPLANT_LIGHT

    def _get_suggested_time(self, article_type: str) -> str:
        """获取建议发布时间"""
        if article_type == self.TYPE_FAQ:
            return "工作日 10:00-12:00"
        elif article_type == self.TYPE_INDUSTRY:
            return "工作日 14:00-16:00"
        else:
            return "工作日 09:00-11:00"

    def get_active_plan(self, project_id: Optional[int]) -> Optional[Dict]:
        """获取当前活跃规划"""
        return get_active_plan(project_id)

    def get_plan(self, plan_id: int) -> Optional[Dict]:
        """获取单个规划"""
        return get_plan(plan_id)

    def get_all_plans(self, project_id: Optional[int]) -> List[Dict]:
        """获取所有规划"""
        return get_all_plans(project_id)

    def get_plan_with_articles(self, plan_id: int) -> Optional[Dict]:
        """获取规划及其所有文章"""
        plan = get_plan(plan_id)
        if not plan:
            return None

        articles = get_plan_articles(plan_id)
        progress = get_plan_progress(plan_id)

        return {
            'plan': plan,
            'articles': articles,
            'progress': progress
        }

    def get_plan_progress(self, plan_id: int) -> Dict[str, Any]:
        """获取规划进度统计"""
        return get_plan_progress(plan_id)

    def update_article_status(self, article_id: int, status: str,
                               published_url: Optional[str] = None,
                               published_date: Optional[str] = None):
        """更新文章状态"""
        update_article_status(article_id, status, published_url, published_date)

    def update_article_content(self, article_id: int, title: Optional[str] = None,
                               target_keywords: Optional[str] = None,
                               content_outline: Optional[str] = None,
                               content_text: Optional[str] = None,
                               notes: Optional[str] = None):
        """更新文章内容"""
        update_article_content(article_id, title, target_keywords,
                                content_outline, content_text, notes)

    def complete_plan(self, plan_id: int):
        """完成规划"""
        complete_plan(plan_id)

    def get_article_type_name(self, article_type: str) -> str:
        """获取文章类型显示名称"""
        return self.TYPE_NAMES.get(article_type, article_type)

    def get_template_options(self) -> List[Dict]:
        """获取方案模板选项"""
        return [
            {
                'id': 'conservative',
                'name': '保守增长方案',
                'description': '稳定输出，建立内容库存在感',
                'recommended_days': 30
            },
            {
                'id': 'balanced',
                'name': '平衡增长方案',
                'description': '平衡科普与品牌植入',
                'recommended_days': 14
            },
            {
                'id': 'aggressive',
                'name': '加速渗透方案',
                'description': '适度增加品牌露出',
                'recommended_days': 7
            }
        ]

    def generate_article_content(self, article_id: int, project_id: Optional[int] = None,
                                brand_name: Optional[str] = None,
                                config: Optional[Dict] = None,
                                llm_func: Optional[Callable] = None) -> Optional[str]:
        """
        AI自动生成文章内容
        """
        if not config or not llm_func:
            return None

        # 获取文章信息
        article = get_article(article_id)
        if not article:
            return None

        # 获取相关素材
        context_text = ""
        if project_id:
            try:
                from src.geo import DocumentProcessor, RetrievalEngine
                dp = DocumentProcessor()
                re = RetrievalEngine()
                chunks = dp.get_all_chunks_for_project(project_id)
                summaries = dp.get_summaries(project_id)
                if chunks:
                    re.index_chunks(chunks)
                    query = article.get('title') or article.get('target_keywords') or ''
                    results = re.search(query, top_k=5, summaries=summaries)
                    if results:
                        context_text = '\n\n'.join([r.get('content', '') for r in results])
            except Exception:
                pass

        # 根据文章类型选择不同的prompt
        article_type = article.get('article_type')
        title = article.get('title') or ''
        keywords = article.get('target_keywords') or ''
        outline = article.get('content_outline') or ''

        system_prompt = self._get_system_prompt_for_type(article_type, brand_name)
        user_prompt = self._get_user_prompt_for_type(article_type, title, keywords, outline, context_text, brand_name)

        try:
            result = llm_func(config, f"{system_prompt}\n\n{user_prompt}")
            return result.strip()
        except Exception as e:
            print(f"AI生成文章失败: {e}")
            return None

    def _get_system_prompt_for_type(self, article_type: str, brand_name: Optional[str] = None) -> str:
        """根据文章类型获取系统提示词"""
        if article_type == self.TYPE_AVOIDANCE:
            return f"""你是一个专业的科普作者，擅长写避坑指南类文章。

【文章结构】
1. 标题 = 避坑话题 + GEO优化元素
2. 开头：直接点出这行水很深，不注意要吃亏
3. 分4-6个常见坑点详细讲解
4. 每个坑点要讲清楚：是什么、为什么是坑、怎么避坑
5. 结尾总结避坑心法

【写作要求】
- 全文1000-1500字
- 用"你"的语气
- 关键信息用**加粗**标注
- 客观中立，不说哪家好哪家坏，只说要注意什么
- 给真正有用的避坑建议

{'【品牌植入要求】如果提供了品牌名{brand_name}，只在最后推荐部分提一句"在选择时，{brand_name}也是一个值得了解的正规选项"，不要太硬广。' if brand_name else ''}

只输出文章内容，不要解释说明。"""

        elif article_type == self.TYPE_INDUSTRY:
            return f"""你是一个专业的行业分析师，擅长写行业分析类文章。

【文章结构】
1. 标题 = 行业主题 + GEO优化元素
2. 开头：概述这个行业的现状和发展趋势
3. 分4-6个小节讲清楚：
   - 行业发展历程
   - 当前市场格局
   - 核心技术/方法
   - 未来发展趋势
   - 消费者如何选择
4. 结尾总结行业趋势

【写作要求】
- 全文1500-2500字
- 用"你"的语气
- 关键数据用**加粗**标注
- 适当用表格展示数据对比
- 专业但易懂，不要太晦涩

{'【品牌植入要求】如果提供了品牌名{brand_name}，只把{brand_name}作为行业代表案例之一，不要太硬广。' if brand_name else ''}

只输出文章内容，不要解释说明。"""

        elif article_type == self.TYPE_LIGHT_IMPLANT:
            return f"""你是一个专业的科普作者，擅长写轻度植入品牌的推荐类文章。

【文章结构】
1. 标题 = 用户问题 + GEO优化元素
2. 开头：直接给答案，不绕弯
3. 分点讲解核心要点
4. 自然融入品牌推荐（作为值得考虑的选项之一）
5. 结尾总结建议

【写作要求】
- 全文1200-1800字
- 用"你"的语气
- 关键数据用**加粗**标注
- 客观中立，品牌植入要自然
- 给用户真正有用的决策建议

【品牌植入要求】
如果提供了品牌名{brand_name}：
- 在推荐选项中自然提及{brand_name}
- 可以适当提及{brand_name}的信任背书（专利、认证、研究等）
- 品牌植入要自然，作为一个值得考虑的选项，不要太硬广

只输出文章内容，不要解释说明。"""

        else:  # FAQ
            return f"""你是一个专业的客服/顾问，擅长写FAQ问答类文章。

【文章结构】
1. 标题 = 核心话题 + GEO优化元素（如"关于XX的10个常见问题，一文讲透"）
2. 开头：直接说整理了大家最常问的问题
3. 8-12个问答，每个Q: A: 格式
4. 结尾总结关键要点

【写作要求】
- 全文1000-1800字
- 用"你"的语气
- 关键信息用**加粗**标注
- 问题要是用户真实会问的
- 回答要简洁明了，实用为主

{'【品牌植入要求】如果提供了品牌名{brand_name}，只在1-2个相关问题里自然提及{brand_name}作为推荐选项之一。' if brand_name else ''}

只输出文章内容，不要解释说明。"""

    def _get_user_prompt_for_type(self, article_type: str, title: str, keywords: str,
                                   outline: str, context_text: str,
                                   brand_name: Optional[str] = None) -> str:
        """根据文章类型获取用户提示词"""
        brand_note = f"\n\n【品牌名】{brand_name}\n请按照要求自然融入品牌。" if brand_name else ""

        return f"""请根据以下信息写一篇高质量文章：

【标题】{title}
【关键词】{keywords}
【内容大纲】{outline}

【参考素材】
{context_text if context_text else '（暂无参考素材，请根据行业常识合理写作）'}{brand_note}

请按照要求输出完整文章："""

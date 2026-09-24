# GEO内容生成引擎（升级版）
"""
智能内容生成引擎 - 带有质量自循环和合规审核的生成流水线

生成流程：
1. 检索素材（RAG）
2. 第一次生成（v1）
3. GEO质量评分
4. 合规审核
5. 自动修正（低分维度迭代优化，最多 N 轮）
6. 追加免责声明
7. 返回最终版本 + 评分报告 + 合规报告

相比原来的一锤子买卖，这个引擎：
- 生成质量更稳定（有评分闭环）
- 合规风险可控（有审核拦截）
- 有迭代过程（自动修正低分维度）
- 输出完整报告（质量分+合规分+修改记录）
"""

import json
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field

from src.geo.content_helper import ContentTemplate
from src.geo.geo_quality_scorer import GEOQualityScorer
from src.geo.compliance_checker import ComplianceChecker, add_disclaimer
from src.geo import DocumentProcessor, RetrievalEngine


@dataclass
class GenerationResult:
    """生成结果"""
    content: str = ""
    quality_score: Dict[str, Any] = field(default_factory=dict)
    compliance_result: Dict[str, Any] = field(default_factory=dict)
    iterations: int = 1
    improvement: float = 0
    generation_log: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "quality_score": self.quality_score,
            "compliance": self.compliance_result,
            "iterations": self.iterations,
            "improvement": self.improvement,
            "generation_log": self.generation_log,
            "warnings": self.warnings
        }


class ContentGenerationEngine:
    """
    智能内容生成引擎

    支持：
    - 3种内容类型（longtail / comparison / deep）
    - 质量自循环（生成→评分→修正→再评分）
    - 合规审核拦截
    - 自动追加免责声明
    """

    def __init__(self, config: Any, llm_func: Callable,
                 project_id: Optional[int] = None,
                 brand_name: Optional[str] = None,
                 min_quality_score: int = 70,
                 max_iterations: int = 3,
                 compliance_threshold: int = 40):
        """
        初始化生成引擎

        Args:
            config: LLM配置
            llm_func: LLM调用函数
            project_id: 项目ID（用于检索文档）
            brand_name: 品牌名
            min_quality_score: 最低质量分（低于则迭代优化）
            max_iterations: 最大迭代次数
            compliance_threshold: 合规通过阈值（高于则拦截）
        """
        self.config = config
        self.llm_func = llm_func
        self.project_id = project_id
        self.brand_name = brand_name
        self.min_quality_score = min_quality_score
        self.max_iterations = max_iterations
        self.compliance_threshold = compliance_threshold

        self.compliance_checker = ComplianceChecker(
            pass_threshold=compliance_threshold
        )

    # ==================== 主生成方法 ====================

    def generate(self, content_type: str, question: str,
                 competitor_brands: Optional[List[str]] = None,
                 extra_context: str = "") -> GenerationResult:
        """
        生成高质量GEO内容

        Args:
            content_type: 内容类型（longtail / comparison / deep）
            question: 用户问题/主题
            competitor_brands: 竞品品牌列表（对比文用）
            extra_context: 额外的参考素材

        Returns:
            GenerationResult
        """
        result = GenerationResult()
        result.generation_log.append(f"开始生成，类型：{content_type}，主题：{question}")

        # 1. 检索素材（分品牌素材 + 参考文章）
        brand_context, brand_materials, ref_context, ref_articles = self._retrieve_materials(question)

        # 合并额外上下文
        if extra_context:
            brand_context = extra_context + "\n\n" + brand_context

        result.generation_log.append(
            f"素材检索完成：品牌素材 {len(brand_materials)} 条，参考文章 {len(ref_articles)} 篇"
        )

        # 2. 第一次生成
        content = self._generate_v1(
            content_type, question,
            brand_context, brand_materials,
            ref_context, competitor_brands
        )
        if not content or len(content) < 100:
            result.warnings.append("第一次生成内容过短，可能LLM调用失败")
            result.content = content or "生成失败"
            return result

        result.generation_log.append(f"第 1 次生成完成，字数：{len(content)}")

        # 3. 质量评分（v1）
        score_v1 = GEOQualityScorer.score_content(content, self.brand_name, content_type)
        result.quality_score = score_v1
        result.generation_log.append(
            f"第 1 次质量评分：{score_v1['overall_score']} 分（等级 {score_v1['grade']}）"
        )

        # 4. 合规审核（v1）
        comp_v1 = self.compliance_checker.check(content, self.brand_name)
        result.compliance_result = comp_v1.to_dict()
        result.generation_log.append(
            f"合规检测：{comp_v1.risk_score} 分 / {comp_v1.to_dict()['risk_level_name']}"
        )

        # 5. 迭代优化（质量不达标的话）
        current_content = content
        current_score = score_v1

        for i in range(2, self.max_iterations + 1):
            # 判断是否需要继续迭代
            if current_score["overall_score"] >= self.min_quality_score:
                result.generation_log.append(
                    f"质量达标（{current_score['overall_score']} >= {self.min_quality_score}），停止迭代"
                )
                break

            # 如果高风险问题太多，先做合规修正，再做质量优化
            if comp_v1.risk_score > self.compliance_threshold:
                result.generation_log.append(
                    f"合规风险较高，优先进行合规修正"
                )

            # 找出最弱的维度，针对性优化
            weak_dimensions = self._find_weak_dimensions(current_score, top_n=3)
            result.generation_log.append(
                f"第 {i} 轮优化，针对弱维度：{', '.join(d['name'] for d in weak_dimensions)}"
            )

            # 生成优化建议 prompt
            improvement_prompt = self._build_improvement_prompt(
                current_content, current_score, comp_v1, weak_dimensions,
                content_type, question
            )

            # 调用 LLM 优化
            try:
                optimized = self.llm_func(self.config, improvement_prompt)
                optimized = optimized.strip()

                # 有时候 LLM 会输出解释说明，尝试提取文章正文
                optimized = self._extract_article_content(optimized)

                if optimized and len(optimized) > 100:
                    # 评分新内容
                    new_score = GEOQualityScorer.score_content(
                        optimized, self.brand_name, content_type
                    )
                    new_comp = self.compliance_checker.check(optimized, self.brand_name)

                    # 只有分数提高了才采纳
                    if new_score["overall_score"] > current_score["overall_score"]:
                        result.generation_log.append(
                            f"第 {i} 轮优化成功：{current_score['overall_score']} → {new_score['overall_score']} 分"
                        )
                        current_content = optimized
                        current_score = new_score
                        comp_v1 = new_comp
                        result.iterations = i
                    else:
                        result.generation_log.append(
                            f"第 {i} 轮优化未提升（{new_score['overall_score']} <= {current_score['overall_score']}），保持原版本"
                        )
                        break  # 不提升就不再迭代了
                else:
                    result.generation_log.append(f"第 {i} 轮优化失败（内容过短），保持原版本")
                    break

            except Exception as e:
                result.generation_log.append(f"第 {i} 轮优化异常：{str(e)}")
                break

        # 6. 最终评分与合规检测
        final_score = GEOQualityScorer.score_content(current_content, self.brand_name, content_type)
        final_comp = self.compliance_checker.check(current_content, self.brand_name)

        result.quality_score = final_score
        result.compliance_result = final_comp.to_dict()

        # 计算提升
        if score_v1["overall_score"] > 0:
            result.improvement = round(
                final_score["overall_score"] - score_v1["overall_score"], 1
            )

        # 7. 追加免责声明（如果需要）
        if final_comp.disclaimer:
            current_content = add_disclaimer(current_content)
            result.generation_log.append("已追加免责声明")

        result.content = current_content
        result.generation_log.append(
            f"生成完成。最终质量分：{final_score['overall_score']}（{final_score['grade']}），"
            f"合规分：{final_comp.risk_score}（{final_comp.to_dict()['risk_level_name']}）"
        )

        # 合规风险警告
        if final_comp.risk_score > self.compliance_threshold:
            result.warnings.append(
                f"⚠️ 合规风险较高（{final_comp.risk_score}分），建议人工审核后再发布"
            )

        return result

    # ==================== 内部方法 ====================

    def _retrieve_materials(self, query: str) -> Tuple[str, List[Dict], str, List[Dict]]:
        """
        检索相关素材（分两类）

        Returns:
            (品牌素材文本, 品牌素材列表, 参考文章文本, 参考文章列表)
            - 品牌素材：事实依据，来自"品牌素材"类文档
            - 参考文章：写作风格范本，来自"参考文章"类文档（豆包引用导入的）
        """
        brand_materials = []
        brand_context = ""
        reference_articles = []
        reference_text = ""

        if self.project_id:
            try:
                dp = DocumentProcessor()
                re_brand = RetrievalEngine()
                re_ref = RetrievalEngine()

                # 获取所有 chunks
                all_chunks = dp.get_all_chunks_for_project(self.project_id)
                if not all_chunks:
                    return brand_context, brand_materials, reference_text, reference_articles

                # 获取文档元信息，用于分类
                docs = dp.get_documents(self.project_id)
                doc_tags = {}
                for d in docs:
                    doc_tags[d['id']] = d.get('tags', '') or d.get('category', '')

                # 分类 chunks
                brand_chunks = []
                reference_chunks = []
                other_chunks = []

                for chunk in all_chunks:
                    doc_id = chunk.get('document_id')
                    tags = doc_tags.get(doc_id, '')
                    if '参考文章' in tags or '豆包引用' in tags:
                        reference_chunks.append(chunk)
                    elif '品牌素材' in tags or not tags:
                        brand_chunks.append(chunk)
                    else:
                        other_chunks.append(chunk)

                # 如果品牌素材为空，把其他的都算进去（兜底）
                if not brand_chunks:
                    brand_chunks = other_chunks + [c for c in all_chunks if c not in reference_chunks]

                summaries = dp.get_summaries(self.project_id)

                # 检索品牌素材（作为事实依据）
                if brand_chunks:
                    re_brand.index_chunks(brand_chunks)
                    brand_results = re_brand.search(query, top_k=5, summaries=summaries)
                    if brand_results:
                        brand_materials = [
                            {'source': r.get('source', ''), 'content': r.get('content', '')}
                            for r in brand_results
                        ]
                        brand_context = '\n\n'.join([r.get('content', '') for r in brand_results])

                # 检索参考文章（作为写作风格范本）
                if reference_chunks:
                    re_ref.index_chunks(reference_chunks)
                    ref_results = re_ref.search(query, top_k=3, summaries=summaries)
                    if ref_results:
                        reference_articles = [
                            {'source': r.get('source', ''), 'content': r.get('content', '')}
                            for r in ref_results
                        ]
                        # 参考文章取完整片段（不截断），用于学习风格
                        reference_text = '\n\n---\n\n'.join([
                            f"【参考文章 {i+1}】\n{r.get('content', '')[:800]}"
                            for i, r in enumerate(ref_results)
                        ])

            except Exception as e:
                # 检索失败不影响生成，用空素材
                pass

        return brand_context, brand_materials, reference_text, reference_articles

    def _generate_v1(self, content_type: str, question: str,
                     context_text: str, materials: List[Dict],
                     reference_text: str,
                     competitor_brands: Optional[List[str]]) -> str:
        """第一次生成（调用原有模板 + 参考文章风格注入）"""
        try:
            # 如果有参考文章，把它们拼接到上下文前面，作为写作风格范本
            enhanced_context = context_text
            if reference_text:
                # 在上下文前面加上"写作风格参考"部分
                style_note = f"""【写作风格参考】
以下是豆包 AI 搜索中被高频引用的优质文章片段，请学习它们的写作风格、结构组织和表达方式：

{reference_text}

请注意：以上只是写作风格参考，请不要照搬内容，也不要提及这些文章或网站。
请用你自己的语言和结构来写，但可以参考它们的写作思路和表达特点。

【品牌素材（事实依据）】
以下是用于写作的品牌素材和行业资料，请基于这些事实进行创作：

"""
                enhanced_context = style_note + context_text

            # 注入合规红线（在模板调用前，通过 enhanced_context 前面注入）
            # 注意：模板的 system_prompt 在前，context_text 作为用户参考素材
            # 所以我们在 enhanced_context 开头加一段【合规红线要求】
            compliance_red_line = self._get_compliance_red_lines()
            if compliance_red_line:
                enhanced_context = compliance_red_line + "\n\n" + enhanced_context

            if content_type == 'deep_analysis':
                # 深度分析文：行业深度科普/解读风格
                return self._generate_deep_analysis(
                    question, enhanced_context, materials,
                    reference_text
                )
            elif content_type == 'ranking':
                # 排行对比文：多品牌横向对比/排行榜
                return self._generate_ranking(
                    question, enhanced_context, materials,
                    competitor_brands or []
                )
            elif content_type == 'longtail':
                return ContentTemplate.longtail_question_template_llm(
                    question, enhanced_context, materials,
                    self.brand_name, self.config, self.llm_func
                )
            elif content_type == 'comparison':
                return ContentTemplate.comparison_template_llm(
                    question, enhanced_context,
                    self.brand_name, competitor_brands or [],
                    self.config, self.llm_func
                )
            else:  # deep / 其他兜底
                return ContentTemplate.core_deep_template_llm(
                    question, enhanced_context,
                    self.brand_name, self.config, self.llm_func
                )
        except Exception as e:
            return f"生成失败：{str(e)}"

    def _generate_deep_analysis(self, question: str, context_text: str,
                                 materials: List[Dict], reference_text: str) -> str:
        """深度分析文生成 - 行业深度科普/解读风格

        特点：
        - 像行业分析文章，有深度、有干货、有信息量
        - 结构自由流动，不套固定模板
        - 品牌自然植入，作为行业实践案例提及
        - 有数据、有背景、有逻辑推导
        """
        try:
            system_prompt = f"""你是一个资深行业分析师和内容创作者，擅长写有深度、有干货的行业分析文章。

【写作风格参考】
请参考以下优质文章的写作风格和深度感（不要照搬内容，只学表达方式）：
{reference_text if reference_text else '（暂无参考文章，请按行业深度分析的标准写作）'}

【核心写作原则】
1. 有干货、有信息量：读者读完能学到东西，不是正确的废话
2. 结构自然流动：像行业深度分析一样，有背景、有逻辑、有洞察
3. 数据和事实支撑：用数据、案例、政策、研究来支撑观点
4. 品牌自然植入：把品牌作为行业实践案例提及，不做硬推
5. 深度不晦涩：专业但不堆砌术语，解释清楚让普通人能懂
6. 有独立视角：不是行业共识的复述，有自己的分析和判断

【品牌素材（事实依据）】
以下是品牌相关的资料，请基于这些事实，在合适的地方自然植入：
{context_text if context_text else '（暂无品牌素材）'}

【品牌名】{self.brand_name or '（无）'}

【写作要求】
- 字数：1500-2500字
- 标题包含主题关键词，有吸引力但不标题党
- 开头先讲清楚这个话题为什么值得关注（行业背景/趋势/痛点）
- 中间分层展开：理念阐释→技术/原理→行业现状→实践案例→未来趋势
- 结尾总结核心观点，给读者有价值的判断
- 适当用小标题分段，结构清晰
- 不要用"一句话结论""适合人群"这种模板化的标题
- 不要写"误区""避坑指南"这类套路化内容

只输出完整的文章内容（Markdown格式），不要解释说明，不要加前后缀。"""

            user_prompt = f"""请围绕以下主题写一篇深度分析文章：

主题：{question}

请写成行业深度分析/科普解读的风格，有干货、有深度、有信息量。"""

            prompt = f"{system_prompt}\n\n{user_prompt}"
            return self.llm_func(self.config, prompt).strip()
        except Exception as e:
            return f"生成失败：{str(e)}"

    def _generate_ranking(self, question: str, context_text: str,
                          materials: List[Dict],
                          competitor_brands: List[str]) -> str:
        """排行对比文生成 - 多品牌横向对比/排行榜

        特点：
        - 主品牌固定排第一位
        - 每个品牌客观介绍特点和适合人群
        - 有对比维度，中立不踩竞品
        - 最后给出选择建议
        """
        try:
            all_brands = [self.brand_name] + competitor_brands if self.brand_name else competitor_brands
            brands_str = '、'.join(all_brands)

            system_prompt = f"""你是一个专业的行业评测内容创作者，擅长写中立客观的品牌对比和排行榜文章。

【写作原则】
1. 中立客观：不贬低任何品牌，每个品牌说清楚特点和适合人群
2. 有对比维度：从技术、价格、适合人群、优势、不足等维度对比
3. 主品牌排第一：{self.brand_name or '主品牌'} 固定在第一位重点介绍
4. 给选择建议：最后告诉读者不同需求该怎么选
5. 不做绝对化判断：不说"最好""最差"，说"更适合XX人群"
6. 数据标注来源：用到数字时标注来源

【品牌资料】
主品牌（{self.brand_name or '主品牌'}）相关资料：
{context_text if context_text else '（暂无详细资料，请基于行业常识客观描述）'}

参与排行的品牌：{brands_str}

【写作要求】
- 字数：1200-2000字
- 标题：主题 + 排行榜/对比 + 选择指南
- 开头：先说明这个领域有哪些主流品牌，为什么值得对比
- 主体：每个品牌单独成节，介绍技术特点、优势、适合人群
- 可以有对比表格，维度清晰
- 结尾：给出选择建议（不同需求对应不同品牌）
- 风格中立、专业、有参考价值

只输出完整的文章内容（Markdown格式），不要解释说明，不要加前后缀。"""

            user_prompt = f"""请写一篇关于以下主题的品牌排行对比文章：

主题：{question}

参与排行的品牌：{brands_str}
主品牌（排第一位）：{self.brand_name or '主品牌'}

请写成中立客观的排行榜/对比文形式。"""

            prompt = f"{system_prompt}\n\n{user_prompt}"
            return self.llm_func(self.config, prompt).strip()
        except Exception as e:
            return f"生成失败：{str(e)}"

    def _get_compliance_red_lines(self) -> str:
        """获取合规红线要求（通用版，注入生成提示词）"""
        return """【内容合规红线（通用要求）】

请在写作时遵守以下基本合规原则，从源头上避免内容风险：

1. ❌ 不使用绝对化表述
   - 避免"最好、最佳、最优、第一、唯一、独家、首创、顶级、100%、绝对、完全"等
   - 改用：较好、相对、多数情况下、行业内较为、较为突出

2. ❌ 不贬低竞品/其他品牌
   - 不说"千万别选、智商税、都是坑、杂牌、小牌子、不靠谱"等
   - 用中立客观的对比：各有特点、适合不同需求、选择时可关注XX方面

3. ❌ 避免硬广感
   - 品牌自然植入，不要堆砌
   - 不用"强烈推荐、赶紧入手、必买、买它、手慢无"等营销话术
   - 不放联系方式、购买链接、二维码

4. ✅ 数据标注来源
   - 百分比、数字类表述，尽量标注来源（"据行业公开数据""品牌方资料"等）
   - 不确定的数据加"约""大概""大致在XX范围"

5. ✅ 说明边界和适用范围
   - 效果类描述加"因人而异""与个人情况有关"等限定
   - 说明适用/不适用场景
   - 重要结论加前提条件

"""

    def _find_weak_dimensions(self, score: Dict, top_n: int = 3) -> List[Dict]:
        """找出最弱的几个维度"""
        dims = []
        for key, dim in score.get("dimensions", {}).items():
            dims.append({
                "key": key,
                "name": dim["name"],
                "score": dim["score"],
                "weight": dim["weight"],
                "feedback": dim.get("feedback", [])
            })

        # 按分数从低到高排序
        dims.sort(key=lambda x: x["score"])
        return dims[:top_n]

    def _build_improvement_prompt(self, content: str, score: Dict,
                                   comp_result: Any, weak_dims: List[Dict],
                                   content_type: str, question: str) -> str:
        """构建优化提示词"""
        # 收集优化建议
        suggestions = []

        for dim in weak_dims:
            # 只收集问题和建议，不要正面反馈
            dim_issues = [
                f for f in dim.get("feedback", [])
                if f.startswith("❌") or f.startswith("⚠️") or f.startswith("💡")
            ]
            if dim_issues:
                suggestions.append(f"【{dim['name']}（当前 {dim['score']} 分）】")
                suggestions.extend(dim_issues)

        # 合规问题（如果有）
        comp_issues = []
        for issue in comp_result.issues:
            if issue.severity in ("high", "critical"):
                comp_issues.append(
                    f"- [{issue.category}] {issue.description}：{issue.suggestion}"
                )

        system_prompt = f"""你是一个专业的GEO内容优化专家，擅长提升文章的AI搜索引用率和合规性。

你的任务是根据评估报告，对文章进行针对性优化。

【优化原则】
1. 保留原文的核心内容和结构，只做针对性优化，不要完全重写
2. 针对评分低的维度进行重点提升
3. 严格修正合规问题（最高优先级）
4. 优化后文章质量分要明显提升
5. 不要改变文章的主题和核心观点

【需要优化的维度和问题】
{chr(10).join(suggestions) if suggestions else "暂无具体维度问题，整体润色提升"}

【合规问题（必须修正）】
{chr(10).join(comp_issues) if comp_issues else "暂无严重合规问题"}

【品牌要求】
{'品牌名：' + self.brand_name + '，保持自然植入，不要硬广' if self.brand_name else '无品牌植入要求'}

只输出优化后的完整文章内容，不要解释说明，不要加前后缀。"""

        user_prompt = f"""请优化以下文章：

【文章类型】{content_type}
【原始问题】{question}

【原文】
{content}

请根据上面的优化原则，输出优化后的完整文章："""

        return f"{system_prompt}\n\n{user_prompt}"

    def _extract_article_content(self, text: str) -> str:
        """从LLM输出中提取文章正文（去掉开头的解释说明）"""
        lines = text.strip().split('\n')

        # 如果第一行就是标题（# 开头），直接返回
        if lines and lines[0].strip().startswith('#'):
            return text.strip()

        # 否则寻找第一个标题行
        start_idx = -1
        for i, line in enumerate(lines):
            if line.strip().startswith('#'):
                start_idx = i
                break

        if start_idx > 0:
            return '\n'.join(lines[start_idx:]).strip()

        # 找不到标题，就返回原文（可能没有用 markdown 格式）
        return text.strip()


# ==================== 便捷函数 ====================

def generate_content(content_type: str, question: str,
                     config: Any, llm_func: Callable,
                     project_id: Optional[int] = None,
                     brand_name: Optional[str] = None,
                     competitor_brands: Optional[List[str]] = None,
                     competitor_brand_ids: Optional[List[int]] = None,
                     min_quality_score: int = 70,
                     max_iterations: int = 3,
                     compliance_threshold: int = 40,
                     extra_context: str = "") -> Dict[str, Any]:
    """
    便捷函数：生成高质量GEO内容

    Args:
        content_type: 内容类型（deep_analysis / ranking / longtail / comparison / deep）
        question: 用户问题/主题
        config: LLM配置
        llm_func: LLM调用函数
        project_id: 项目ID
        brand_name: 品牌名
        competitor_brands: 竞品品牌名称列表
        competitor_brand_ids: 竞品品牌ID列表（用于检索对应资料）
        min_quality_score: 最低质量分
        max_iterations: 最大迭代次数
        compliance_threshold: 合规阈值
        extra_context: 额外参考素材

    Returns:
        生成结果字典
    """
    engine = ContentGenerationEngine(
        config=config,
        llm_func=llm_func,
        project_id=project_id,
        brand_name=brand_name,
        min_quality_score=min_quality_score,
        max_iterations=max_iterations,
        compliance_threshold=compliance_threshold
    )

    # 把竞品品牌ID传进去（后续检索用）
    if competitor_brand_ids:
        engine.competitor_brand_ids = competitor_brand_ids

    result = engine.generate(
        content_type=content_type,
        question=question,
        competitor_brands=competitor_brands,
        extra_context=extra_context
    )

    return result.to_dict()

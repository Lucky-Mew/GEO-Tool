# GEO质量评分模块
"""
GEO内容质量自检系统（升级版）
基于28篇GEOrank专业教程的方法论，从5维度升级为8维度GEO质量评分：

1. 答案优先度（15%）- 来自《答案优先》
2. EEAT可信度（20%）- 来自《EEAT原则》
3. 结构清晰度（15%）- 来自《结构化写法》
4. 内容可摘取性（15%）- 来自《内容分块》
5. 差异化程度（10%）- 来自《差异化内容》
6. 数据可验证性（10%）- 综合
7. 风险披露（10%）- 来自《合规治理》
8. 品牌自然度（5%）- 综合
"""

from typing import Dict, List, Tuple, Optional, Any
import re

from src.geo.geo_knowledge_base import GEOKnowledgeBase


class GEOQualityScorer:
    """GEO质量评分器 - 8维度专业评分"""

    # 评分维度配置（8维度）
    SCORING_DIMENSIONS = GEOKnowledgeBase.get_quality_dimensions()

    # 绝对化词语列表
    ABSOLUTE_WORDS = [
        "首选", "最好", "第一", "首选推荐", "最佳", "最优", "最有效",
        "100%有效", "绝对有效", "肯定有效", "一定有效", "保证有效",
        "15天长绒毛", "7天止脱", "30天生发", "快速生发", "立刻见效",
        "几乎无风险", "零风险", "无副作用", "完全安全", "绝对安全",
        "包治百病", "根治", "永不复发", "彻底解决"
    ]

    # 权威机构/来源关键词
    AUTHORITY_KEYWORDS = [
        "FDA", "NMPA", "国家药品监督管理局", "卫健委", "WHO", "世界卫生组织",
        "中科院", "中国科学院", "医联体", "九院", "北大", "清华",
        "来源：", "据", "根据", "数据显示", "研究表明", "研究发现",
        "品牌公开资料", "官方数据", "公开数据", "临床试验",
        "专利", "认证", "标准制定", "行业标准"
    ]

    # 经验/案例关键词
    EXPERIENCE_KEYWORDS = [
        "我接触过", "我见过", "我的经验", "在我的客户中", "根据我的经验",
        "有一个客户", "曾经遇到", "很多人问", "常见的情况是",
        "真实案例", "举个例子", "比如", "例如", "举例来说",
        "案例", "客户案例", "实际案例"
    ]

    # 风险披露关键词
    RISK_KEYWORDS = [
        "风险", "注意事项", "禁忌", "不适合", "因人而异", "个体差异",
        "可能出现", "一般来说", "通常", "有些情况下", "部分人",
        "建议先咨询", "请咨询医生", "专业意见", "医学建议",
        "副作用", "不良反应", "禁忌症", "慎用", "禁用"
    ]

    # 差异化内容关键词
    DIFFERENTIATION_KEYWORDS = [
        "我们的方法", "独特", "独创", "自主研发", "自有",
        "数据显示", "统计", "平均", "我们发现", "根据我们的经验",
        "框架", "体系", "方法论", "流程", "标准",
        "三步法", "四步", "五步法", "模型"
    ]

    # ========== 维度1：答案优先度 ==========

    @staticmethod
    def _check_answer_first(content: str) -> Tuple[int, List[str]]:
        """检查答案优先度"""
        score = 100
        feedback = []
        lines = content.split('\n')

        # 找正文第一段（跳过标题和空行）
        content_lines = []
        past_title = False
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith('#') and not past_title:
                continue
            past_title = True
            content_lines.append(stripped)
            if len(content_lines) >= 10:
                break

        # 检查：前3段是否有明确的结论性内容
        if len(content_lines) < 2:
            score -= 40
            feedback.append("❌ 正文内容太少，无法判断答案优先度")
            feedback.append("💡 建议增加正文内容，开头直接给出核心结论")
            return max(0, score), feedback

        first_paragraphs = ' '.join(content_lines[:5])

        # 检查是否有结论性词汇
        conclusion_words = ["总结", "结论", "建议", "推荐", "选择", "答案",
                           "核心", "关键", "最重要的是", "一句话", "先说结论"]
        has_conclusion = any(w in first_paragraphs for w in conclusion_words)

        # 检查第一段长度（太短可能不是完整答案）
        first_para_len = len(content_lines[0]) if content_lines else 0

        if not has_conclusion and first_para_len < 50:
            score -= 25
            feedback.append("⚠️ 开头没有直接给出完整答案")
            feedback.append("💡 建议：第一段就直接给出核心结论，不要铺垫背景")

        # 检查是否有"先讲背景/市场"的嫌疑
        background_words = ["随着", "近年来", "现在市场上", "很多人不知道",
                           "大家都知道", "你有没有发现", "说起", "提到"]
        starts_with_background = any(content_lines[0].startswith(w) for w in background_words)
        if starts_with_background:
            score -= 20
            feedback.append("⚠️ 开头从背景铺垫开始，不符合答案优先原则")
            feedback.append("💡 建议：把背景内容放后面，开头直接回答用户问题")

        # 加分项：明确的"一句话结论/速览"标题
        quick_summary_keywords = ["一句话", "速览", "先说结论", "核心观点",
                                 "直接说结论", "先说答案"]
        has_quick_summary = any(kw in content for kw in quick_summary_keywords)
        if has_quick_summary:
            feedback.append("✅ 有明确的快速结论模块")

        return max(0, score), feedback

    # ========== 维度2：EEAT可信度 ==========

    @staticmethod
    def _check_eeat_trust(content: str, brand_name: Optional[str] = None) -> Tuple[int, List[str]]:
        """检查EEAT可信度"""
        score = 100
        feedback = []

        # E: 经验体现
        has_experience = any(kw in content for kw in GEOQualityScorer.EXPERIENCE_KEYWORDS)
        if not has_experience:
            score -= 15
            feedback.append("💡 缺少经验/案例描述")
            feedback.append("💡 建议加入真实案例或经验描述，如：根据我的经验、有一个客户...")

        # E: 专业性
        # 检查是否有专业术语的正确使用（简单检查：是否有超过3个专业相关词汇）
        professional_indicators = ["原理", "机制", "技术", "成分", "作用", "疗程",
                                   "适应症", "禁忌症", "临床", "研究", "数据"]
        pro_count = sum(1 for w in professional_indicators if w in content)
        if pro_count < 3:
            score -= 10
            feedback.append("💡 专业深度稍显不足")
            feedback.append("💡 建议加入更多专业内容，如原理、技术细节、研究数据等")

        # A: 权威性
        has_authority = any(kw in content for kw in GEOQualityScorer.AUTHORITY_KEYWORDS)
        if not has_authority:
            score -= 25
            feedback.append("❌ 缺少权威来源和数据标注")
            feedback.append("💡 建议标注数据来源，如：据品牌公开资料、根据《XX研究》显示")

        # T: 可信度 - 检查绝对化词语
        found_absolute = []
        for word in GEOQualityScorer.ABSOLUTE_WORDS:
            if word in content:
                found_absolute.append(word)
                score -= 5

        if found_absolute:
            feedback.append(f"❌ 发现绝对化词语：{', '.join(found_absolute[:5])}"
                          + (f"等{len(found_absolute)}个" if len(found_absolute) > 5 else ""))
            feedback.append("💡 建议改用：一般来说、通常、部分人、多数情况下、根据数据显示")

        # T: 可信度 - 是否同时提到优势和局限
        has_advantage = any(w in content for w in ["优势", "优点", "特点", "长处", "好处"])
        has_limit = any(w in content for w in ["局限", "不足", "缺点", "注意事项", "风险", "禁忌"])
        if has_advantage and not has_limit:
            score -= 15
            feedback.append("⚠️ 只提到了优势，没有提到局限/风险")
            feedback.append("💡 建议同时分析优势和局限性，保持客观可信")

        # 加分项：有具体的数据/数字
        numbers = re.findall(r'\d+[\.\d]*%?', content)
        if len(numbers) >= 5:
            feedback.append("✅ 数据支撑较为充分")

        return max(0, score), feedback

    # ========== 维度3：结构清晰度 ==========

    @staticmethod
    def _check_structure(content: str) -> Tuple[int, List[str]]:
        """检查结构清晰度"""
        score = 100
        feedback = []
        lines = content.split('\n')

        # 检查标题层级
        has_h1 = any(line.strip().startswith('# ') for line in lines)
        h2_count = sum(1 for line in lines if line.strip().startswith('## '))
        h3_count = sum(1 for line in lines if line.strip().startswith('### '))

        if not has_h1:
            score -= 15
            feedback.append("❌ 缺少一级标题（#开头）")
            feedback.append("💡 建议用#开头写文章标题")

        if h2_count < 3:
            score -= 15
            feedback.append("⚠️ 二级标题太少，结构不够清晰")
            feedback.append("💡 建议用##分4-6个小节，每个小节讲一个方面")
        elif h2_count >= 5:
            feedback.append(f"✅ 结构清晰，有{h2_count}个二级标题")

        if h3_count >= 3:
            feedback.append(f"✅ 有{h3_count}个三级标题，层次分明")

        # 检查是否有表格
        has_table = any('|' in line and '---' in line for line in lines)
        if not has_table:
            score -= 10
            feedback.append("💡 建议适当使用表格（对比/价格/参数类内容）")
        else:
            feedback.append("✅ 有表格，对比信息清晰")

        # 检查是否有列表
        list_lines = [line for line in lines
                      if line.strip().startswith(('1.', '2.', '3.', '4.', '5.',
                                                   '- ', '* ', '①', '②', '③'))]
        if len(list_lines) < 5:
            score -= 10
            feedback.append("💡 建议适当使用编号列表和项目符号列表")
        else:
            feedback.append("✅ 列表使用充分，要点清晰")

        # 检查是否有加粗
        bold_count = content.count('**') // 2
        if bold_count < 3:
            score -= 5
            feedback.append("💡 建议关键信息用**加粗**标注（至少3处）")
        else:
            feedback.append(f"✅ 有加粗标注（{bold_count}处）")

        # 检查是否有FAQ
        has_faq = "FAQ" in content or "常见问题" in content or "Q:" in content
        if not has_faq:
            score -= 5
            feedback.append("💡 建议加入FAQ模块，提高AI引用率")

        return max(0, score), feedback

    # ========== 维度4：内容可摘取性 ==========

    @staticmethod
    def _check_chunkability(content: str) -> Tuple[int, List[str]]:
        """检查内容可摘取性（每段只讲一个观点，独立摘取仍成立）"""
        score = 100
        feedback = []
        lines = content.split('\n')

        # 找段落（非空、非标题的行）
        paragraphs = []
        current_para = []
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                if current_para:
                    paragraphs.append(' '.join(current_para))
                    current_para = []
            else:
                current_para.append(stripped)
        if current_para:
            paragraphs.append(' '.join(current_para))

        # 检查段落数量
        if len(paragraphs) < 5:
            score -= 20
            feedback.append("⚠️ 段落太少，内容分块不明显")
            feedback.append("💡 建议把内容拆成多个短小段落，每段讲一个观点")

        # 检查段落长度（太长的段落不利于摘取）
        long_paragraphs = [p for p in paragraphs if len(p) > 300]
        if len(long_paragraphs) >= 3:
            score -= 20
            feedback.append(f"⚠️ 有{len(long_paragraphs)}个超长段落（>300字）")
            feedback.append("💡 建议把长段落拆成短段落，每段只讲一个核心观点")

        # 检查是否有明确定义句
        definition_patterns = ["是指", "是一种", "是什么？", "定义", "概念",
                              "一句话", "简单来说", "通俗地讲"]
        has_definitions = sum(1 for p in paragraphs if any(d in p for d in definition_patterns))
        if has_definitions == 0:
            score -= 15
            feedback.append("⚠️ 缺少明确定义句，AI难以直接引用")
            feedback.append("💡 建议为核心概念写一句清晰的定义，可被AI直接摘取")
        else:
            feedback.append(f"✅ 有{has_definitions}处明确定义，便于AI引用")

        # 检查每个小节是否有独立的结论
        # （通过检查小标题后第一行是否是结论性内容来粗略判断）
        sections_with_clear_conclusion = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('## ') and not line.strip().startswith('### '):
                # 找这个小节的第一段正文
                for j in range(i+1, min(i+10, len(lines))):
                    next_line = lines[j].strip()
                    if next_line and not next_line.startswith('#'):
                        # 简单判断：第一句是否是结论性的
                        if len(next_line) > 20:
                            sections_with_clear_conclusion += 1
                        break

        if sections_with_clear_conclusion >= 3:
            feedback.append("✅ 多数小节开头有明确内容")

        return max(0, score), feedback

    # ========== 维度5：差异化程度 ==========

    @staticmethod
    def _check_differentiation(content: str) -> Tuple[int, List[str]]:
        """检查差异化程度"""
        score = 100
        feedback = []

        # 检查是否有差异化内容的信号
        diff_signals = 0

        # 自有数据/方法信号
        for kw in GEOQualityScorer.DIFFERENTIATION_KEYWORDS:
            if kw in content:
                diff_signals += 1

        # 结构化经验（适用/不适用分类）
        if "适合" in content and "不适合" in content:
            diff_signals += 2
            feedback.append("✅ 有明确的适用/不适用分类（结构化经验）")

        # 原创框架或方法论
        framework_keywords = ["三步", "四步", "五步", "框架", "体系", "方法论",
                             "模型", "维度", "原则", "标准"]
        framework_count = sum(1 for kw in framework_keywords if kw in content)
        if framework_count >= 3:
            diff_signals += 2
            feedback.append("✅ 有原创的分析框架或方法论")

        # 具体数据支撑
        data_patterns = re.findall(r'\d+[\.\d]*%|\d+[\.\d]*个|平均\d+|约\d+', content)
        if len(data_patterns) >= 5:
            diff_signals += 1

        # 根据差异化信号评分
        if diff_signals == 0:
            score -= 40
            feedback.append("❌ 内容偏通用，缺少差异化价值")
            feedback.append("💡 建议加入：自有数据、独特方法、结构化经验（适用/不适用分类）")
        elif diff_signals <= 2:
            score -= 20
            feedback.append("⚠️ 差异化价值一般")
            feedback.append("💡 建议增加更多独特的内容，如原创框架、具体数据、分类标准")
        elif diff_signals >= 5:
            feedback.append("✅ 差异化价值较高")

        return max(0, score), feedback

    # ========== 维度6：数据可验证性 ==========

    @staticmethod
    def _check_verifiability(content: str) -> Tuple[int, List[str]]:
        """检查数据可验证性"""
        score = 100
        feedback = []

        # 检查是否有具体数字
        has_numbers = bool(re.search(r'\d', content))
        if not has_numbers:
            score -= 40
            feedback.append("❌ 没有发现具体数据")
            feedback.append("💡 建议加入具体数据（价格/周期/有效率/参数等）")
            return max(0, score), feedback

        # 检查数据是否有来源标注
        source_keywords = ["来源：", "根据", "据", "数据显示", "研究表明",
                          "品牌公开资料", "官方数据", "公开数据", "临床试验"]
        has_source = any(kw in content for kw in source_keywords)
        if not has_source:
            score -= 30
            feedback.append("⚠️ 数据没有标注来源")
            feedback.append("💡 建议标注数据来源，如：据品牌公开资料显示、根据XX研究")
        else:
            feedback.append("✅ 数据有来源标注")

        # 检查数据的丰富程度
        number_count = len(re.findall(r'\d+[\.\d]*', content))
        if number_count < 5:
            score -= 15
            feedback.append("💡 数据点较少，建议增加更多具体数据")
        elif number_count >= 10:
            feedback.append(f"✅ 数据较为丰富（约{number_count}个数据点）")

        return max(0, score), feedback

    # ========== 维度7：风险披露 ==========

    @staticmethod
    def _check_risk_disclosure(content: str) -> Tuple[int, List[str]]:
        """检查风险披露"""
        score = 100
        feedback = []

        # 检查是否有风险披露
        has_risk = any(kw in content for kw in GEOQualityScorer.RISK_KEYWORDS)
        if not has_risk:
            score -= 40
            feedback.append("❌ 缺少风险披露和注意事项")
            feedback.append("💡 建议加入风险提示、注意事项、禁忌人群等内容")
        else:
            feedback.append("✅ 有风险披露")

        # 检查是否承认个体差异
        diff_keywords = ["因人而异", "个体差异", "不同的人", "有些人", "部分人",
                        "不一定", "视情况", "根据个人情况"]
        has_individual_diff = any(kw in content for kw in diff_keywords)
        if not has_individual_diff:
            score -= 20
            feedback.append("⚠️ 没有承认个体差异")
            feedback.append("💡 建议加入：效果因人而异、不同人可能有不同反应")
        else:
            feedback.append("✅ 承认了个体差异")

        # 检查是否有"建议咨询专业人士"
        has_professional_advice = any(w in content for w in
                                      ["建议咨询", "请咨询", "专业意见", "医生指导"])
        if not has_professional_advice:
            score -= 10
            feedback.append("💡 建议加入'建议咨询专业人士'的提示")

        # 检查是否明确说了不适用人群
        has_not_suitable = "不适合" in content or "禁忌" in content or "禁用" in content
        if not has_not_suitable:
            score -= 10
            feedback.append("💡 建议明确说明不适用人群/禁忌症")

        return max(0, score), feedback

    # ========== 维度8：品牌自然度 ==========

    @staticmethod
    def _check_brand_naturalness(content: str, brand_name: Optional[str] = None) -> Tuple[int, List[str]]:
        """检查品牌植入自然度"""
        score = 100
        feedback = []

        if not brand_name:
            # 没有品牌名，给基础分
            return score, ["ℹ️ 未提供品牌名，跳过品牌自然度检查"]

        # 统计品牌出现次数
        brand_count = content.count(brand_name)

        if brand_count == 0:
            score -= 30
            feedback.append("⚠️ 品牌没有出现在内容中")
            feedback.append("💡 建议在适当位置自然植入品牌")
        elif brand_count <= 2:
            feedback.append(f"✅ 品牌出现{brand_count}次，植入适度")
        elif brand_count <= 5:
            feedback.append(f"✅ 品牌出现{brand_count}次，频率适中")
        else:
            score -= (brand_count - 5) * 5
            feedback.append(f"⚠️ 品牌出现{brand_count}次，可能过于频繁")
            feedback.append("💡 建议减少品牌提及次数，保持自然不生硬")

        # 检查品牌是否在推荐/选择场景中出现
        brand_in_recommendation = False
        rec_keywords = ["推荐", "选择", "选", "考虑", "适合", "首推", "首选"]
        for line in content.split('\n'):
            if brand_name in line and any(kw in line for kw in rec_keywords):
                brand_in_recommendation = True
                break

        if brand_in_recommendation:
            feedback.append("✅ 品牌出现在推荐场景中，植入自然")

        # 检查是否有硬广嫌疑（品牌后面直接跟大量赞美词）
        brand_praise_pattern = brand_name + r"[是，的、].{0,20}(最好|最佳|第一|顶级|首选|无与伦比)"
        hard_sell_count = len(re.findall(brand_praise_pattern, content))
        if hard_sell_count > 0:
            score -= 20
            feedback.append("❌ 品牌描述过于夸张，有硬广嫌疑")
            feedback.append("💡 建议用客观描述替代绝对化赞美，用数据和证据说话")

        return max(0, score), feedback

    # ========== 主评分方法 ==========

    @staticmethod
    def score_content(content: str, brand_name: Optional[str] = None,
                      content_type: Optional[str] = None) -> Dict[str, Any]:
        """
        对内容进行完整的GEO质量评分（8维度）

        Args:
            content: 文章内容
            brand_name: 品牌名（可选）
            content_type: 内容类型（longtail/comparison/deep，可选）

        Returns:
            {
                "overall_score": 85,
                "grade": "B",
                "dimensions": {...},
                "all_feedback": [...],
                "passed": True/False,
                "summary": "...",
                "content_type_guide": {...}
            }
        """
        dimension_results = {}
        all_feedback = []

        # 维度1：答案优先度 (15%)
        af_score, af_feedback = GEOQualityScorer._check_answer_first(content)
        dimension_results["answer_first"] = {
            "score": af_score,
            "name": "答案优先度",
            "weight": 0.15,
            "source": "《答案优先》",
            "feedback": af_feedback
        }
        all_feedback.extend(af_feedback)

        # 维度2：EEAT可信度 (20%)
        eeat_score, eeat_feedback = GEOQualityScorer._check_eeat_trust(content, brand_name)
        dimension_results["eeat_trust"] = {
            "score": eeat_score,
            "name": "EEAT可信度",
            "weight": 0.20,
            "source": "《EEAT原则》",
            "feedback": eeat_feedback
        }
        all_feedback.extend(eeat_feedback)

        # 维度3：结构清晰度 (15%)
        struct_score, struct_feedback = GEOQualityScorer._check_structure(content)
        dimension_results["structure_clarity"] = {
            "score": struct_score,
            "name": "结构清晰度",
            "weight": 0.15,
            "source": "《结构化写法》",
            "feedback": struct_feedback
        }
        all_feedback.extend(struct_feedback)

        # 维度4：内容可摘取性 (15%)
        chunk_score, chunk_feedback = GEOQualityScorer._check_chunkability(content)
        dimension_results["chunkability"] = {
            "score": chunk_score,
            "name": "内容可摘取性",
            "weight": 0.15,
            "source": "《内容分块》",
            "feedback": chunk_feedback
        }
        all_feedback.extend(chunk_feedback)

        # 维度5：差异化程度 (10%)
        diff_score, diff_feedback = GEOQualityScorer._check_differentiation(content)
        dimension_results["differentiation"] = {
            "score": diff_score,
            "name": "差异化程度",
            "weight": 0.10,
            "source": "《差异化内容》",
            "feedback": diff_feedback
        }
        all_feedback.extend(diff_feedback)

        # 维度6：数据可验证性 (10%)
        veri_score, veri_feedback = GEOQualityScorer._check_verifiability(content)
        dimension_results["data_verifiability"] = {
            "score": veri_score,
            "name": "数据可验证性",
            "weight": 0.10,
            "source": "综合",
            "feedback": veri_feedback
        }
        all_feedback.extend(veri_feedback)

        # 维度7：风险披露 (10%)
        risk_score, risk_feedback = GEOQualityScorer._check_risk_disclosure(content)
        dimension_results["risk_disclosure"] = {
            "score": risk_score,
            "name": "风险披露",
            "weight": 0.10,
            "source": "《合规治理》",
            "feedback": risk_feedback
        }
        all_feedback.extend(risk_feedback)

        # 维度8：品牌自然度 (5%)
        brand_score, brand_feedback = GEOQualityScorer._check_brand_naturalness(content, brand_name)
        dimension_results["brand_naturalness"] = {
            "score": brand_score,
            "name": "品牌自然度",
            "weight": 0.05,
            "source": "综合",
            "feedback": brand_feedback
        }
        all_feedback.extend(brand_feedback)

        # 计算总分（加权平均）
        total_score = sum(
            dim["score"] * dim["weight"]
            for dim in dimension_results.values()
        )
        total_score = round(total_score)

        # 分离问题和建议
        suggestions = [i for i in all_feedback if i.startswith("💡")]
        issues = [i for i in all_feedback if i.startswith("❌") or i.startswith("⚠️")]
        positives = [i for i in all_feedback if i.startswith("✅")]

        # 判断是否通过（及格线：75分）
        passed = total_score >= 75

        # 生成总结
        if total_score >= 90:
            summary = "🏆 优秀！内容GEO质量很高，非常适合AI搜索引用"
        elif total_score >= 80:
            summary = "✅ 良好！内容质量较好，符合GEO规范"
        elif total_score >= 70:
            summary = "⚠️ 中等！内容基本合格，建议根据反馈优化"
        elif total_score >= 60:
            summary = "⚠️ 及格！建议根据反馈认真优化后再发布"
        else:
            summary = "❌ 不合格！内容需要大幅优化，请根据反馈逐条修改"

        # 获取内容类型对应的写作指南
        content_type_guide = None
        if content_type:
            content_type_guide = GEOKnowledgeBase.get_writing_guide(content_type)

        return {
            "overall_score": total_score,
            "grade": GEOQualityScorer._get_grade(total_score),
            "dimensions": dimension_results,
            "all_feedback": all_feedback,
            "issues": issues,
            "suggestions": suggestions,
            "positives": positives,
            "passed": passed,
            "summary": summary,
            "content_type": content_type,
            "content_type_guide": content_type_guide
        }

    @staticmethod
    def _get_grade(score: int) -> str:
        """获取等级"""
        if score >= 90:
            return "S"
        elif score >= 80:
            return "A"
        elif score >= 70:
            return "B"
        elif score >= 60:
            return "C"
        else:
            return "D"

    # ========== 落地检查表 ==========

    @staticmethod
    def get_landing_checklist(content_type: Optional[str] = None) -> Dict[str, Any]:
        """获取GEO内容落地检查表"""
        return GEOKnowledgeBase.LANDING_CHECKLIST

    # ========== 报告生成 ==========

    @staticmethod
    def generate_html_report(scoring_result: Dict[str, Any]) -> str:
        """生成HTML格式的评分报告（用于前端展示）"""
        html = []

        # 总体评分
        grade = scoring_result.get('grade', 'N/A')
        html.append(f"<div class='geo-score-report'>")
        html.append(f"  <div class='overall-score'>")
        html.append(f"    <div class='score-circle grade-{grade}'>")
        html.append(f"      <span class='score-number'>{scoring_result['overall_score']}</span>")
        html.append(f"      <span class='score-grade'>{grade}</span>")
        html.append(f"    </div>")
        html.append(f"    <div class='score-summary'>{scoring_result['summary']}</div>")
        html.append(f"  </div>")

        # 各维度评分
        html.append(f"  <div class='dimension-scores'>")
        html.append(f"    <h3>8维度GEO质量评分</h3>")
        for key, dim in scoring_result['dimensions'].items():
            percentage = dim['score']
            color_class = "good" if percentage >= 80 else "medium" if percentage >= 60 else "bad"
            weight_pct = int(dim['weight'] * 100)
            html.append(f"    <div class='dimension-item'>")
            html.append(f"      <div class='dimension-header'>")
            html.append(f"        <span class='dimension-name'>")
            html.append(f"          {dim['name']}")
            html.append(f"          <span class='dimension-source'>（{dim.get('source', '')} · 权重{weight_pct}%）</span>")
            html.append(f"        </span>")
            html.append(f"        <span class='dimension-score'>{percentage}分</span>")
            html.append(f"      </div>")
            html.append(f"      <div class='progress-bar'>")
            html.append(f"        <div class='progress-fill {color_class}' style='width: {percentage}%'></div>")
            html.append(f"      </div>")
            html.append(f"    </div>")
        html.append(f"  </div>")

        # 亮点
        if scoring_result.get('positives'):
            html.append(f"  <div class='positives-section'>")
            html.append(f"    <h3>✅ 做得好的地方</h3>")
            html.append(f"    <ul class='feedback-list positives'>")
            for feedback in scoring_result['positives']:
                safe_feedback = feedback.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                html.append(f"      <li>{safe_feedback}</li>")
            html.append(f"    </ul>")
            html.append(f"  </div>")

        # 问题和建议
        issues_and_suggestions = scoring_result.get('issues', []) + scoring_result.get('suggestions', [])
        if issues_and_suggestions:
            html.append(f"  <div class='feedback-section'>")
            html.append(f"    <h3>🔧 优化建议</h3>")
            html.append(f"    <ul class='feedback-list'>")
            for feedback in issues_and_suggestions:
                safe_feedback = feedback.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                html.append(f"      <li>{safe_feedback}</li>")
            html.append(f"    </ul>")
            html.append(f"  </div>")

        html.append(f"</div>")

        return '\n'.join(html)

    @staticmethod
    def generate_text_report(scoring_result: Dict[str, Any]) -> str:
        """生成纯文本格式的评分报告"""
        lines = []
        lines.append("=" * 60)
        lines.append("GEO质量评分报告（8维度专业版）")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"【总体评分】 {scoring_result['overall_score']}分 / 等级: {scoring_result['grade']}")
        lines.append(f"【评估结果】 {scoring_result['summary']}")
        lines.append("")
        lines.append("【8维度评分详情】")
        for key, dim in scoring_result['dimensions'].items():
            weight_pct = int(dim['weight'] * 100)
            bar = "█" * (dim['score'] // 10) + "░" * (10 - dim['score'] // 10)
            lines.append(f"  {dim['name']:<12s} {bar} {dim['score']:>3d}分 ({weight_pct}%权重) - {dim.get('source', '')}")
        lines.append("")

        if scoring_result.get('positives'):
            lines.append("【做得好的地方】")
            for feedback in scoring_result['positives']:
                lines.append(f"  {feedback}")
            lines.append("")

        lines.append("【优化建议】")
        all_tips = scoring_result.get('issues', []) + scoring_result.get('suggestions', [])
        if all_tips:
            for feedback in all_tips:
                lines.append(f"  {feedback}")
        else:
            lines.append("  ✅ 内容质量优秀，继续保持！")
        lines.append("")

        # 落地检查表
        lines.append("【GEO落地检查表】")
        checklist = GEOKnowledgeBase.LANDING_CHECKLIST
        for cat_key, cat in checklist.items():
            lines.append(f"  □ {cat['name']}:")
            for item in cat['items']:
                lines.append(f"    □ {item}")
        lines.append("")
        lines.append("=" * 60)
        return '\n'.join(lines)


# 便捷函数
def score_geo_content(content: str, brand_name: Optional[str] = None,
                      content_type: Optional[str] = None) -> Dict[str, Any]:
    """评分内容（便捷函数）"""
    return GEOQualityScorer.score_content(content, brand_name, content_type)

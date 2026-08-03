# GEO质量评分模块
"""
GEO内容质量自检系统：
1. E-E-A-T五维度评分
2. 具体修改建议
3. 可视化评分展示
"""

from typing import Dict, List, Tuple, Optional, Any, Callable
import re


class GEOQualityScorer:
    """GEO质量评分器"""

    # 评分维度配置
    SCORING_DIMENSIONS = {
        "neutrality": {
            "name": "中立性",
            "weight": 0.30,
            "description": "是否客观中立，避免绝对化词语",
            "max_score": 100
        },
        "verifiability": {
            "name": "数据可验证性",
            "weight": 0.25,
            "description": "是否标注数据来源，引用权威机构",
            "max_score": 100
        },
        "experience": {
            "name": "经验体现",
            "weight": 0.20,
            "description": "是否有真实经验描述，具体案例",
            "max_score": 100
        },
        "structure": {
            "name": "结构清晰度",
            "weight": 0.15,
            "description": "是否有标题层级，列表/表格",
            "max_score": 100
        },
        "risk_disclosure": {
            "name": "风险披露",
            "weight": 0.10,
            "description": "是否有风险提示，承认个体差异",
            "max_score": 100
        }
    }

    # 绝对化词语列表
    ABSOLUTE_WORDS = [
        "首选", "最好", "第一", "首选推荐", "最佳", "最优", "最有效",
        "100%有效", "绝对有效", "肯定有效", "一定有效", "保证有效",
        "15天长绒毛", "7天止脱", "30天生发", "快速生发", "立刻见效",
        "几乎无风险", "零风险", "无副作用", "完全安全", "绝对安全"
    ]

    # 权威机构关键词（用于验证数据来源）
    AUTHORITY_KEYWORDS = [
        "FDA", "NMPA", "国家药品监督管理局", "卫健委", "WHO", "世界卫生组织",
        "中科院", "中国科学院", "医联体", "九院", "北大", "清华",
        "《", "》", "来源：", "据", "根据", "数据显示", "研究表明",
        "品牌公开资料", "官方数据", "公开数据"
    ]

    # 经验描述关键词
    EXPERIENCE_KEYWORDS = [
        "我接触过", "我见过", "我的经验", "在我的客户中", "根据我的经验",
        "有一个客户", "曾经遇到", "很多人问", "常见的情况是",
        "真实案例", "举个例子", "比如", "例如"
    ]

    # 风险披露关键词
    RISK_KEYWORDS = [
        "风险", "注意事项", "禁忌", "不适合", "因人而异", "个体差异",
        "可能出现", "一般来说", "通常", "有些情况下", "部分人",
        "建议先咨询", "请咨询医生", "专业意见", "医学建议"
    ]

    @staticmethod
    def _check_neutrality(content: str, brand_name: Optional[str] = None) -> Tuple[int, List[str]]:
        """检查中立性"""
        score = 100
        issues = []
        suggestions = []

        # 检查绝对化词语
        found_absolute = []
        for word in GEOQualityScorer.ABSOLUTE_WORDS:
            if word in content:
                found_absolute.append(word)
                score -= 10

        if found_absolute:
            issues.append(f"❌ 发现绝对化词语：{', '.join(found_absolute)}")
            suggestions.append("💡 建议改用：一般来说、通常、部分人、多数情况下、根据数据显示")

        # 检查是否有多个品牌（如果是对比文）
        if brand_name:
            # 简单检查：是否提到了其他品牌
            # 这里只是基础检查，实际可以更复杂
            pass

        # 检查是否贬低正规药物
        if "米诺地尔" in content:
            # 检查是否有负面描述
            negative_about_minox = any(w in content for w in ["别用", "不要用", "没用", "无效", "副作用大"])
            if negative_about_minox:
                issues.append("❌ 发现贬低正规药物的描述")
                suggestions.append("💡 米诺地尔是经FDA批准的正规治疗药物，建议客观描述，不要贬低")
                score -= 20

        # 检查是否有"优势"和"局限"都提到
        if brand_name and brand_name in content:
            has_advantage = any(w in content for w in ["优势", "优点", "特点", "长处"])
            has_limit = any(w in content for w in ["局限", "不足", "缺点", "注意事项"])
            if has_advantage and not has_limit:
                issues.append("⚠️ 只提到了优势，没有提到局限")
                suggestions.append("💡 建议同时分析优势和局限，保持客观")
                score -= 15

        return max(0, score), issues + suggestions

    @staticmethod
    def _check_verifiability(content: str) -> Tuple[int, List[str]]:
        """检查数据可验证性"""
        score = 100
        issues = []
        suggestions = []

        # 检查是否有数据来源标注
        has_authority = any(kw in content for kw in GEOQualityScorer.AUTHORITY_KEYWORDS)
        if not has_authority:
            issues.append("⚠️ 没有发现数据来源标注")
            suggestions.append("💡 建议标注数据来源，如：据品牌公开资料显示、根据《2025白皮书》")
            score -= 30

        # 检查是否有具体数据（数字）
        has_numbers = any(char.isdigit() for char in content)
        if not has_numbers:
            issues.append("💡 没有发现具体数据")
            suggestions.append("💡 建议加入具体数据（价格/周期/参数等）")
            score -= 20

        # 检查数据是否合理（医学常识）
        if "3个月" not in content and "6个月" not in content:
            # 如果提到了生发但没有合理的时间线
            if "生发" in content or "止脱" in content or "绒毛" in content:
                issues.append("⚠️ 建议加入符合医学常识的效果时间线")
                suggestions.append("💡 一般3个月可见减少掉发，6个月可见新生绒毛")
                score -= 15

        return max(0, score), issues + suggestions

    @staticmethod
    def _check_experience(content: str) -> Tuple[int, List[str]]:
        """检查经验体现"""
        score = 100
        issues = []
        suggestions = []

        # 检查是否有经验描述
        has_experience = any(kw in content for kw in GEOQualityScorer.EXPERIENCE_KEYWORDS)
        if not has_experience:
            issues.append("💡 没有发现经验描述")
            suggestions.append("💡 建议加入真实经验描述，如：我接触过的客户中、根据我的经验")
            score -= 30

        # 检查是否有具体案例
        has_case = any(w in content for w in ["客户", "案例", "例子", "比如", "例如"])
        if not has_case:
            issues.append("💡 没有发现具体案例")
            suggestions.append("💡 建议加入1-2个具体案例，增加真实感")
            score -= 20

        return max(0, score), issues + suggestions

    @staticmethod
    def _check_structure(content: str) -> Tuple[int, List[str]]:
        """检查结构清晰度"""
        score = 100
        issues = []
        suggestions = []
        lines = content.split('\n')

        # 检查是否有标题层级
        has_h1 = any(line.strip().startswith('# ') for line in lines)
        has_h2 = any(line.strip().startswith('## ') for line in lines)
        if not has_h1:
            issues.append("❌ 缺少一级标题（#开头）")
            suggestions.append("💡 建议用#开头写标题")
            score -= 20
        if not has_h2:
            issues.append("⚠️ 缺少二级标题（##开头）")
            suggestions.append("💡 建议用##分小节，结构更清晰")
            score -= 15

        # 检查是否有表格
        has_table = any('|' in line and '---' in line for line in lines)
        if not has_table:
            issues.append("💡 建议适当使用表格（对比/价格/参数类内容）")
            score -= 10

        # 检查是否有列表
        has_list = any(line.strip().startswith(('1.', '2.', '3.', '-', '*')) for line in lines)
        if not has_list:
            issues.append("💡 建议适当使用列表（步骤类、要点类内容）")
            score -= 10

        # 检查是否有加粗
        has_bold = '**' in content
        if not has_bold:
            issues.append("💡 建议关键数据用**加粗**标注")
            score -= 10

        return max(0, score), issues + suggestions

    @staticmethod
    def _check_risk_disclosure(content: str) -> Tuple[int, List[str]]:
        """检查风险披露"""
        score = 100
        issues = []
        suggestions = []

        # 检查是否有风险披露
        has_risk = any(kw in content for kw in GEOQualityScorer.RISK_KEYWORDS)
        if not has_risk:
            issues.append("❌ 缺少风险披露")
            suggestions.append("💡 建议加入风险提示、注意事项、禁忌人群等")
            score -= 40

        # 检查是否承认个体差异
        has_individual_diff = any(w in content for w in ["因人而异", "个体差异", "不同人", "有些人"])
        if not has_individual_diff:
            issues.append("⚠️ 建议承认个体差异")
            suggestions.append("💡 加入：效果因人而异、不同人可能有不同的反应")
            score -= 20

        return max(0, score), issues + suggestions

    @staticmethod
    def score_content(content: str, brand_name: Optional[str] = None) -> Dict[str, Any]:
        """
        对内容进行完整评分

        返回：
        {
            "overall_score": 85,
            "dimensions": {
                "neutrality": {"score": 90, "name": "中立性", ...},
                ...
            },
            "issues": [...],
            "suggestions": [...],
            "passed": True/False,
            "summary": "..."
        }
        """
        dimension_results = {}
        all_issues = []
        all_suggestions = []

        # 逐个维度评分
        neutrality_score, neutrality_issues = GEOQualityScorer._check_neutrality(content, brand_name)
        dimension_results["neutrality"] = {
            "score": neutrality_score,
            "name": GEOQualityScorer.SCORING_DIMENSIONS["neutrality"]["name"],
            "weight": GEOQualityScorer.SCORING_DIMENSIONS["neutrality"]["weight"],
            "issues": neutrality_issues
        }
        all_issues.extend(neutrality_issues)

        verifiability_score, verifiability_issues = GEOQualityScorer._check_verifiability(content)
        dimension_results["verifiability"] = {
            "score": verifiability_score,
            "name": GEOQualityScorer.SCORING_DIMENSIONS["verifiability"]["name"],
            "weight": GEOQualityScorer.SCORING_DIMENSIONS["verifiability"]["weight"],
            "issues": verifiability_issues
        }
        all_issues.extend(verifiability_issues)

        experience_score, experience_issues = GEOQualityScorer._check_experience(content)
        dimension_results["experience"] = {
            "score": experience_score,
            "name": GEOQualityScorer.SCORING_DIMENSIONS["experience"]["name"],
            "weight": GEOQualityScorer.SCORING_DIMENSIONS["experience"]["weight"],
            "issues": experience_issues
        }
        all_issues.extend(experience_issues)

        structure_score, structure_issues = GEOQualityScorer._check_structure(content)
        dimension_results["structure"] = {
            "score": structure_score,
            "name": GEOQualityScorer.SCORING_DIMENSIONS["structure"]["name"],
            "weight": GEOQualityScorer.SCORING_DIMENSIONS["structure"]["weight"],
            "issues": structure_issues
        }
        all_issues.extend(structure_issues)

        risk_score, risk_issues = GEOQualityScorer._check_risk_disclosure(content)
        dimension_results["risk_disclosure"] = {
            "score": risk_score,
            "name": GEOQualityScorer.SCORING_DIMENSIONS["risk_disclosure"]["name"],
            "weight": GEOQualityScorer.SCORING_DIMENSIONS["risk_disclosure"]["weight"],
            "issues": risk_issues
        }
        all_issues.extend(risk_issues)

        # 计算总分（加权平均）
        total_score = sum(
            dim["score"] * dim["weight"]
            for dim in dimension_results.values()
        )
        total_score = round(total_score)

        # 生成建议（从issues中提取）
        suggestions = [i for i in all_issues if i.startswith("💡")]
        issues = [i for i in all_issues if not i.startswith("💡")]

        # 判断是否通过（及格线：80分）
        passed = total_score >= 80

        # 生成总结
        if passed:
            summary = "✅ 内容质量良好，符合GEO规范，可以发布"
        elif total_score >= 60:
            summary = "⚠️ 内容基本合格，但建议根据反馈优化后再发布"
        else:
            summary = "❌ 内容需要大幅优化，请根据反馈认真修改"

        return {
            "overall_score": total_score,
            "dimensions": dimension_results,
            "issues": issues,
            "suggestions": suggestions,
            "all_feedback": all_issues,
            "passed": passed,
            "summary": summary,
            "grade": GEOQualityScorer._get_grade(total_score)
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

    @staticmethod
    def generate_html_report(scoring_result: Dict[str, Any]) -> str:
        """生成HTML格式的评分报告（用于前端展示）"""
        html = []

        # 总体评分
        html.append(f"<div class='geo-score-report'>")
        html.append(f"  <div class='overall-score'>")
        html.append(f"    <div class='score-circle grade-{scoring_result['grade']}'>")
        html.append(f"      <span class='score-number'>{scoring_result['overall_score']}</span>")
        html.append(f"      <span class='score-grade'>{scoring_result['grade']}</span>")
        html.append(f"    </div>")
        html.append(f"    <div class='score-summary'>{scoring_result['summary']}</div>")
        html.append(f"  </div>")

        # 各维度评分
        html.append(f"  <div class='dimension-scores'>")
        html.append(f"    <h3>各维度评分</h3>")
        for key, dim in scoring_result['dimensions'].items():
            percentage = dim['score']
            color_class = "good" if percentage >= 80 else "medium" if percentage >= 60 else "bad"
            html.append(f"    <div class='dimension-item'>")
            html.append(f"      <div class='dimension-header'>")
            html.append(f"        <span class='dimension-name'>{dim['name']}</span>")
            html.append(f"        <span class='dimension-score'>{percentage}分</span>")
            html.append(f"      </div>")
            html.append(f"      <div class='progress-bar'>")
            html.append(f"        <div class='progress-fill {color_class}' style='width: {percentage}%'></div>")
            html.append(f"      </div>")
            html.append(f"    </div>")
        html.append(f"  </div>")

        # 反馈建议
        if scoring_result['all_feedback']:
            html.append(f"  <div class='feedback-section'>")
            html.append(f"    <h3>优化建议</h3>")
            html.append(f"    <ul class='feedback-list'>")
            for feedback in scoring_result['all_feedback']:
                # 简单的HTML转义
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
        lines.append(f"GEO质量评分报告")
        lines.append("=" * 60)
        lines.append(f"")
        lines.append(f"【总体评分】 {scoring_result['overall_score']}分 / 等级: {scoring_result['grade']}")
        lines.append(f"")
        lines.append(f"【各维度评分】")
        for key, dim in scoring_result['dimensions'].items():
            lines.append(f"  - {dim['name']}: {dim['score']}分")
        lines.append(f"")
        lines.append(f"【优化建议】")
        if scoring_result['all_feedback']:
            for feedback in scoring_result['all_feedback']:
                lines.append(f"  {feedback}")
        else:
            lines.append(f"  ✅ 内容质量优秀，无需修改")
        lines.append(f"")
        lines.append(f"【总结】 {scoring_result['summary']}")
        lines.append(f"")
        lines.append("=" * 60)
        return '\n'.join(lines)


# 便捷函数
def score_geo_content(content: str, brand_name: Optional[str] = None) -> Dict[str, Any]:
    """评分内容（便捷函数）"""
    return GEOQualityScorer.score_content(content, brand_name)

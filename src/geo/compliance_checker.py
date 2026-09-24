# GEO内容合规审核模块
"""
通用内容合规检测系统

检测维度（通用，不绑定特定行业）：
1. 绝对化表述
2. 贬低竞品
3. 硬广嫌疑
4. 数据真实性（未标注来源的数据）
5. 风险披露（加分项：有免责声明/注意事项的减分）

风险等级：
- SAFE (0-20)：安全
- LOW (21-40)：低风险
- MEDIUM (41-60)：中风险
- HIGH (61-80)：高风险
- CRITICAL (81-100)：极高风险
"""

import re
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field


@dataclass
class ComplianceIssue:
    """合规问题项"""
    category: str           # 问题类别
    severity: str           # 严重程度：low / medium / high / critical
    description: str        # 问题描述
    matched_text: str       # 匹配到的原文
    suggestion: str         # 修改建议
    position: int = -1      # 在文中的位置（字符索引）


@dataclass
class ComplianceResult:
    """合规检测结果"""
    risk_score: int = 0                 # 风险总分 0-100
    risk_level: str = "safe"            # 风险等级
    issues: List[ComplianceIssue] = field(default_factory=list)
    passed: bool = True                 # 是否通过
    summary: str = ""                   # 总结描述
    disclaimer: str = ""                # 建议追加的免责声明

    def to_dict(self) -> Dict[str, Any]:
        level_names = {
            "safe": "✅ 安全",
            "low": "⚠️ 低风险",
            "medium": "⚡ 中风险",
            "high": "🔴 高风险",
            "critical": "💀 极高风险"
        }
        return {
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "risk_level_name": level_names.get(self.risk_level, self.risk_level),
            "passed": self.passed,
            "summary": self.summary,
            "disclaimer": self.disclaimer,
            "issues": [
                {
                    "category": i.category,
                    "severity": i.severity,
                    "description": i.description,
                    "matched_text": i.matched_text,
                    "suggestion": i.suggestion
                }
                for i in self.issues
            ]
        }


class ComplianceChecker:
    """
    通用合规检测器

    只检测通用的、跨行业的内容风险：
    - 绝对化表述
    - 贬低竞品
    - 硬广嫌疑
    - 数据真实性
    """

    # 【绝对化表述词】
    ABSOLUTE_WORDS = [
        # 排名类
        "最好", "最佳", "最优", "最有效", "最安全", "最专业",
        "排名第一", "全国第一", "行业第一", "TOP1", "top1", "Top1",
        "第一品牌", "第一选择", "首选品牌", "首选推荐",
        # 唯一类
        "唯一", "独家", "首创", "独一无二", "绝无仅有",
        # 级别类
        "国家级", "世界级", "顶级", "顶尖", "至尊",
        "最高级", "最高端", "最先进",
        # 完全类
        "完全", "彻底", "绝对", "100%", "百分之百",
        # 承诺类
        "零风险", "无风险", "没有任何风险",
        "无副作用", "没有任何副作用",
        "保证有效", "保证效果",
    ]

    # 【贬低竞品模式】
    DEROGATORY_PATTERNS = [
        (r"千万别[选买用]", "警告式贬低"),
        (r"千万不要[选买用]", "警告式贬低"),
        (r"不建议[选买用]", "不建议式贬低"),
        (r"智商税", "定性式贬低"),
        (r"都是坑", "定性式贬低"),
        (r"杂牌", "贬低性标签"),
        (r"小牌子", "贬低性标签"),
        (r"不靠谱", "贬低性评价"),
        (r"比[^，。]{2,10}差远了", "对比式贬低"),
        (r"不如[^，。]{2,10}的一根毫毛", "夸张式贬低"),
    ]

    # 【硬广/营销模式】
    HARDSELL_PATTERNS = [
        (r"强烈推荐", "强推式"),
        (r"赶紧入手", "催促式"),
        (r"赶紧买", "催促式"),
        (r"买它", "带货式"),
        (r"必买", "绝对化推荐"),
        (r"必选", "绝对化推荐"),
        (r"错过就没", "稀缺式营销"),
        (r"限时优惠", "限时营销"),
        (r"名额有限", "稀缺式营销"),
        (r"手慢无", "催促式"),
    ]

    # 【未验证数据模式】
    UNVERIFIED_DATA_PATTERNS = [
        (r"\d{2,3}%", "百分比数据"),
        (r"增长\s*\d+[%％]", "增长率数据"),
        (r"下降\s*\d+[%％]", "下降率数据"),
        (r"\d+\s*个(?:品牌|机构|门店|产品)", "数量数据"),
        (r"连续\s*\d+\s*年", "时间数据"),
    ]

    # 【数据来源标注关键词】
    DATA_SOURCE_MARKERS = [
        "来源：", "数据来源", "根据", "据", "研究表明",
        "公开资料", "官方数据", "公开数据", "行业报告",
        "品牌公开资料", "官方公布", "统计显示",
    ]

    # 【风险披露关键词】（有则减分）
    RISK_DISCLOSURE_KEYWORDS = [
        "因人而异", "个体差异", "不同的人", "有些人", "部分人",
        "不一定", "视情况", "根据个人情况",
        "风险", "注意事项", "禁忌", "不适合", "慎用",
        "建议咨询", "请咨询", "专业意见", "仅供参考",
    ]

    # 【免责声明模板（通用）】
    DISCLAIMER_GENERIC = (
        "⚠️ 免责声明：\n"
        "本文内容仅供参考，不构成专业建议。"
        "具体选择请根据个人实际情况，必要时咨询专业人士。"
    )

    def __init__(self, pass_threshold: int = 40):
        """
        初始化合规检测器

        Args:
            pass_threshold: 通过阈值（风险分低于此值算通过）
        """
        self.pass_threshold = pass_threshold

    # ==================== 主检测方法 ====================

    def check(self, content: str, brand_name: Optional[str] = None) -> ComplianceResult:
        """
        对内容进行合规检测

        Args:
            content: 文章内容
            brand_name: 品牌名（用于硬广检测）

        Returns:
            ComplianceResult 检测结果
        """
        result = ComplianceResult()
        issues: List[ComplianceIssue] = []

        if not content or not content.strip():
            result.summary = "内容为空，无法检测"
            result.passed = False
            return result

        # 1. 绝对化表述检测
        absolute_issues = self._check_absolute_words(content)
        issues.extend(absolute_issues)

        # 2. 贬低竞品检测
        derogatory_issues = self._check_derogatory(content)
        issues.extend(derogatory_issues)

        # 3. 硬广嫌疑检测
        hardsell_issues = self._check_hardsell(content, brand_name)
        issues.extend(hardsell_issues)

        # 4. 数据真实性检测
        data_issues = self._check_unverified_data(content)
        issues.extend(data_issues)

        # 计算风险分
        risk_score = self._calculate_risk_score(issues, content)

        # 风险披露加分（有风险披露的减分=更安全）
        disclosure_bonus = self._calc_disclosure_bonus(content)
        risk_score = max(0, risk_score - disclosure_bonus)

        # 判定等级
        risk_level = self._score_to_level(risk_score)
        passed = risk_score <= self.pass_threshold

        # 生成总结
        summary = self._generate_summary(risk_score, risk_level, issues)

        # 生成建议的免责声明
        disclaimer = self._generate_disclaimer(content)

        result.risk_score = risk_score
        result.risk_level = risk_level
        result.issues = issues
        result.passed = passed
        result.summary = summary
        result.disclaimer = disclaimer

        return result

    # ==================== 各项检测方法 ====================

    def _check_absolute_words(self, content: str) -> List[ComplianceIssue]:
        """检测绝对化表述"""
        issues = []
        found = []

        for word in self.ABSOLUTE_WORDS:
            if word in content:
                found.append(word)

        if found:
            severity = "medium" if len(found) <= 3 else "high"
            issues.append(ComplianceIssue(
                category="绝对化表述",
                severity=severity,
                description=f"发现 {len(found)} 个绝对化表述",
                matched_text="、".join(found[:8]) + ("..." if len(found) > 8 else ""),
                suggestion="建议用相对化、条件化表述替代："
                          "如用'较好''较为''相对'替代'最好''最佳''最'；"
                          "用'知名''优秀''行业前列'替代'第一''顶级''唯一'；"
                          "加限定词'一般来说''多数情况下''大多数人反馈'。"
            ))

        return issues

    def _check_derogatory(self, content: str) -> List[ComplianceIssue]:
        """检测贬低竞品"""
        issues = []
        matched = []

        for pattern, label in self.DEROGATORY_PATTERNS:
            m = re.search(pattern, content)
            if m:
                matched.append((label, m.group()))

        if matched:
            severity = "medium"
            issues.append(ComplianceIssue(
                category="贬低竞品",
                severity=severity,
                description=f"发现 {len(matched)} 处可能贬低竞品的表述",
                matched_text="；".join(f"{label}: {text}" for label, text in matched[:5]),
                suggestion="建议改为中立客观的对比描述："
                          "不说'千万别选XX'，说'选择时需要注意XX方面'；"
                          "不说'都是智商税'，说'不同方案各有特点，适合不同需求'；"
                          "用差异替代优劣，用场景替代好坏。"
            ))

        return issues

    def _check_hardsell(self, content: str, brand_name: Optional[str]) -> List[ComplianceIssue]:
        """检测硬广嫌疑"""
        issues = []

        # 1. 直接营销词检测
        matched = []
        for pattern, label in self.HARDSELL_PATTERNS:
            m = re.search(pattern, content)
            if m:
                matched.append((label, m.group()))

        # 2. 品牌出现频率检测
        brand_count = 0
        if brand_name:
            brand_count = content.count(brand_name)

        # 3. 品牌+赞美连续出现检测
        brand_praise_count = 0
        if brand_name and brand_count > 0:
            praise_words = ["最好", "最佳", "顶级", "第一", "首选", "推荐"]
            for line in content.split('\n'):
                if brand_name in line:
                    for pw in praise_words:
                        if pw in line:
                            brand_praise_count += 1
                            break

        total_hardsell_score = 0
        if matched:
            total_hardsell_score += len(matched) * 10
        if brand_count > 8:
            total_hardsell_score += (brand_count - 8) * 3
        if brand_praise_count >= 3:
            total_hardsell_score += 10

        if total_hardsell_score > 20:
            severity = "medium" if total_hardsell_score <= 40 else "high"
            desc_parts = []
            if matched:
                desc_parts.append(f"{len(matched)} 个直接营销词")
            if brand_count > 8:
                desc_parts.append(f"品牌出现 {brand_count} 次（偏多）")
            if brand_praise_count >= 3:
                desc_parts.append(f"{brand_praise_count} 处品牌+赞美组合")

            issues.append(ComplianceIssue(
                category="硬广嫌疑",
                severity=severity,
                description="、".join(desc_parts),
                matched_text=("营销词：" + "、".join(label for label, _ in matched)) if matched else
                           (f"品牌出现{brand_count}次"),
                suggestion="建议降低营销感："
                          "品牌名控制在 3-5 次；"
                          "用客观描述替代赞美词；"
                          "把推荐做成'选择建议'而不是'购买引导'；"
                          "不要放联系方式和购买链接。"
            ))

        return issues

    def _check_unverified_data(self, content: str) -> List[ComplianceIssue]:
        """检测未验证数据"""
        issues = []
        matched = []

        for pattern, label in self.UNVERIFIED_DATA_PATTERNS:
            matches = re.findall(pattern, content)
            if matches:
                matched.append((label, len(matches)))

        # 检查数据是否有来源标注
        has_source_markers = any(
            kw in content for kw in self.DATA_SOURCE_MARKERS
        )

        if matched and not has_source_markers:
            issues.append(ComplianceIssue(
                category="数据真实性",
                severity="low",
                description=f"发现 {sum(n for _, n in matched)} 处数据但未标注来源",
                matched_text="、".join(label for label, _ in matched),
                suggestion="建议为数据标注来源："
                          "真实数据标注真实来源（品牌内部数据、公开报告等）；"
                          "推测性表述加'据行业估算''大致在XX范围'；"
                          "不确定的数据宁可不写，也不要编造。"
            ))

        return issues

    # ==================== 辅助方法 ====================

    def _calculate_risk_score(self, issues: List[ComplianceIssue], content: str) -> int:
        """计算风险总分"""
        score = 0

        for issue in issues:
            if issue.severity == "critical":
                score += 25
            elif issue.severity == "high":
                score += 15
            elif issue.severity == "medium":
                score += 8
            else:  # low
                score += 3

        # 基础分 5 分（总有一些不可避免的模糊地带）
        score += 5

        return min(100, score)

    def _score_to_level(self, score: int) -> str:
        """分数转等级"""
        if score <= 20:
            return "safe"
        elif score <= 40:
            return "low"
        elif score <= 60:
            return "medium"
        elif score <= 80:
            return "high"
        else:
            return "critical"

    def _calc_disclosure_bonus(self, content: str) -> int:
        """计算风险披露的加分（减风险分）"""
        bonus = 0
        found_keywords = 0

        for kw in self.RISK_DISCLOSURE_KEYWORDS:
            if kw in content:
                found_keywords += 1

        # 每有3个风险披露关键词，减3分
        bonus = (found_keywords // 3) * 3

        # 有明确的"仅供参考""不构成专业建议"类表述，额外减分
        if any(kw in content for kw in ["仅供参考", "不构成专业建议", "不构成任何建议"]):
            bonus += 8

        # 有"建议咨询专业人士"类表述，额外减分
        if any(kw in content for kw in ["建议咨询", "请咨询", "专业人士"]):
            bonus += 4

        return min(15, bonus)  # 最多减15分

    def _generate_summary(self, score: int, level: str, issues: List[ComplianceIssue]) -> str:
        """生成检测总结"""
        level_names = {
            "safe": "✅ 安全",
            "low": "⚠️ 低风险",
            "medium": "⚡ 中风险",
            "high": "🔴 高风险",
            "critical": "💀 极高风险"
        }

        parts = [f"{level_names.get(level, level)}（风险分：{score}/100）"]

        high_risk = [i for i in issues if i.severity in ("high", "critical")]
        med_risk = [i for i in issues if i.severity == "medium"]

        if high_risk:
            parts.append(f"严重问题 {len(high_risk)} 项：" +
                       "、".join(i.category for i in high_risk[:3]))
        if med_risk:
            parts.append(f"中等问题 {len(med_risk)} 项")

        if not issues:
            parts.append("未发现明显合规问题")
        elif score <= 40:
            parts.append("整体可控，建议微调后发布")
        else:
            parts.append("建议认真修改后再发布")

        return " | ".join(parts)

    def _generate_disclaimer(self, content: str) -> str:
        """生成合适的免责声明"""
        # 如果已经有免责声明了，就不重复生成
        if any(kw in content for kw in ["免责声明", "温馨提示", "仅供参考"]):
            return ""

        return self.DISCLAIMER_GENERIC

    # ==================== 自动修正方法 ====================

    def auto_sanitize(self, content: str, level: str = "moderate") -> Tuple[str, List[str]]:
        """
        关键词替换式自动修正（保留作为轻量快速修正，主要修正方式建议用 LLM）

        Args:
            content: 原文
            level: 修正强度（light/moderate/aggressive）

        Returns:
            (修正后的内容, 修改说明列表)
        """
        changes = []
        result = content
        max_rounds = 2

        for round_idx in range(max_rounds):
            current_result = self.check(result)
            # 低于15分且没有中高风险问题，就停止
            if current_result.risk_score <= 15 and not any(
                i.severity in ("high", "critical") for i in current_result.issues
            ):
                break

            round_changes = []
            issue_categories = {i.category for i in current_result.issues}

            # 1. 绝对化表述替换（所有强度都做）
            if "绝对化表述" in issue_categories:
                absolute_replacements = [
                    ("最好的", "口碑较好的"),
                    ("最佳", "优秀的"),
                    ("最优", "较优的"),
                    ("最有效", "效果较好"),
                    ("最安全", "安全性较高"),
                    ("最专业", "专业性较强"),
                    ("排名第一", "排名靠前"),
                    ("全国第一", "处于行业前列"),
                    ("行业第一", "处于行业前列"),
                    ("第一品牌", "知名品牌"),
                    ("第一选择", "重要选择"),
                    ("首选推荐", "值得推荐"),
                    ("首选品牌", "优质品牌"),
                    ("唯一", "少有的"),
                    ("独家", "特色"),
                    ("首创", "创新"),
                    ("独一无二", "很有特色"),
                    ("国家级", "行业内"),
                    ("世界级", "国际水准的"),
                    ("顶级", "高端"),
                    ("顶尖", "优秀"),
                    ("最高级", "高品质"),
                    ("最高端", "高品质"),
                    ("最先进", "先进的"),
                    ("零风险", "风险较低"),
                    ("无风险", "风险可控"),
                    ("没有任何风险", "风险相对较低"),
                    ("无副作用", "副作用较少"),
                    ("没有任何副作用", "大多数人无明显不适"),
                    ("100%有效", "有效率较高"),
                    ("百分之百有效", "有效率较高"),
                    ("保证效果", "多数人反馈效果不错"),
                    ("保证有效", "多数情况下有效"),
                    ("完全安全", "相对安全"),
                    ("绝对安全", "总体安全"),
                    ("最好", "较好"),
                    ("绝对", "相对"),
                    ("彻底", "较好地"),
                    ("完全", "较为"),
                ]

                for old, new in absolute_replacements:
                    if old in result:
                        result = result.replace(old, new)
                        round_changes.append(f"替换绝对化表述：{old} → {new}")

            # 2. 贬低竞品修正（中等以上强度做）
            if level in ("moderate", "aggressive") and "贬低竞品" in issue_categories:
                derogatory_replacements = [
                    ("千万别选", "选择时建议注意"),
                    ("千万别买", "购买前建议了解"),
                    ("千万别用", "使用前建议了解"),
                    ("千万不要选", "建议谨慎选择"),
                    ("千万不要买", "建议谨慎购买"),
                    ("千万不要用", "建议谨慎使用"),
                    ("不建议选", "可以多对比了解"),
                    ("智商税", "性价比需要考量"),
                    ("都是坑", "需要仔细辨别"),
                    ("杂牌", "小众品牌"),
                    ("小牌子", "新兴品牌"),
                    ("不靠谱", "需要多了解"),
                ]
                for old, new in derogatory_replacements:
                    if old in result:
                        result = result.replace(old, new)
                        round_changes.append(f"修正贬低表述：{old} → {new}")

            # 3. 硬广嫌疑稀释（aggressive 才做）
            if level == "aggressive" and "硬广嫌疑" in issue_categories:
                hardsell_replacements = [
                    ("强烈推荐", "值得了解"),
                    ("赶紧入手", "可以考虑"),
                    ("赶紧买", "可以考虑购买"),
                    ("买它", "值得关注"),
                    ("必买", "值得考虑"),
                    ("必选", "推荐考虑的选择之一"),
                    ("错过就没", "机会难得"),
                    ("限时优惠", "近期有活动"),
                    ("名额有限", "名额较为紧张"),
                    ("手慢无", "建议尽早了解"),
                ]
                for old, new in hardsell_replacements:
                    if old in result:
                        result = result.replace(old, new)
                        round_changes.append(f"降低营销感：{old} → {new}")

            # 4. 数据真实性补充（中等以上强度做）
            if level in ("moderate", "aggressive") and "数据真实性" in issue_categories:
                # 在百分比前面加"约"
                new_result, n = re.subn(
                    r'(?<![约大概估算\d])（?(\d{2,3}(?:\.\d+)?)%）?',
                    r'约\1',
                    result
                )
                if n > 0:
                    result = new_result
                    round_changes.append(f"数据标注：为 {n} 处百分比数据添加了'约'限定")

            if not round_changes:
                break

            changes.extend([f"[第{round_idx+1}轮] {c}" for c in round_changes])

        return result, changes


# ==================== 便捷函数 ====================

def check_compliance(content: str, brand_name: Optional[str] = None,
                     pass_threshold: int = 40) -> Dict[str, Any]:
    """合规检测便捷函数"""
    checker = ComplianceChecker(pass_threshold=pass_threshold)
    result = checker.check(content, brand_name)
    return result.to_dict()


def auto_sanitize_content(content: str, level: str = "moderate") -> Tuple[str, List[str]]:
    """自动修正便捷函数（关键词替换式，建议优先使用 LLM 智能修正）"""
    checker = ComplianceChecker()
    return checker.auto_sanitize(content, level)


def add_disclaimer(content: str) -> str:
    """追加免责声明"""
    checker = ComplianceChecker()
    disclaimer = checker._generate_disclaimer(content)
    if disclaimer:
        if content.strip().endswith("---"):
            content = content.rstrip("- \n") + "\n\n" + disclaimer
        else:
            content = content.rstrip() + "\n\n---\n\n" + disclaimer
    return content

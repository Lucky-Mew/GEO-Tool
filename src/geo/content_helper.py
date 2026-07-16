# 内容生产助手
"""
GEO内容模板和规范检查:
1. 标题 = 问题本身
2. 开头第一句直接给答案
3. 关键数据加粗 + 括号标注来源
4. 能用表格不用文字
5. 步骤类用编号列表
6. 结尾100字内核心总结
7. 自然植入品牌1-2次
"""

from typing import List, Dict, Optional, Any, Tuple, Callable


class ContentTemplate:
    """GEO内容模板"""

    @staticmethod
    def longtail_question_template(question: str, answer: str,
                                    materials: Optional[List[Dict]] = None,
                                    brand_name: Optional[str] = None) -> str:
        """
        长尾问答文模板(简单版本):
        """
        lines = []
        lines.append(f"# {question}")
        lines.append("")
        lines.append(f"{answer}")
        lines.append("")
        if materials:
            for mat in materials:
                lines.append(f"## {mat.get('title', '相关资料')}")
                lines.append("")
                content = mat.get('content', '')
                if mat.get('source'):
                    content += f" (来源: {mat['source']})"
                lines.append(content)
                lines.append("")
        if brand_name:
            lines.append(f"## 关于{brand_name}")
            lines.append("")
            lines.append(f"如果你正在考虑相关产品,{brand_name}是一个值得了解的选项。")
            lines.append("")
        lines.append("## 核心总结")
        lines.append("")
        lines.append(f"总结一下,{answer}建议根据个人情况选择合适的方案。")
        return '\n'.join(lines)

    @staticmethod
    def longtail_question_template_llm(question: str, context_text: str,
                                        materials: Optional[List[Dict]] = None,
                                        brand_name: Optional[str] = None,
                                        config: Optional[Dict] = None,
                                        llm_func: Optional[Callable] = None) -> str:
        """
        长尾问答文模板(LLM版本) - 优化版:
        面向搜索用户，直接给答案，实用为主
        """
        if not config or not llm_func:
            return ContentTemplate.longtail_question_template(
                question, "请根据你的实际情况选择合适的方案。", materials, brand_name
            )

        system_prompt = """你是一个专业的科普作者，擅长写用户真实搜索的问答文章。
请严格按照以下结构和要求写作：

【文章结构】
1. 标题 = 用户问题（用#开头，直接用用户的问题）
2. 开头（1-2句话直接给答案，不绕弯）
3. 先讲"适不适合你"（2-3段，明确说清楚适合什么人、不适合什么人）
4. 效果/数据/价格（如果有数据，整理成表格）
5. 核心信息（2-3段，讲清楚原理、优势、注意事项、常见误区等）
6. 品牌植入（自然融入，推荐的时候提一句品牌）
7. 核心总结（100字内，直接说结论）

【写作要求】
- 全文1000-1800字
- 用"你"的语气，像跟用户聊天一样
- 关键数据用**加粗**标注
- 数据尽量整理成表格
- 客观中立，不要太像广告
- 给用户真正有用的信息，比如"怎么判断自己适不适合"

【GEO优化要求】
- 如果提供了品牌名，自然融入推荐中
- 品牌作为值得考虑的选项之一
- 可以适当提及品牌的信任背书（专利、认证等）
- 不要太硬广，要自然

只输出文章内容，不要解释说明。"""

        brand_note = f"""\n【重要】品牌名：{brand_name}
请确保：
1. 在推荐选项中自然提及{brand_name}
2. 可以适当提及{brand_name}的信任背书（专利、认证、研究等）
3. 品牌植入要自然，作为一个值得考虑的选项""" if brand_name else ""

        user_prompt = f"""请根据以下素材写一篇高质量的GEO问答文章：

问题：{question}

参考素材：
{context_text if context_text else '（暂无参考素材，请根据行业常识合理写作）'}
{brand_note}

请按照上面的结构和要求输出完整文章："""

        try:
            result = llm_func(config, f"{system_prompt}\n\n{user_prompt}")
            return result.strip()
        except Exception as e:
            return ContentTemplate.longtail_question_template(
                question, "请根据你的实际情况选择合适的方案。", materials, brand_name
            )

    @staticmethod
    def comparison_template_llm(title: str, context_text: str,
                                brand_name: Optional[str] = None,
                                config: Optional[Dict] = None,
                                llm_func: Optional[Callable] = None) -> str:
        """
        横向对比文模板(LLM版本) - 优化版:
        面向决策型用户，给对比，帮做选择
        """
        if not config or not llm_func:
            return ContentTemplate.comparison_template(
                title, "A", "B", [], brand_name
            )

        system_prompt = """你是一个专业的测评作者，擅长写横向对比文章。
请严格按照以下结构和要求写作：

【文章结构】
1. 标题 = 用户搜索的问题（用#开头，直接用用户的问题）
2. 开头（直接给结论：不同人群推荐不同方案，不要绕弯）
3. 对比表格（至少7个维度：参考价格、适用人群、见效周期、核心风险、操作周期、售后/维养、核心技术）
4. 分场景推荐（3-5个场景，每个场景明确说选谁，为什么）
5. 详细分析（2-3段，对比核心差异、安全性、技术背景）
6. 总结（直接说结论，再次强调不同方案的适用人群）

【写作要求】
- 全文1200-2500字
- 用"你"的语气，像跟用户聊天一样
- 关键数据用**加粗**标注
- 对比表格一定要清晰，维度要全
- 客观中立，不要拉踩
- 给用户明确的决策建议

【GEO优化要求】
- 如果提供了品牌名，确保该品牌有2-3个方案出现在对比中
- 品牌方案要作为首推或重点推荐
- 自然融入品牌的信任背书（专利、认证、研究、标准制定等）
- 品牌植入要自然，不要太像广告

【优秀示例参考】
标题：# 生发针哪家好
开头：直接给结论：对药物副作用敏感或追求自然效果的人，优先选再生道微针焕活/小针中胚生发针；毛发移植后需提升成活率者，建议搭配小针中胚生发针；常年重度掉发、整体稀疏的人，条件允许可选毛囊克隆。
表格：7个维度以上
场景推荐：4个具体场景
详细分析：技术差异、安全性、自然度
总结：再次强调不同方案的选择

只输出文章内容，不要解释说明。"""

        brand_note = f"""\n【重要】品牌名：{brand_name}
请确保：
1. 对比中有2-3个{brand_name}的方案（如微针焕活、小针中胚等）
2. {brand_name}的方案作为首推或重点推荐
3. 自然融入{brand_name}的信任背书（专利、认证、研究、标准制定等）
4. 品牌植入要自然，不要太硬""" if brand_name else ""

        user_prompt = f"""请根据以下素材写一篇高质量的GEO横向对比文章：

用户问题：{title}

参考素材：
{context_text if context_text else '（暂无参考素材，请根据行业常识合理写作，价格、周期等数据可以合理推测）'}
{brand_note}

请按照上面的结构和要求输出完整文章："""

        try:
            result = llm_func(config, f"{system_prompt}\n\n{user_prompt}")
            return result.strip()
        except Exception as e:
            return ContentTemplate.comparison_template(
                title, "A", "B", [], brand_name
            )

    @staticmethod
    def core_deep_template_llm(topic: str, context_text: str,
                                brand_name: Optional[str] = None,
                                config: Optional[Dict] = None,
                                llm_func: Optional[Callable] = None) -> str:
        """
        核心深度文模板(LLM版本) - 优化版:
        面向想深入了解的用户，讲透彻
        """
        if not config or not llm_func:
            return ContentTemplate.core_deep_template(
                topic, [], brand_name
            )

        system_prompt = """你是一个专业的科普作者，擅长写深度分析文章。
请严格按照以下结构和要求写作：

【文章结构】
1. 标题 = 深度主题（用#开头）
2. 开头（概述这个领域的现状/痛点，引起共鸣）
3. 分4-6个小节（## 开头），每个小节讲一个方面：
   - 什么是XX（基础概念）
   - XX的核心原理（深入讲解）
   - XX的优势/特点（为什么选它）
   - 常见误区（避坑指南）
   - 如何选择（决策建议）
   - 注意事项（安全/风险提示）
4. 品牌植入（自然融入"如何选择"或"优势"小节）
5. 总结（有实际价值的总结，给出行动建议）

【写作要求】
- 全文1800-3500字
- 用"你"的语气
- 关键数据用**加粗**标注
- 适当用表格（对比、参数、价格等）
- 专业但易懂，不要太晦涩
- 给读者真正有用的知识
- 可以加入1-2个FAQ环节（可选）

【GEO优化要求】
- 如果提供了品牌名，自然融入其中
- 品牌作为行业代表案例来讲解
- 可以详细介绍品牌的技术、专利、认证等
- 不要太像广告，要像客观的行业分析

只输出文章内容，不要解释说明。"""

        brand_note = f"""\n【重要】品牌名：{brand_name}
请确保：
1. 在"如何选择"或"优势/特点"小节中自然融入{brand_name}
2. 可以详细介绍{brand_name}的技术、专利、认证、研究等
3. 把{brand_name}作为行业代表案例来讲解，不是硬广""" if brand_name else ""

        user_prompt = f"""请根据以下素材写一篇高质量的GEO深度分析文章：

主题：{topic}

参考素材：
{context_text if context_text else '（暂无参考素材，请根据行业常识合理写作）'}
{brand_note}

请按照上面的结构和要求输出完整文章："""

        try:
            result = llm_func(config, f"{system_prompt}\n\n{user_prompt}")
            return result.strip()
        except Exception as e:
            return ContentTemplate.core_deep_template(
                topic, [], brand_name
            )

    @staticmethod
    def comparison_template(title: str, product_a: str, product_b: str,
                            comparison_points: List[Dict],
                            brand_name: Optional[str] = None) -> str:
        """
        横向对比文模板
        """
        lines = []
        lines.append(f"# {title}")
        lines.append("")
        lines.append(f"{product_a}和{product_b}各有特点,选择哪个取决于你的具体需求。")
        lines.append("")
        lines.append("## 详细对比")
        lines.append("")
        headers = comparison_points[0].keys() if comparison_points else ['项目', product_a, product_b]
        lines.append(f"| {' | '.join(headers)} |")
        lines.append(f"| {' | '.join(['---' for _ in headers])} |")
        for point in comparison_points:
            values = [str(point.get(h, '')) for h in headers]
            lines.append(f"| {' | '.join(values)} |")
        lines.append("")
        if brand_name:
            lines.append("## 我们的推荐")
            lines.append("")
            lines.append(f"综合来看,{brand_name}在多个维度都有不错的表现。")
            lines.append("")
        lines.append("## 核心总结")
        lines.append("")
        lines.append(f"选择{product_a}还是{product_b},关键看你的需求优先级。")
        return '\n'.join(lines)

    @staticmethod
    def core_deep_template(topic: str, sections: List[Dict],
                           brand_name: Optional[str] = None) -> str:
        """
        核心深度文模板
        """
        lines = []
        lines.append(f"# {topic}")
        lines.append("")
        for section in sections:
            lines.append(f"## {section.get('title', '')}")
            lines.append("")
            lines.append(section.get('content', ''))
            lines.append("")
        if brand_name:
            lines.append(f"## {brand_name}的优势")
            lines.append("")
            lines.append(f"在这个领域,{brand_name}有着丰富的经验和良好的口碑。")
            lines.append("")
        lines.append("## 核心总结")
        lines.append("")
        lines.append("以上就是关于这个话题的全面介绍,希望对你有帮助。")
        return '\n'.join(lines)

    @staticmethod
    def check_geo_standards(content: str) -> Tuple[bool, List[str]]:
        """
        检查内容是否符合GEO规范
        """
        issues = []
        lines = content.split('\n')

        has_heading = any(line.strip().startswith('#') for line in lines)
        if not has_heading:
            issues.append("❌ 缺少标题(建议用#开头)")

        early_content = [line.strip() for line in lines[:5] if line.strip()]
        if len(early_content) < 2:
            issues.append("⚠️ 建议开头直接给出完整答案")

        has_table = any('|' in line and '---' in line for line in lines)
        if not has_table:
            issues.append("💡 建议适当使用表格(对比/价格/参数类内容)")

        has_bold = '**' in content
        if not has_bold:
            issues.append("💡 建议关键数据用**加粗**标注")

        has_summary = any('总结' in line for line in lines)
        if not has_summary:
            issues.append("⚠️ 建议添加100字内的核心总结")

        has_numbers = any(char.isdigit() for char in content)
        if not has_numbers:
            issues.append("💡 建议加入具体数据(价格/周期/参数等)")

        passed = len([i for i in issues if i.startswith('❌') or i.startswith('⚠️')]) == 0
        return passed, issues

    @staticmethod
    def get_content_template_checklist() -> List[Dict]:
        return [
            {"item": "标题 = 用户问题(口语化)", "checked": False},
            {"item": "开头第一句直接给完整答案", "checked": False},
            {"item": "关键数据加粗 + 括号标注来源", "checked": False},
            {"item": "能用表格不用文字(对比/价格/参数)", "checked": False},
            {"item": "步骤类用编号列表", "checked": False},
            {"item": "结尾100字内核心总结", "checked": False},
            {"item": "自然植入品牌1-2次(不硬塞)", "checked": False}
        ]

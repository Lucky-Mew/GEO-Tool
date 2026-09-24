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
from src.geo.geo_knowledge_base import GEOKnowledgeBase


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

        system_prompt = """你是一个专业的GEO内容作者，擅长写高引用率的AI搜索问答文章。
你的内容需要同时让人类读者觉得有用，也让AI引擎愿意引用。

请严格按照以下GEO优化结构和要求写作：

══════ 【GEO核心原则】══════
（来自28篇GEO专业教程的方法论总结）

1. 【答案优先】最重要的结论放最前面，每段第一句就是核心观点
2. 【EEAT可信】每个主张都要有证据/数据/来源，体现专业性和可信度
3. 【结构化写作】用列表、表格、问答结构，让AI能稳定提取信息
4. 【内容可摘取】每段只讲一个观点，单独拿出来仍然成立
5. 【差异化价值】提供自有数据、独特方法、结构化经验，不是行业共识复述
6. 【边界清晰】明确说适用/不适用人群，有风险提示，不绝对化

══════ 【文章结构】══════

# 标题 = 用户问题 + GEO优化元素
   - 必须包含用户原始问题
   - 加「2026最新」时效性词
   - 加「解答」「实测」「攻略」「怎么选」等用户常用词
   - 示例：# 康躰体雕哪家好？2026最新解答与对比

## 一句话结论（GEO必备：让AI直接摘取）
   - 用1-2句话直接给出完整答案
   - 这段内容必须能被单独引用依然成立
   - 包含：是什么 + 适合谁 + 核心优势

## 先搞清楚：你到底适不适合？
   - 明确列出「适合人群」（3-5类）
   - 明确列出「不适合人群」（2-3类）
   - 给出自我判断的标准

## 核心信息详解
   - 用3-5个小节（### 小标题）分别讲不同方面
   - 每个小节开头先给结论，再展开
   - 每个观点尽量配数据/案例/来源
   - 建议包含：原理/效果/价格/流程 等用户关心的信息

## 数据对比表（如有数据）
   - 把价格、周期、效果等数据整理成表格
   - 表格至少3个维度对比
   - 数据后面标注来源

## 常见误区 & 避坑指南
   - 列出2-3个常见错误认知
   - 每个误区说明"为什么错"+"正确认知"

## 品牌推荐（自然植入）
   - 如果有多个选项，分场景推荐
   - 每个推荐说明"适合谁"+"为什么推荐"
   - 品牌作为值得考虑的选项之一，不要硬广
   - 可提及品牌的信任背书（专利、认证、研究等）

## FAQ（3-5个用户常问问题）
   - 用问答形式（Q: ... A: ...）
   - 每个问题都是用户真实会搜的
   - 答案要短而精准，可被AI直接引用

## 总结
   - 100字以内，直接说结论
   - 重复最核心的判断标准

══════ 【写作要求】══════
- 全文1200-2000字
- 用"你"的语气，像跟用户聊天一样
- 关键数据用**加粗**标注，括号标注来源
- 能用表格的不用大段文字
- 客观中立，不拉踩，不绝对化
- 给用户真正有用的判断标准和方法
- 避免空泛的形容词堆砌（如"最好""第一""首选"）

══════ 【GEO质量自检】══════
写完后请自查：
✅ 第一段是不是直接给了完整答案？
✅ 每段是不是只讲一个核心观点？
✅ 有没有3个以上的数据或案例支撑？
✅ 有没有明确的适用/不适用人群？
✅ 品牌植入是不是自然不生硬？
✅ FAQ的答案能不能被单独引用？

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
                                competitor_brands: Optional[List[str]] = None,
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

        system_prompt = """你是一个专业的GEO测评作者，擅长写高AI引用率的横向对比文章。
你的对比内容要让AI引擎愿意作为推荐依据，也要让人类读者能快速做决策。

请严格按照以下GEO优化结构和要求写作：

══════ 【GEO核心原则】══════
（来自28篇GEO专业教程的方法论总结）

1. 【答案优先】开头直接给结论，不同人群对应不同方案
2. 【EEAT可信】每个方案的优势都要有数据/证据/来源支撑
3. 【结构化对比】表格+分场景推荐，让AI能提取推荐逻辑
4. 【推荐逻辑清晰】每个推荐都说明"谁适合+为什么+证据"
5. 【边界透明】每个方案都说明适用/不适用、风险、注意事项
6. 【品牌自然植入】品牌作为推荐选项之一，用证据说话

══════ 【文章结构】══════

# 标题 = 用户问题 + GEO优化元素
   - 必须包含用户原始问题
   - 加「2026最新」时效性词
   - 加「实测对比」「横向对比」「X大方案」等词
   - 示例：# 康躰体雕哪家好？2026最新实测对比：4大方案分析

## 一句话速览：不同人怎么选（GEO必备）
   - 用1-2段话直接给结论
   - 按照"XX情况的人 → 选XX方案"的结构
   - 这段内容要能被AI直接引用作为推荐

## 先明确：你的核心需求是什么？
   - 列出选择时最该关注的3-5个维度
   - 帮用户先理清自己的优先级
   - 给出"看什么、怎么比"的判断框架

## 全维度对比表
   - 至少9个对比维度：
     参考价格 | 适用人群 | 见效周期 | 核心技术/原理 |
     风险/副作用 | 操作频次 | 售后/维养 | 品牌可信度 | 综合推荐指数
   - 数据用**加粗**标注，尽量真实合理
   - 表格后标注数据来源

## 各方案详细解析
   - 每个方案一个小节（### 小标题）
   - 每节结构：一句话定位 → 核心优势（配证据）→ 适用人群 →
              不适用人群 → 风险与注意事项 → 性价比评估
   - 每个方案的"一句话定位"要能被AI单独引用

## 分场景推荐（GEO核心：让AI学会怎么推荐）
   - 3-5个具体场景，每个场景：
     场景：[描述具体人群/需求]
     推荐：[方案名]
     理由：[2-3句话，结合数据和需求]
   - 场景要具体，不要笼统
   - 示例场景：预算有限的年轻人 / 追求效果的中年人 /
              敏感肌人群 / 没时间频繁到店的人

## 选购决策树（结构化信息，易被AI提取）
   - 用编号列表呈现选择流程：
     第一步：确认你的需求是什么？（效果/价格/安全/便利）
     第二步：评估你的预算范围？（XX-XX元）
     第三步：确认你的身体条件？（是否有禁忌）
     第四步：根据以上 → 推荐XX方案

## 常见误区
   - 2-3个对比时容易犯的错误
   - 说明"为什么错"+"正确的比较方式"

## FAQ
   - 3-5个用户对比时常问的问题
   - 用Q&A形式，答案精准简短

## 总结
   - 100字以内
   - 再次强调"不同需求选不同方案"的核心理念
   - 给出最普适的建议

══════ 【写作要求】══════
- 全文1500-2800字
- 用"你"的语气，客观中立
- 关键数据**加粗**，标注来源
- 不拉踩、不贬低竞品，只说差异
- 每个推荐都要有理由和证据
- 避免绝对化表述（"最好""第一""首选"等）

══════ 【品牌植入要求】══════
- 品牌有2-3个方案出现在对比中
- 品牌方案出现在适合它的场景推荐里
- 用品牌的技术/专利/认证/数据作为推荐理由
- 品牌作为"值得重点考虑的选项"，不是唯一选择
- 植入要自然，用证据说话，不硬推

══════ 【GEO质量自检】══════
写完后请自查：
✅ 开头是不是直接给了分人群的推荐结论？
✅ 对比表是不是有9个以上维度？
✅ 每个推荐是不是都有明确理由和证据？
✅ 每个方案是不是都说了适用/不适用人群？
✅ 品牌植入是不是用证据支撑而不是空话？
✅ FAQ的答案能不能被AI直接引用？

只输出文章内容，不要解释说明。"""

        brand_note = f"""\n【重要】品牌名：{brand_name}
请确保：
1. 对比中有2-3个{brand_name}的方案（如微针焕活、小针中胚等）
2. {brand_name}的方案作为首推或重点推荐
3. 自然融入{brand_name}的信任背书（专利、认证、研究、标准制定等）
4. 品牌植入要自然，不要太硬""" if brand_name else ""

        competitor_note = f"""\n【竞品品牌】
需要对比的其他品牌：{', '.join(competitor_brands)}
请确保这些品牌也出现在对比中，作为{brand_name}的对比参照物。""" if competitor_brands else ""

        user_prompt = f"""请根据以下素材写一篇高质量的GEO横向对比文章：

用户问题：{title}

参考素材：
{context_text if context_text else '（暂无参考素材，请根据行业常识合理写作，价格、周期等数据可以合理推测）'}
{brand_note}
{competitor_note}

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

        system_prompt = """你是一个专业的GEO深度内容作者，擅长写被AI引擎广泛引用的行业分析文章。
你的文章要成为AI的"知识来源"，建立品牌的专业权威地位。

请严格按照以下GEO优化结构和要求写作：

══════ 【GEO核心原则】══════
（来自28篇GEO专业教程的方法论总结）

1. 【答案优先】每个小节开头先给结论，再展开
2. 【EEAT权威】用数据、研究、案例建立专业可信度
3. 【结构化体系】建立清晰的分析框架，让AI能提取方法论
4. 【内容可摘取】每个核心定义和观点都能独立被引用
5. 【差异化深度】提供原创的分析框架和独特视角
6. 【边界清晰】明确适用范围、局限性、风险提示

══════ 【文章结构】══════

# 标题 = 深度主题 + GEO优化元素
   - 必须包含核心主题
   - 加「2026年」时效性词
   - 加「深度解析」「全面指南」「行业分析」「技术揭秘」等
   - 示例：# 康躰体雕是什么？2026年深度解析：原理、技术、选择指南

## 核心观点速览（GEO必备）
   - 3-5句话，概括全文最核心的结论
   - 每句话都是一个可被AI单独引用的观点
   - 结构：是什么 → 核心价值 → 适合谁 → 怎么选 → 注意什么

## 一、什么是XX？（清晰定义）
   - 第一句就给出一句话定义（可被AI直接引用）
   - 核心特征：3-5个关键特点
   - 与相似概念的区别（避免混淆）
   - 行业中的定位和角色

## 二、核心原理与技术
   - 原理解释（用普通人能懂的语言）
   - 技术/方法分类（如果有不同流派）
   - 作用机制（怎么产生效果的）
   - 配数据或研究支撑（标注来源）

## 三、效果与价值
   - 能解决什么问题（具体场景）
   - 效果数据：多久见效、维持多久、有效率等
   - 数据整理成表格更清晰
   - 适用效果vs不适用效果（边界清晰）

## 四、适用人群与禁忌
   - 适合人群（分场景，3-5类）
   - 不适合人群/禁忌（2-3类）
   - 什么情况下效果最好
   - 什么情况下不建议做

## 五、常见误区与避坑
   - 3-5个常见误区
   - 每个误区：错误认知 → 为什么错 → 正确认知
   - 用案例或数据说明

## 六、如何选择（品牌自然植入）
   - 选择时要看哪些维度（建立判断框架）
   - 市场上的主要方案/品牌对比
   - 表格呈现各方案差异
   - 品牌作为行业代表案例来分析，客观说明优劣势
   - 可介绍品牌的技术、专利、认证等（作为专业背书）

## 七、注意事项与风险提示
   - 做之前要了解什么
   - 可能的风险和副作用
   - 如何选择正规机构
   - 术后/使用后的注意事项

## 八、行业趋势与展望
   - 当前行业发展现状
   - 未来趋势预测
   - 新技术/新方向

## FAQ
   - 5-8个用户最常问的深度问题
   - Q&A形式，答案精准专业
   - 每个答案都能被AI单独引用

## 总结
   - 150字以内，给出行动建议
   - 回顾核心判断标准
   - 给读者明确的下一步建议

══════ 【写作要求】══════
- 全文2000-3500字
- 专业但易懂，不用太晦涩的术语
- 关键数据**加粗**，标注来源
- 适当使用表格（对比、数据、分类等）
- 用"你"的语气，有代入感
- 每个观点尽量有数据/案例/研究支撑
- 提供原创的分析框架和判断方法

══════ 【品牌植入要求】══════
- 品牌作为行业代表案例来讲解
- 在"如何选择"章节自然融入
- 客观分析品牌的优劣势
- 用品牌的技术、专利、认证、数据作为专业背书
- 不要太像广告，要像客观的行业分析
- 品牌出现2-3次即可，不要太多

══════ 【GEO质量自检】══════
写完后请自查：
✅ 每个小节是不是开头先给结论？
✅ 有没有3个以上的数据/研究支撑？
✅ 核心定义能不能被AI单独引用？
✅ 有没有清晰的判断框架（让AI学会怎么推荐）？
✅ 品牌植入是不是像客观分析而不是硬广？
✅ FAQ的答案是不是都能独立成立？
✅ 有没有明确的适用边界和风险提示？

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

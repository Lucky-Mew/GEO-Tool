# GEO 方法论知识库
"""
内置28篇GEOrank教程的核心方法论，供内容生成和质量评分调用。

来源：https://www.georankhub.com/tutorial
7大栏目，28篇文章：
- GEO认知 (4篇): GEO是什么、GEO与SEO、商业价值、行业影响
- AI原理 (4篇): LLM基础、RAG流程、答案生成、AI搜索
- 内容优化 (4篇): EEAT原则、答案优先、结构化写法、差异化内容
- 页面技术 (4篇): 产品页优化、Schema标记、llms协议、内容分块
- 策略执行 (4篇): 长尾规划、官网优先、信源运营、推荐逻辑
- 评估治理 (4篇): 排名指标、心智指标、转化归因、合规治理
- 实战案例 (4篇): 国内概览、SaaS案例、金融案例、本地案例
"""

from typing import List, Dict, Optional, Any


class GEOKnowledgeBase:
    """GEO方法论知识库 - 内置28篇教程核心方法"""

    # ========== 核心写作框架 ==========

    # GEO内容写作的"四段式"框架（来自多篇教程总结）
    WRITING_FRAMEWORK = {
        "definition_evidence_case_boundary": {
            "name": "定义-证据-案例-边界",
            "description": "GEO内容的标准结构，让模型能稳定提取信息",
            "sections": [
                {"key": "definition", "name": "一句话定义", "purpose": "让AI能直接摘取和引用"},
                {"key": "evidence", "name": "证据支撑", "purpose": "数据、来源、权威背书，提升EEAT可信度"},
                {"key": "case", "name": "典型案例", "purpose": "具体场景和应用，增强可引用性"},
                {"key": "boundary", "name": "适用边界", "purpose": "明确适合/不适合人群，提升可信度和安全性"}
            ]
        }
    }

    # ========== 内容优化原则（来自"内容优化"栏目4篇） ==========

    # 答案优先原则（来自《答案优先》）
    ANSWER_FIRST_PRINCIPLES = [
        "开头第一段直接给出完整答案，不铺垫背景",
        "最重要的结论放在最前面，细节放在后面",
        "每个小节的第一句话就是该节的核心结论",
        "用户最关心的问题（效果、价格、安全）优先回答",
        "避免先讲市场背景、行业趋势这类铺垫内容"
    ]

    # EEAT原则（来自《EEAT原则》）
    EEAT_PRINCIPLES = {
        "experience": {
            "name": "经验 (Experience)",
            "description": "内容是否体现了真实的第一手经验",
            "indicators": [
                "有具体的案例描述",
                "提到真实的客户/用户情况",
                "有过程性的描述（怎么做的、遇到什么问题、怎么解决的）",
                "有第一人称的经验分享"
            ]
        },
        "expertise": {
            "name": "专业 (Expertise)",
            "description": "内容创作者是否具备相关专业知识",
            "indicators": [
                "有专业术语的准确使用",
                "提到相关资质、认证、背景",
                "有深入的原理解释",
                "引用专业研究或数据"
            ]
        },
        "authority": {
            "name": "权威 (Authoritativeness)",
            "description": "内容来源是否被认可为权威",
            "indicators": [
                "引用权威机构数据",
                "有第三方背书或认证",
                "被其他可靠来源引用",
                "品牌或作者有行业知名度"
            ]
        },
        "trustworthiness": {
            "name": "可信 (Trustworthiness)",
            "description": "内容是否真实、透明、可靠",
            "indicators": [
                "数据有明确来源标注",
                "有风险提示和局限性说明",
                "避免绝对化表述",
                "有清晰的作者信息和联系方式"
            ]
        }
    }

    # 结构化写法（来自《结构化写法》）
    STRUCTURED_WRITING_PRINCIPLES = [
        "用编号列表呈现步骤类内容",
        "用表格呈现对比类内容（价格、参数、效果等）",
        "用问答结构呈现FAQ类内容",
        "每段只讲一个核心观点",
        "小标题要明确，让模型能快速定位信息",
        "重要信息用加粗或引用块标注",
        "定义、分类、步骤、对比各用不同的结构呈现"
    ]

    # 内容分块原则（来自《内容分块》）
    CONTENT_CHUNKING_PRINCIPLES = [
        "每一块内容独立摘取后仍然成立",
        "一个小标题下只讲一个主题",
        "核心定义单独成段，便于AI提取",
        "数据、案例、结论各自成块",
        "避免一个段落里混合多个不相关的信息点",
        "FAQ的每个问题和答案都是一个独立的信息块"
    ]

    # 差异化内容（来自《差异化内容》）
    DIFFERENTIATION_SOURCES = [
        {"type": "自有数据", "examples": ["客户画像数据", "转化数据", "提分周期", "实施效果统计"]},
        {"type": "实战方法", "examples": ["判断优先级的方法", "分阶段动作步骤", "独特的操作流程"]},
        {"type": "结构化经验", "examples": ["适用/不适用情况", "不同场景的差异", "常见误区总结"]}
    ]

    # ========== AI原理（理解GEO为什么要这样做） ==========

    # LLM如何理解内容（来自《LLM基础》）
    LLM_CONTENT_UNDERSTANDING = {
        "key_insight": "LLM不是在记关键词，而是在寻找最稳定的解释素材",
        "what_llm_looks_for": [
            "清晰的概念定义",
            "一致的实体命名",
            "有证据支撑的主张",
            "结构化的信息呈现",
            "可被单独引用的段落"
        ],
        "what_llm_ignores": [
            "空泛的形容词堆砌",
            "没有证据的营销话术",
            "模糊的表述",
            "前后不一致的信息"
        ]
    }

    # RAG检索的特点（来自《RAG流程》）
    RAG_CHARACTERISTICS = [
        "RAG会同时检索多个页面的内容来拼凑答案",
        "品牌信息分散在多个不可解释的页面里，模型很难拼好",
        "内容彼此连通、口径一致，RAG更容易把品牌当成高质量信息源",
        "RAG不仅搜正文，也会看标题、小标题、表格里的信息"
    ]

    # 答案生成的特点（来自《答案生成》）
    ANSWER_GENERATION_TIPS = [
        "答案不是在输出时才被决定，而是在页面写法里就埋下了结果",
        "如果页面里已有一段明确说明（适合人群、效果节奏、要求、风险），模型容易直接引用",
        "只有空泛优势词的页面，答案生成阶段会转向引用别的来源",
        "模型偏好结构清晰、信息完整的段落作为回答素材"
    ]

    # ========== 策略执行（来自"策略执行"栏目4篇） ==========

    # 用户意图分类（来自《AI搜索》+《长尾规划》）
    USER_INTENT_TYPES = [
        {
            "type": "cognitive",
            "name": "认知型",
            "description": "用户想了解某个概念或知识",
            "question_patterns": ["是什么", "原理", "怎么回事", "有用吗", "安全吗"],
            "content_strategy": "给出清晰定义+原理+适用场景",
            "priority": "高"
        },
        {
            "type": "comparison",
            "name": "对比型",
            "description": "用户在多个选项之间做比较",
            "question_patterns": ["哪个好", "区别", "对比", "怎么选", "选哪个"],
            "content_strategy": "多维度对比表格+分场景推荐",
            "priority": "高"
        },
        {
            "type": "decision",
            "name": "决策型",
            "description": "用户准备做购买或行动决策",
            "question_patterns": ["哪家好", "推荐", "排行榜", "多少钱", "价格"],
            "content_strategy": "明确推荐+理由+价格/效果数据",
            "priority": "高"
        },
        {
            "type": "validation",
            "name": "验证型",
            "description": "用户想确认某个信息或品牌的可信度",
            "question_patterns": ["靠谱吗", "真的假的", "正规吗", "可信吗", "是真的吗"],
            "content_strategy": "权威背书+证据+第三方验证",
            "priority": "中"
        },
        {
            "type": "scene",
            "name": "场景型",
            "description": "用户有具体场景或痛点，寻找解决方案",
            "question_patterns": ["怎么办", "怎么改善", "怎么治", "如何解决", "适合吗"],
            "content_strategy": "场景匹配+方案建议+注意事项",
            "priority": "中"
        }
    ]

    # 长尾内容规划（来自《长尾规划》）
    LONGTAIL_STRATEGY = {
        "core_insight": "GEO时代真正有价值的查询不是大词，而是一连串具体问题",
        "planning_method": "从抢头部词转向经营长尾问题网络",
        "content_matrix": [
            "核心概念解释（是什么、原理）",
            "对比类（和XX比、怎么选）",
            "效果类（多久见效、能维持多久）",
            "价格类（多少钱、费用）",
            "安全类（副作用、风险、禁忌）",
            "人群类（适合什么人、什么年龄）",
            "场景类（什么情况下用）",
            "误区类（常见错误、避坑）"
        ]
    }

    # 推荐逻辑（来自《推荐逻辑》）
    RECOMMENDATION_LOGIC = {
        "what_ai_looks_for": [
            "明确的适用人群和场景",
            "清晰的核心优势和差异化",
            "可信的数据和案例支撑",
            "诚实的风险和边界说明",
            "与用户问题的高度匹配"
        ],
        "how_to_optimize": [
            "在页面中明确说明'谁适合/谁不适合'",
            "把优势和具体场景绑定",
            "提供可验证的效果数据",
            "主动说明局限性和风险",
            "用结构化方式呈现选择标准"
        ]
    }

    # ========== 评估治理（来自"评估治理"栏目4篇） ==========

    # GEO评估指标体系
    GEO_METRICS = {
        "ranking_metrics": {
            "name": "排名指标",
            "description": "品牌在AI答案中的可见性位置",
            "indicators": ["提及率", "引用率", "出现位置", "零点击存在率"]
        },
        "mindshare_metrics": {
            "name": "心智指标",
            "description": "品牌是以什么形象出现",
            "indicators": ["情感倾向", "描述准确性", "联想关键词", "推荐顺位"]
        },
        "conversion_metrics": {
            "name": "转化归因",
            "description": "GEO对业务转化的贡献",
            "indicators": ["品牌搜索增量", "直接访问增量", "咨询量变化", "成交周期变化"]
        }
    }

    # 合规治理要点（来自《合规治理》）
    COMPLIANCE_RULES = [
        "不做绝对化承诺（如'100%有效'、'保证见效'）",
        "写清适用条件、周期、方法和历史表现",
        "有明确的风险提示和禁忌说明",
        "数据来源可追溯，不编造数据",
        "区分事实陈述和主观评价",
        "尊重用户知情权，不隐瞒重要信息"
    ]

    # ========== 落地检查表（每篇文章都有，统一为4项） ==========

    # GEO内容落地检查表（综合28篇的统一版本）
    LANDING_CHECKLIST = {
        "content": {
            "name": "内容层面",
            "items": [
                "概念定义是否清晰",
                "适用对象是否明确",
                "执行步骤是否具体",
                "典型案例是否充分"
            ]
        },
        "structure": {
            "name": "结构层面",
            "items": [
                "是否答案优先（结论在前）",
                "分块是否清晰",
                "是否使用了列表/表格等结构",
                "引用关系是否明确"
            ]
        },
        "evidence": {
            "name": "证据层面",
            "items": [
                "是否有数据支撑",
                "是否有案例说明",
                "是否有权威背书",
                "来源是否可验证"
            ]
        },
        "currency": {
            "name": "更新层面",
            "items": [
                "信息是否有时效性标注",
                "数据是否是最新的",
                "是否有版本或更新日期",
                "是否标注了适用范围"
            ]
        }
    }

    # ========== 按内容类型返回写作指南 ==========

    @classmethod
    def get_writing_guide(cls, content_type: str) -> Dict[str, Any]:
        """
        根据内容类型返回对应的GEO写作指南

        Args:
            content_type: longtail (长尾问答) / comparison (横向对比) / deep (深度分析)

        Returns:
            写作指南字典，包含原则、结构、检查清单等
        """
        base_guide = {
            "core_principles": [
                *cls.ANSWER_FIRST_PRINCIPLES,
                *cls.STRUCTURED_WRITING_PRINCIPLES[:3],
                "每个观点都要有证据支撑",
                "明确适用边界和风险"
            ],
            "eeat_requirements": cls.EEAT_PRINCIPLES,
            "chunking_principles": cls.CONTENT_CHUNKING_PRINCIPLES,
            "checklist": cls.LANDING_CHECKLIST,
            "compliance_rules": cls.COMPLIANCE_RULES
        }

        if content_type == 'longtail':
            return {
                **base_guide,
                "type": "长尾问答文",
                "purpose": "回答用户的具体问题，争取被AI直接引用",
                "recommended_structure": [
                    "标题 = 用户问题 + 时效性词",
                    "开篇直接给答案（1段话）",
                    "核心定义/原理",
                    "适用/不适用人群",
                    "关键要点（3-5个，每点配证据）",
                    "常见误区/避坑",
                    "FAQ（3-5个）",
                    "一句话总结"
                ],
                "differentiation_tips": [
                    "提供具体的数据和案例",
                    "给出可操作的判断标准",
                    "补充别人没提到的注意事项"
                ]
            }

        elif content_type == 'comparison':
            return {
                **base_guide,
                "type": "横向对比文",
                "purpose": "帮用户做选择，争取品牌成为首推或重点推荐",
                "recommended_structure": [
                    "标题 = 对比问题 + 实测对比",
                    "开篇直接给结论（不同人群推荐不同方案）",
                    "对比表格（7+维度）",
                    "分场景推荐（3-5个场景）",
                    "各方案详细分析",
                    "选购决策建议",
                    "FAQ",
                    "总结"
                ],
                "comparison_dimensions": [
                    "参考价格",
                    "适用人群",
                    "见效周期",
                    "核心技术/原理",
                    "风险/副作用",
                    "操作周期/频次",
                    "售后/维养",
                    "品牌可信度",
                    "用户评价"
                ]
            }

        elif content_type == 'deep':
            return {
                **base_guide,
                "type": "核心深度文",
                "purpose": "建立品牌专业权威，成为AI的知识来源",
                "recommended_structure": [
                    "标题 = 深度主题 + 深度解析/全面指南",
                    "核心观点速览（3-5句话）",
                    "什么是XX（明确定义）",
                    "XX的核心原理",
                    "XX的优势和特点",
                    "适用人群/场景",
                    "常见误区和避坑",
                    "如何选择（品牌自然植入）",
                    "注意事项和风险提示",
                    "FAQ",
                    "总结与行动建议"
                ],
                "authority_tips": [
                    "引用研究数据和权威机构",
                    "提供原创的分析框架",
                    "用案例和数据支撑每个观点",
                    "展示专业深度和行业洞察"
                ]
            }

        else:
            return base_guide

    # ========== 获取关键词挖掘的指导 ==========

    @classmethod
    def get_keyword_strategy(cls) -> Dict[str, Any]:
        """获取GEO关键词策略指导"""
        return {
            "intent_types": cls.USER_INTENT_TYPES,
            "longtail_strategy": cls.LONGTAIL_STRATEGY,
            "content_matrix": cls.LONGTAIL_STRATEGY["content_matrix"],
            "four_tier_system": {
                "brand": {
                    "name": "品牌词",
                    "description": "品牌名+常见搜索后缀，直接承接品牌搜索",
                    "target_count": 20,
                    "value": "高（高转化意图）"
                },
                "accurate": {
                    "name": "精准词",
                    "description": "产品/服务+具体问题，精准用户",
                    "target_count": 30,
                    "value": "高（强意图）"
                },
                "generic": {
                    "name": "大词",
                    "description": "行业通用词，曝光量大但竞争激烈",
                    "target_count": 10,
                    "value": "中（品牌曝光）"
                },
                "scene": {
                    "name": "场景词",
                    "description": "用户痛点场景问题，长尾流量",
                    "target_count": 40,
                    "value": "中（精准触达）"
                }
            }
        }

    # ========== 获取质量评分维度 ==========

    @classmethod
    def get_quality_dimensions(cls) -> Dict[str, Any]:
        """获取GEO内容质量评分的8个维度"""
        return {
            "answer_first": {
                "name": "答案优先度",
                "weight": 0.15,
                "description": "是否在开头直接给出核心答案",
                "source": "《答案优先》",
                "scoring_guide": "检查前3段是否包含核心结论，结论是否完整"
            },
            "eeat_trust": {
                "name": "EEAT可信度",
                "weight": 0.20,
                "description": "内容的经验、专业、权威、可信度",
                "source": "《EEAT原则》",
                "scoring_guide": "检查是否有数据来源、案例支撑、权威背书、风险提示"
            },
            "structure_clarity": {
                "name": "结构清晰度",
                "weight": 0.15,
                "description": "内容结构是否清晰、易于AI提取",
                "source": "《结构化写法》",
                "scoring_guide": "检查标题层级、列表使用、表格使用、分段合理性"
            },
            "chunkability": {
                "name": "内容可摘取性",
                "weight": 0.15,
                "description": "内容是否容易被AI单独摘取引用",
                "source": "《内容分块》",
                "scoring_guide": "检查每段是否只讲一个观点，定义是否独立成段"
            },
            "differentiation": {
                "name": "差异化程度",
                "weight": 0.10,
                "description": "是否提供了独特的价值和信息",
                "source": "《差异化内容》",
                "scoring_guide": "检查是否有自有数据、独特方法、结构化经验"
            },
            "data_verifiability": {
                "name": "数据可验证性",
                "weight": 0.10,
                "description": "数据是否有来源标注，是否可追溯",
                "source": "综合",
                "scoring_guide": "检查数据是否标注来源，是否有权威机构引用"
            },
            "risk_disclosure": {
                "name": "风险披露",
                "weight": 0.10,
                "description": "是否有风险提示和适用边界",
                "source": "《合规治理》",
                "scoring_guide": "检查是否有禁忌、副作用、不适用人群等说明"
            },
            "brand_naturalness": {
                "name": "品牌自然度",
                "weight": 0.05,
                "description": "品牌植入是否自然不生硬",
                "source": "综合",
                "scoring_guide": "检查品牌出现的位置、频率、融入方式"
            }
        }

    # ========== 工具方法 ==========

    @classmethod
    def get_article_methodology(cls, article_title: str) -> Optional[Dict[str, str]]:
        """获取指定文章的核心方法"""
        article_map = {
            "GEO是什么": "一句话定义+答案优先+品牌解释权",
            "GEO与SEO": "SEO打地基，GEO做放大器",
            "答案优先": "结论在前，细节在后，每节开头给核心观点",
            "EEAT原则": "经验+专业+权威+可信，四维可信度建设",
            "结构化写法": "列表、表格、问答，让AI易提取",
            "内容分块": "一段一观点，摘取后仍独立成立",
            "差异化内容": "自有数据+实战方法+结构化经验",
            "长尾规划": "从抢头部词到经营长尾问题网络",
            "推荐逻辑": "明确适用人群+核心优势+数据支撑+边界说明",
            "合规治理": "不绝对化+写清条件+风险提示+数据可追溯"
        }
        if article_title in article_map:
            return {"title": article_title, "core_method": article_map[article_title]}
        return None

    @classmethod
    def get_all_core_methods(cls) -> List[Dict[str, str]]:
        """获取所有核心方法论摘要"""
        return [
            {"article": "答案优先", "method": "开头直接给完整答案，每节结论在前"},
            {"article": "EEAT原则", "method": "经验+专业+权威+可信，四维可信度"},
            {"article": "结构化写法", "method": "列表/表格/问答结构，让AI易提取"},
            {"article": "内容分块", "method": "一段一观点，独立摘取仍成立"},
            {"article": "差异化内容", "method": "自有数据+实战方法+结构化经验"},
            {"article": "长尾规划", "method": "从抢大词转向经营长尾问题网络"},
            {"article": "推荐逻辑", "method": "适用人群+核心优势+数据+边界"},
            {"article": "合规治理", "method": "不绝对化+写清条件+风险提示"},
            {"article": "定义-证据-案例-边界", "method": "GEO内容的标准四段式结构"},
        ]

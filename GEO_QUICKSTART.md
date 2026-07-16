# GEO优化工作台 - 快速入门

## 升级概述

我们已经将原来的纯监测工具升级为完整的GEO优化工作台!新功能包括:

1. **关键词管理系统** - 四层关键词库(品牌词/精准词/大词/场景词)
2. **独有信息素材库** - 分类管理价格/周期/专利等数据
3. **内容生产助手** - GEO规范模板,内容结构检查
4. **命中率监测** - 分层统计,趋势分析
5. **竞品分析** - 识别竞品引用模式,空白分析
6. **8周执行计划** - 标准执行计划,进度追踪

## 快速开始

### 1. 初始化数据库

启动Web服务后,数据库会自动创建新表:

```bash
python run_web.py
```

### 2. 第1周: 基础建设

#### 步骤1: 添加独有信息素材

```python
from src.geo import MaterialManager

mm = MaterialManager()
project_id = 1  # 替换为你的项目ID

# 添加价格数据
mm.add_material(
    project_id,
    category='price',
    title='价格体系',
    content='轻度19800起/区,中度39800起/区,重度69800起/区',
    source='官方定价',
    use_cases=['价格', '多少钱', '费用']
)

# 添加专利信息
mm.add_material(
    project_id,
    category='patent',
    title='专利认证',
    content='专利号ZL 2016 1 0339273.8,318项专利,中科院授权',
    source='专利局',
    use_cases=['专利', '正规', '认证']
)

# 添加周期数据
mm.add_material(
    project_id,
    category='period',
    title='治疗周期',
    content='15天一次,4次一疗程,7天/14天/21天/30天/60天变化',
    source='临床数据',
    use_cases=['周期', '多久', '疗程']
)
```

#### 步骤2: 创建关键词库

```python
from src.geo import KeywordManager

km = KeywordManager()

# 自动生成关键词建议
suggestions = km.generate_suggestions(
    project_id,
    brand_name='完形康躰',
    core_product='康躰脂雕',
    competitors=['竞品A', '竞品B']
)

# 批量添加品牌词
brand_keywords = [
    {"keyword": kw, "tier": "brand", "difficulty": 20, "is_target": True}
    for kw in suggestions['brand'][:20]
]
km.batch_add_keywords(project_id, brand_keywords)

# 批量添加精准词
accurate_keywords = [
    {"keyword": kw, "tier": "accurate", "difficulty": 40, "is_target": True}
    for kw in suggestions['accurate'][:30]
]
km.batch_add_keywords(project_id, accurate_keywords)

# 批量添加场景词
scene_keywords = [
    {"keyword": kw, "tier": "scene", "difficulty": 30, "is_target": False}
    for kw in suggestions['scene'][:40]
]
km.batch_add_keywords(project_id, scene_keywords)

# 批量添加大词
generic_keywords = [
    {"keyword": kw, "tier": "generic", "difficulty": 70, "is_target": True}
    for kw in suggestions['generic'][:10]
]
km.batch_add_keywords(project_id, generic_keywords)
```

#### 步骤3: 创建8周执行计划

```python
from src.geo import PlanManager

pm = PlanManager()

# 创建标准8周计划
pm.create_8week_plan(project_id)

# 查看计划
plan = pm.get_plan(project_id)
for item in plan:
    print(f"第{item['week']}周: {item['description']} - {item['status']}")
```

### 3. 第2-4周: 内容生产

#### 使用内容模板

```python
from src.geo import ContentTemplate, MaterialManager

mm = MaterialManager()
ct = ContentTemplate()

# 获取相关素材
materials = mm.get_materials_for_keyword(project_id, "康躰脂雕多少钱")

# 生成长尾问答文
content = ct.longtail_question_template(
    question="康躰脂雕多少钱",
    answer="康躰脂雕的价格根据部位不同有所差异",
    materials=materials,
    brand_name="完形康躰"
)

print(content)

# 检查GEO规范
passed, issues = ct.check_geo_standards(content)
print(f"是否通过: {passed}")
print("问题列表:")
for issue in issues:
    print(f"  {issue}")
```

#### 检查清单

```python
checklist = ct.get_content_template_checklist()
for item in checklist:
    status = "✅" if item['checked'] else "⬜"
    print(f"{status} {item['item']}")
```

### 4. 监测与优化

#### 记录命中情况

```python
from src.geo import HitTracker

ht = HitTracker()

# 记录一次命中
ht.record_hit(
    project_id,
    keyword_id=1,  # 关键词ID
    keyword="康躰脂雕多少钱",
    is_hit=True,
    position="first",  # first/middle/last
    mention_count=2,
    cited_sources=["https://your-site.com/page1"],
    response_snippet="康躰脂雕的价格是..."
)

# 查看命中率
hit_rate = ht.get_hit_rate(project_id, days=7)
print(f"总体命中率: {hit_rate['hit_rate']:.1%}")

# 查看分层命中率
tier_rates = ht.get_tier_hit_rates(project_id)
for tier, data in tier_rates.items():
    print(f"{tier}: {data['hit_rate']:.1%}")
```

#### 竞品分析

```python
from src.geo import CompetitorAnalyzer

ca = CompetitorAnalyzer()

# 添加竞品
ca.add_competitor(
    project_id,
    name="竞品A",
    url="https://competitor-a.com",
    notes="主要竞争对手"
)

# 记录竞品被引用
ca.add_citation(
    project_id,
    competitor_id=1,
    keyword="生发针哪家好",
    cited_content="竞品A的技术...",
    content_structure="table",  # table/list/data/text
    source_url="https://competitor-a.com/page"
)

# 空白分析
gap = ca.get_gap_analysis(project_id)
print(f"空白关键词: {gap['gap_keywords']}")
```

## GEO内容规范(强制执行)

### 7条标准

1. ✅ **标题 = 用户问题**(口语化)
2. ✅ **开头第一句直接给完整答案**
3. ✅ **关键数据加粗 + 括号标注来源**
4. ✅ **能用表格不用文字**(对比/价格/参数)
5. ✅ **步骤类用编号列表**
6. ✅ **结尾100字内核心总结**
7. ✅ **自然植入品牌1-2次**(不硬塞)

### 发布平台优先级

1. **头条号**(最高优先级) - 豆包自家数据源
2. **知乎** - 问答结构
3. **抖音** - 标题和文案埋关键词
4. **微博** - 话题标签扩散

### 多账号配合

- **主号** - 专业科普,发布核心深度文
- **测评号** - 中立第三方,发布横向对比
- **经验号** - 过来人角度,发布体验分享

**技巧**: 三个账号说同样的事实,但用不同语气、角度、句式 — AI会采信度更高!

## 数据结构说明

### 四层关键词

| 层级 | 数量 | 竞争难度 | 例子 |
|------|------|----------|------|
| 品牌词 | 20 | 低 | 完形康躰效果怎么样 |
| 精准词 | 30 | 中 | 康躰脂雕靠谱吗 |
| 大词 | 10 | 高 | 生发针哪家好 |
| 场景词 | 40 | 低 | 发际线后移怎么办 |

### 素材分类

| 分类 | 说明 |
|------|------|
| price | 价格数据 |
| period | 周期数据 |
| technical | 技术参数 |
| patent | 专利信息 |
| clinical | 临床背书 |
| population | 适用人群 |

## 8周预期效果

| 时间 | 阶段 | 预期效果 |
|------|------|----------|
| 第1周 | 基础建设 | 完成100关键词库+独有素材表 |
| 第2-4周 | 内容爆发 | 36篇内容上线(1+5+30矩阵) |
| 第5-6周 | 权重积累 | 品牌词命中率≥80% |
| 第7-8周 | 品类攻坚 | 大词开始出现,稳定在备选答案 |

## 关键认知

- **30篇打底,50篇见效,100篇形成壁垒**
- **数量本身就是权重**
- **越具体、越有数字、越有编号,越容易被AI引用**
- **头条是主战场,必须优先**

## 下一步

1. 启动Web服务: `python run_web.py`
2. 创建你的第1个GEO项目
3. 添加独有信息素材(至少10条)
4. 生成100个关键词库
5. 启动8周执行计划

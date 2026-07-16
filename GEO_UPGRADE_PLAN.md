# GEO品牌监测工具 - 优化工作台升级方案

## 📋 升级目标

从**纯监测工具**升级为**GEO优化工作台**,支持从关键词规划→内容生产→效果监测的完整闭环。

---

## 🏗️ 第一阶段:数据库升级 (P0)

### 新增数据表

```sql
-- 1. 关键词库表
CREATE TABLE geo_keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    keyword TEXT NOT NULL,           -- 关键词
    tier TEXT NOT NULL,              -- 层级: brand/accurate/generic/scene
    difficulty INTEGER DEFAULT 50,   -- 竞争难度 0-100
    status TEXT DEFAULT 'pending',   -- 状态: pending/monitoring/improved/dominating
    is_target INTEGER DEFAULT 0,     -- 是否核心目标词
    notes TEXT,                      -- 备注
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects (id)
);

-- 2. 独有信息素材库表
CREATE TABLE geo_materials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    category TEXT NOT NULL,          -- 类别: price/period/technical/patent/clinical/population
    title TEXT NOT NULL,             -- 素材标题
    content TEXT NOT NULL,           -- 具体内容(含数据)
    source TEXT,                     -- 来源
    use_cases TEXT,                  -- 适用场景(逗号分隔)
    is_verified INTEGER DEFAULT 1,   -- 是否核实
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects (id)
);

-- 3. 内容清单表
CREATE TABLE geo_contents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    title TEXT NOT NULL,             -- 内容标题
    content_type TEXT NOT NULL,      -- 类型: core/comparison/longtail/faq
    target_keywords TEXT,            -- 目标关键词(逗号分隔)
    status TEXT DEFAULT 'idea',      -- 状态: idea/drafting/reviewing/published
    publish_url TEXT,                -- 发布链接
    publish_platform TEXT,           -- 发布平台: toutiao/zhihu/bilibili
    publish_date TEXT,               -- 发布日期
    word_count INTEGER DEFAULT 0,    -- 字数
    has_table INTEGER DEFAULT 0,     -- 是否有表格
    has_data INTEGER DEFAULT 0,      -- 是否有具体数据
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects (id)
);

-- 4. 关键词命中记录表
CREATE TABLE geo_hit_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    keyword_id INTEGER,
    keyword TEXT NOT NULL,
    date_str TEXT NOT NULL,
    hour INTEGER,
    is_hit INTEGER DEFAULT 0,        -- 是否命中
    position TEXT,                   -- 提及位置: first/middle/last/not_mentioned
    mention_count INTEGER DEFAULT 0, -- 提及次数
    cited_sources TEXT,              -- 引用来源(逗号分隔URL)
    response_snippet TEXT,           -- 回答片段
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects (id),
    FOREIGN KEY (keyword_id) REFERENCES geo_keywords (id)
);

-- 5. 竞品分析表
CREATE TABLE geo_competitors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    name TEXT NOT NULL,              -- 竞品名称
    url TEXT,                        -- 相关链接
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects (id)
);

-- 6. 竞品内容引用表
CREATE TABLE geo_competitor_citations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    competitor_id INTEGER,
    keyword TEXT,                    -- 搜索的关键词
    cited_content TEXT,              -- 被引用的内容
    content_structure TEXT,          -- 内容结构分析
    source_url TEXT,                 -- 来源链接
    date_str TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects (id),
    FOREIGN KEY (competitor_id) REFERENCES geo_competitors (id)
);

-- 7. 执行计划表
CREATE TABLE geo_plan (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    week INTEGER NOT NULL,           -- 第几周
    phase TEXT NOT NULL,             -- 阶段: foundation/content/distribution/optimization
    description TEXT,                -- 任务描述
    deliverable TEXT,                -- 交付物
    status TEXT DEFAULT 'pending',   -- 状态: pending/in_progress/completed
    due_date TEXT,
    completed_date TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects (id)
);
```

---

## 🎯 第二阶段:核心功能模块 (P0)

### 模块1:关键词管理系统

```python
# src/geo/keyword_manager.py

class KeywordManager:
    """关键词库管理"""
    
    TIER_BRAND = 'brand'          # 品牌词(20个)
    TIER_ACCURATE = 'accurate'    # 精准词(30个)
    TIER_GENERIC = 'generic'      # 大词(10个)
    TIER_SCENE = 'scene'          # 场景词(40个)
    
    def add_keyword(self, project_id, keyword, tier, difficulty=50, is_target=False):
        """添加关键词"""
        pass
    
    def generate_suggestions(self, project_id, brand_name, core_product):
        """
        基于品牌和产品生成关键词建议
        - 品牌词: {品牌}效果/价格/正规吗/原理/疗程
        - 精准词: {产品}靠谱吗/是什么/和XX比
        - 场景词: 发际线后移怎么办/脂溢性脱发怎么治
        """
        pass
    
    def get_tier_stats(self, project_id):
        """获取各层级统计数据"""
        pass
```

### 模块2:独有信息素材库

```python
# src/geo/material_manager.py

class MaterialManager:
    """独有信息素材库管理"""
    
    CAT_PRICE = 'price'           # 价格数据
    CAT_PERIOD = 'period'         # 周期数据
    CAT_TECHNICAL = 'technical'   # 技术参数
    CAT_PATENT = 'patent'         # 专利信息
    CAT_CLINICAL = 'clinical'     # 临床背书
    CAT_POPULATION = 'population' # 适用人群
    
    def add_material(self, project_id, category, title, content, source=None, use_cases=None):
        """添加素材"""
        pass
    
    def get_materials_for_keyword(self, project_id, keyword):
        """根据关键词获取适用素材"""
        pass
    
    def get_random_materials(self, project_id, count=3):
        """随机获取素材(用于内容生成)"""
        pass
```

### 模块3:内容生产助手

```python
# src/geo/content_helper.py

class ContentTemplate:
    """GEO内容模板"""
    
    @staticmethod
    def longtail_question_template(question, answer, materials):
        """
        长尾问答文模板:
        1. 标题 = 问题本身
        2. 开头第一句直接给答案
        3. 关键数据加粗 + 括号标注来源
        4. 能用表格不用文字
        5. 结尾100字内核心总结
        6. 自然植入品牌1-2次
        """
        pass
    
    @staticmethod
    def comparison_template(product_a, product_b, comparison_points):
        """横向对比文模板"""
        pass
    
    @staticmethod
    def core_deep_template(topic, sections):
        """核心深度文模板"""
        pass
    
    @staticmethod
    def check_geo_standards(content):
        """
        检查内容是否符合GEO规范:
        ✓ 开头是否直接给答案
        ✓ 是否有具体数据
        ✓ 是否有表格(如果适用)
        ✓ 关键数据是否加粗
        ✓ 是否有核心总结
        """
        pass
```

---

## 📈 第三阶段:监测与分析升级 (P1)

### 模块4:命中率监测系统

扩展现有监测功能,新增:

```python
# src/geo/hit_tracker.py

class HitTracker:
    """关键词命中追踪"""
    
    def monitor_keyword(self, project_id, keyword_id, keyword):
        """监测单个关键词,记录命中情况"""
        # 1. 搜索关键词
        # 2. 分析回答中是否提及品牌
        # 3. 记录提及位置
        # 4. 提取引用来源
        # 5. 保存到 geo_hit_records
        pass
    
    def get_hit_rate(self, project_id, tier=None, days=7):
        """获取命中率"""
        pass
    
    def get_hit_trend(self, project_id, keyword_id, days=30):
        """获取单个关键词的命中趋势"""
        pass
```

### 模块5:竞品GEO分析

```python
# src/geo/competitor_analyzer.py

class CompetitorAnalyzer:
    """竞品GEO分析"""
    
    def analyze_competitor_citation(self, keyword, competitor_name):
        """
        分析竞品被引用情况:
        - AI引用了竞品的哪些内容
        - 内容结构是什么样(表格/列表/纯文字)
        - 我们的空白切入机会
        """
        pass
    
    def get_competitor_content_patterns(self, project_id, competitor_id):
        """获取竞品内容模式总结"""
        pass
```

### 模块6:执行计划管理

```python
# src/geo/plan_manager.py

class PlanManager:
    """8周执行计划管理"""
    
    def create_8week_plan(self, project_id):
        """创建标准8周计划"""
        weeks = [
            # 第1周: 基础建设
            {"week": 1, "phase": "foundation", "deliverable": "100关键词库+独有素材表"},
            # 第2-4周: 内容爆发
            {"week": 2, "phase": "content", "deliverable": "核心深度文1篇+长尾文10篇"},
            {"week": 3, "phase": "content", "deliverable": "对比文3篇+长尾文10篇"},
            {"week": 4, "phase": "content", "deliverable": "对比文2篇+长尾文10篇"},
            # 第5-6周: 权重积累
            {"week": 5, "phase": "distribution", "deliverable": "品牌词命中率≥80%"},
            {"week": 6, "phase": "distribution", "deliverable": "精准词开始命中"},
            # 第7-8周: 品类攻坚
            {"week": 7, "phase": "optimization", "deliverable": "大词开始出现"},
            {"week": 8, "phase": "optimization", "deliverable": "稳定出现在备选答案"}
        ]
        pass
    
    def get_weekly_tasks(self, project_id, week):
        """获取当周任务"""
        pass
```

---

## 🌐 第四阶段:Web界面升级 (P0-P1)

### 新增页面/功能

| 页面 | 功能 | 优先级 |
|------|------|--------|
| `/geo/keywords` | 关键词库管理,分层展示,批量导入 | P0 |
| `/geo/materials` | 独有信息素材库,分类管理 | P0 |
| `/geo/contents` | 内容清单,状态追踪,发布记录 | P0 |
| `/geo/monitor` | 命中率仪表盘,分层统计,趋势图 | P1 |
| `/geo/competitors` | 竞品分析,引用模式识别 | P1 |
| `/geo/plan` | 8周执行计划,进度追踪 | P1 |

---

## 📁 文件结构变化

```
GEO-Tool/
├── src/
│   ├── geo/                      # 新增:GEO优化模块
│   │   ├── __init__.py
│   │   ├── keyword_manager.py    # 关键词管理
│   │   ├── material_manager.py   # 素材库管理
│   │   ├── content_helper.py     # 内容生产助手
│   │   ├── hit_tracker.py        # 命中率追踪
│   │   ├── competitor_analyzer.py # 竞品分析
│   │   └── plan_manager.py       # 执行计划管理
│   ├── collector/                # 现有:保持不变
│   ├── web/
│   │   ├── app.py                # 扩展:新增GEO相关API
│   │   ├── templates/
│   │   │   ├── index.html        # 扩展:GEO入口
│   │   │   ├── geo_keywords.html # 新增
│   │   │   ├── geo_materials.html # 新增
│   │   │   ├── geo_contents.html # 新增
│   │   │   ├── geo_monitor.html  # 新增
│   │   │   └── geo_plan.html     # 新增
│   │   └── static/
│   │       └── js/
│   │           └── geo.js        # 新增:GEO前端逻辑
│   └── db/
│       └── models.py             # 扩展:新增GEO表
└── data/
    └── geo_templates/            # 新增:内容模板库
        ├── longtail.md
        ├── comparison.md
        └── core.md
```

---

## 🚀 实施优先级

### Phase 1: MVP (1-2周)
- [ ] 数据库表设计与创建
- [ ] 关键词管理系统基础版
- [ ] 独有信息素材库
- [ ] 内容生产助手(模板)
- [ ] 基础Web界面

### Phase 2: 监测增强 (1周)
- [ ] 命中率监测系统
- [ ] 关键词命中记录
- [ ] 命中率统计仪表盘

### Phase 3: 分析功能 (1周)
- [ ] 竞品分析模块
- [ ] 执行计划管理
- [ ] AI引用模式分析

---

## 📊 预期效果

升级后,工具将支持:

1. **完整工作流**: 关键词→素材→内容→监测→优化
2. **数据驱动**: 基于命中率数据调整策略
3. **竞品洞察**: 分析竞品哪些内容被引用
4. **进度追踪**: 8周计划可视化,确保按节奏执行
5. **效果可量化**: 品牌词/精准词/大词分层统计

---

## 💡 关键GEO原则(内置到工具)

### 内容标准检查清单
- [ ] 标题 = 用户问题(口语化)
- [ ] 开头第一句直接给完整答案
- [ ] 关键数据加粗 + 括号标注来源
- [ ] 能用表格不用文字(对比/价格/参数)
- [ ] 步骤类用编号列表
- [ ] 结尾100字内核心总结
- [ ] 自然植入品牌1-2次(不硬塞)

### 发布原则
- 头条号优先(豆包主要数据源)
- 三个账号配合(专业/中立/经验)
- 同一事实多角度表达(制造共识)
- 场景词铺量,大词攻坚

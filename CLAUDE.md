# GEO 品牌监测工具 - 项目记忆

## 项目概述

GEO（Generative Engine Optimization）品牌监测工具，自动监测品牌在 AI 搜索引擎（豆包 Doubao）中的曝光情况，支持 Web 可视化展示。

**核心流程**：用户输入监测问题 → LLM 衍生 2 个相似问题（共 3 个）→ Playwright 自动向豆包提问 → 抓取豆包回复 → LLM 分析 + 保存到数据库 → Web 仪表盘可视化展示。

**用户背景**：用户运营品牌"完形康躰"（康躰脂雕），监测该品牌在豆包 AI 搜索中的排名和推荐情况。

## 技术栈

- **Python 3.12** (Windows)
- **Tkinter** - GUI 桌面应用
- **Playwright** (sync_playwright) - 浏览器自动化
- **Flask** - Web 仪表盘后端
- **ECharts** - 前端图表（CDN 加载）
- **SQLite** - 数据库
- **Anthropic SDK** - LLM API（通过兼容接口调用 qwen3.6-flash）
- **PyYAML** - 配置文件管理

## 文件结构

```
GEO-Tool/
├── run_gui.py                    # 启动 GUI
├── run_web.py                    # 启动 Web 仪表盘
├── config.yaml                   # 配置文件
├── requirements.txt
├── CLAUDE.md
├── README.md
├── src/
│   ├── config.py                 # 统一配置管理
│   ├── collector/                # 数据采集模块
│   │   ├── gui.py                # Tkinter GUI
│   │   ├── question_generator.py # LLM 衍生问题
│   │   ├── doubao_query.py       # Playwright 浏览器自动化
│   │   └── monitor_analysis.py   # LLM 分析回复
│   ├── web/                      # Web 仪表盘
│   │   ├── app.py                # Flask 后端
│   │   ├── templates/index.html
│   │   └── static/css/style.css, js/main.js
│   └── db/                       # 数据库
│       ├── models.py             # SQLite 表定义和查询
│       └── importer.py           # JSON → DB 导入
└── data/                         # 数据目录（gitignore）
    ├── monitor/YYYYMMDD/         # JSON + MD 报告
    └── geo_monitor.db            # SQLite 数据库
```

## 启动方式

- **GUI 采集数据**：`python run_gui.py`
- **Web 仪表盘**：`python run_web.py` → http://localhost:5000

## 关键技术决策

### 1. 浏览器必须可见（headless=False）
豆包会检测 headless 并触发 CAPTCHA，必须 `headless=False`。

### 2. CDP 连接模式
优先连接已运行的 Chrome（`_find_cdp_port()` 扫描 9222/9223/9224），减少 CAPTCHA 触发。

### 3. 智能等待策略（2026-06-12 新增）
- 问题间随机延迟：第1个 60-90s，第2个 90-120s，第3个 120-180s
- 人类行为模拟：鼠标移动、滚动、打字速度随机变化、标点后停顿
- 3 种备用发送方式（按钮/textarea Enter/keyboard Enter），避免 element detached 错误
- 可通过 `config.yaml` 的 `delay_between_questions` 覆盖为固定值

### 4. 回复提取
`_extract_doubao_response()` 只提取聊天回复，忽略侧边栏/历史记录。

### 5. 数据库设计（SQLite）
4 张表：`monitor_tasks`（任务）、`questions`（问题+回复）、`brand_mentions`（品牌提及+位置+情感）、`daily_summaries`（每日摘要）

### 6. 日期格式
数据库 `date_str` 存的是 `YYYYMMDD` 格式（如 `20260613`），不能用 SQLite 的 `date()` 函数比较。

## 当前状态

### LLM API
- 模型：`qwen3.6-flash`（阿里云百炼 token-plan）

### 数据库
- 已有 5 天历史数据（20260602 ~ 20260612）
- brand_mentions 表已提取品牌提及信息

## 待办事项

- [x] GUI 添加 LLM 模型切换功能 - 2026-06-03
- [x] 清理项目，只保留监测功能 - 2026-06-03
- [x] 智能等待策略 + 人类行为模拟 - 2026-06-12
- [x] 项目结构重构 + Web 仪表盘 + SQLite - 2026-06-12
- [x] 清理旧文件（根目录 .py、dist/、__pycache__/）- 2026-06-13
- [ ] 修复统计数据准确性（部分日期 question_count 偏少）
- [ ] 品牌位置分布图（Web 端）
- [ ] 竞品标签功能
- [ ] 测试 CDP 连接功能
- [ ] PyInstaller 打包成 .exe

## 配置文件 (config.yaml)

```yaml
doubao:
  chrome_profile: ...
  delay_between_questions: 60  # 留空则用智能随机延迟
  reply_wait: 60
  timeout: 60
  url: https://www.doubao.com
llm_api:
  provider: qwen
  model: qwen3.6-flash
  base_url: https://token-plan.cn-beijing.maas.aliyuncs.com/apps/anthropic
  api_key: sk-sp-...
monitor:
  question: 康躰脂雕哪家好
  brand: 完形康躰
  schedule_hours: []
```

## 用户偏好

- 中文界面和交流
- 不要静默运行浏览器（保持可见）
- 不需要截图功能（已移除）
- 报告只关注豆包回答内容，不分析侧边栏/历史记录
- 报告要列出所有品牌/机构名称（按频次排序）
- API 和网页版结果可能不一致，网页版更真实（用户原话）
- 浏览器自动化容易触发 CAPTCHA，不要过度增加平台/问题数量

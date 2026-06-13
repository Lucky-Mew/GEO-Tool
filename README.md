# GEO 品牌监测工具

自动监测品牌在 AI 搜索引擎（豆包 Doubao）中的曝光情况，帮助品牌做生成式引擎优化（GEO）。

## 项目结构

```
GEO-Tool/
├── src/
│   ├── collector/          # 数据采集模块（Tkinter GUI）
│   │   ├── gui.py
│   │   ├── question_generator.py
│   │   ├── doubao_query.py
│   │   └── monitor_analysis.py
│   ├── web/                # Web 仪表盘模块
│   │   ├── app.py
│   │   ├── templates/
│   │   └── static/
│   ├── db/                 # 数据库模块
│   │   ├── models.py
│   │   └── importer.py
│   └── config.py           # 统一配置管理
├── data/                   # 数据目录
│   ├── monitor/            # 监测数据（按日期存放）
│   └── geo_monitor.db      # SQLite 数据库
├── config.yaml             # 配置文件
├── requirements.txt        # 依赖
├── run_gui.py             # 启动 GUI
└── run_web.py             # 启动 Web 仪表盘
```

## 工作原理

```
输入1个监测问题
      ↓
LLM 衍生出2个相似问题（共3个）
      ↓
Playwright 自动打开浏览器，向豆包逐个提问
      ↓
抓取豆包回复
      ↓
LLM 分析回复，生成品牌监测报告
      ↓
保存到数据库，Web 仪表盘可视化展示
```

## 环境要求

- **Python 3.10+**（推荐 3.12 或更高）
- **Google Chrome / Edge 浏览器**（已安装并登录过豆包）
- **LLM API Key**（阿里云百炼 / OpenAI / Claude / 豆包，任选其一）

## 安装步骤

### 1. 克隆项目

```bash
git clone https://github.com/Lucky-Mew/GEO-Tool.git
cd GEO-Tool
```

### 2. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 3. 安装 Playwright 浏览器

```bash
playwright install chromium
```

### 4. 准备配置文件

复制模板并重命名为 `config.yaml`（如果还没有的话）：

```bash
cp config.example.yaml config.yaml
```

然后编辑 `config.yaml`，或在 GUI 界面直接配置。

## 运行方式

### 1. 启动 GUI 采集数据

```bash
python run_gui.py
```

GUI 功能：
- **测试连接** — 测试 LLM API 是否配置正确
- **立即执行** — 马上跑一次完整监测流程
- **定时监测** — 设置每天固定时间自动执行（最多5个时间点）
- **导入数据** — 导入历史 JSON 数据到数据库
- **Web 仪表盘** — 一键打开可视化页面

### 2. 启动 Web 仪表盘查看数据

```bash
python run_web.py
```

然后访问 `http://localhost:5000` 查看可视化图表。

## 功能说明

### 核心特性

- **智能延迟策略** — 问题间随机延迟，模拟真实用户行为，减少 CAPTCHA 触发
- **数据库存储** — 所有数据保存到 SQLite，方便查询和分析
- **Web 可视化** — 美观的仪表盘，展示趋势和统计
- **自动品牌提取** — 简单的 NER 提取回复中的品牌名
- **向后兼容** — 保留原有的 JSON 文件输出

### 人类行为模拟

- 页面加载后短暂等待+轻微滚动
- 鼠标先移动到输入框附近再点击
- 逐字输入（60-120ms/字），标点后偶尔停顿
- 输入后模拟检查（短暂等待）
- 发送后等待回复期间，偶尔移动鼠标
- 问题间智能延迟（60-180秒随机，根据问题位置递增）

## 输出

### 数据目录（data/）

```
data/
├── monitor/
│   └── 20260602/
│       ├── timepoint_15.json          # 原始数据
│       └── monitor_report_品牌_日期.md  # 分析报告
└── geo_monitor.db                      # SQLite 数据库
```

### 数据库表

- `monitor_tasks` - 监测任务记录
- `questions` - 问题和回复
- `brand_mentions` - 品牌提及情况
- `daily_summaries` - 每日摘要

## 常见问题

### Q: 弹出了人机验证（CAPTCHA）怎么办？

工具会自动检测并暂停，等你手动完成验证后继续。你也可以提前用以下方式减少验证触发：

以调试模式启动 Chrome，让 Playwright 复用已有浏览器：

```bash
# Windows
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
```

工具会自动扫描端口 9222/9223/9224，找到后直接连接。

### Q: API 报错 429（配额不足）？

说明你的 API Key 额度用完了，需要充值或更换 Key。

### Q: 可以换其他 LLM 吗？

可以。在 GUI 界面直接修改：
- **模型名称** — 填入你的模型名（如 `qwen3.6-flash`、`doubao-seed-2.0-code`、`gpt-4o`）
- **API 地址** — 填入服务商提供的 API 地址
- **API Key** — 填入你的密钥

支持的兼容接口：
- 阿里云百炼（Anthropic 兼容）
- 火山引擎豆包（Anthropic/OpenAI 兼容）
- OpenAI 及兼容接口
- Anthropic Claude

### Q: 旧的 output/ 目录下的数据怎么办？

运行一次 GUI 工具，点击"导入数据"按钮，旧数据会被导入到数据库中。

### Q: Web 仪表盘和 GUI 可以同时运行吗？

可以。Web 仪表盘只是读取数据，不会冲突。建议用 GUI 采集数据，用 Web 查看。

## 技术说明

- 浏览器**必须可见**（`headless=False`），因为豆包会检测无头浏览器
- 问题逐字输入（60-120ms/字随机），标点后偶尔停顿，模拟真人操作
- 页面加载最多重试 3 次，超时 60 秒
- 回复提取只抓取聊天内容，忽略侧边栏和历史记录
- 人类行为模拟：鼠标移动、滚动、随机延迟等
- 数据库：SQLite（轻量，无需额外安装）
- Web 框架：Flask（轻量，易部署）

## 升级说明（2026-06-12）

本次升级重构了项目结构：

- 原有代码移动到 `src/collector/` 目录
- 新增 `src/web/` Web 仪表盘模块
- 新增 `src/db/` 数据库模块
- 新增 `src/config.py` 统一配置管理
- 数据目录从 `output/` 改为 `data/`
- 启动脚本改为 `run_gui.py` 和 `run_web.py`
- 保留向后兼容，旧数据可通过 GUI 导入

## 许可

本项目仅供个人学习使用。

# GEO 品牌监测工具 - 项目记忆

## 项目概述

这是一个 **GEO（Generative Engine Optimization，生成式引擎优化）品牌监测工具**，用于自动监测品牌在 AI 搜索引擎（豆包 Doubao）中的曝光情况。

**核心流程**：用户输入一个监测问题 → LLM 衍生出 2 个相似问题（共 3 个）→ 用 Playwright 自动向豆包提问 → 抓取豆包回复 → LLM 分析回复并生成品牌监测报告。

**用户背景**：用户运营品牌"完形康躰"（康躰脂雕），需要监测该品牌在豆包 AI 搜索中的排名和推荐情况。

## 技术栈

- **Python 3.14** (Windows)
- **Tkinter** - GUI 桌面应用（从 CLI 转型而来）
- **Playwright** (sync_playwright) - 浏览器自动化，向豆包提问
- **Anthropic SDK** - 调用 LLM API（通过兼容接口调用 qwen3.6-flash）
- **PyYAML** - 配置文件管理 (config.yaml)
- **LLM API**：支持多种 provider（qwen/claude/openai/doubao），当前配置为阿里云百炼 token-plan + `qwen3.6-flash`

## 文件结构

```
GEO-Tool/
├── gui.py                  # 主入口，Tkinter GUI（唯一入口）
├── question_generator.py   # 模块1：LLM 衍生问题（1→3个）
├── doubao_query.py         # 模块2：Playwright 自动向豆包提问
├── monitor_analysis.py     # 模块3：LLM 分析豆包回复，生成报告
├── config.yaml             # 配置文件
├── requirements.txt
└── output/monitor/         # 输出目录，按日期组织
    └── YYYYMMDD/
        ├── timepoint_HH.json
        └── monitor_report_品牌_日期.md
```

已删除的旧文件（2026-06-03 清理）：
- `generate_article.py` - 文章生成（用户不需要）
- `analysis.py` - 旧版分析模块（已被 monitor_analysis.py 替代）
- `main.py` - CLI 入口（已被 gui.py 替代）
- `monitor.py` - CLI 定时监测（已被 gui.py 替代）

## 关键技术决策（重要！）

### 1. 浏览器必须可见（headless=False）
豆包会检测 headless 浏览器并触发人机验证（CAPTCHA），所以 **必须用 `headless=False`**，浏览器窗口保持可见。不支持静默运行。

### 2. CDP 连接模式（避免 CAPTCHA）
为减少 CAPTCHA 触发，优先连接已运行的 Chrome：
- `_find_cdp_port()` 扫描端口 9222/9223/9224 查找已运行 Chrome 的调试端口
- 如果找到 → `connect_over_cdp()` 复用已有浏览器（`_run_with_existing_browser`）
- 如果没找到 → `launch_persistent_context()` 启动新 Chrome（使用已有 profile）
- 需要用户先以 `--remote-debugging-port=9222` 参数启动 Chrome

### 3. 回复提取（只抓聊天内容）
`_extract_doubao_response()` 用 DOM 选择器只提取豆包的聊天回复，忽略侧边栏和历史记录：
- 优先尝试：`div[class*="message"][class*="assistant"]` 等选择器
- 回退：`div[class*="chat"], main` 等
- 最后兜底：`page.inner_text("body")`

### 4. CAPTCHA 检测与等待
- `_check_captcha()` 通过关键词（拖拽、拖动、captcha等）和图片数量（≥12张）检测
- `_wait_for_captcha_solve()` 暂停执行，等用户手动完成验证（最多120秒）
- `_clean_response_text()` 在分析前过滤掉验证相关内容

### 5. 页面加载重试
`_safe_goto()` 最多重试 3 次，超时 60 秒，应对网络波动。

### 6. 逐字输入
`_type_with_delay()` 逐字输入问题（80ms/字），模拟真人输入，有助于触发豆包的联网搜索而非纯 AI 生成。

## GUI 功能说明

### LLM 模型切换（gui.py 新增）
GUI 界面新增了 LLM 设置区域，可以直接在界面上切换模型，无需手动改配置文件：
- **接口类型**（provider）：下拉选择 `qwen` / `claude` / `openai` / `doubao`
- **模型名称**（model）：文本输入，如 `qwen3.6-flash`
- **API 地址**（base_url）：文本输入
- **API Key**：密码输入框（界面显示为 `***`）
- 点击"立即执行"或"定时监测"时自动保存到 config.yaml

## 当前状态

### LLM API
- 当前使用 key: `sk-sp-D.HEXEX...`（2026-06-03 验证可用）
- 模型：`qwen3.6-flash`（阿里云百炼 token-plan）
- 之前旧 key `sk-sp-D.DLLHD...` 配额已耗尽（429 错误），已更换

## 待办事项

- [x] GUI 添加 LLM 模型切换功能（provider/model/base_url/api_key）- 2026-06-03 完成
- [x] 清理项目，只保留监测功能（删除 generate_article.py、analysis.py、main.py、monitor.py）- 2026-06-03 完成
- [ ] 测试 CDP 连接功能（连接已有 Chrome 避免 CAPTCHA）
- [ ] PyInstaller 打包成独立 .exe（用户提到过但尚未开始）
- [ ] 考虑添加 API 配额错误时更友好的提示

## 配置文件 (config.yaml) 关键字段

```yaml
doubao:
  chrome_profile: ...         # Chrome 用户数据目录
  delay_between_questions: 60 # 问题间隔（秒）
  reply_wait: 60              # 等待回复时间（秒）
  timeout: 60
  url: https://www.doubao.com
llm_api:
  provider: qwen
  model: qwen3.6-flash
  base_url: https://token-plan.cn-beijing.maas.aliyuncs.com/apps/anthropic
  api_key: sk-sp-...
monitor:
  question: 康躰脂雕哪家好    # 监测问题
  brand: 完形康躰             # 品牌名
  schedule_hours: []          # 定时执行的小时（最多5个）
```

## 用户偏好

- 中文界面和交流
- 不要静默运行浏览器（保持可见）
- 不需要截图功能（已移除）
- 报告要只关注豆包的回答内容，不要分析侧边栏/历史记录
- 报告要列出豆包提到的所有品牌/机构名称（按频次排序）

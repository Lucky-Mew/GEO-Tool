# GEO 品牌监测工具

自动监测品牌在 AI 搜索引擎（豆包 Doubao）中的曝光情况，帮助品牌做生成式引擎优化（GEO）。

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
```

报告内容包括：豆包推荐了哪些品牌/机构、你的品牌是否被提及、排名情况等。

## 环境要求

- **Python 3.10+**（推荐 3.12 或更高）
- **Google Chrome 浏览器**（已安装并登录过豆包）
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

复制模板并重命名为 `config.yaml`：

```bash
cp config.example.yaml config.yaml
```

然后编辑 `config.yaml`，填入你的信息：

| 字段 | 说明 | 示例 |
|------|------|------|
| `doubao.chrome_profile` | Chrome 用户数据目录路径 | `C:/Users/你的用户名/AppData/Local/Google/Chrome/User Data/Default` |
| `llm_api.api_key` | 你的 LLM API Key | `sk-sp-xxxxx` |
| `llm_api.model` | 模型名称 | `qwen3.6-flash` / `doubao-seed-2.0-code` |
| `llm_api.base_url` | API 地址 | 根据你的服务商填写 |
| `monitor.brand` | 你的品牌名 | `完形康躰` |
| `monitor.question` | 监测问题 | `康躰脂雕哪家好` |

> **如何找到 Chrome 用户数据目录：**
> - Windows：`C:/Users/你的用户名/AppData/Local/Google/Chrome/User Data/Default`
> - macOS：`~/Library/Application Support/Google/Chrome/Default`
> - Linux：`~/.config/google-chrome/Default`

### 5. 提前登录豆包

在使用前，请先用 Chrome 浏览器手动访问 https://www.doubao.com 并登录账号，确保 Playwright 能复用你的登录状态。

## 运行

### Windows 用户（推荐）

双击 **`启动工具.vbs`** — 启动后不会显示黑色命令行窗口。

或双击 **`启动工具.bat`**。

### 命令行运行

```bash
python gui.py
```

启动后会看到图形界面，可以：

- **测试连接** — 先测试 LLM API 是否配置正确
- **立即执行** — 马上跑一次完整监测流程
- **定时监测** — 设置每天固定时间自动执行（最多5个时间点）

运行过程中会自动弹出浏览器窗口向豆包提问，**请勿关闭浏览器窗口**。

## 输出

每次监测结果保存在 `output/monitor/` 目录下：

```
output/monitor/
└── 20260602/
    ├── timepoint_15.json          # 原始数据
    └── monitor_report_品牌_日期.md  # 分析报告
```

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

## 技术说明

- 浏览器**必须可见**（`headless=False`），因为豆包会检测无头浏览器
- 问题逐字输入（80ms/字），模拟真人操作，更容易触发联网搜索
- 页面加载最多重试 3 次，超时 60 秒
- 回复提取只抓取聊天内容，忽略侧边栏和历史记录

## 许可

本项目仅供个人学习使用。

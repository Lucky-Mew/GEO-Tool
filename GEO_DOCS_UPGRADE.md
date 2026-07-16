# GEO 智能文档库 - 升级说明

## 新功能

### 📚 **文档库
- 支持上传 Word、PDF、PPT、TXT、Markdown
- 自动解析、智能分段
- 分类管理（价格/周期/技术/专利/临床/人群）

### 📝 **摘要管理**
- 文档摘要：单个文档的核心要点
- 分类摘要：某个分类所有文档的汇总
- 全局摘要：项目整体核心要点
- 人工编辑摘要，可控性更强

### 🔍 **智能检索**
- 简单的 TF-IDF + 余弦相似度检索
- 优先检索摘要，摘要中找不到再检索原文片段
- 构建上下文供内容生产使用

## 安装依赖

```bash
pip install python-docx PyPDF2 python-pptx
```

- `python-docx` - 解析 Word 文档
- `PyPDF2` - 解析 PDF 文档
- `python-pptx` - 解析 PPT 文档

如果不安装这些库，仍然可以上传 TXT 和 Markdown，或者直接添加素材。

## 使用流程

### 1. 上传文档
1. 选择项目（如"再生道"）
2. 进入 GEO 优化 → 文档库
3. 点击"上传文档"
4. 选择文件和分类，上传

### 2. 创建摘要（可选）
- **文档摘要**：为单个文档创建摘要
- **分类摘要**：为某个分类创建汇总摘要
- 摘要可以人工编辑修改

### 3. 内容生产时检索
1. 进入内容生产
2. 输入问题/标题
3. 点击"🔍 检索素材"
4. 系统会从摘要和文档中检索相关内容
5. 点击"✨ 生成内容"

## 后端新增 API

| API | 方法 | 说明 |
|-----|------|------|
| `/api/geo/documents` | GET | 获取文档列表 |
| `/api/geo/documents` | POST | 上传文档 |
| `/api/geo/documents/:id` | GET | 获取单个文档详情 |
| `/api/geo/documents/:id` | DELETE | 删除文档 |
| `/api/geo/summaries` | POST | 创建摘要 |
| `/api/geo/summaries/:id` | PUT | 更新摘要 |
| `/api/geo/summaries/:id` | DELETE | 删除摘要 |
| `/api/geo/retrieve` | POST | 检索相关素材 |

## 数据库新增表

| 表名 | 说明 |
|------|------|
| `geo_documents` | 文档主表 |
| `geo_document_chunks` | 文档分段表 |
| `geo_summaries` | 摘要表 |

## 下一步计划

- [ ] AI 自动生成摘要（调用配置的大模型）
- [ ] 更强大的向量检索（集成 ChromaDB）
- [ ] 知识图谱可视化
- [ ] 内容生成时自动注入检索到的素材

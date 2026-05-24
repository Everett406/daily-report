# 🚀 Hacker News 精选

自动抓取 Hacker News Top 故事，翻译标题并生成中文摘要。

## 📰 功能介绍

### 自动抓取
- 每天早上 **8:00（北京时间）** 自动运行
- 抓取 Hacker News Top 15 故事
- 支持手动触发（workflow_dispatch）

### 智能翻译
- 使用 LLM 自动翻译英文标题为中文
- 保留原文供对照阅读
- 翻译质量取决于配置的 LLM 模型

### 智能分类
自动将故事分类为：
- 🔧 **技术** - 编程、开发、框架相关
- 🤖 **AI** - 人工智能、机器学习相关
- 💼 **创业** - 创业、商业、融资相关
- 🔒 **安全** - 网络安全、漏洞相关
- 💻 **硬件** - 芯片、设备相关
- 🔬 **科学** - 科学研究、论文相关
- 📦 **其他** - 其他类型

## ⚙️ 配置说明

### 必需配置
系统会自动使用您已有的 `LLM_API_KEY` secret，无需额外配置。

### 可选配置
如需自定义 LLM 配置，可在仓库 Settings -> Secrets 中添加：

| Secret | 说明 | 默认值 |
|:---:|:---|:---|
| `LLM_BASE_URL` | API 基础地址 | `https://yunwu.ai/v1` |
| `LLM_MODEL` | 使用的模型 | `gemini-3-pro-preview` |
| `CREATE_HN_ISSUE` | 是否创建 Issue | `false` |

### 启用 Issue 创建
将 `CREATE_HN_ISSUE` 设置为 `true`，每天会自动创建一个 Issue 推送 HN 精选。

## 📄 输出文件

报告会生成在 `HACKERNEWS.md` 文件中，包含：
- 🔥 热门 Top 5（带翻译）
- 📂 分类浏览
- 📊 统计信息

## 🔗 数据来源

- [Hacker News](https://news.ycombinator.com)
- [Hacker News API](https://github.com/HackerNews/API)

## 💡 使用建议

1. **每天早上查看** - 了解全球技术圈最新动态
2. **关注分类** - 快速找到感兴趣的话题
3. **阅读原文** - 点击链接阅读完整文章和评论
4. **参与讨论** - 到 HN 参与评论区的深度讨论

# 🚀 Hacker News 精选

自动抓取 Hacker News Top 故事，翻译标题并生成中文摘要，**每天自动推送 Issue 通知**。

## 📰 功能介绍

### 自动抓取 & 推送
- 每天早上 **8:00（北京时间）** 自动运行
- 抓取 Hacker News Top 15 故事
- **自动创建 Issue 推送摘要** - 不用手动查看！

### 智能翻译
- 使用 LLM 自动翻译英文标题为中文
- 保留原文供对照阅读

### 智能分类
自动将故事分类为：
- 🔧 **技术** - 编程、开发、框架相关
- 🤖 **AI** - 人工智能、机器学习相关
- 💼 **创业** - 创业、商业、融资相关
- 🔒 **安全** - 网络安全、漏洞相关
- 💻 **硬件** - 芯片、设备相关
- 🔬 **科学** - 科学研究、论文相关
- 📦 **其他** - 其他类型

## 🔔 通知方式

每天会自动创建一个 Issue，包含：
- 今日 Top 5 精选（带链接）
- 完整报告链接
- 更新时间

**示例 Issue 标题**: `🚀 HN 精选 | 2026-05-24`

**示例 Issue 内容**:
```
## 🚀 今日 Hacker News 精选

- [AI 新突破：GPT-5 发布](https://example.com)
- [Rust 2.0 正式发布](https://example.com)
- [创业：如何找到 PMF](https://example.com)
- ...

---

📄 [查看完整报告](https://github.com/Everett406/daily-report/blob/main/HACKERNEWS.md)

⏰ 更新时间: 2026/5/24 08:00:00
```

## ⚙️ 配置说明

### 必需配置
系统会自动使用您已有的 `LLM_API_KEY` secret，无需额外配置。

### 可选配置
如需自定义 LLM 配置，可在仓库 Settings -> Secrets 中添加：

| Secret | 说明 | 默认值 |
|:---:|:---|:---|
| `LLM_BASE_URL` | API 基础地址 | `https://yunwu.ai/v1` |
| `LLM_MODEL` | 使用的模型 | `gemini-3-pro-preview` |

### 关闭 Issue 通知
如果只想生成报告而不创建 Issue：
1. 手动触发 workflow
2. 选择 `create_issue` = `false`

## 📄 输出文件

| 文件 | 说明 |
|:---:|:---|
| `HACKERNEWS.md` | 完整报告（包含 Top 5 + 分类浏览） |
| Issue | 每日摘要通知 |

## 🔗 数据来源

- [Hacker News](https://news.ycombinator.com)
- [Hacker News API](https://github.com/HackerNews/API)

## 💡 使用建议

1. **每天早上查看 Issue** - 快速浏览今日热点
2. **点击链接阅读** - 感兴趣的话题直接点击阅读全文
3. **查看完整报告** - 需要更多内容时查看 HACKERNEWS.md
4. **参与讨论** - 到 HN 参与评论区的深度讨论

## 🛠️ 技术细节

- 推送代码后等待 **10 秒** 确保同步完成
- 使用正则表达式提取 Top 5 内容生成摘要
- Issue 自动添加 `hackernews` 和 `daily` 标签

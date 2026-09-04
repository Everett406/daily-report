#!/usr/bin/env python3
"""
Hacker News 精选
自动获取 Top 故事，批量翻译标题，生成每日精选
"""

import json
import os
import re
from datetime import datetime, timezone, timedelta
import requests

BJ_TZ = timezone(timedelta(hours=8))

def get_bj_now():
    return datetime.now(BJ_TZ)

def fetch_top_stories(limit=15):
    try:
        response = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=30)
        story_ids = response.json()[:limit]
        stories = []
        for story_id in story_ids:
            try:
                story_resp = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json", timeout=30)
                story = story_resp.json()
                if story and story.get("title"):
                    stories.append(story)
            except Exception as e:
                print(f"Error fetching story {story_id}: {e}")
                continue
        return stories
    except Exception as e:
        print(f"Error fetching top stories: {e}")
        return []


def batch_translate_titles(titles, api_key, base_url, model):
    """一次 LLM 调用批量翻译全部标题，返回 {原文: 译文} 映射"""
    if not api_key or not titles:
        return {}
    unique = list(dict.fromkeys(titles))
    numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(unique))
    prompt = f"""请把以下 {len(unique)} 条 Hacker News 英文标题翻译成简洁准确的中文。

要求：
- 按原编号逐行输出，格式：编号. 译文
- 只输出译文，不要解释，不要输出其他内容
- 专有名词、产品名、公司名保留英文

{numbered}"""

    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 3000,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    for attempt in range(2):
        try:
            resp = requests.post(f"{base_url}/chat/completions", headers=headers, json=data, timeout=90)
            result = resp.json()
            reply = result["choices"][0]["message"]["content"].strip()
            mapping = {}
            for line in reply.splitlines():
                m = re.match(r"\s*(\d+)\s*[.、)．:：]\s*(.+)", line.strip())
                if m:
                    idx = int(m.group(1)) - 1
                    if 0 <= idx < len(unique):
                        mapping[unique[idx]] = m.group(2).strip()
            if mapping:
                print(f"Translated {len(mapping)}/{len(unique)} titles in one batch call")
                return mapping
        except Exception as e:
            print(f"[WARN] Batch translate attempt {attempt + 1}/2 failed: {e}")
    print("[WARN] Batch translation failed, will use original English titles")
    return {}


def get_domain(url):
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        return domain.replace("www.", "")
    except Exception:
        return "news.ycombinator.com"


def categorize_story(title):
    categories = {
        "AI": ["ai", "llm", "gpt", "gemini", "claude", "neural", "machine learning", "model"],
        "技术": ["programming", "code", "software", "api", "framework", "language",
               "python", "javascript", "rust", "go", "typescript", "sql", "database", "linux"],
        "安全": ["security", "hack", "vulnerability", "exploit", "breach", "malware"],
        "硬件": ["hardware", "chip", "cpu", "gpu", "raspberry", "arduino", "device"],
        "创业": ["startup", "business", "company", "funding", "saas"],
        "科学": ["science", "research", "study", "paper", "space", "physics"],
    }
    title_lower = title.lower()
    for category, keywords in categories.items():
        if any(kw in title_lower for kw in keywords):
            return category
    return "其他"


def generate_hn_report(stories, translations):
    categorized = {}
    for story in stories:
        category = categorize_story(story.get("title", ""))
        categorized.setdefault(category, []).append(story)

    date_str = get_bj_now().strftime("%Y年%m月%d日")
    report = f"""# 🚀 Hacker News 精选 | {date_str}

> 自动抓取 Hacker News Top 故事，批量翻译标题生成中文精选

---

"""

    def show_title(story):
        t = story.get("title", "")
        return translations.get(t, t)

    report += "## 🔥 热门 Top 5\n\n"
    for i, story in enumerate(stories[:5], 1):
        title = story.get("title", "")
        url = story.get("url", f"https://news.ycombinator.com/item?id={story.get('id')}")
        score = story.get("score", 0)
        comments = story.get("descendants", 0)
        domain = get_domain(url)
        report += f"""### {i}. [{show_title(story)}]({url})
- **原文**: {title}
- **来源**: {domain} | 👍 {score} | 💬 {comments}

"""

    report += "---\n\n## 📂 分类浏览\n\n"
    priority = ["AI", "技术", "安全", "硬件", "创业", "科学", "其他"]
    for category in priority:
        if not categorized.get(category):
            continue
        report += f"### {category}\n\n"
        for story in categorized[category][:3]:
            url = story.get("url", f"https://news.ycombinator.com/item?id={story.get('id')}")
            score = story.get("score", 0)
            report += f"- [{show_title(story)}]({url}) ({score}👍)\n"
        report += "\n"

    translated_count = sum(1 for s in stories if s.get("title") in translations)
    report += f"""---

## 📊 统计

- **抓取时间**: {get_bj_now().strftime('%Y-%m-%d %H:%M:%S')}
- **故事总数**: {len(stories)}
- **已翻译标题**: {translated_count}/{len(stories)}
- **数据来源**: [Hacker News](https://news.ycombinator.com)

---
*由 GitHub Actions 自动生成*
"""
    return report


def main():
    api_key = os.environ.get("LLM_API_KEY")
    base_url = os.environ.get("LLM_BASE_URL", "https://yunwu.ai/v1")
    model = os.environ.get("LLM_MODEL", "gemini-3-pro-preview")
    print("Fetching Hacker News top stories...")
    stories = fetch_top_stories(limit=15)
    if not stories:
        print("No stories fetched!")
        return
    print(f"Fetched {len(stories)} stories")

    titles = [s.get("title", "") for s in stories if s.get("title")]
    translations = batch_translate_titles(titles, api_key, base_url, model)

    print("Generating report...")
    report = generate_hn_report(stories, translations)
    with open("HACKERNEWS.md", "w", encoding="utf-8") as f:
        f.write(report)
    print("Hacker News report generated successfully!")


if __name__ == "__main__":
    main()

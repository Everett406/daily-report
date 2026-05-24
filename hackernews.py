#!/usr/bin/env python3
"""
Hacker News 精选
自动获取 Top 故事，翻译标题和摘要，生成每日精选
"""

import json
import os
import re
from datetime import datetime, timezone, timedelta
import requests

BJ_TZ = timezone(timedelta(hours=8))

def get_bj_now():
    return datetime.now(BJ_TZ)

def fetch_top_stories(limit=10):
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

def fetch_story_content(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        return resp.text[:5000]
    except:
        return ""

def translate_text(text, api_key, base_url, model):
    if not api_key:
        return text
    try:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        prompt = f"""请将以下英文翻译成中文，保持简洁准确：

{text}

只返回翻译结果，不要解释。"""
        data = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.3}
        response = requests.post(f"{base_url}/chat/completions", headers=headers, json=data, timeout=60)
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Translation error: {e}")
        return text

def summarize_text(text, api_key, base_url, model):
    if not api_key or not text:
        return "暂无摘要"
    try:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        text = text[:3000]
        prompt = f"""请为以下内容生成一段简短的中文摘要（50字以内）：

{text}

只返回摘要，不要解释。"""
        data = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.5}
        response = requests.post(f"{base_url}/chat/completions", headers=headers, json=data, timeout=60)
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Summarization error: {e}")
        return "摘要生成失败"

def get_domain(url):
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        return domain.replace("www.", "")
    except:
        return "news.ycombinator.com"

def categorize_story(title):
    categories = {
        "技术": ["programming", "code", "software", "api", "framework", "language", "python", "javascript", "rust", "go"],
        "AI": ["ai", "machine learning", "llm", "gpt", "neural", "model"],
        "创业": ["startup", "business", "company", "funding"],
        "安全": ["security", "hack", "vulnerability", "exploit"],
        "硬件": ["hardware", "chip", "cpu", "gpu", "device"],
        "科学": ["science", "research", "study", "paper"]
    }
    title_lower = title.lower()
    for category, keywords in categories.items():
        if any(kw in title_lower for kw in keywords):
            return category
    return "其他"

def generate_hn_report(stories, api_key=None, base_url=None, model=None):
    categorized = {}
    for story in stories:
        category = categorize_story(story.get("title", ""))
        if category not in categorized:
            categorized[category] = []
        categorized[category].append(story)
    date_str = get_bj_now().strftime("%Y年%m月%d日")
    report = f"""# 🚀 Hacker News 精选 | {date_str}

> 自动抓取 Hacker News Top 故事，翻译标题并生成中文摘要

---

"""
    report += "## 🔥 热门 Top 5\n\n"
    for i, story in enumerate(stories[:5], 1):
        title = story.get("title", "")
        url = story.get("url", f"https://news.ycombinator.com/item?id={story.get('id')}")
        score = story.get("score", 0)
        comments = story.get("descendants", 0)
        domain = get_domain(url)
        translated_title = title
        if api_key:
            translated_title = translate_text(title, api_key, base_url, model)
        report += f"""### {i}. [{translated_title}]({url})
- **原文**: {title}
- **来源**: {domain} | 👍 {score} | 💬 {comments}

"""
    report += "---\n\n## 📂 分类浏览\n\n"
    priority = ["技术", "AI", "创业", "安全", "硬件", "科学", "其他"]
    for category in priority:
        if category not in categorized or not categorized[category]:
            continue
        report += f"### {category}\n\n"
        for story in categorized[category][:3]:
            title = story.get("title", "")
            url = story.get("url", f"https://news.ycombinator.com/item?id={story.get('id')}")
            score = story.get("score", 0)
            translated_title = title
            if api_key:
                translated_title = translate_text(title, api_key, base_url, model)
            report += f"- [{translated_title}]({url}) ({score}👍)\n"
        report += "\n"
    report += f"""---

## 📊 统计

- **抓取时间**: {get_bj_now().strftime('%Y-%m-%d %H:%M:%S')}
- **故事总数**: {len(stories)}
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
    print("Generating report...")
    report = generate_hn_report(stories, api_key, base_url, model)
    with open("HACKERNEWS.md", "w", encoding="utf-8") as f:
        f.write(report)
    print("Hacker News report generated successfully!")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Hacker News \u7cbe\u9009
\u81ea\u52a8\u83b7\u53d6 Top \u6545\u4e8b\uff0c\u7ffb\u8bd1\u6807\u9898\u548c\u6458\u8981\uff0c\u751f\u6210\u6bcf\u65e5\u7cbe\u9009
"""

import json
import os
import re
from datetime import datetime, timezone, timedelta

BJ_TZ = timezone(timedelta(hours=8))

def get_bj_now():
    return datetime.now(BJ_TZ)

import requests

def fetch_top_stories(limit=10):
    """\u83b7\u53d6 Hacker News Top \u6545\u4e8b"""
    try:
        response = requests.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json",
            timeout=30
        )
        story_ids = response.json()[:limit]
        
        stories = []
        for story_id in story_ids:
            try:
                story_resp = requests.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json",
                    timeout=30
                )
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
    """\u83b7\u53d6\u7f51\u9875\u5185\u5bb9"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0"
        }
        resp = requests.get(url, headers=headers, timeout=10)
        return resp.text[:5000]
    except:
        return ""

def translate_text(text, api_key, base_url, model):
    """\u4f7f\u7528 LLM \u7ffb\u8bd1\u6587\u672c"""
    if not api_key:
        return text
    
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        prompt = f"""\u8bf7\u5c06\u4ee5\u4e0b\u82f1\u6587\u7ffb\u8bd1\u6210\u4e2d\u6587\uff0c\u4fdd\u6301\u7b80\u6d01\u51c6\u786e\uff1a\n
{text}

\u53ea\u8fd4\u56de\u7ffb\u8bd1\u7ed3\u679c\uff0c\u4e0d\u8981\u89e3\u91ca\u3002"""
        
        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3
        }
        
        response = requests.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=data,
            timeout=60
        )
        
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Translation error: {e}")
        return text

def summarize_text(text, api_key, base_url, model):
    """\u4f7f\u7528 LLM \u751f\u6210\u6458\u8981"""
    if not api_key or not text:
        return "\u6682\u65e0\u6458\u8981"
    
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        text = text[:3000]
        
        prompt = f"""\u8bf7\u4e3a\u4ee5\u4e0b\u5185\u5bb9\u751f\u6210\u4e00\u6bb5\u7b80\u77ed\u7684\u4e2d\u6587\u6458\u8981\uff0850\u5b57\u4ee5\u5185\uff09\uff1a\n
{text}

\u53ea\u8fd4\u56de\u6458\u8981\uff0c\u4e0d\u8981\u89e3\u91ca\u3002"""
        
        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.5
        }
        
        response = requests.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=data,
            timeout=60
        )
        
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Summarization error: {e}")
        return "\u6458\u8981\u751f\u6210\u5931\u8d25"

def get_domain(url):
    """\u4ece URL \u63d0\u53d6\u57df\u540d"""
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        return domain.replace("www.", "")
    except:
        return "news.ycombinator.com"

def categorize_story(title):
    """\u6839\u636e\u6807\u9898\u5206\u7c7b\u6545\u4e8b"""
    categories = {
        "\u6280\u672f": ["programming", "code", "software", "api", "framework", "language", "python", "javascript", "rust", "go", "\u5f00\u53d1", "\u7f16\u7a0b"],
        "AI": ["ai", "machine learning", "llm", "gpt", "neural", "model", "\u4eba\u5de5\u667a\u80fd", "\u673a\u5668\u5b66\u4e60"],
        "\u521b\u4e1a": ["startup", "business", "company", "funding", "\u878d\u8d44", "\u521b\u4e1a", "\u516c\u53f8"],
        "\u5b89\u5168": ["security", "hack", "vulnerability", "exploit", "\u5b89\u5168", "\u6f0f\u6d1e"],
        "\u786c\u4ef6": ["hardware", "chip", "cpu", "gpu", "device", "\u786c\u4ef6", "\u82af\u7247"],
        "\u79d1\u5b66": ["science", "research", "study", "paper", "\u79d1\u5b66", "\u7814\u7a76"]
    }
    
    title_lower = title.lower()
    for category, keywords in categories.items():
        if any(kw in title_lower for kw in keywords):
            return category
    return "\u5176\u4ed6"

def generate_hn_report(stories, api_key=None, base_url=None, model=None):
    """\u751f\u6210 Hacker News \u62a5\u544a"""
    
    categorized = {}
    for story in stories:
        category = categorize_story(story.get("title", ""))
        if category not in categorized:
            categorized[category] = []
        categorized[category].append(story)
    
    date_str = get_bj_now().strftime("%Y\u5e74%m\u6708%d\u65e5")
    
    report = f"""# \ud83d\ude80 Hacker News \u7cbe\u9009 | {date_str}

> \u81ea\u52a8\u6293\u53d6 Hacker News Top \u6545\u4e8b\uff0c\u7ffb\u8bd1\u6807\u9898\u548c\u751f\u6210\u4e2d\u6587\u6458\u8981

---

"""
    
    report += "## \ud83d\udd25 \u70ed\u95e8 Top 5\n\n"
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
- **\u539f\u6587**: {title}
- **\u6765\u6e90**: {domain} | \ud83d\udc4d {score} | \ud83d\udcac {comments}

"""
    
    report += "---\n\n## \ud83d\udcc2 \u5206\u7c7b\u6d4f\u89c8\n\n"
    
    priority = ["\u6280\u672f", "AI", "\u521b\u4e1a", "\u5b89\u5168", "\u786c\u4ef6", "\u79d1\u5b66", "\u5176\u4ed6"]
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
            
            report += f"- [{translated_title}]({url}) ({score}\ud83d\udc4d)\n"
        
        report += "\n"
    
    report += f"""---

## \ud83d\udcca \u7edf\u8ba1

- **\u6293\u53d6\u65f6\u95f4**: {get_bj_now().strftime('%Y-%m-%d %H:%M:%S')}
- **\u6545\u4e8b\u603b\u6570**: {len(stories)}
- **\u6570\u636e\u6765\u6e90**: [Hacker News](https://news.ycombinator.com)

---
*\u7531 GitHub Actions \u81ea\u52a8\u751f\u6210*
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

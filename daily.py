import calendar
import json
import os
import random
import re
import sys
import urllib.request
from datetime import date, datetime

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


def req_json(url, headers=None):
    h = {"User-Agent": "Mozilla/5.0"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def req_text(url, ua="curl/7.68.0"):
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read().decode("utf-8").strip()


def fetch_bing():
    d = req_json("https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=zh-CN")
    img = d["images"][0]
    return "https://www.bing.com" + img["url"], img["copyright"]


def fetch_hitokoto():
    d = req_json("https://v1.hitokoto.cn/?encode=json")
    return d["hitokoto"], d.get("from_who") or "", d.get("from") or ""


def fetch_weather(city):
    return req_text(f"https://wttr.in/{city}?format=4")


def fetch_history():
    now = datetime.now()
    d = req_json(f"https://history.muffinlabs.com/date/{now.month}/{now.day}")
    ev = d.get("data", {}).get("Events", [])
    if ev:
        e = ev[-1]
        t = re.sub(r"<[^>]+>", "", e["text"])
        return f"{e['year']}年：{t}"
    return "暂无记录"


def fetch_weibo():
    d = req_json("https://weibo.com/ajax/side/hotSearch", headers={"Referer": "https://weibo.com/"})
    tops = d.get("data", {}).get("realtime", [])[:5]
    return [(t.get("rank", i) + 1, t.get("note", "无标题")) for i, t in enumerate(tops)]


def fetch_poison():
    d = req_json("https://api.shadiao.pro/chp")
    return d["data"]["text"]


def fetch_holiday():
    d = req_json("https://timor.tech/api/holiday/next")
    h = d.get("holiday", {})
    return h.get("name", "未知假期"), h.get("rest", "?")


def calc_progress():
    now = datetime.now()
    leap = now.year % 4 == 0 and (now.year % 100 != 0 or now.year % 400 == 0)
    total = 366 if leap else 365
    y = round(now.timetuple().tm_yday / total * 100, 1)
    m = round(now.day / calendar.monthrange(now.year, now.month)[1] * 100, 1)
    w = round((now.weekday() + 1) / 7 * 100, 1)
    s = now.hour * 3600 + now.minute * 60 + now.second
    d = round(s / 86400 * 100, 1)
    return y, m, w, d


def calc_countdown():
    today = date.today()
    ds = (5 - today.weekday()) % 7
    if ds == 0:
        wf = "今天就是周六！"
    else:
        wf = f"还有 {ds} 天"
    ny = (date(today.year + 1, 1, 1) - today).days
    return wf, ny


def get_yiji():
    seed = int(datetime.now().strftime("%Y%m%d"))
    random.seed(seed)
    yi = random.sample(["摸鱼", "喝奶茶", "发呆", "追剧", "吃火锅", "睡到自然醒", "逛公园", "买刮刮乐", "带薪聊天", "早退"], 2)
    ji = random.sample(["开会", "加班", "看余额", "称体重", "回领导消息", "早起", "讲道理", "做重大决定", "立 flag", "素颜出门"], 2)
    return yi, ji


def close_old_issues(token):
    url = "https://api.github.com/repos/Everett406/daily-report/issues?state=open"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            issues = json.loads(resp.read())
    except Exception:
        return
    for issue in issues:
        patch_url = issue["url"]
        data = json.dumps({"state": "closed"}).encode()
        req2 = urllib.request.Request(patch_url, data=data, method="PATCH")
        req2.add_header("Authorization", f"Bearer {token}")
        req2.add_header("Accept", "application/vnd.github+json")
        req2.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req2, timeout=10):
                pass
        except Exception as e:
            print(f"[WARN] close issue failed: {e}")


def create_issue(title, body, token):
    close_old_issues(token)
    url = "https://api.github.com/repos/Everett406/daily-report/issues"
    data = json.dumps({"title": title, "body": body}).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


# ---------- RSS ----------

def fetch_rss(url, max_items=3):
    try:
        import feedparser
        d = feedparser.parse(url)
        entries = d.entries[:max_items]
        articles = []
        for e in entries:
            title = e.get("title", "无标题")
            summary = e.get("summary", "") or e.get("description", "")
            summary = re.sub(r"<[^>]+>", "", summary)
            summary = re.sub(r"\s+", " ", summary).strip()
            if len(summary) > 800:
                summary = summary[:800] + "..."
            articles.append({"title": title, "summary": summary})
        return articles
    except Exception:
        return _fetch_rss_simple(url, max_items)


def _fetch_rss_simple(url, max_items):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            xml = resp.read().decode("utf-8")
    except Exception:
        return []
    import xml.etree.ElementTree as ET
    items = []
    try:
        root = ET.fromstring(xml)
        channel = root.find("channel")
        if channel is not None:
            for item in channel.findall("item")[:max_items]:
                title = item.findtext("title", default="无标题")
                desc = item.findtext("description", default="")
                desc = re.sub(r"<[^>]+>", "", desc)
                items.append({"title": title, "summary": desc[:800]})
            return items
    except Exception:
        pass
    try:
        root = ET.fromstring(xml)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("atom:entry", ns)[:max_items]:
            title = entry.findtext("atom:title", default="无标题", namespaces=ns)
            summary = entry.findtext("atom:summary", default="", namespaces=ns) or entry.findtext("atom:content", default="", namespaces=ns)
            summary = re.sub(r"<[^>]+>", "", summary)
            items.append({"title": title, "summary": summary[:800]})
        return items
    except Exception:
        pass
    return []


# ---------- LLM ----------

def summarize_with_llm(articles, api_key, base_url, model):
    if not articles:
        return "今日 RSS 暂无更新。"

    content = "\n\n".join([f"标题：{a['title']}\n摘要：{a['summary']}" for a in articles])

    prompt = f"""请阅读以下RSS订阅文章，用中文总结为3-5条早报简讯。
要求：
- 每条简讯控制在50字以内
- 只保留最关键的信息
- 语气轻松，像朋友之间分享消息
- 输出格式为 bullet points（用 - 开头）

{content}"""

    data = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 800
    }).encode()

    req = urllib.request.Request(f"{base_url}/chat/completions", data=data, method="POST")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")

    with urllib.request.urlopen(req, timeout=90) as resp:
        result = json.loads(resp.read())

    text = result["choices"][0]["message"]["content"]
    return text.strip()


# ================= 主逻辑 =================

with open("config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

if not cfg.get("enabled", True):
    with open("README.md", "w", encoding="utf-8") as f:
        f.write("# 每日早报\n\n今日已暂停更新。如需恢复，请将 `config.json` 中的 `enabled` 改为 `true`。")
    print("[PAUSED] 今日已暂停")
    sys.exit(0)

city = cfg.get("city", "Beijing")
today = datetime.now()
date_str = today.strftime("%Y年%m月%d日")
week_map = {"Monday":"周一","Tuesday":"周二","Wednesday":"周三","Thursday":"周四","Friday":"周五","Saturday":"周六","Sunday":"周日"}
week_str = week_map.get(today.strftime("%A"), today.strftime("%A"))

# ---------- 抓取数据 ----------
data = {}

# Bing
data["bing_url"] = ""
data["bing_copy"] = ""
if cfg.get("bing_wallpaper", True):
    try:
        data["bing_url"], data["bing_copy"] = fetch_bing()
    except Exception as e:
        print(f"[WARN] Bing: {e}")

# Hitokoto
data["sentence"] = ""
data["origin"] = ""
if cfg.get("hitokoto", True):
    try:
        sent, auth, src = fetch_hitokoto()
        origin = f"—— {auth} " if auth else ""
        if src:
            origin += f"《{src}》"
        data["sentence"] = sent
        data["origin"] = origin.strip()
    except Exception as e:
        print(f"[WARN] Hitokoto: {e}")

# Weather
data["weather"] = ""
if cfg.get("weather", True):
    try:
        data["weather"] = fetch_weather(city)
    except Exception as e:
        data["weather"] = f"获取失败: {e}"

# History
data["history"] = ""
if cfg.get("history_today", True):
    try:
        data["history"] = fetch_history()
    except Exception as e:
        data["history"] = f"获取失败: {e}"

# Weibo
data["tops"] = []
if cfg.get("weibo_hot", True):
    try:
        data["tops"] = fetch_weibo()
    except Exception as e:
        print(f"[WARN] Weibo: {e}")

# Poison
data["soup"] = ""
if cfg.get("poison_soup", True):
    try:
        data["soup"] = fetch_poison()
    except Exception as e:
        data["soup"] = "失败不可怕，可怕的是你还相信这句话。"

# Holiday
data["hname"] = "未知假期"
data["hrest"] = "?"
if cfg.get("countdown", True):
    try:
        data["hname"], data["hrest"] = fetch_holiday()
    except Exception as e:
        print(f"[WARN] Holiday: {e}")

# Progress
data["progress"] = (0, 0, 0, 0)
if cfg.get("time_progress", True):
    data["progress"] = calc_progress()

# Countdown
data["weekend"] = ""
data["newyear"] = ""
if cfg.get("countdown", True):
    data["weekend"], data["newyear"] = calc_countdown()

# Yiji
data["yi"] = []
data["ji"] = []
if cfg.get("daily_tips", True):
    data["yi"], data["ji"] = get_yiji()

# RSS + LLM
data["rss_summary"] = ""
data["rss_raw"] = []
llm_cfg = cfg.get("llm", {})
rss_cfg = cfg.get("rss", [])
api_key = os.environ.get("LLM_API_KEY")

if llm_cfg.get("enabled", False) and api_key and rss_cfg:
    all_articles = []
    for src in rss_cfg:
        try:
            articles = fetch_rss(src.get("url"), src.get("max", 3))
            all_articles.extend(articles)
            data["rss_raw"].append({"name": src.get("name", "未知"), "articles": articles})
        except Exception as e:
            print(f"[WARN] RSS {src.get('name')}: {e}")
    if all_articles:
        try:
            data["rss_summary"] = summarize_with_llm(
                all_articles,
                api_key,
                llm_cfg.get("base_url", "https://api.openai.com/v1"),
                llm_cfg.get("model", "gpt-4o-mini")
            )
        except Exception as e:
            print(f"[WARN] LLM summary: {e}")
            data["rss_summary"] = ""

# ---------- 生成 README（详细版） ----------
readme = []
readme.append(f"# 📰 每日早报 {date_str} {week_str}")
readme.append("")

if data["sentence"]:
    readme.append(f"> **{data['sentence']}** {data['origin']}")
    readme.append("")

if data["bing_url"]:
    readme.append(f"![Bing Wallpaper]({data['bing_url']})")
    readme.append(f"> {data['bing_copy']}")
    readme.append("")

# RSS Summary (README 置顶)
if data["rss_summary"]:
    readme.append("## 📡 RSS 资讯摘要")
    readme.append("")
    readme.append(data["rss_summary"])
    readme.append("")
    # 原始来源折叠
    readme.append("<details>")
    readme.append("<summary>点击查看原始 RSS 来源</summary>")
    readme.append("")
    for src in data["rss_raw"]:
        if src["articles"]:
            readme.append(f"**{src['name']}**")
            for a in src["articles"]:
                readme.append(f"- {a['title']}")
            readme.append("")
    readme.append("</details>")
    readme.append("")

if cfg.get("time_progress", True):
    y, m, w, d = data["progress"]
    readme.append("## ⏳ 时间进度")
    readme.append("")
    readme.append("| 今年 | 本月 | 本周 | 今日 |")
    readme.append("|:---:|:---:|:---:|:---:|")
    readme.append(f"| {y}% | {m}% | {w}% | {d}% |")
    readme.append("")

if cfg.get("countdown", True):
    readme.append("## ⏰ 倒计时")
    readme.append(f"- 周末：{data['weekend']}")
    readme.append(f"- {data['hname']}：还有 {data['hrest']} 天")
    readme.append(f"- 2027年元旦：还有 {data['newyear']} 天")
    readme.append("")

if cfg.get("weather", True) and data["weather"]:
    readme.append("## ☁️ 天气")
    readme.append(f"```\n{data['weather']}\n```")
    readme.append("")

if cfg.get("daily_tips", True):
    readme.append("## 📋 今日宜忌")
    readme.append(f"- **宜**：{'、'.join(data['yi'])}")
    readme.append(f"- **忌**：{'、'.join(data['ji'])}")
    readme.append("")

if data["tops"]:
    readme.append("## 🔥 微博热搜 TOP5")
    for rank, note in data["tops"]:
        readme.append(f"{rank}. {note}")
    readme.append("")

if cfg.get("history_today", True) and data["history"]:
    readme.append("## 📜 历史上的今天")
    readme.append(data["history"])
    readme.append("")

if cfg.get("poison_soup", True) and data["soup"]:
    readme.append("## 🍵 毒鸡汤")
    readme.append(f"> {data['soup']}")
    readme.append("")

readme.append("---")
readme.append(f"*最后更新于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

with open("README.md", "w", encoding="utf-8") as f:
    f.write("\n".join(readme))

# ---------- 生成 Issue（精简版） ----------
issue = []
issue.append(f"## 📰 {date_str} {week_str}")
issue.append("")

if data["sentence"]:
    issue.append(f"> {data['sentence']}")
    issue.append("")

# RSS 摘要放 Issue 里也很合适
if data["rss_summary"]:
    issue.append("**📡 今日资讯**")
    issue.append(data["rss_summary"])
    issue.append("")

if cfg.get("weather", True) and data["weather"]:
    issue.append(f"**☁️ 天气**：`{data['weather']}`")
    issue.append("")

if cfg.get("countdown", True):
    issue.append("**⏳ 倒计时**：")
    issue.append(f"- 周末：{data['weekend']}")
    issue.append(f"- {data['hname']}：还有 {data['hrest']} 天")
    issue.append("")

if cfg.get("daily_tips", True):
    issue.append(f"**📋 今日宜忌**：宜 {'、'.join(data['yi'])}；忌 {'、'.join(data['ji'])}")
    issue.append("")

if data["tops"]:
    issue.append("**🔥 热搜速览**：")
    for rank, note in data["tops"][:3]:
        issue.append(f"{rank}. {note}")
    issue.append("")

if cfg.get("poison_soup", True) and data["soup"]:
    issue.append(f"**🍵 毒鸡汤**：{data['soup']}")
    issue.append("")

issue.append("---")
issue.append("[查看完整版](https://github.com/Everett406/daily-report#readme)")

issue_title = f"📰 每日早报 {date_str}"
issue_body = "\n".join(issue)

# ---------- 创建 Issue ----------
token = os.environ.get("GH_TOKEN")
if token and cfg.get("create_issue", True):
    try:
        create_issue(issue_title, issue_body, token)
        print("[OK] Issue created")
    except Exception as e:
        print(f"[WARN] Create issue failed: {e}")
else:
    print("[SKIP] No token or issue disabled")

print("[OK] README.md generated")

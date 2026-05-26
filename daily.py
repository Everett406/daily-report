import calendar
import json
import os
import random
import re
import sys
import urllib.request
from datetime import date, datetime, timezone, timedelta

BJ_TZ = timezone(timedelta(hours=8))

def get_bj_now():
    return datetime.now(BJ_TZ)

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
    now = get_bj_now()
    d = req_json(f"https://history.muffinlabs.com/date/{now.month}/{now.day}")
    ev = d.get("data", {}).get("Events", [])
    if ev:
        e = ev[-1]
        t = re.sub(r"<[^>]+>", "", e["text"])
        return f"{e['year']}\u5e74\uff1a{t}"
    return "\u6682\u65e0\u8bb0\u5f55"


def fetch_weibo():
    d = req_json("https://weibo.com/ajax/side/hotSearch", headers={"Referer": "https://weibo.com/"})
    tops = d.get("data", {}).get("realtime", [])[:5]
    return [(t.get("rank", i) + 1, t.get("note", "\u65e0\u6807\u9898")) for i, t in enumerate(tops)]


def fetch_poison():
    d = req_json("https://api.shadiao.pro/chp")
    return d["data"]["text"]


def fetch_holiday():
    d = req_json("https://timor.tech/api/holiday/next")
    h = d.get("holiday", {})
    return h.get("name", "\u672a\u77e5\u5047\u671f"), h.get("rest", "?")


def calc_progress():
    now = get_bj_now()
    leap = now.year % 4 == 0 and (now.year % 100 != 0 or now.year % 400 == 0)
    total = 366 if leap else 365
    y = round(now.timetuple().tm_yday / total * 100, 1)
    m = round(now.day / calendar.monthrange(now.year, now.month)[1] * 100, 1)
    w = round((now.weekday() + 1) / 7 * 100, 1)
    s = now.hour * 3600 + now.minute * 60 + now.second
    d = round(s / 86400 * 100, 1)
    return y, m, w, d


def calc_countdown():
    today = get_bj_now().date()
    ds = (5 - today.weekday()) % 7
    if ds == 0:
        wf = "\u4eca\u5929\u5c31\u662f\u5468\u516d\uff01"
    else:
        wf = f"\u8fd8\u6709 {ds} \u5929"
    ny = (date(today.year + 1, 1, 1) - today).days
    return wf, ny


def get_yiji():
    seed = int(get_bj_now().strftime("%Y%m%d"))
    random.seed(seed)
    yi = random.sample(["\u6478\u9c7c", "\u559d\u5976\u8336", "\u53d1\u5446", "\u8ffd\u5267", "\u5403\u706b\u9505", "\u7761\u5230\u81ea\u7136\u9192", "\u901b\u516c\u56ed", "\u4e70\u522e\u522e\u4e50", "\u5e26\u85aa\u804a\u5929", "\u65e9\u9000"], 2)
    ji = random.sample(["\u5f00\u4f1a", "\u52a0\u73ed", "\u770b\u4f59\u989d", "\u79f0\u4f53\u91cd", "\u56de\u9886\u5bfc\u6d88\u606f", "\u65e9\u8d77", "\u8bb2\u9053\u7406", "\u505a\u91cd\u5927\u51b3\u5b9a", "\u7acb flag", "\u7d20\u989c\u51fa\u95e8"], 2)
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
            title = e.get("title", "\u65e0\u6807\u9898")
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
                title = item.findtext("title", default="\u65e0\u6807\u9898")
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
            title = entry.findtext("atom:title", default="\u65e0\u6807\u9898", namespaces=ns)
            summary = entry.findtext("atom:summary", default="", namespaces=ns) or entry.findtext("atom:content", default="", namespaces=ns)
            summary = re.sub(r"<[^>]+>", "", summary)
            items.append({"title": title, "summary": summary[:800]})
        return items
    except Exception:
        pass
    return []


# ---------- LLM\uff08\u4e09\u6b21\u91cd\u8bd5\uff09 ----------

def summarize_with_llm(articles, api_key, base_url, model, max_retries=3):
    if not articles:
        return "\u4eca\u65e5 RSS \u6682\u65e0\u66f4\u65b0\u3002"

    content = "\n\n".join([f"\u6807\u9898\uff1a{a['title']}\n\u6458\u8981\uff1a{a['summary']}" for a in articles])

    prompt = f"""\u4f60\u662f\u4e00\u4e2a\u8d44\u6df1\u79d1\u6280\u65e9\u62a5\u7f16\u8f91\u3002\u8bf7\u9605\u8bfb\u4ee5\u4e0bRSS\u8ba2\u9605\u6587\u7ae0\uff0c\u5148\u6df1\u5165\u7406\u89e3\u6bcf\u7bc7\u6587\u7ae0\u7684\u6838\u5fc3\u8981\u70b9\uff08\u6b64\u6b65\u9aa4\u4ec5\u7528\u4e8e\u4f60\u7684\u5185\u90e8\u63a8\u7406\uff0c\u4e0d\u8981\u8f93\u51fa\uff09\uff0c\u7136\u540e\u76f4\u63a5\u8f93\u51fa\u6700\u7ec8\u603b\u7ed3\u3002\n\n\u8981\u6c42\uff1a\n- \u603b\u7ed3\u4e3a3-5\u6761\u65e9\u62a5\u7b80\u8baf\n- \u6bcf\u6761\u63a7\u5236\u572850\u5b57\u4ee5\u5185\n- \u53ea\u4fdd\u7559\u6700\u5173\u952e\u7684\u4fe1\u606f\n- \u8bed\u6c14\u8f7b\u677e\uff0c\u50cf\u670b\u53cb\u4e4b\u95f4\u5206\u4eab\u6d88\u606f\n- \u8f93\u51fa\u683c\u5f0f\u4e3a bullet points\uff08\u7528 - \u5f00\u5934\uff09\n\n{content}"""

    data = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 2000
    }).encode()

    last_error = None
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(f"{base_url}/chat/completions", data=data, method="POST")
            req.add_header("Authorization", f"Bearer {api_key}")
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=90) as resp:
                result = json.loads(resp.read())
            text = result["choices"][0]["message"]["content"]
            return text.strip()
        except Exception as e:
            last_error = e
            print(f"[WARN] LLM attempt {attempt + 1}/{max_retries} failed: {e}")

    return f"LLM \u603b\u7ed3\u5931\u8d25\uff08\u5df2\u91cd\u8bd5{max_retries}\u6b21\uff09: {last_error}"


# ================= \u4e3b\u903b\u8f91 =================

with open("config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

if not cfg.get("enabled", True):
    with open("README.md", "w", encoding="utf-8") as f:
        f.write("# \u6bcf\u65e5\u65e9\u62a5\n\n\u4eca\u65e5\u5df2\u6682\u505c\u66f4\u65b0\u3002\u5982\u9700\u6062\u590d\uff0c\u8bf7\u5c06 `config.json` \u4e2d\u7684 `enabled` \u6539\u4e3a `true`\u3002")
    print("[PAUSED] \u4eca\u65e5\u5df2\u6682\u505c")
    sys.exit(0)

city = cfg.get("city", "Beijing")
today = get_bj_now()
date_str = today.strftime("%Y\u5e74%m\u6708%d\u65e5")
week_map = {"Monday":"\u5468\u4e00","Tuesday":"\u5468\u4e8c","Wednesday":"\u5468\u4e09","Thursday":"\u5468\u56db","Friday":"\u5468\u4e94","Saturday":"\u5468\u516d","Sunday":"\u5468\u65e5"}
week_str = week_map.get(today.strftime("%A"), today.strftime("%A"))

# ---------- \u6293\u53d6\u6570\u636e ----------
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
        origin = f"\u2014\u2014 {auth} " if auth else ""
        if src:
            origin += f"\u300a{src}\u300b"
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
        data["weather"] = f"\u83b7\u53d6\u5931\u8d25: {e}"

# History
data["history"] = ""
if cfg.get("history_today", True):
    try:
        data["history"] = fetch_history()
    except Exception as e:
        data["history"] = f"\u83b7\u53d6\u5931\u8d25: {e}"

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
        data["soup"] = "\u5931\u8d25\u4e0d\u53ef\u6015\uff0c\u53ef\u6015\u7684\u662f\u4f60\u8fd8\u76f8\u4fe1\u8fd9\u53e5\u8bdd\u3002"

# Holiday
data["hname"] = "\u672a\u77e5\u5047\u671f"
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
            data["rss_raw"].append({"name": src.get("name", "\u672a\u77e5"), "articles": articles})
        except Exception as e:
            print(f"[WARN] RSS {src.get('name')}: {e}")
    if all_articles:
        try:
            data["rss_summary"] = summarize_with_llm(
                all_articles,
                api_key,
                llm_cfg.get("base_url", "https://yunwu.ai/v1"),
                llm_cfg.get("model", "gemini-3-pro-preview")
            )
        except Exception as e:
            print(f"[WARN] LLM summary: {e}")
            data["rss_summary"] = ""

# ---------- \u751f\u6210 README\uff08\u8be6\u7ec6\u7248\uff09 ----------
readme = []
readme.append(f"# 📰 \u6bcf\u65e5\u65e9\u62a5 {date_str} {week_str}")
readme.append("")

if data["sentence"]:
    readme.append(f"> **{data['sentence']}** {data['origin']}")
    readme.append("")

if data["bing_url"]:
    readme.append(f"![Bing Wallpaper]({data['bing_url']})")
    readme.append(f"> {data['bing_copy']}")
    readme.append("")

# RSS Summary (README \u7f6e\u9876)
if data["rss_summary"]:
    readme.append("## 📡 RSS \u8d44\u8baf\u6458\u8981")
    readme.append("")
    readme.append(data["rss_summary"])
    readme.append("")
    readme.append("<details>")
    readme.append("<summary>\u70b9\u51fb\u67e5\u770b\u539f\u59cb RSS \u6765\u6e90</summary>")
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
    readme.append("## \u23f3 \u65f6\u95f4\u8fdb\u5ea6")
    readme.append("")
    readme.append("| \u4eca\u5e74 | \u672c\u6708 | \u672c\u5468 | \u4eca\u65e5 |")
    readme.append("|:---:|:---:|:---:|:---:|")
    readme.append(f"| {y}% | {m}% | {w}% | {d}% |")
    readme.append("")

if cfg.get("countdown", True):
    readme.append("## \u23f0 \u5012\u8ba1\u65f6")
    readme.append(f"- \u5468\u672b\uff1a{data['weekend']}")
    readme.append(f"- {data['hname']}\uff1a\u8fd8\u6709 {data['hrest']} \u5929")
    readme.append(f"- 2027\u5e74\u5143\u65e6\uff1a\u8fd8\u6709 {data['newyear']} \u5929")
    readme.append("")

if cfg.get("weather", True) and data["weather"]:
    readme.append("## \u2601\ufe0f \u5929\u6c14")
    readme.append(f"```\n{data['weather']}\n```")
    readme.append("")

if cfg.get("daily_tips", True):
    readme.append("## 📋 \u4eca\u65e5\u5b9c\u5fcc")
    yi_sep = "\u3001"
    readme.append(f"- **\u5b9c**\uff1a{yi_sep.join(data['yi'])}")
    ji_sep = "\u3001"
    readme.append(f"- **\u5fcc**\uff1a{ji_sep.join(data['ji'])}")
    readme.append("")

if data["tops"]:
    readme.append("## 🔥 \u5fae\u535a\u70ed\u641c TOP5")
    for rank, note in data["tops"]:
        readme.append(f"{rank}. {note}")
    readme.append("")

if cfg.get("history_today", True) and data["history"]:
    readme.append("## 📼 \u5386\u53f2\u4e0a\u7684\u4eca\u5929")
    readme.append(data["history"])
    readme.append("")

if cfg.get("poison_soup", True) and data["soup"]:
    readme.append("## 🍵 \u6bd2\u9e21\u6c64")
    readme.append(f"> {data['soup']}")
    readme.append("")

readme.append("---")
readme.append(f"*\u6700\u540e\u66f4\u65b0\u4e8e {get_bj_now().strftime('%Y-%m-%d %H:%M:%S')}*")

with open("README.md", "w", encoding="utf-8") as f:
    f.write("\n".join(readme))

# ---------- \u751f\u6210 Issue\uff08\u7cbe\u7b80\u7248\uff09 ----------
issue = []
issue.append(f"## 📰 {date_str} {week_str}")
issue.append("")

if data["sentence"]:
    issue.append(f"> {data['sentence']}")
    issue.append("")

if data["rss_summary"]:
    issue.append("**📡 \u4eca\u65e5\u8d44\u8baf**")
    issue.append(data["rss_summary"])
    issue.append("")

if cfg.get("weather", True) and data["weather"]:
    issue.append(f"**\u2601\ufe0f \u5929\u6c14**\uff1a`{data['weather']}`")
    issue.append("")

if cfg.get("countdown", True):
    issue.append("**\u23f3 \u5012\u8ba1\u65f6**\uff1a")
    issue.append(f"- \u5468\u672b\uff1a{data['weekend']}")
    issue.append(f"- {data['hname']}\uff1a\u8fd8\u6709 {data['hrest']} \u5929")
    issue.append("")

if cfg.get("daily_tips", True):
    issue_sep = "\u3001"
    issue.append(f"**📋 \u4eca\u65e5\u5b9c\u5fcc**\uff1a\u5b9c {issue_sep.join(data['yi'])}\uff1b\u5fcc {issue_sep.join(data['ji'])}")
    issue.append("")

if data["tops"]:
    issue.append("**🔥 \u70ed\u641c\u901f\u89c8**\uff1a")
    for rank, note in data["tops"][:3]:
        issue.append(f"{rank}. {note}")
    issue.append("")

if cfg.get("poison_soup", True) and data["soup"]:
    issue.append(f"**🍵 \u6bd2\u9e21\u6c64**\uff1a{data['soup']}")
    issue.append("")

issue.append("---")
issue.append("[\u67e5\u770b\u5b8c\u6574\u7248](https://github.com/Everett406/daily-report#readme)")

issue_title = f"📰 \u6bcf\u65e5\u65e9\u62a5 {date_str}"
issue_body = "\n".join(issue)

# ---------- \u521b\u5efa Issue ----------
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

import calendar
import json
import os
import random
import re
import sys
import urllib.request
import urllib.parse
from datetime import date, datetime, timezone, timedelta

BJ_TZ = timezone(timedelta(hours=8))

def get_bj_now():
    return datetime.now(BJ_TZ)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


def req_json(url, headers=None, timeout=15):
    h = {"User-Agent": "Mozilla/5.0"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def req_text(url, ua="curl/7.68.0", timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8").strip()


def fetch_bing():
    d = req_json("https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=zh-CN")
    img = d["images"][0]
    return "https://www.bing.com" + img["url"], img["copyright"]


def fetch_hitokoto():
    d = req_json("https://v1.hitokoto.cn/?encode=json")
    return d["hitokoto"], d.get("from_who") or "", d.get("from") or ""


def make_hitokoto_origin(auth, src):
    """过滤『—— 网络 《网络》』这类无意义署名"""
    parts = []
    if auth and auth not in ("网络", "佚名", "互联网"):
        parts.append(f"—— {auth}")
    if src and src != "网络":
        parts.append(f"《{src}》")
    return " ".join(parts)


# ---------- 天气（Open-Meteo 优先，wttr.in 兜底） ----------

WMO_CODES = {
    0: ("晴", "☀️"), 1: ("基本晴", "🌤️"), 2: ("局部多云", "⛅"), 3: ("阴", "☁️"),
    45: ("雾", "🌫️"), 48: ("雾凇", "🌫️"),
    51: ("毛毛雨", "🌦️"), 53: ("毛毛雨", "🌦️"), 55: ("大毛毛雨", "🌦️"),
    56: ("冻毛毛雨", "🌧️"), 57: ("冻毛毛雨", "🌧️"),
    61: ("小雨", "🌦️"), 63: ("中雨", "🌧️"), 65: ("大雨", "🌧️"),
    66: ("冻雨", "🌧️"), 67: ("冻雨", "🌧️"),
    71: ("小雪", "🌨️"), 73: ("中雪", "🌨️"), 75: ("大雪", "❄️"), 77: ("雪粒", "🌨️"),
    80: ("阵雨", "🌦️"), 81: ("阵雨", "🌧️"), 82: ("强阵雨", "🌧️"),
    85: ("阵雪", "🌨️"), 86: ("阵雪", "🌨️"),
    95: ("雷暴", "⛈️"), 96: ("雷暴伴冰雹", "⛈️"), 99: ("雷暴伴冰雹", "⛈️"),
}

def fetch_weather_open_meteo(city):
    geo_url = "https://geocoding-api.open-meteo.com/v1/search?" + urllib.parse.urlencode(
        {"name": city, "count": 1, "language": "zh", "format": "json"})
    geo = req_json(geo_url, timeout=10)
    results = geo.get("results") or []
    if not results:
        raise RuntimeError(f"geocoding no result: {city}")
    loc = results[0]
    name = loc.get("name") or city
    wx_url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode({
        "latitude": loc["latitude"], "longitude": loc["longitude"],
        "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
        "timezone": "Asia/Shanghai"})
    d = req_json(wx_url, timeout=10)
    cur = d.get("current", {})
    code = int(cur.get("weather_code", -1))
    desc, emoji = WMO_CODES.get(code, ("未知", "🌡️"))
    temp = cur.get("temperature_2m")
    hum = cur.get("relative_humidity_2m")
    wind = cur.get("wind_speed_10m")
    parts = [f"{name} {emoji} {desc}"]
    if temp is not None:
        parts.append(f"{temp}°C")
    if hum is not None:
        parts.append(f"湿度{hum}%")
    if wind is not None:
        parts.append(f"风速{wind}km/h")
    return " · ".join(parts)


def fetch_weather(city):
    return req_text(f"https://wttr.in/{urllib.parse.quote(city)}?format=4&m")


def fetch_history():
    now = get_bj_now()
    d = req_json(f"https://history.muffinlabs.com/date/{now.month}/{now.day}")
    ev = d.get("data", {}).get("Events", [])
    if ev:
        e = ev[-1]
        t = re.sub(r"<[^>]+>", "", e["text"])
        return e["year"], t
    return None, "暂无记录"


def fetch_news_60s(max_items=10):
    d = req_json("https://60s.viki.moe/v2/60s", timeout=10)
    news = d.get("data", {}).get("news", [])[:max_items]
    return [re.sub(r"\s+", " ", n).strip() for n in news if n.strip()]


def fetch_weibo(max_items=10):
    d = req_json("https://weibo.com/ajax/side/hotSearch", headers={"Referer": "https://weibo.com/"})
    realtime = d.get("data", {}).get("realtime", [])
    seen = set()
    tops = []
    for t in realtime:
        note = (t.get("note") or "").strip()
        if not note or t.get("is_ad") or note in seen:
            continue
        seen.add(note)
        tops.append(note)
        if len(tops) >= max_items:
            break
    return [(i + 1, note) for i, note in enumerate(tops)]


def fetch_poison():
    d = req_json("https://api.shadiao.pro/chp")
    return d["data"]["text"]


def fetch_holiday():
    d = req_json("https://timor.tech/api/holiday/next")
    h = d.get("holiday") or {}
    return h.get("name") or "", h.get("rest")


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


def progress_bar(pct, length=10):
    filled = int(round(pct / 100 * length))
    return "█" * filled + "░" * (length - filled)


def calc_countdown():
    today = get_bj_now().date()
    ds = (5 - today.weekday()) % 7
    if ds == 0:
        wf = "今天就是周六！"
    else:
        wf = f"还有 {ds} 天"
    ny = (date(today.year + 1, 1, 1) - today).days
    return wf, ny


def get_yiji():
    seed = int(get_bj_now().strftime("%Y%m%d"))
    random.seed(seed)
    yi = random.sample(["摸鱼", "喝奶茶", "发呆", "追剧", "吃火锅", "睡到自然醒", "逛公园", "买刮刮乐", "带薪聊天", "早退"], 2)
    ji = random.sample(["开会", "加班", "看余额", "称体重", "回领导消息", "早起", "讲道理", "做重大决定", "立 flag", "素颜出门"], 2)
    return yi, ji


# ---------- GitHub Issue ----------

def gh_headers(token):
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
            "Content-Type": "application/json"}


def close_old_issues(token, repo):
    """只关闭 bot 自己创建的旧 Issue，不动用户手动开的"""
    url = f"https://api.github.com/repos/{repo}/issues?state=open&per_page=50"
    req = urllib.request.Request(url, headers=gh_headers(token))
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            issues = json.loads(resp.read())
    except Exception:
        return
    for issue in issues:
        if issue.get("user", {}).get("login") != "github-actions[bot]":
            continue
        req2 = urllib.request.Request(issue["url"], data=json.dumps({"state": "closed"}).encode(),
                                      method="PATCH", headers=gh_headers(token))
        try:
            with urllib.request.urlopen(req2, timeout=10):
                pass
        except Exception as e:
            print(f"[WARN] close issue failed: {e}")


def create_issue(title, body, token, repo):
    close_old_issues(token, repo)
    url = f"https://api.github.com/repos/{repo}/issues"
    data = json.dumps({"title": title, "body": body}).encode()
    req = urllib.request.Request(url, data=data, method="POST", headers=gh_headers(token))
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
            xml = resp.read().decode("utf-8", errors="replace")
    except Exception:
        return []
    import xml.etree.ElementTree as ET
    items = []

    def clean(s):
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()

    try:
        root = ET.fromstring(xml)
        channel = root.find("channel")
        if channel is not None:
            for item in channel.findall("item")[:max_items]:
                title = item.findtext("title", default="无标题")
                desc = item.findtext("description", default="")
                items.append({"title": clean(title), "summary": clean(desc)[:800]})
            if items:
                return items
    except Exception:
        pass
    try:
        root = ET.fromstring(xml)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("atom:entry", ns)[:max_items]:
            title = entry.findtext("atom:title", default="无标题", namespaces=ns)
            summary = entry.findtext("atom:summary", default="", namespaces=ns) or \
                      entry.findtext("atom:content", default="", namespaces=ns)
            items.append({"title": clean(title), "summary": clean(summary)[:800]})
    except Exception:
        pass
    return items


# ---------- LLM ----------

def llm_chat(messages, api_key, base_url, model, temperature=0.7, max_tokens=2000, max_retries=2):
    data = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }).encode()
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    last_error = None
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(f"{base_url}/chat/completions", data=data,
                                         method="POST", headers=headers)
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read())
            return result["choices"][0]["message"]["content"].strip()
        except Exception as e:
            last_error = e
            print(f"[WARN] LLM attempt {attempt + 1}/{max_retries} failed: {e}")
    print(f"[WARN] LLM failed after {max_retries} retries: {last_error}")
    return None


def summarize_rss(articles, api_key, base_url, model):
    if not articles:
        return None
    content = "\n\n".join([f"标题：{a['title']}\n摘要：{a['summary']}" for a in articles])
    prompt = f"""你是一个资深科技早报编辑。请阅读以下RSS订阅文章，先深入理解每篇文章的核心要点（此步骤仅用于你的内部推理，不要输出），然后直接输出最终总结。

要求：
- 总结为3-5条早报简讯
- 每条控制在50字以内
- 只保留最关键的信息
- 语气轻松，像朋友之间分享消息
- 输出格式为 bullet points（用 - 开头）

{content}"""
    return llm_chat([{"role": "user", "content": prompt}], api_key, base_url, model)


def translate_history(text, api_key, base_url, model):
    if not api_key:
        return ""
    prompt = f"请把下面这段历史事件描述翻译成简洁流畅的中文，只输出译文，不要解释：\n\n{text[:400]}"
    return llm_chat([{"role": "user", "content": prompt}], api_key, base_url, model,
                    temperature=0.3, max_tokens=500) or ""


# ================= 主逻辑 =================

with open("config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

if not cfg.get("enabled", True):
    with open("README.md", "w", encoding="utf-8") as f:
        f.write("# 每日早报\n\n今日已暂停更新。如需恢复，请将 `config.json` 中的 `enabled` 改为 `true`。")
    print("[PAUSED] 今日已暂停")
    sys.exit(0)

city = cfg.get("city", "Changsha")
today = get_bj_now()
date_str = today.strftime("%Y年%m月%d日")
week_map = {"Monday": "周一", "Tuesday": "周二", "Wednesday": "周三", "Thursday": "周四",
            "Friday": "周五", "Saturday": "周六", "Sunday": "周日"}
week_str = week_map.get(today.strftime("%A"), today.strftime("%A"))

repo = os.environ.get("GITHUB_REPOSITORY", "Everett406/daily-report")
api_key = os.environ.get("LLM_API_KEY")
llm_cfg = cfg.get("llm", {})
base_url = os.environ.get("LLM_BASE_URL") or llm_cfg.get("base_url", "https://yunwu.ai/v1")
model = os.environ.get("LLM_MODEL") or llm_cfg.get("model", "gemini-3-pro-preview")
llm_ready = bool(llm_cfg.get("enabled", False) and api_key)

# ---------- 抓取数据 ----------
data = {}

# 今日要闻（60秒读懂世界）
data["news"] = []
if cfg.get("news_60s", True):
    try:
        data["news"] = fetch_news_60s(10)
    except Exception as e:
        print(f"[WARN] 60s news: {e}")

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
        data["sentence"] = sent
        data["origin"] = make_hitokoto_origin(auth, src)
    except Exception as e:
        print(f"[WARN] Hitokoto: {e}")

# 天气：Open-Meteo 优先，wttr.in 兜底
data["weather"] = ""
if cfg.get("weather", True):
    try:
        data["weather"] = fetch_weather_open_meteo(city)
    except Exception as e:
        print(f"[WARN] Open-Meteo: {e}, fallback to wttr.in")
        try:
            data["weather"] = fetch_weather(city)
        except Exception as e2:
            print(f"[WARN] Weather: {e2}")

# 历史上的今天（LLM 可用时翻译成中文）
data["history"] = ""
if cfg.get("history_today", True):
    try:
        year, text = fetch_history()
        if year:
            if llm_ready:
                translated = translate_history(f"{year}年：{text}", api_key, base_url, model)
                data["history"] = translated if translated else f"{year}年：{text}"
            else:
                data["history"] = f"{year}年：{text}"
    except Exception as e:
        print(f"[WARN] History: {e}")

# 微博热搜
data["tops"] = []
if cfg.get("weibo_hot", True):
    try:
        data["tops"] = fetch_weibo(10)
    except Exception as e:
        print(f"[WARN] Weibo: {e}")

# 毒鸡汤
data["soup"] = ""
if cfg.get("poison_soup", True):
    try:
        data["soup"] = fetch_poison()
    except Exception as e:
        data["soup"] = "失败不可怕，可怕的是你还相信这句话。"

# 假期倒计时
data["hname"] = ""
data["hrest"] = None
if cfg.get("countdown", True):
    try:
        data["hname"], data["hrest"] = fetch_holiday()
    except Exception as e:
        print(f"[WARN] Holiday: {e}")

# 时间进度
data["progress"] = (0, 0, 0, 0)
if cfg.get("time_progress", True):
    data["progress"] = calc_progress()

# 周末 / 元旦倒计时
data["weekend"] = ""
data["newyear"] = ""
if cfg.get("countdown", True):
    data["weekend"], data["newyear"] = calc_countdown()

# 宜忌
data["yi"] = []
data["ji"] = []
if cfg.get("daily_tips", True):
    data["yi"], data["ji"] = get_yiji()

# RSS：永远抓取；LLM 可用才做摘要，失败优雅降级
data["rss_summary"] = ""
data["rss_raw"] = []
rss_cfg = cfg.get("rss", [])
all_articles = []
for src in rss_cfg:
    try:
        articles = fetch_rss(src.get("url"), src.get("max", 3))
        articles = [a for a in articles if a["title"]]
        all_articles.extend(articles)
        if articles:
            data["rss_raw"].append({"name": src.get("name", "未知"), "articles": articles})
    except Exception as e:
        print(f"[WARN] RSS {src.get('name')}: {e}")

if llm_ready and all_articles:
    data["rss_summary"] = summarize_rss(all_articles, api_key, base_url, model) or ""
    if not data["rss_summary"]:
        print("[INFO] LLM summary failed, fallback to raw titles")

# ---------- 生成 README ----------
readme = []
readme.append(f"# 📰 每日早报 {date_str} {week_str}")
readme.append("")

if data["sentence"]:
    readme.append(f"> **{data['sentence']}** {data['origin']}".rstrip())
    readme.append("")

if data["bing_url"]:
    readme.append(f"![Bing Wallpaper]({data['bing_url']})")
    readme.append(f"> {data['bing_copy']}")
    readme.append("")

# 今日要闻
if data["news"]:
    readme.append("## 🌍 今日要闻")
    readme.append("")
    for n in data["news"]:
        readme.append(f"- {n}")
    readme.append("")
    readme.append("> 数据源：[每天 60 秒读懂世界](https://github.com/vikiboss/60s)")
    readme.append("")

# RSS / AI 摘要
if data["rss_raw"]:
    readme.append("## 📡 科技资讯")
    readme.append("")
    if data["rss_summary"]:
        readme.append(data["rss_summary"])
        readme.append("")
    else:
        readme.append("> 🤖 AI 摘要暂时不可用，先看原始标题速览：")
        readme.append("")
    readme.append("<details>")
    readme.append("<summary>点击查看原始 RSS 来源</summary>")
    readme.append("")
    for src in data["rss_raw"]:
        readme.append(f"**{src['name']}**")
        for a in src["articles"]:
            readme.append(f"- {a['title']}")
        readme.append("")
    readme.append("</details>")
    readme.append("")

# 时间进度
if cfg.get("time_progress", True):
    y, m, w, d = data["progress"]
    readme.append("## ⏳ 时间进度")
    readme.append("")
    readme.append("| 今年 | 本月 | 本周 | 今日 |")
    readme.append("|:---:|:---:|:---:|:---:|")
    readme.append(f"| {progress_bar(y)} {y}% | {progress_bar(m)} {m}% | {progress_bar(w)} {w}% | {progress_bar(d)} {d}% |")
    readme.append("")

# 倒计时
if cfg.get("countdown", True):
    readme.append("## ⏰ 倒计时")
    readme.append(f"- 周末：{data['weekend']}")
    if data["hname"] and data["hrest"] is not None:
        readme.append(f"- {data['hname']}：还有 {data['hrest']} 天")
    readme.append(f"- 2027年元旦：还有 {data['newyear']} 天")
    readme.append("")

# 天气
if cfg.get("weather", True) and data["weather"]:
    readme.append("## ☁️ 天气")
    readme.append(f"`{data['weather']}`")
    readme.append("")

# 微博热搜
if data["tops"]:
    readme.append("## 🔥 微博热搜 TOP10")
    readme.append("")
    for rank, note in data["tops"]:
        readme.append(f"{rank}. {note}")
    readme.append("")

# 历史上的今天
if cfg.get("history_today", True) and data["history"]:
    readme.append("## 📼 历史上的今天")
    readme.append(data["history"])
    readme.append("")

# 宜忌
if cfg.get("daily_tips", True):
    readme.append("## 📋 今日宜忌")
    readme.append(f"- **宜**：{'、'.join(data['yi'])}")
    readme.append(f"- **忌**：{'、'.join(data['ji'])}")
    readme.append("")

# 毒鸡汤
if cfg.get("poison_soup", True) and data["soup"]:
    readme.append("## 🍵 毒鸡汤")
    readme.append(f"> {data['soup']}")
    readme.append("")

readme.append("---")
readme.append(f"*最后更新于 {get_bj_now().strftime('%Y-%m-%d %H:%M:%S')}（北京时间）*")

with open("README.md", "w", encoding="utf-8") as f:
    f.write("\n".join(readme))

# ---------- 生成 Issue（精简版） ----------
issue = []
issue.append(f"## 📰 {date_str} {week_str}")
issue.append("")

if data["sentence"]:
    issue.append(f"> {data['sentence']}")
    issue.append("")

if data["news"]:
    issue.append("**🌍 今日要闻**")
    for n in data["news"][:5]:
        issue.append(f"- {n}")
    issue.append("")

if data["rss_summary"]:
    issue.append("**📡 科技资讯**")
    issue.append(data["rss_summary"])
    issue.append("")

if cfg.get("weather", True) and data["weather"]:
    issue.append(f"**☁️ 天气**：`{data['weather']}`")
    issue.append("")

if cfg.get("countdown", True):
    issue.append("**⏳ 倒计时**")
    issue.append(f"- 周末：{data['weekend']}")
    if data["hname"] and data["hrest"] is not None:
        issue.append(f"- {data['hname']}：还有 {data['hrest']} 天")
    issue.append("")

if cfg.get("daily_tips", True):
    issue.append(f"**📋 今日宜忌**：宜 {'、'.join(data['yi'])}；忌 {'、'.join(data['ji'])}")
    issue.append("")

if data["tops"]:
    issue.append("**🔥 热搜速览**")
    for rank, note in data["tops"][:3]:
        issue.append(f"{rank}. {note}")
    issue.append("")

if cfg.get("poison_soup", True) and data["soup"]:
    issue.append(f"**🍵 毒鸡汤**：{data['soup']}")
    issue.append("")

issue.append("---")
issue.append(f"[查看完整版](https://github.com/{repo}#readme)")

issue_title = f"📰 每日早报 {date_str}"
issue_body = "\n".join(issue)

token = os.environ.get("GH_TOKEN")
if token and cfg.get("create_issue", True):
    try:
        create_issue(issue_title, issue_body, token, repo)
        print("[OK] Issue created")
    except Exception as e:
        print(f"[WARN] Create issue failed: {e}")
else:
    print("[SKIP] No token or issue disabled")

print("[OK] README.md generated")

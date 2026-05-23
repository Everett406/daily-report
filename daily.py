import calendar
import json
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
        wf = f"{ds} 天"
    ny = (date(today.year + 1, 1, 1) - today).days
    return wf, ny


def get_yiji():
    seed = int(datetime.now().strftime("%Y%m%d"))
    random.seed(seed)
    yi = random.sample(["摸鱼", "喝奶茶", "发呆", "追剧", "吃火锅", "睡到自然醒", "逛公园", "买刮刮乐", "带薪聊天", "早退"], 2)
    ji = random.sample(["开会", "加班", "看余额", "称体重", "回领导消息", "早起", "讲道理", "做重大决定", "立 flag", "素颜出门"], 2)
    return yi, ji


def progress_card(label, pct, color):
    colors = {"blue": "bg-blue-500", "emerald": "bg-emerald-500", "amber": "bg-amber-500", "rose": "bg-rose-500"}
    bar = colors.get(color, "bg-slate-500")
    return f'''<div class="bg-white rounded-2xl p-5 shadow-sm border border-slate-100">
      <div class="flex justify-between items-center mb-2">
        <span class="text-xs text-slate-500 font-medium">{label}</span>
        <span class="text-sm font-bold text-slate-700">{pct}%</span>
      </div>
      <div class="w-full bg-slate-100 rounded-full h-2"><div class="{bar} h-2 rounded-full transition-all" style="width: {pct}%"></div></div>
    </div>'''


# ================= 主逻辑 =================

with open("config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

if not cfg.get("enabled", True):
    with open("README.md", "w", encoding="utf-8") as f:
        f.write("# 每日早报\n\n今日已暂停更新。如需恢复，请将 `config.json` 中的 `enabled` 改为 `true`。")
    with open("index.html", "w", encoding="utf-8") as f:
        f.write("<h1>今日已暂停更新</h1>")
    print("[PAUSED] 今日已暂停")
    sys.exit(0)

city = cfg.get("city", "Beijing")
today = datetime.now()
date_str = today.strftime("%Y年%m月%d日")
week_map = {"Monday":"周一","Tuesday":"周二","Wednesday":"周三","Thursday":"周四","Friday":"周五","Saturday":"周六","Sunday":"周日"}
week_str = week_map.get(today.strftime("%A"), today.strftime("%A"))

parts = {}

# Bing
if cfg.get("bing_wallpaper", True):
    try:
        bing_url, bing_copy = fetch_bing()
        parts["bing_url"] = bing_url
        parts["bing_copy"] = bing_copy
    except Exception as e:
        parts["bing_url"] = ""
        parts["bing_copy"] = str(e)
else:
    parts["bing_url"] = ""
    parts["bing_copy"] = ""

# Hitokoto
if cfg.get("hitokoto", True):
    try:
        sent, auth, src = fetch_hitokoto()
        origin = f"—— {auth} " if auth else ""
        if src:
            origin += f"《{src}》"
        parts["sentence"] = sent
        parts["origin"] = origin.strip()
    except Exception as e:
        parts["sentence"] = "生活明朗，万物可爱。"
        parts["origin"] = ""
else:
    parts["sentence"] = ""
    parts["origin"] = ""

# Progress
if cfg.get("time_progress", True):
    y, m, w, d = calc_progress()
    prog_html = "".join([
        progress_card("今年", y, "blue"),
        progress_card("本月", m, "emerald"),
        progress_card("本周", w, "amber"),
        progress_card("今日", d, "rose"),
    ])
    parts["progress"] = f'<section class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">{prog_html}</section>'
else:
    parts["progress"] = ""

# Countdown
if cfg.get("countdown", True):
    wf, ny = calc_countdown()
    try:
        hname, hrest = fetch_holiday()
    except Exception:
        hname, hrest = "未知假期", "?"
    parts["countdown"] = f'''<div class="bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
      <h3 class="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4">⏳ 倒计时</h3>
      <div class="space-y-4">
        <div class="flex justify-between items-center"><span class="text-slate-500">周末</span><span class="text-lg font-bold text-blue-600">{wf}</span></div>
        <div class="flex justify-between items-center"><span class="text-slate-500">{hname}</span><span class="text-lg font-bold text-emerald-600">{hrest} 天</span></div>
        <div class="flex justify-between items-center"><span class="text-slate-500">2027年元旦</span><span class="text-lg font-bold text-purple-600">{ny} 天</span></div>
      </div>
    </div>'''
else:
    parts["countdown"] = ""

# Weather
if cfg.get("weather", True):
    try:
        w = fetch_weather(city)
    except Exception as e:
        w = f"获取失败: {e}"
    parts["weather"] = f'''<div class="bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
      <h3 class="text-sm font-bold text-slate-400 uppercase tracking-wider mb-3">☁️ 天气</h3>
      <pre class="text-lg font-mono text-slate-700 whitespace-pre-wrap">{w}</pre>
    </div>'''
else:
    parts["weather"] = ""

# History
if cfg.get("history_today", True):
    try:
        h = fetch_history()
    except Exception as e:
        h = f"获取失败: {e}"
    parts["history"] = f'''<div class="bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
      <h3 class="text-sm font-bold text-slate-400 uppercase tracking-wider mb-3">📜 历史上的今天</h3>
      <p class="text-slate-700 leading-relaxed">{h}</p>
    </div>'''
else:
    parts["history"] = ""

# Yiji
if cfg.get("daily_tips", True):
    yi, ji = get_yiji()
    yi_tags = "".join([f'<span class="inline-block bg-emerald-50 text-emerald-600 text-xs px-2 py-1 rounded-full mr-2 mb-2">{x}</span>' for x in yi])
    ji_tags = "".join([f'<span class="inline-block bg-rose-50 text-rose-600 text-xs px-2 py-1 rounded-full mr-2 mb-2">{x}</span>' for x in ji])
    parts["yiji"] = f'''<div class="bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
      <h3 class="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4">📋 今日宜忌</h3>
      <div class="mb-3"><span class="text-xs text-emerald-600 font-bold mr-2">宜</span>{yi_tags}</div>
      <div><span class="text-xs text-rose-600 font-bold mr-2">忌</span>{ji_tags}</div>
    </div>'''
else:
    parts["yiji"] = ""

# Weibo
if cfg.get("weibo_hot", True):
    try:
        tops = fetch_weibo()
    except Exception:
        tops = []
    if tops:
        rows = []
        for rank, note in tops:
            if rank == 1:
                badge = '<span class="text-amber-500 font-bold mr-2 text-sm">1</span>'
            elif rank == 2:
                badge = '<span class="text-slate-400 font-bold mr-2 text-sm">2</span>'
            elif rank == 3:
                badge = '<span class="text-orange-400 font-bold mr-2 text-sm">3</span>'
            else:
                badge = f'<span class="text-slate-300 font-bold mr-2 text-sm w-4 inline-block text-right">{rank}</span>'
            rows.append(f'<div class="flex items-start py-2 border-b border-slate-50 last:border-0">{badge}<span class="text-slate-700 text-sm">{note}</span></div>')
        weibo_html = "".join(rows)
    else:
        weibo_html = "<p class='text-sm text-slate-400'>暂无数据</p>"
    parts["weibo"] = f'''<div class="bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
      <h3 class="text-sm font-bold text-slate-400 uppercase tracking-wider mb-3">🔥 微博热搜</h3>
      <div>{weibo_html}</div>
    </div>'''
else:
    parts["weibo"] = ""

# Poison soup
if cfg.get("poison_soup", True):
    try:
        soup = fetch_poison()
    except Exception:
        soup = "失败不可怕，可怕的是你还相信这句话。"
    parts["soup"] = f'''<div class="bg-slate-800 rounded-2xl p-6 shadow-sm text-white">
      <h3 class="text-sm font-bold text-slate-400 uppercase tracking-wider mb-3">🍵 毒鸡汤</h3>
      <p class="italic text-slate-200 leading-relaxed">"{soup}"</p>
    </div>'''
else:
    parts["soup"] = ""

template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>每日早报 - {{date_str}}</title>
<script src="https://cdn.tailwindcss.com"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;700&family=Noto+Sans+SC:wght@300;400;500;700&display=swap');
body { font-family: 'Noto Sans SC', sans-serif; }
.serif { font-family: 'Noto Serif SC', serif; }
</style>
</head>
<body class="bg-slate-50 text-slate-800">
<div class="max-w-5xl mx-auto px-4 py-10">

  <header class="text-center mb-10">
    <div class="text-xs text-slate-400 tracking-[0.3em] uppercase mb-3">Daily Morning Report</div>
    <h1 class="text-5xl font-bold text-slate-900 mb-2">{{date_str}}</h1>
    <p class="text-lg text-slate-500">{{week_str}}</p>
  </header>

  <section class="relative rounded-3xl overflow-hidden shadow-2xl mb-8 h-80 group">
    <img src="{{bing_url}}" class="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105">
    <div class="absolute inset-0 bg-gradient-to-t from-black/80 via-black/30 to-transparent flex flex-col justify-end p-8">
      <p class="text-white text-2xl serif italic leading-relaxed drop-shadow-lg">"{{sentence}}"</p>
      <p class="text-white/70 text-sm mt-3">{{origin}}</p>
      <p class="text-white/50 text-xs mt-4">{{bing_copy}}</p>
    </div>
  </section>

  {{progress}}

  <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
    <div class="space-y-6">
      {{weather}}
      {{history}}
      {{yiji}}
    </div>
    <div class="space-y-6">
      {{countdown}}
    </div>
    <div class="space-y-6">
      {{weibo}}
      {{soup}}
    </div>
  </div>

  <footer class="text-center text-slate-400 text-sm py-6 border-t border-slate-200">
    更新于 {{update_time}} · 由 GitHub Actions 自动生成
  </footer>

</div>
</body>
</html>"""

html = template
html = html.replace("{{date_str}}", date_str)
html = html.replace("{{week_str}}", week_str)
html = html.replace("{{bing_url}}", parts["bing_url"])
html = html.replace("{{bing_copy}}", parts["bing_copy"])
html = html.replace("{{sentence}}", parts["sentence"])
html = html.replace("{{origin}}", parts["origin"])
html = html.replace("{{progress}}", parts["progress"])
html = html.replace("{{weather}}", parts["weather"])
html = html.replace("{{history}}", parts["history"])
html = html.replace("{{yiji}}", parts["yiji"])
html = html.replace("{{countdown}}", parts["countdown"])
html = html.replace("{{weibo}}", parts["weibo"])
html = html.replace("{{soup}}", parts["soup"])
html = html.replace("{{update_time}}", today.strftime("%Y-%m-%d %H:%M:%S"))

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

readme = """# 每日早报

👉 [点这里看今日早报页面](https://everett406.github.io/daily-report)

由 GitHub Actions 每日自动更新。
"""
with open("README.md", "w", encoding="utf-8") as f:
    f.write(readme)

print("[OK] index.html and README.md generated.")

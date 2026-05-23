import json
import re
import sys
import urllib.request
from datetime import datetime


def fetch_bing():
    url = "https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=zh-CN"
    with urllib.request.urlopen(url, timeout=10) as resp:
        data = json.loads(resp.read())
    img = data["images"][0]
    return "https://www.bing.com" + img["url"], img["copyright"]


def fetch_hitokoto():
    url = "https://v1.hitokoto.cn/?encode=json"
    with urllib.request.urlopen(url, timeout=10) as resp:
        data = json.loads(resp.read())
    return data["hitokoto"], data.get("from_who") or "", data.get("from") or ""


def fetch_weather(city):
    url = f"https://wttr.in/{city}?format=4"
    req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read().decode("utf-8").strip()


def fetch_history():
    now = datetime.now()
    url = f"https://history.muffinlabs.com/date/{now.month}/{now.day}"
    with urllib.request.urlopen(url, timeout=10) as resp:
        data = json.loads(resp.read())
    events = data.get("data", {}).get("Events", [])
    if events:
        e = events[-1]
        text = re.sub(r"<[^>]+>", "", e["text"])
        return f"{e['year']}年：{text}"
    return "暂无记录"


# ================= 主逻辑 =================

with open("config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

if not cfg.get("enabled", True):
    with open("README.md", "w", encoding="utf-8") as f:
        f.write("# 🌅 每日早报\n\n今日已暂停更新。如需恢复，请将 `config.json` 中的 `enabled` 改为 `true`。")
    print("⏸️ 今日已暂停")
    sys.exit(0)

city = cfg.get("city", "Beijing")
today_str = datetime.now().strftime("%Y-%m-%d %A")
lines = []
lines.append(f"# 🌅 每日早报 {today_str}")
lines.append("")

if cfg.get("bing_wallpaper", True):
    try:
        url, copy = fetch_bing()
        lines.append(f"![Bing Wallpaper]({url})")
        lines.append(f"> {copy}")
        lines.append("")
    except Exception as e:
        print(f"Bing 获取失败: {e}")

if cfg.get("hitokoto", True):
    try:
        sentence, author, source = fetch_hitokoto()
        origin = f"—— {author} " if author else ""
        if source:
            origin += f"《{source}》"
        lines.append(f"> **{sentence}** {origin.strip()}")
        lines.append("")
    except Exception as e:
        print(f"一言获取失败: {e}")

lines.append("---")
lines.append("")

if cfg.get("weather", True):
    try:
        w = fetch_weather(city)
        lines.append("## 🌤️ 今日天气")
        lines.append("```")
        lines.append(w)
        lines.append("```")
        lines.append("")
    except Exception as e:
        print(f"天气获取失败: {e}")

if cfg.get("history_today", True):
    try:
        h = fetch_history()
        lines.append("## 📅 历史上的今天")
        lines.append(h)
        lines.append("")
    except Exception as e:
        print(f"历史获取失败: {e}")

lines.append("---")
lines.append("")
lines.append(f"*⏰ 自动更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

with open("README.md", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("✅ README.md 已生成")

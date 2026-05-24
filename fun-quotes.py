#!/usr/bin/env python3
"""
有趣语录推送
每 45 分钟随机推送一条有趣内容到 Issue
北京时间 06:00-23:00 运行，23:00-06:00 静默
"""

import json
import os
import random
import urllib.request
from datetime import datetime, timezone, timedelta

BJ_TZ = timezone(timedelta(hours=8))

def get_bj_now():
    return datetime.now(BJ_TZ)

def req_json(url, headers=None):
    h = {"User-Agent": "Mozilla/5.0"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())

# ==================== 数据源 ====================

def fetch_poison_soup():
    """毒鸡汤"""
    try:
        d = req_json("https://api.shadiao.pro/chp")
        text = d["data"]["text"]
        return {"type": "🍵 毒鸡汤", "text": text}
    except Exception as e:
        print(f"[WARN] poison_soup: {e}")
        return None

def fetch_hitokoto():
    """一言"""
    try:
        d = req_json("https://v1.hitokoto.cn/?encode=json")
        text = d["hitokoto"]
        from_who = d.get("from_who") or ""
        from_ = d.get("from") or ""
        source = ""
        if from_who:
            source += f"—— {from_who} "
        if from_:
            source += f"《{from_}》"
        return {"type": "✨ 一言", "text": text, "source": source.strip()}
    except Exception as e:
        print(f"[WARN] hitokoto: {e}")
        return None

def fetch_tiyanhua():
    """土味情话"""
    try:
        d = req_json("https://api.shadiao.pro/pyq")
        text = d["data"]["text"]
        return {"type": "🌹 土味情话", "text": text}
    except Exception as e:
        print(f"[WARN] tiyanhua: {e}")
        return None

def fetch_dog_diary():
    """舔狗日记"""
    try:
        d = req_json("https://api.shadiao.pro/dog")
        text = d["data"]["text"]
        return {"type": "🐕 舔狗日记", "text": text}
    except Exception as e:
        print(f"[WARN] dog_diary: {e}")
        return None

def fetch_pengyu():
    """朋也文案"""
    try:
        d = req_json("https://api.shadiao.pro/wpy")
        text = d["data"]["text"]
        return {"type": "📖 文案", "text": text}
    except Exception as e:
        print(f"[WARN] pengyu: {e}")
        return None

def fetch_netease_hot_comment():
    """网易云热评"""
    try:
        d = req_json("https://api.shadiao.pro/duan")
        text = d["data"]["text"]
        return {"type": "🎵 网易热评", "text": text}
    except Exception as e:
        print(f"[WARN] netease: {e}")
        return None

def fetch_rainbow_fart():
    """彩虹屁"""
    try:
        d = req_json("https://api.shadiao.pro/rainbow")
        text = d["data"]["text"]
        return {"type": "🌈 彩虹屁", "text": text}
    except Exception as e:
        print(f"[WARN] rainbow: {e}")
        return None

def fetch_sleep_early():
    """早点睡文案"""
    try:
        d = req_json("https://api.shadiao.pro/sleep")
        text = d["data"]["text"]
        return {"type": "😴 早点睡", "text": text}
    except Exception as e:
        print(f"[WARN] sleep: {e}")
        return None

# ==================== 备用本地语录 ====================

LOCAL_QUOTES = [
    {"type": "🍵 毒鸡汤", "text": "你努力的样子，像极了在黑暗中挣扎的蝼蚁。"},
    {"type": "🍵 毒鸡汤", "text": "别灰心，人生就是这样起起落落落落落落落落落的。"},
    {"type": "🍵 毒鸡汤", "text": "有时候你不努力一下，就不知道什么叫绝望。"},
    {"type": "🍵 毒鸡汤", "text": "比你优秀的人还在努力，那你努力还有什么用？"},
    {"type": "🍵 毒鸡汤", "text": "不要看别人表面上一帆风顺，实际上他们背地里也是一帆风顺。"},
    {"type": "✨ 一言", "text": "生活不止眼前的苟且，还有读不懂的诗和到不了的远方。"},
    {"type": "✨ 一言", "text": "万物皆有裂痕，那是光照进来的地方。"},
    {"type": "✨ 一言", "text": "你要做一个不动声色的大人了。不准情绪化，不准偷偷想念，不准回头看。"},
    {"type": "🌹 土味情话", "text": "你知道你和星星的区别吗？星星点亮了黑夜，而你点亮了我的心。"},
    {"type": "🌹 土味情话", "text": "我怀疑你的本质是一本书，不然为什么让我越看越想睡？"},
    {"type": "🐕 舔狗日记", "text": "今天她回我消息了，虽然只是一个"嗯"，但我已经心满意足了。"},
    {"type": "🐕 舔狗日记", "text": "下雨了，不知道她有没有带伞，算了，她肯定有人接。"},
    {"type": "🎵 网易热评", "text": "小时候总是骗爸妈自己没钱了，现在骗爸妈自己还有钱。"},
    {"type": "🌈 彩虹屁", "text": "你今天特别讨厌，讨人喜欢和百看不厌。"},
    {"type": "😴 早点睡", "text": "熬夜对身体不好，建议你通宵。"},
]

# ==================== 主逻辑 ====================

# 所有数据源
FETCHERS = [
    fetch_poison_soup,
    fetch_hitokoto,
    fetch_tiyanhua,
    fetch_dog_diary,
    fetch_pengyu,
    fetch_netease_hot_comment,
    fetch_rainbow_fart,
    fetch_sleep_early,
]

def get_random_quote():
    """随机获取一条语录，优先从 API 获取，失败则用本地"""
    # 随机打乱顺序
    fetchers = FETCHERS[:]
    random.shuffle(fetchers)

    for fetcher in fetchers:
        try:
            result = fetcher()
            if result and result.get("text"):
                return result
        except Exception:
            continue

    # API 全部失败，用本地备用
    return random.choice(LOCAL_QUOTES)

def create_issue(title, body, token):
    """创建 Issue"""
    url = "https://api.github.com/repos/Everett406/daily-report/issues"
    data = json.dumps({"title": title, "body": body}).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())

def main():
    now = get_bj_now()
    hour = now.hour

    # 北京时间 23:00-06:00 不发送
    if hour >= 23 or hour < 6:
        print(f"[SKIP] 当前北京时间 {now.strftime('%H:%M')}，在静默时段 23:00-06:00，跳过")
        return

    token = os.environ.get("GH_TOKEN")
    if not token:
        print("[ERROR] Missing GH_TOKEN")
        return

    # 获取随机语录
    quote = get_random_quote()
    print(f"[OK] 获取到: {quote['type']} - {quote['text'][:30]}...")

    # 构建 Issue 内容
    time_str = now.strftime("%H:%M")
    title = f"{quote['type']} | {time_str}"

    body_parts = []
    body_parts.append(f"## {quote['type']}")
    body_parts.append("")
    body_parts.append(f"> {quote['text']}")

    if quote.get("source"):
        body_parts.append(f"")
        body_parts.append(f"{quote['source']}")

    body_parts.append(f"")
    body_parts.append(f"---")
    body_parts.append(f"⏰ {now.strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
    body_parts.append(f"")
    body_parts.append(f"💡 下次推送约 45 分钟后")

    body = "\n".join(body_parts)

    # 创建 Issue
    try:
        result = create_issue(title, body, token)
        print(f"[OK] Issue created: {result.get('html_url')}")
    except Exception as e:
        print(f"[ERROR] Create issue failed: {e}")

if __name__ == "__main__":
    main()

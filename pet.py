#!/usr/bin/env python3
"""
GitHub 仓库养宠物系统
通过昨天的 commit 次数来喂养和升级虚拟宠物
（早报在清晨运行，统计昨日 commit 更合理）
"""

import json
import os
import random
import urllib.request
from datetime import datetime, timedelta, timezone

BJ_TZ = timezone(timedelta(hours=8))

def get_bj_now():
    return datetime.now(BJ_TZ)

def load_pet_data():
    pet_file = "pet.json"
    if os.path.exists(pet_file):
        try:
            with open(pet_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return get_default_pet()

def save_pet_data(pet_data):
    with open("pet.json", "w", encoding="utf-8") as f:
        json.dump(pet_data, f, ensure_ascii=False, indent=2)

def get_default_pet():
    return {
        "name": "",
        "level": 1,
        "exp": 0,
        "hunger": 50,
        "happiness": 50,
        "health": 100,
        "created_at": get_bj_now().isoformat(),
        "last_fed": get_bj_now().isoformat(),
        "total_commits": 0,
        "evolution_stage": "egg",
        "personality": random.choice(["活泼", "温顺", "调皮", "聪慧", "贪吃"]),
        "favorite_food": random.choice(["代码", "Bug", "Commit", "PR", "Star"]),
        "mood": "开心"
    }

def get_evolution_stage(level):
    if level < 5:
        return "egg", "🥚"
    elif level < 15:
        return "baby", "🐣"
    elif level < 30:
        return "child", "🐤"
    elif level < 50:
        return "teen", "🐥"
    else:
        return "adult", "🦅"

def get_pet_appearance(evolution_stage, personality):
    appearances = {
        "egg": "\n      .-.\n     (   )\n      `-'\n        ",
        "baby": "\n       \\\\   /_\n        \\\\/  \\\\\n       /  \\\\__/ \\\\\n      / /  \\\\ \\\\ \\\\\n      \\\\/   \\\\/\n       |     |\n       |     |\n        ",
        "child": "\n         .-.\n        (o o)\n        |O|\n       /| |\\\n      (_/ \\_)\n        ",
        "teen": "\n       \\\\    /_\n        \\\\  /  \\\\\n         \\\\/  .  \\\\\n         |  /\\  |\n        /| /  \\ |\\\n       (_//    \\\\)\n        ",
        "adult": "\n         /\\\n        /  \\\\    /|\n       /    \\\\  / |\n      /  /\\  \\/  |\n     /  /  \\\\     |\n    /__/    \\\\____|\n    |  |    |    |\n    |__|    |____|\n        "
    }
    return appearances.get(evolution_stage, appearances["egg"])

def get_status_bar(value, max_val=100, length=20):
    if max_val <= 0:
        max_val = 1
    filled = int(value / max_val * length)
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}] {value}%"

def calculate_exp_for_level(level):
    return level * 100

def feed_pet(pet_data, commits_yesterday):
    now = get_bj_now()
    try:
        last_fed = datetime.fromisoformat(pet_data["last_fed"])
        if last_fed.tzinfo is None:
            last_fed = last_fed.replace(tzinfo=BJ_TZ)
    except Exception:
        last_fed = now
    days_passed = (now - last_fed).days
    pet_data["hunger"] = max(0, pet_data["hunger"] - days_passed * 20)
    if commits_yesterday > 0:
        hunger_increase = min(commits_yesterday * 5, 100 - pet_data["hunger"])
        pet_data["hunger"] += hunger_increase
        pet_data["exp"] += commits_yesterday * 10
        pet_data["happiness"] = min(100, pet_data["happiness"] + commits_yesterday * 2)
        pet_data["total_commits"] += commits_yesterday
        pet_data["last_fed"] = now.isoformat()
        while pet_data["exp"] >= calculate_exp_for_level(pet_data["level"]):
            pet_data["exp"] -= calculate_exp_for_level(pet_data["level"])
            pet_data["level"] += 1
            pet_data["health"] = min(100, pet_data["health"] + 10)
    else:
        pet_data["happiness"] = max(0, pet_data["happiness"] - 10)
    pet_data["evolution_stage"], _ = get_evolution_stage(pet_data["level"])
    if pet_data["hunger"] < 30:
        pet_data["mood"] = "饥饿"
    elif pet_data["happiness"] < 30:
        pet_data["mood"] = "难过"
    elif pet_data["health"] < 50:
        pet_data["mood"] = "生病"
    else:
        pet_data["mood"] = random.choice(["开心", "兴奋", "满足", "悠闲"])
    return pet_data

def get_commits_yesterday(repo_name, token):
    try:
        yesterday = (get_bj_now() - timedelta(days=1)).date().isoformat()
        url = (f"https://api.github.com/repos/{repo_name}/commits"
               f"?since={yesterday}T00:00:00%2B08:00&until={yesterday}T23:59:59%2B08:00&per_page=100")
        req = urllib.request.Request(url, headers={
            "User-Agent": "daily-report-pet",
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            commits = json.loads(resp.read())
        return len(commits) if isinstance(commits, list) else 0
    except Exception as e:
        print(f"Error fetching commits: {e}")
        return 0

def generate_pet_report(pet_data, commits_yesterday):
    stage, emoji = get_evolution_stage(pet_data["level"])
    appearance = get_pet_appearance(stage, pet_data["personality"])
    titles = {"egg": "蛋蛋", "baby": "宝宝", "child": "幼崽", "teen": "少年", "adult": "成体"}
    title = titles.get(stage, "未知")
    report = f"""# 🐾 我的 GitHub 宠物\n
```
{appearance}
```

## {emoji} {pet_data['name'] or '未命名宠物'} | Lv.{pet_data['level']} {title}

> **性格**: {pet_data['personality']} | **最爱食物**: {pet_data['favorite_food']} | **当前心情**: {pet_data['mood']}

### 📊 状态面板

| 属性 | 状态 |
|:---:|:---|
| 🍖 饱食度 | {get_status_bar(pet_data['hunger'])} |
| 😊 心情值 | {get_status_bar(pet_data['happiness'])} |
| ❤️ 健康值 | {get_status_bar(pet_data['health'])} |
| ⭐ 经验值 | {get_status_bar(pet_data['exp'], calculate_exp_for_level(pet_data['level']))} |

### 📈 成长记录\n
- **总提交次数**: {pet_data['total_commits']}
- **昨日提交**: {commits_yesterday}
- **创建时间**: {pet_data['created_at'][:10]}
- **进化阶段**: {stage}

### 💡 喂养指南\n
1. **提交代码**来喂养宠物，每次提交增加饱食度和经验值
2. 宠物每天会自然消耗饱食度，记得常来提交代码哦
3. 达到一定等级后宠物会**进化**
4. 保持心情和健康值，宠物会成长得更快\n
---
*最后更新: {get_bj_now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    return report

def main():
    token = os.environ.get("GH_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        print("Missing required environment variables")
        return
    pet_data = load_pet_data()
    commits_yesterday = get_commits_yesterday(repo, token)
    print(f"Yesterday's commits: {commits_yesterday}")
    pet_data = feed_pet(pet_data, commits_yesterday)
    save_pet_data(pet_data)
    report = generate_pet_report(pet_data, commits_yesterday)
    with open("PET.md", "w", encoding="utf-8") as f:
        f.write(report)
    print("Pet report generated successfully!")

if __name__ == "__main__":
    main()

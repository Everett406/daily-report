#!/usr/bin/env python3
"""
GitHub 仓库养宠物系统
通过 commit 次数来喂养和升级虚拟宠物
"""

import json
import os
from datetime import datetime, timedelta, timezone
from github import Github
import random

BJ_TZ = timezone(timedelta(hours=8))

def get_bj_now():
    return datetime.now(BJ_TZ)

def load_pet_data():
    """加载宠物数据"""
    pet_file = "pet.json"
    if os.path.exists(pet_file):
        with open(pet_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return get_default_pet()

def save_pet_data(pet_data):
    """保存宠物数据"""
    with open("pet.json", "w", encoding="utf-8") as f:
        json.dump(pet_data, f, ensure_ascii=False, indent=2)

def get_default_pet():
    """获取默认宠物数据"""
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
        "personality": random.choice(["\u6d3b\u6cfc", "\u6e29\u987a", "\u8c03\u76ae", "\u806a\u660e", "\u8d2a\u5403"]),
        "favorite_food": random.choice(["\u4ee3\u7801", "Bug", "Commit", "PR", "Star"]),
        "mood": "\u5f00\u5fc3"
    }

def get_evolution_stage(level):
    if level < 5:
        return "egg", "\ud83e\udd5a"
    elif level < 15:
        return "baby", "\ud83d\udc23"
    elif level < 30:
        return "child", "\ud83d\udc25"
    elif level < 50:
        return "teen", "\ud83d\udc24"
    else:
        return "adult", "\ud83e\udd85"

def get_pet_appearance(evolution_stage, personality):
    appearances = {
        "egg": "\n      .-.\n     (   )\n      `-'\n        ",
        "baby": "\n       \\\\   /_\n        \\\\/  \\\\\n       /  \\\\__/ \\\\\n      / /  \\\\ \\\\ \\\\n      \\\\\\/   \\\\/\n       |     |\n       |     |\n        ",
        "child": "\n         .-.\n        (o o)\n        |O|\n       /| |\\\\n      (_/ \\_)\n        ",
        "teen": "\n       \\\\    /_\n        \\\\  /  \\\\\n         \\\\/  .  \\\\\n         |  /\\\\  |\n        /| /  \\\\ |\\\\n       (_//    \\\\\\)\n        ",
        "adult": "\n         /\\\\n        /  \\\\    /|\n       /    \\\\  / |\n      /  /\\\\  \\\\/  |\n     /  /  \\\\     |\n    /__/    \\\\____|\n    |  |    |    |\n    |__|    |____|\n        "
    }
    return appearances.get(evolution_stage, appearances["egg"])

def get_status_bar(value, max_val=100, length=20):
    filled = int(value / max_val * length)
    bar = "\u2588" * filled + "\u2591" * (length - filled)
    return f"[{bar}] {value}%"

def calculate_exp_for_level(level):
    return level * 100

def feed_pet(pet_data, commits_today):
    now = get_bj_now()
    last_fed = datetime.fromisoformat(pet_data["last_fed"])
    days_passed = (now - last_fed).days
    pet_data["hunger"] = max(0, pet_data["hunger"] - days_passed * 20)
    if commits_today > 0:
        hunger_increase = min(commits_today * 5, 100 - pet_data["hunger"])
        pet_data["hunger"] += hunger_increase
        pet_data["exp"] += commits_today * 10
        pet_data["happiness"] = min(100, pet_data["happiness"] + commits_today * 2)
        pet_data["total_commits"] += commits_today
        pet_data["last_fed"] = now.isoformat()
        while pet_data["exp"] >= calculate_exp_for_level(pet_data["level"]):
            pet_data["exp"] -= calculate_exp_for_level(pet_data["level"])
            pet_data["level"] += 1
            pet_data["health"] = min(100, pet_data["health"] + 10)
    else:
        pet_data["happiness"] = max(0, pet_data["happiness"] - 10)
    pet_data["evolution_stage"], _ = get_evolution_stage(pet_data["level"])
    if pet_data["hunger"] < 30:
        pet_data["mood"] = "\u9965\u997f"
    elif pet_data["happiness"] < 30:
        pet_data["mood"] = "\u96be\u8fc7"
    elif pet_data["health"] < 50:
        pet_data["mood"] = "\u751f\u75c5"
    else:
        pet_data["mood"] = random.choice(["\u5f00\u5fc3", "\u5174\u594b", "\u6ee1\u8db3", "\u60a0\u95f2"])
    return pet_data

def get_commits_today(repo_name, token):
    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
        today = get_bj_now().date()
        tomorrow = today + timedelta(days=1)
        commits = repo.get_commits(since=f"{today}T00:00:00Z", until=f"{tomorrow}T00:00:00Z")
        return commits.totalCount
    except Exception as e:
        print(f"Error fetching commits: {e}")
        return 0

def generate_pet_report(pet_data, commits_today):
    stage, emoji = get_evolution_stage(pet_data["level"])
    appearance = get_pet_appearance(stage, pet_data["personality"])
    titles = {"egg": "\u86cb\u86cb", "baby": "\u5b9d\u5b9d", "child": "\u5e7c\u5d3d", "teen": "\u5c11\u5e74", "adult": "\u6210\u4f53"}
    title = titles.get(stage, "\u672a\u77e5")
    report = f"""# \ud83d\udc3e \u6211\u7684 GitHub \u5ba0\u7269\n
```
{appearance}
```

## {emoji} {pet_data['name'] or '\u672a\u547d\u540d\u5ba0\u7269'} | Lv.{pet_data['level']} {title}

> **\u6027\u683c**: {pet_data['personality']} | **\u6700\u7231\u98df\u7269**: {pet_data['favorite_food']} | **\u5f53\u524d\u5fc3\u60c5**: {pet_data['mood']}

### \ud83d\udcca \u72b6\u6001\u9762\u677f

| \u5c5e\u6027 | \u72b6\u6001 |
|:---:|:---|
| \ud83c\udf56 \u9971\u98df\u5ea6 | {get_status_bar(pet_data['hunger'])} |
| \ud83d\ude0a \u5fc3\u60c5\u503c | {get_status_bar(pet_data['happiness'])} |
| \u2764\ufe0f \u5065\u5eb7\u503c | {get_status_bar(pet_data['health'])} |
| \u2b50 \u7ecf\u9a8c\u503c | {get_status_bar(pet_data['exp'], calculate_exp_for_level(pet_data['level']))} |

### \ud83d\udcc8 \u6210\u957f\u8bb0\u5f55\n
- **\u603b\u63d0\u4ea4\u6b21\u6570**: {pet_data['total_commits']}
- **\u4eca\u65e5\u63d0\u4ea4**: {commits_today}
- **\u521b\u5efa\u65f6\u95f4**: {pet_data['created_at'][:10]}
- **\u8fdb\u5316\u9636\u6bb5**: {stage}

### \ud83d\udca1 \u5582\u517b\u6307\u5357\n
1. **\u63d0\u4ea4\u4ee3\u7801**\u6765\u5582\u517b\u5ba0\u7269\uff0c\u6bcf\u6b21\u63d0\u4ea4\u589e\u52a0\u9971\u98df\u5ea6\u548c\u7ecf\u9a8c\u503c
2. \u5ba0\u7269\u6bcf\u5929\u4f1a\u81ea\u7136\u6d88\u8017\u9971\u98df\u5ea6\uff0c\u8bb0\u5f97\u5e38\u6765\u63d0\u4ea4\u4ee3\u7801\u54e6
3. \u8fbe\u5230\u4e00\u5b9a\u7b49\u7ea7\u540e\u5ba0\u7269\u4f1a**\u8fdb\u5316**
4. \u4fdd\u6301\u5fc3\u60c5\u548c\u5065\u5eb7\u503c\uff0c\u5ba0\u7269\u4f1a\u6210\u957f\u5f97\u66f4\u5feb\n
---
*\u6700\u540e\u66f4\u65b0: {get_bj_now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    return report

def main():
    token = os.environ.get("GH_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        print("Missing required environment variables")
        return
    pet_data = load_pet_data()
    commits_today = get_commits_today(repo, token)
    print(f"Today's commits: {commits_today}")
    pet_data = feed_pet(pet_data, commits_today)
    save_pet_data(pet_data)
    report = generate_pet_report(pet_data, commits_today)
    with open("PET.md", "w", encoding="utf-8") as f:
        f.write(report)
    print("Pet report generated successfully!")

if __name__ == "__main__":
    main()

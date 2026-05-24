#!/usr/bin/env python3
"""
GitHub 仓库养宠物系统
通过 commit 次数来喂养和升级虚拟宠物
"""

import json
import os
from datetime import datetime, timedelta
from github import Github
import random

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
        "hunger": 50,  # 饥饿度 0-100，越高越饱
        "happiness": 50,  # 心情 0-100
        "health": 100,  # 健康 0-100
        "created_at": datetime.now().isoformat(),
        "last_fed": datetime.now().isoformat(),
        "total_commits": 0,
        "evolution_stage": "egg",  # egg -> baby -> child -> teen -> adult
        "personality": random.choice(["活泼", "温顺", "调皮", "聪明", "贪吃"]),
        "favorite_food": random.choice(["代码", "Bug", "Commit", "PR", "Star"]),
        "mood": "开心"
    }

def get_evolution_stage(level):
    """根据等级获取进化阶段"""
    if level < 5:
        return "egg", "🥚"
    elif level < 15:
        return "baby", "🐣"
    elif level < 30:
        return "child", "🐥"
    elif level < 50:
        return "teen", "🐤"
    else:
        return "adult", "🦅"

def get_pet_appearance(evolution_stage, personality):
    """获取宠物外观 ASCII 艺术"""
    appearances = {
        "egg": """
      .-.
     (   )
      `-'
        """,
        "baby": """
       \\   /_
        \\_/  \\
       /  \\__/ \\
      / /  \\ \\ \\
      \\\\/   \\/
       |     |
       |     |
        """,
        "child": """
         .-.
        (o o)
        |O|
       /| |\\
      (_/ \_)
        """,
        "teen": """
       \\    /_
        \\  /  \\
         \\/  .  \\
         |  /\\  |
        /| /  \\ |\\
       (_//    \\\_)
        """,
        "adult": """
         /\
        /  \\    /|
       /    \\  / |
      /  /\\  \\/  |
     /  /  \\     |
    /__/    \\____|
    |  |    |    |
    |__|    |____|
        """
    }
    return appearances.get(evolution_stage, appearances["egg"])

def get_status_bar(value, max_val=100, length=20):
    """生成状态条"""
    filled = int(value / max_val * length)
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}] {value}%"

def calculate_exp_for_level(level):
    """计算升级所需经验"""
    return level * 100

def feed_pet(pet_data, commits_today):
    """喂养宠物"""
    now = datetime.now()
    last_fed = datetime.fromisoformat(pet_data["last_fed"])
    
    # 计算饥饿度下降（每过一天下降 20）
    days_passed = (now - last_fed).days
    pet_data["hunger"] = max(0, pet_data["hunger"] - days_passed * 20)
    
    # 根据 commit 数量喂养
    if commits_today > 0:
        # 每个 commit 增加 5 点饱食度
        hunger_increase = min(commits_today * 5, 100 - pet_data["hunger"])
        pet_data["hunger"] += hunger_increase
        
        # 增加经验值
        exp_gain = commits_today * 10
        pet_data["exp"] += exp_gain
        
        # 增加心情
        pet_data["happiness"] = min(100, pet_data["happiness"] + commits_today * 2)
        
        # 更新总 commit 数
        pet_data["total_commits"] += commits_today
        
        pet_data["last_fed"] = now.isoformat()
        
        # 检查升级
        while pet_data["exp"] >= calculate_exp_for_level(pet_data["level"]):
            pet_data["exp"] -= calculate_exp_for_level(pet_data["level"])
            pet_data["level"] += 1
            pet_data["health"] = min(100, pet_data["health"] + 10)
    else:
        # 没有 commit，心情下降
        pet_data["happiness"] = max(0, pet_data["happiness"] - 10)
    
    # 更新进化阶段
    pet_data["evolution_stage"], _ = get_evolution_stage(pet_data["level"])
    
    # 更新心情状态
    if pet_data["hunger"] < 30:
        pet_data["mood"] = "饥饿"
    elif pet_data["happiness"] < 30:
        pet_data["mood"] = "难过"
    elif pet_data["health"] < 50:
        pet_data["mood"] = "生病"
    else:
        pet_data["mood"] = random.choice(["开心", "兴奋", "满足", "悠闲"])
    
    return pet_data

def get_commits_today(repo_name, token):
    """获取今天的 commit 数量"""
    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
        
        # 获取今天的日期范围
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        
        # 获取 commits
        commits = repo.get_commits(since=f"{today}T00:00:00Z", until=f"{tomorrow}T00:00:00Z")
        return commits.totalCount
    except Exception as e:
        print(f"Error fetching commits: {e}")
        return 0

def generate_pet_report(pet_data, commits_today):
    """生成宠物状态报告"""
    stage, emoji = get_evolution_stage(pet_data["level"])
    appearance = get_pet_appearance(stage, pet_data["personality"])
    
    # 获取等级称号
    titles = {
        "egg": "蛋蛋",
        "baby": "宝宝",
        "child": "幼崽",
        "teen": "少年",
        "adult": "成体"
    }
    title = titles.get(stage, "未知")
    
    report = f"""# 🐾 我的 GitHub 宠物

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

### 📈 成长记录

- **总提交次数**: {pet_data['total_commits']}
- **今日提交**: {commits_today}
- **创建时间**: {pet_data['created_at'][:10]}
- **进化阶段**: {stage}

### 💡 喂养指南

1. **提交代码**来喂养宠物，每次提交增加饱食度和经验值
2. 宠物每天会自然消耗饱食度，记得常来提交代码哦
3. 达到一定等级后宠物会**进化**
4. 保持心情和健康值，宠物会成长得更快

---
*最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    return report

def main():
    # 获取环境变量
    token = os.environ.get("GH_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    
    if not token or not repo:
        print("Missing required environment variables")
        return
    
    # 加载宠物数据
    pet_data = load_pet_data()
    
    # 获取今日 commit 数量
    commits_today = get_commits_today(repo, token)
    print(f"Today's commits: {commits_today}")
    
    # 喂养宠物
    pet_data = feed_pet(pet_data, commits_today)
    
    # 保存宠物数据
    save_pet_data(pet_data)
    
    # 生成报告
    report = generate_pet_report(pet_data, commits_today)
    
    # 保存到文件
    with open("PET.md", "w", encoding="utf-8") as f:
        f.write(report)
    
    print("Pet report generated successfully!")

if __name__ == "__main__":
    main()

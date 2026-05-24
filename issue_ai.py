import json
import os
import sys
import urllib.request


def req_json(url, headers=None, data=None, method="GET", timeout=90):
    h = {"User-Agent": "Mozilla/5.0"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h, data=data, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def fetch_comments(repo, issue_number, token):
    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception:
        return []


def call_llm(messages, api_key, base_url, model, max_retries=3):
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 2000
    }).encode()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    last_error = None
    for attempt in range(max_retries):
        try:
            result = req_json(
                f"{base_url}/chat/completions",
                headers=headers,
                data=payload,
                method="POST",
                timeout=90
            )
            return result["choices"][0]["message"]["content"].strip()
        except Exception as e:
            last_error = e
            print(f"[WARN] LLM attempt {attempt + 1}/{max_retries} failed: {e}")

    return f"AI 回复生成失败（已重试{max_retries}次）: {last_error}"


def post_comment(repo, issue_number, body, token):
    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments"
    data = json.dumps({"body": body}).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def main():
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        print("[SKIP] No GITHUB_EVENT_PATH")
        return

    with open(event_path, "r", encoding="utf-8") as f:
        event = json.load(f)

    issue = event.get("issue", {})
    comment = event.get("comment")
    issue_number = issue.get("number")
    issue_title = issue.get("title", "")
    issue_body = issue.get("body") or ""

    if not issue_number:
        print("[SKIP] No issue number")
        return

    # 如果是评论事件，且评论者是 bot 自己，直接退出防止循环
    if comment and comment.get("user", {}).get("login") == "github-actions[bot]":
        print("[SKIP] Bot comment, ignore to prevent loop")
        return

    # 读取配置
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        cfg = {}

    llm_cfg = cfg.get("llm", {})
    api_key = os.environ.get("LLM_API_KEY")

    if not api_key or not llm_cfg.get("enabled"):
        print("[SKIP] LLM not configured")
        return

    repo = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GH_TOKEN")

    if not repo or not token:
        print("[SKIP] Missing repo or token")
        return

    # 获取该 Issue 的所有评论历史
    comments = fetch_comments(repo, issue_number, token)

    # 构建多轮对话 messages
    system_prompt = (
        "你是一个聪明、友善的AI助手。用户在 GitHub Issue 里和你进行多轮对话。"
        "请基于完整的上下文认真回答。如果用户的问题不清楚，可以礼貌地请用户补充信息。"
        "回答请用中文，语气自然像朋友聊天。"
    )

    messages = [{"role": "system", "content": system_prompt}]

    # Issue 正文作为第一轮用户输入
    init_content = f"【Issue标题】{issue_title}\n\n【Issue内容】\n{issue_body}"
    if len(init_content) > 3000:
        init_content = init_content[:3000] + "\n\n...（内容过长，已截断）"
    messages.append({"role": "user", "content": init_content})

    # 之后的评论历史
    for c in comments:
        author = c.get("user", {}).get("login", "")
        text = c.get("body", "")
        if author == "github-actions[bot]":
            messages.append({"role": "assistant", "content": text})
        else:
            messages.append({"role": "user", "content": text})

    # 调用 LLM
    reply = call_llm(
        messages,
        api_key,
        llm_cfg.get("base_url", "https://yunwu.ai/v1"),
        llm_cfg.get("model", "gemini-3-pro-preview")
    )

    # 发布评论
    try:
        post_comment(repo, issue_number, reply, token)
        print(f"[OK] Comment posted to issue #{issue_number}")
    except Exception as e:
        print(f"[ERROR] Post comment failed: {e}")


if __name__ == "__main__":
    main()

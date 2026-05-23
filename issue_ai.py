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


def call_llm(prompt, api_key, base_url, model, max_retries=3):
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
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
    # 读取 GitHub webhook event
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        print("[SKIP] No GITHUB_EVENT_PATH")
        return

    with open(event_path, "r", encoding="utf-8") as f:
        event = json.load(f)

    issue = event.get("issue", {})
    issue_number = issue.get("number")
    issue_title = issue.get("title", "")
    issue_body = issue.get("body") or ""

    if not issue_number:
        print("[SKIP] No issue number")
        return

    # 读取 LLM 配置
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

    # 截断过长的 Issue body
    if len(issue_body) > 3000:
        issue_body = issue_body[:3000] + "\n\n...（内容过长，已截断）"

    # 构建 prompt
    prompt = f"""你是一个聪明、友善的AI助手。请认真回答用户的问题。

用户 Issue 标题：{issue_title}
用户 Issue 内容：
{issue_body}

请给出清晰、有帮助的回答。如果问题不清楚，可以礼貌地请用户补充信息。回答请用中文。"""

    # 调用 LLM
    reply = call_llm(
        prompt,
        api_key,
        llm_cfg.get("base_url", "https://yunwu.ai/v1"),
        llm_cfg.get("model", "gemini-3-pro-preview")
    )

    # 发布评论
    repo = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GH_TOKEN")

    if not repo or not token:
        print("[SKIP] Missing repo or token")
        return

    try:
        post_comment(repo, issue_number, reply, token)
        print(f"[OK] Comment posted to issue #{issue_number}")
    except Exception as e:
        print(f"[ERROR] Post comment failed: {e}")


if __name__ == "__main__":
    main()

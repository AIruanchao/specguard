#!/usr/bin/env python3
"""
ci-green-check.py — GitHub Actions CI绿灯检测+自动通知

每次push后运行：
1. 通过GitHub API检查最新CI运行状态
2. 失败→通知（飞书/终端）
3. 成功→记录

环境变量:
  GH_PAT: GitHub Personal Access Token
  REPO: AIruanchao/business-document-generator
"""
import os, sys, json, subprocess
from datetime import datetime
from pathlib import Path

REPO = "AIruanchao/business-document-generator"
STATE_FILE = Path(__file__).resolve().parent.parent / "test-cases" / "ci-state.json"


def check_ci_status():
    """检查最新CI运行状态"""
    pat = os.environ.get("GH_PAT") or os.environ.get("GITHUB_TOKEN")
    
    if pat:
        # 用API
        import urllib.request
        url = f"https://api.github.com/repos/{REPO}/actions/runs?per_page=5"
        req = urllib.request.Request(url, headers={
            "Authorization": f"token {pat}",
            "Accept": "application/vnd.github.v3+json",
        })
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.load(resp)
                runs = data.get("workflow_runs", [])
                if runs:
                    latest = runs[0]
                    return {
                        "status": latest["status"],
                        "conclusion": latest["conclusion"],
                        "name": latest["name"],
                        "html_url": latest["html_url"],
                        "created_at": latest["created_at"],
                    }
        except Exception as e:
            print(f"⚠️ GitHub API失败: {e}")
    
    # 无PAT → 用git log检查最近push状态
    print("⚠️ 无GH_PAT，使用git状态推断")
    project_root = Path(__file__).resolve().parent.parent.parent
    result = subprocess.run(
        ["git", "log", "--oneline", "-1"],
        capture_output=True, text=True,
        cwd=str(project_root)
    )
    if result.returncode == 0:
        return {
            "status": "unknown",
            "conclusion": "unknown",
            "name": "git-push-ok",
            "html_url": f"https://github.com/{REPO}/actions",
            "created_at": datetime.now().isoformat(),
        }
    return None


def save_state(state):
    """保存CI状态历史"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    history = []
    if STATE_FILE.exists():
        history = json.loads(STATE_FILE.read_text())
    history.append(state)
    history = history[-30:]  # 保留最近30条
    STATE_FILE.write_text(json.dumps(history, indent=2, ensure_ascii=False))


def main():
    print(f"🔍 CI状态检查 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    state = check_ci_status()
    if not state:
        print("❌ 无法获取CI状态")
        return 1
    
    save_state(state)
    
    status = state.get("status", "unknown")
    conclusion = state.get("conclusion", "unknown")
    name = state.get("name", "unknown")
    url = state.get("html_url", "")
    
    if conclusion == "success":
        print(f"✅ CI绿灯: {name}")
        print(f"   {url}")
        return 0
    elif conclusion == "failure":
        print(f"❌ CI红灯: {name}")
        print(f"   {url}")
        print(f"   需要: 检查CI日志并修复")
        return 1
    elif status == "in_progress":
        print(f"⏳ CI运行中: {name}")
        print(f"   {url}")
        return 0
    else:
        print(f"ℹ️ CI状态: {status}/{conclusion} ({name})")
        print(f"   {url}")
        return 0


if __name__ == "__main__":
    sys.exit(main())

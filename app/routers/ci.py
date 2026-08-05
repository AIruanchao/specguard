"""CI状态检查路由 — 包装ci_engine.py核心逻辑"""
import os, json, subprocess
from datetime import datetime
from fastapi import APIRouter
from app.models import CIStatusResponse
from app.config import DATA_DIR

router = APIRouter()


@router.get("/status", response_model=CIStatusResponse)
async def get_ci_status(repo: str = "AIruanchao/business-document-generator"):
    """获取GitHub Actions最新运行状态"""
    pat = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_PAT")

    if pat:
        import urllib.request
        url = f"https://api.github.com/repos/{repo}/actions/runs?per_page=1"
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
                    return CIStatusResponse(
                        repo=repo,
                        latest_run={
                            "status": latest["status"],
                            "conclusion": latest["conclusion"],
                            "name": latest["name"],
                            "url": latest["html_url"],
                            "created_at": latest["created_at"],
                        },
                    )
        except Exception as e:
            return CIStatusResponse(repo=repo, message=f"API调用失败: {e}")

    return CIStatusResponse(
        repo=repo,
        message="无GITHUB_TOKEN，无法获取CI状态",
    )

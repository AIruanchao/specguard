"""Spec management routes reading project sdd directories."""
import re
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from app.config import resolve_project_path

router = APIRouter()

try:
    import yaml
except ImportError:
    yaml = None


class SpecItem(BaseModel):
    spec_id: str = ""
    title: str = ""
    module: str = ""
    level: str = ""
    status: str = ""
    version: str = ""
    path: str = ""
    owner: str = ""


class SpecListResponse(BaseModel):
    project: str
    specs: list[SpecItem] = []


def _parse_frontmatter(content: str) -> dict:
    """解析Spec文件的YAML frontmatter"""
    if not yaml:
        return {}
    m = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not m:
        return {}
    try:
        return yaml.safe_load(m.group(1)) or {}
    except Exception:
        return {}


@router.get("/list", response_model=SpecListResponse)
async def list_specs(project: str = "business-document-generator", project_path: str = ""):
    """列出项目的所有Spec文件"""
    root_path = resolve_project_path(project, project_path)
    sdd_dir = root_path / "sdd" / "domain-spec"

    specs = []
    if sdd_dir.exists():
        for spec_file in sorted(sdd_dir.rglob("*.md")):
            try:
                content = spec_file.read_text(encoding="utf-8")
                fm = _parse_frontmatter(content)
                specs.append(SpecItem(
                    spec_id=fm.get("spec_id", ""),
                    title=fm.get("title", ""),
                    module=fm.get("module", ""),
                    level=fm.get("level", ""),
                    status=fm.get("status", ""),
                    version=str(fm.get("version", "")),
                    path=str(spec_file.relative_to(root_path)),
                    owner=fm.get("owner", ""),
                ))
            except Exception:
                continue

    return SpecListResponse(project=project, specs=specs)

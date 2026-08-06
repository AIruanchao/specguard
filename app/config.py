"""SpecGuard configuration management."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Service configuration
PORT = int(os.environ.get("SPECGUARD_PORT", "8700"))
HOST = os.environ.get("SPECGUARD_HOST", "0.0.0.0")

# Managed projects. MANAGED_PROJECTS accepts either:
# - name=/path/to/project,name2=/path/to/project2
# - /path/to/project,/path/to/project2 (name defaults to directory name)
def _parse_managed_projects(raw_value: str) -> dict[str, str]:
    projects = {}
    for item in raw_value.split(","):
        item = item.strip()
        if not item:
            continue
        if "=" in item:
            name, path = item.split("=", 1)
            name = name.strip()
            path = path.strip()
        else:
            path = item
            name = Path(path).name
        if name and path:
            projects[name] = path
    return projects


MANAGED_PROJECTS = _parse_managed_projects(os.environ.get("MANAGED_PROJECTS", ""))


def resolve_project_path(project: str = "", project_path: str = "") -> Path:
    """Resolve a project name or explicit path to a project root."""
    if project_path:
        return Path(project_path)
    if project and project in MANAGED_PROJECTS:
        return Path(MANAGED_PROJECTS[project])
    if project:
        candidate = Path(project)
        if candidate.is_absolute() or "/" in project:
            return candidate
        return Path("/Users/maccc/projects") / project
    return Path("/Users/maccc/projects/business-document-generator")

# GitHub integration
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# Data directory
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

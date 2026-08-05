"""SpecGuard 配置管理"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# 服务配置
PORT = int(os.environ.get("SPECGUARD_PORT", "8700"))
HOST = os.environ.get("SPECGUARD_HOST", "0.0.0.0")

# 管理的项目
MANAGED_PROJECTS = [
    p.strip() for p in os.environ.get(
        "MANAGED_PROJECTS", ""
    ).split(",") if p.strip()
]

# GitHub集成
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# 数据目录
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

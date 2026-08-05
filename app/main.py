"""SpecGuard — 企业级SDD治理平台 V0.2"""
import logging
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.routers import gate, coverage, ci, health, specs, web

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SpecGuard",
    description="企业级SDD治理平台 — SDD领域的SonarQube",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件
static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# API路由
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(gate.router, prefix="/api/v1/gate", tags=["gate"])
app.include_router(coverage.router, prefix="/api/v1/coverage", tags=["coverage"])
app.include_router(ci.router, prefix="/api/v1/ci", tags=["ci"])
app.include_router(specs.router, prefix="/api/v1/specs", tags=["specs"])

# Web UI路由
app.include_router(web.router, tags=["web"])


@app.on_event("startup")
async def startup():
    logger.info("🚀 SpecGuard v0.2 启动完成 — Web UI可用")

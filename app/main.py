"""SpecGuard — 企业级SDD治理平台 V0.1"""
import logging
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import gate, coverage, ci, health

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SpecGuard",
    description="企业级SDD治理平台 — SDD领域的SonarQube",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(gate.router, prefix="/api/v1/gate", tags=["gate"])
app.include_router(coverage.router, prefix="/api/v1/coverage", tags=["coverage"])
app.include_router(ci.router, prefix="/api/v1/ci", tags=["ci"])


@app.on_event("startup")
async def startup():
    logger.info("🚀 SpecGuard v0.1 启动完成")

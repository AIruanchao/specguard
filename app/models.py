"""SpecGuard Pydantic models."""
from pydantic import BaseModel, Field
from typing import Optional


class HealthResponse(BaseModel):
    status: str = "healthy"
    service: str = "specguard"
    version: str = "0.1.0"


class Project(BaseModel):
    name: str
    path: str
    language: str = Field(default="python", description="Primary project language")
    test_runner: str = Field(default="pytest", description="Coverage runner: pytest or vitest")


class GateCheckRequest(BaseModel):
    project: str = Field(default="", description="托管项目名称")
    project_path: str = Field(default="", description="项目根目录路径")
    changed_files: list[str] = Field(default_factory=list, description="变更文件列表")
    pr_body: str = Field(default="", description="PR描述")
    pr_labels: list[str] = Field(default_factory=list, description="PR标签")


class GateCheckResponse(BaseModel):
    passed: bool
    affected_modules: list[str] = Field(default_factory=list)
    spec_refs: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CoverageModule(BaseModel):
    module: str
    coverage: float
    level: str
    target: int = 80


class CoverageResponse(BaseModel):
    project: str
    total_coverage: float
    modules: list[CoverageModule] = Field(default_factory=list)


class CoverageAnalyzeRequest(BaseModel):
    project: str = Field(default="", description="托管项目名称")
    project_path: str = ""


class TSReverseRequest(BaseModel):
    project_path: str = Field(description="TypeScript project root path")
    files: list[str] = Field(default_factory=list, description="TS/TSX files to analyze")


class CoverageAnalyzeResponse(BaseModel):
    gaps_found: int
    task_card_path: Optional[str] = None
    message: str


class CIStatusResponse(BaseModel):
    repo: str
    latest_run: Optional[dict] = None
    message: str = ""

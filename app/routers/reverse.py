"""Reverse engineering API routes."""
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.reverse_engine import ReverseEngine


router = APIRouter()
_JOBS: dict[str, dict] = {}


class ReverseAnalyzeRequest(BaseModel):
    project_path: str = Field(description="Project root path to analyze")
    module: str = Field(default="", description="Module path or name to analyze")


class ReverseAnalyzeResponse(BaseModel):
    job_id: str
    specs_generated: int
    findings: dict


class ReverseResultResponse(BaseModel):
    status: str
    specs: list[str] = Field(default_factory=list)
    findings: dict = Field(default_factory=dict)


@router.post("/analyze", response_model=ReverseAnalyzeResponse)
async def analyze_reverse(req: ReverseAnalyzeRequest):
    """Analyze Python code and generate draft reverse specs."""
    project_path = Path(req.project_path)
    if not project_path.exists():
        raise HTTPException(status_code=404, detail=f"Project path not found: {req.project_path}")

    engine = ReverseEngine(req.project_path)
    analyses = engine.analyze_module(req.module)
    specs = [engine.generate_spec(analysis) for analysis in analyses]
    findings = {
        "files_analyzed": len(analyses),
        "functions": sum(len(analysis.get("functions", [])) for analysis in analyses),
        "routes": sum(len(analysis.get("routes", [])) for analysis in analyses),
        "models": sum(len(analysis.get("models", [])) for analysis in analyses),
        "imports": sum(len(analysis.get("imports", [])) for analysis in analyses),
        "analyses": analyses,
    }
    job_id = str(uuid4())
    _JOBS[job_id] = {"status": "completed", "specs": specs, "findings": findings}

    return ReverseAnalyzeResponse(
        job_id=job_id,
        specs_generated=len(specs),
        findings=findings,
    )


@router.get("/result/{job_id}", response_model=ReverseResultResponse)
async def get_reverse_result(job_id: str):
    """Return a completed reverse analysis result."""
    job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Reverse job not found: {job_id}")
    return ReverseResultResponse(**job)

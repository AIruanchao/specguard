"""覆盖率引擎路由 — 包装coverage_engine.py核心逻辑"""
import subprocess, json, re
from pathlib import Path
from fastapi import APIRouter
from app.models import (
    CoverageResponse, CoverageModule,
    CoverageAnalyzeRequest, CoverageAnalyzeResponse,
)

router = APIRouter()

# A级模块配置
A_LEVEL_MODULES = {
    "app/services/smart_seal.py": ("seal-engine", "A"),
    "app/services/seal_position.py": ("seal-engine", "A"),
    "app/services/smart_stamp.py": ("seal-engine", "A"),
    "app/services/renderer.py": ("pdf-renderer", "A"),
    "app/services/postprocess.py": ("pdf-renderer", "A"),
    "app/auth.py": ("auth", "A"),
    "app/routes/auth_routes.py": ("auth", "A"),
    "app/routes/stamp_upload.py": ("file-io", "A"),
    "app/services/agent.py": ("llm-agent", "A"),
    "app/services/agent_tools.py": ("llm-agent", "A"),
    "app/services/model_router.py": ("llm-agent", "A"),
    "app/services/extractor.py": ("llm-agent", "A"),
    "app/models.py": ("models", "A"),
    "app/schema.py": ("models", "A"),
    "app/routes/contracts/actions.py": ("document-state-machine", "A"),
    "app/routes/contracts/common.py": ("document-state-machine", "A"),
}


@router.get("/{project_name}", response_model=CoverageResponse)
async def get_coverage(project_name: str):
    """获取项目覆盖率"""
    # 从项目路径推断
    project_path = f"/Users/maccc/projects/{project_name}"
    if not Path(project_path).exists():
        return CoverageResponse(
            project=project_name,
            total_coverage=0,
            modules=[],
        )

    # 运行覆盖率（如果.venv存在）
    venv_python = Path(project_path) / ".venv" / "bin" / "python"
    if not venv_python.exists():
        venv_python = Path("python3")

    result = subprocess.run(
        [str(venv_python), "-m", "pytest", "tests/", "-q", "--tb=no",
         "--cov=app", "--cov-report=json:/tmp/cov_report.json", "--cov-branch"],
        capture_output=True, text=True, timeout=120,
        cwd=project_path
    )

    report_path = Path("/tmp/cov_report.json")
    if not report_path.exists():
        return CoverageResponse(
            project=project_name,
            total_coverage=0,
            modules=[],
        )

    with open(report_path) as f:
        cov_data = json.load(f)

    total_cov = cov_data.get("totals", {}).get("percent_covered", 0)
    modules = []

    for filepath, (module_name, level) in A_LEVEL_MODULES.items():
        file_data = cov_data.get("files", {}).get(filepath, {})
        if file_data:
            summary = file_data.get("summary", {})
            line_rate = summary.get("percent_covered", 0)
            modules.append(CoverageModule(
                module=module_name,
                coverage=round(line_rate, 1),
                level=level,
            ))

    return CoverageResponse(
        project=project_name,
        total_coverage=round(total_cov, 1),
        modules=modules,
    )


@router.post("/analyze", response_model=CoverageAnalyzeResponse)
async def analyze_coverage(req: CoverageAnalyzeRequest):
    """分析覆盖率缺口并生成任务卡"""
    project_path = Path(req.project_path)
    if not project_path.exists():
        return CoverageAnalyzeResponse(
            gaps_found=0,
            message=f"项目路径不存在: {req.project_path}",
        )

    # 运行覆盖率分析脚本
    venv_python = project_path / ".venv" / "bin" / "python"
    script = project_path / "sdd" / "scripts" / "coverage-auto-improve.py"

    if not venv_python.exists():
        venv_python = Path("python3")

    if script.exists():
        result = subprocess.run(
            [str(venv_python), str(script)],
            capture_output=True, text=True, timeout=120,
            cwd=str(project_path)
        )
        # 从输出提取TASK_CARD路径
        task_line = [l for l in result.stdout.split('\n') if l.startswith('TASK_CARD=')]
        task_path = task_line[0].split('=', 1)[1] if task_line else None

        gaps = result.stdout.count('⚠️')
        return CoverageAnalyzeResponse(
            gaps_found=gaps,
            task_card_path=task_path,
            message=f"分析完成，发现{gaps}个缺口"
        )

    return CoverageAnalyzeResponse(
        gaps_found=0,
        message="coverage-auto-improve.py不存在",
    )

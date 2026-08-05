"""Web UI路由 — serve HTML页面"""
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()

# 模板目录
TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html", {})


@router.get("/coverage", response_class=HTMLResponse)
async def coverage_page(request: Request):
    return templates.TemplateResponse(request, "coverage.html", {})


@router.get("/specs", response_class=HTMLResponse)
async def specs_page(request: Request):
    return templates.TemplateResponse(request, "specs.html", {})


@router.get("/gate", response_class=HTMLResponse)
async def gate_page(request: Request):
    return templates.TemplateResponse(request, "gate.html", {})

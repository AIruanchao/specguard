# 任务卡: SpecGuard V1.5 多项目+TS逆向引擎

## 背景

SpecGuard是企业级SDD治理平台(FastAPI)。V1.0已完成(Python项目支持)。
V1.5目标: 多项目管理 + TypeScript逆向引擎(正则方案,Spike验证83%准确率)。

## 项目位置

`/Users/maccc/projects/specguard`

## 需要开发的文件

### 1. 多项目支持
- `app/config.py` — 改MANAGED_PROJECTS为多项目dict
- `app/models.py` — 加Project模型
- `app/routers/gate.py` — 路径白名单参数化(每项目独立module_paths.json)
- `app/routers/coverage.py` — 按项目选择pytest/vitest
- `app/routers/specs.py` — 按项目路径读Spec

### 2. TypeScript逆向引擎
- `app/services/ts_reverse_engine.py` — 新文件
- `app/routers/reverse.py` — 加TS分析端点

### ts_reverse_engine.py 设计

```python
import re
from pathlib import Path
from typing import Dict, List, Any

class TypeScriptReverseEngine:
    """TypeScript/TSX逆向分析引擎（正则方案，Spike验证83%准确率）"""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)

    def analyze_file(self, filepath: str, content: str = None) -> Dict[str, Any]:
        """分析单个TS/TSX文件"""
        if content is None:
            content = (self.project_path / filepath).read_text()
        
        findings = {}

        # 1. Server/Client Component检测
        findings["is_client"] = '"use client"' in content[:200] or "'use client'" in content[:200]
        findings["is_server_action"] = '"use server"' in content[:200]

        # 2. API Route HTTP方法提取
        findings["http_methods"] = re.findall(
            r'export\s+async\s+function\s+(GET|POST|PUT|DELETE|PATCH)\s*\(', content)

        # 3. Prisma调用提取
        findings["prisma_calls"] = re.findall(r'prisma\.(\w+)\.(\w+)\s*\(', content)
        findings["prisma_models"] = list(set(m for m, _ in findings["prisma_calls"]))

        # 4. import依赖图
        findings["imports"] = re.findall(
            r'import\s+(?:type\s+)?(?:\{[^}]+\}|\w+|.+?from)\s+["\']([^"\']+)', content)
        findings["type_imports"] = re.findall(
            r'import\s+type\s+\{[^}]+\}\s+from\s+["\']([^"\']+)', content)

        # 5. 文件名→路由角色
        filename = Path(filepath).name
        if filename == "page.tsx":
            findings["router_role"] = "page"
        elif filename == "layout.tsx":
            findings["router_role"] = "layout"
        elif filename == "route.ts":
            findings["router_role"] = "api-route"
        elif filename == "error.tsx":
            findings["router_role"] = "error-boundary"
        elif filename == "loading.tsx":
            findings["router_role"] = "loading"
        elif filename == "middleware.ts":
            findings["router_role"] = "middleware"
        elif filename == "actions.ts":
            findings["router_role"] = "server-actions"
        else:
            findings["router_role"] = "component"

        # 6. 组件名提取
        default_export = re.search(r'export\s+default\s+function\s+(\w+)', content)
        findings["component_name"] = default_export.group(1) if default_export else filename

        # 7. React hooks（标注低准确率）
        all_hooks = re.findall(r'\b(use[A-Z]\w+)\b', content)
        standard_hooks = {"useState", "useEffect", "useContext", "useReducer",
                         "useCallback", "useMemo", "useRef", "useLayoutEffect"}
        findings["standard_hooks"] = [h for h in all_hooks if h in standard_hooks]
        findings["custom_hooks"] = [h for h in all_hooks if h not in standard_hooks]

        # 8. 三段式分类
        findings["classification"] = self._classify(findings)
        return findings

    def analyze_module(self, module_pattern: str) -> List[Dict]:
        """分析整个模块（按glob pattern）"""
        results = []
        for filepath in self.project_path.glob(module_pattern):
            if filepath.suffix in ('.ts', '.tsx'):
                rel = str(filepath.relative_to(self.project_path))
                results.append(self.analyze_file(rel))
        return results

    def generate_spec(self, analysis: Dict) -> str:
        """生成spec.md内容"""
        lines = ['---']
        lines.append(f'spec_id: "reverse-ts-{Path(analysis.get("filepath","unknown")).stem}"')
        lines.append(f'title: "Reverse Spec for {analysis.get("filepath","")}"')
        lines.append(f'module: "ts-{analysis.get("router_role","component")}"')
        lines.append('level: "C"')
        lines.append('status: "draft"')
        lines.append('owner: "ts-reverse-engine"')
        lines.append('version: "0.1.0"')
        lines.append('generated_by: SpecGuard TSReverseEngine')
        lines.append(f'source_file: "{analysis.get("filepath","")}"')
        lines.append('---')
        lines.append('')
        lines.append(f'# Reverse Spec for {analysis.get("filepath","")}')
        lines.append('')

        # Confirmed Facts
        lines.append('## Confirmed Facts')
        if analysis.get("router_role") != "component":
            lines.append(f'- Router role: `{analysis["router_role"]}`')
        if analysis.get("is_client"):
            lines.append('- Client Component (`"use client"` directive)')
        else:
            lines.append('- Server Component (no `"use client"` directive)')
        if analysis.get("http_methods"):
            lines.append(f'- API methods: {", ".join(f"`{m}`" for m in analysis["http_methods"])}')
        if analysis.get("prisma_models"):
            lines.append(f'- Prisma models used: {", ".join(f"`{m}`" for m in analysis["prisma_models"])}')
        for imp in analysis.get("imports", [])[:10]:
            lines.append(f'- Import: `{imp}`')
        lines.append('')

        # Inferred Rules
        lines.append('## Inferred Rules')
        if analysis.get("standard_hooks"):
            lines.append(f'- Standard hooks: {", ".join(analysis["standard_hooks"])}')
        if analysis.get("custom_hooks"):
            lines.append(f'- Custom hooks (may include false positives): {", ".join(analysis["custom_hooks"][:5])}')
        lines.append('')

        return '\n'.join(lines)

    def _classify(self, findings: Dict) -> Dict[str, List[str]]:
        """三段式分类"""
        confirmed = []
        inferred = []
        unclear = []

        if findings.get("http_methods"):
            confirmed.append(f"API Route: {findings['http_methods']}")
        if findings.get("prisma_models"):
            confirmed.append(f"Prisma models: {findings['prisma_models']}")
        if findings.get("imports"):
            confirmed.append(f"Imports: {len(findings['imports'])}")
        confirmed.append(f"Router role: {findings.get('router_role','component')}")
        confirmed.append(f"{'Client' if findings.get('is_client') else 'Server'} Component")

        if findings.get("custom_hooks"):
            inferred.append(f"Custom hooks (may have false positives): {findings['custom_hooks'][:3]}")

        return {"confirmed": confirmed, "inferred": inferred, "unclear": unclear}


# Vitest覆盖率解析
def parse_vitest_coverage(report_path: str) -> Dict:
    """解析vitest --coverage的JSON报告"""
    import json
    with open(report_path) as f:
        data = json.load(f)
    # vitest格式: {total: {lines: {pct}, functions: {pct}, ...}, ...}
    total = data.get("total", {})
    return {
        "lines": total.get("lines", {}).get("pct", 0),
        "functions": total.get("functions", {}).get("pct", 0),
        "branches": total.get("branches", {}).get("pct", 0),
        "statements": total.get("statements", {}).get("pct", 0),
    }
```

### 3. reverse.py 新端点

```python
@router.post("/analyze-ts")
async def analyze_typescript(req: TSReverseRequest):
    """分析TypeScript文件"""
    engine = TypeScriptReverseEngine(req.project_path)
    results = []
    for filepath in req.files:
        full_path = Path(req.project_path) / filepath
        if full_path.exists() and full_path.suffix in ('.ts', '.tsx'):
            analysis = engine.analyze_file(filepath)
            analysis["filepath"] = filepath
            results.append(analysis)
    return {"files_analyzed": len(results), "results": results}
```

### 4. 测试

`tests/test_ts_reverse.py`:
- test_analyze_api_route — 测route.ts的HTTP方法提取
- test_analyze_page — 测page.tsx的Server Component检测
- test_analyze_client_component — 测"use client"检测
- test_analyze_prisma_calls — 测prisma.model.operation()提取
- test_analyze_imports — 测import依赖图
- test_generate_spec — 测spec.md生成含frontmatter
- test_router_role_detection — 测文件名→路由角色映射
- test_vitest_coverage_parse — 测vitest JSON解析

## 约束
- 只用Python标准库(re/json/pathlib)，不引入ts-morph或Node.js依赖
- 不修改现有Python逆向引擎(reverse_engine.py)
- 在main.py中挂载新路由
- 全英文代码注释

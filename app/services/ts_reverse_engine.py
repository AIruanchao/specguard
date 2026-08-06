"""Regex-based TypeScript reverse engineering engine."""
import json
import re
from pathlib import Path
from typing import Any, Optional


class TypeScriptReverseEngine:
    """TypeScript/TSX reverse analysis engine using regex extraction."""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)

    def analyze_file(self, filepath: str, content: Optional[str] = None) -> dict[str, Any]:
        """Analyze a single TS/TSX file."""
        if content is None:
            content = (self.project_path / filepath).read_text(encoding="utf-8")

        findings = {}

        findings["is_client"] = '"use client"' in content[:200] or "'use client'" in content[:200]
        findings["is_server_action"] = '"use server"' in content[:200] or "'use server'" in content[:200]

        findings["http_methods"] = re.findall(
            r"export\s+async\s+function\s+(GET|POST|PUT|DELETE|PATCH)\s*\(", content
        )

        findings["prisma_calls"] = re.findall(r"prisma\.(\w+)\.(\w+)\s*\(", content)
        findings["prisma_models"] = sorted({model for model, _ in findings["prisma_calls"]})

        findings["imports"] = re.findall(
            r"import\s+(?:type\s+)?(?:\{[^}]+\}|\w+|.+?from)\s+[\"']([^\"']+)", content
        )
        findings["type_imports"] = re.findall(
            r"import\s+type\s+\{[^}]+\}\s+from\s+[\"']([^\"']+)", content
        )

        filename = Path(filepath).name
        findings["router_role"] = self._router_role(filename)

        default_export = re.search(r"export\s+default\s+function\s+(\w+)", content)
        findings["component_name"] = default_export.group(1) if default_export else filename

        all_hooks = re.findall(r"\b(use[A-Z]\w+)\b", content)
        standard_hooks = {
            "useState",
            "useEffect",
            "useContext",
            "useReducer",
            "useCallback",
            "useMemo",
            "useRef",
            "useLayoutEffect",
        }
        findings["standard_hooks"] = self._unique_ordered(
            hook for hook in all_hooks if hook in standard_hooks
        )
        findings["custom_hooks"] = self._unique_ordered(
            hook for hook in all_hooks if hook not in standard_hooks
        )

        findings["classification"] = self._classify(findings)
        return findings

    def analyze_module(self, module_pattern: str) -> list[dict[str, Any]]:
        """Analyze a module by glob pattern."""
        results = []
        for filepath in self.project_path.glob(module_pattern):
            if filepath.suffix in (".ts", ".tsx"):
                rel = str(filepath.relative_to(self.project_path))
                analysis = self.analyze_file(rel)
                analysis["filepath"] = rel
                results.append(analysis)
        return results

    def generate_spec(self, analysis: dict[str, Any]) -> str:
        """Generate spec.md content from TypeScript analysis."""
        filepath = analysis.get("filepath", "")
        lines = ["---"]
        lines.append(f'spec_id: "reverse-ts-{Path(analysis.get("filepath", "unknown")).stem}"')
        lines.append(f'title: "Reverse Spec for {filepath}"')
        lines.append(f'module: "ts-{analysis.get("router_role", "component")}"')
        lines.append('level: "C"')
        lines.append('status: "draft"')
        lines.append('owner: "ts-reverse-engine"')
        lines.append('version: "0.1.0"')
        lines.append("generated_by: SpecGuard TSReverseEngine")
        lines.append(f'source_file: "{filepath}"')
        lines.append("---")
        lines.append("")
        lines.append(f"# Reverse Spec for {filepath}")
        lines.append("")

        lines.append("## Confirmed Facts")
        if analysis.get("router_role") != "component":
            lines.append(f'- Router role: `{analysis["router_role"]}`')
        if analysis.get("is_client"):
            lines.append('- Client Component (`"use client"` directive)')
        else:
            lines.append('- Server Component (no `"use client"` directive)')
        if analysis.get("http_methods"):
            lines.append(f'- API methods: {", ".join(f"`{method}`" for method in analysis["http_methods"])}')
        if analysis.get("prisma_models"):
            lines.append(f'- Prisma models used: {", ".join(f"`{model}`" for model in analysis["prisma_models"])}')
        for imported in analysis.get("imports", [])[:10]:
            lines.append(f"- Import: `{imported}`")
        lines.append("")

        lines.append("## Inferred Rules")
        if analysis.get("standard_hooks"):
            lines.append(f'- Standard hooks: {", ".join(analysis["standard_hooks"])}')
        if analysis.get("custom_hooks"):
            lines.append(
                f'- Custom hooks (may include false positives): {", ".join(analysis["custom_hooks"][:5])}'
            )
        lines.append("")

        return "\n".join(lines)

    def _router_role(self, filename: str) -> str:
        roles = {
            "page.tsx": "page",
            "layout.tsx": "layout",
            "route.ts": "api-route",
            "error.tsx": "error-boundary",
            "loading.tsx": "loading",
            "middleware.ts": "middleware",
            "actions.ts": "server-actions",
        }
        return roles.get(filename, "component")

    def _unique_ordered(self, values) -> list[str]:
        seen = set()
        unique = []
        for value in values:
            if value not in seen:
                unique.append(value)
                seen.add(value)
        return unique

    def _classify(self, findings: dict[str, Any]) -> dict[str, list[str]]:
        """Classify findings as confirmed, inferred, or unclear."""
        confirmed = []
        inferred = []
        unclear = []

        if findings.get("http_methods"):
            confirmed.append(f"API Route: {findings['http_methods']}")
        if findings.get("prisma_models"):
            confirmed.append(f"Prisma models: {findings['prisma_models']}")
        if findings.get("imports"):
            confirmed.append(f"Imports: {len(findings['imports'])}")
        confirmed.append(f"Router role: {findings.get('router_role', 'component')}")
        confirmed.append(f"{'Client' if findings.get('is_client') else 'Server'} Component")

        if findings.get("custom_hooks"):
            inferred.append(f"Custom hooks (may have false positives): {findings['custom_hooks'][:3]}")

        return {"confirmed": confirmed, "inferred": inferred, "unclear": unclear}


def parse_vitest_coverage(report_path: str) -> dict[str, float]:
    """Parse a vitest coverage-summary JSON report."""
    with open(report_path, encoding="utf-8") as report_file:
        data = json.load(report_file)
    total = data.get("total", {})
    return {
        "lines": total.get("lines", {}).get("pct", 0),
        "functions": total.get("functions", {}).get("pct", 0),
        "branches": total.get("branches", {}).get("pct", 0),
        "statements": total.get("statements", {}).get("pct", 0),
    }

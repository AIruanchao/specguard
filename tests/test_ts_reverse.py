"""TypeScript reverse engine tests."""
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services.ts_reverse_engine import TypeScriptReverseEngine, parse_vitest_coverage


class TestTypeScriptReverseEngine:
    def setup_method(self):
        self.engine = TypeScriptReverseEngine("/tmp")

    def test_analyze_api_route(self):
        analysis = self.engine.analyze_file(
            "app/api/users/route.ts",
            """
            export async function GET() { return Response.json({}) }
            export async function POST(request: Request) { return Response.json({}) }
            """,
        )

        assert analysis["http_methods"] == ["GET", "POST"]
        assert analysis["router_role"] == "api-route"

    def test_analyze_page(self):
        analysis = self.engine.analyze_file(
            "app/dashboard/page.tsx",
            "export default function DashboardPage() { return <main /> }",
        )

        assert analysis["is_client"] is False
        assert analysis["router_role"] == "page"
        assert analysis["component_name"] == "DashboardPage"

    def test_analyze_client_component(self):
        analysis = self.engine.analyze_file(
            "components/Counter.tsx",
            """
            "use client"
            import { useState } from "react"
            export default function Counter() { const [count] = useState(0); return count }
            """,
        )

        assert analysis["is_client"] is True
        assert analysis["standard_hooks"] == ["useState"]

    def test_analyze_prisma_calls(self):
        analysis = self.engine.analyze_file(
            "app/actions.ts",
            """
            export async function saveUser() {
                await prisma.user.create({ data: {} })
                await prisma.order.findMany()
            }
            """,
        )

        assert analysis["prisma_calls"] == [("user", "create"), ("order", "findMany")]
        assert analysis["prisma_models"] == ["order", "user"]

    def test_analyze_imports(self):
        analysis = self.engine.analyze_file(
            "app/page.tsx",
            """
            import React from "react"
            import { Button } from "@/components/ui/button"
            import type { User } from "@/types/user"
            """,
        )

        assert "react" in analysis["imports"]
        assert "@/components/ui/button" in analysis["imports"]
        assert "@/types/user" in analysis["imports"]
        assert analysis["type_imports"] == ["@/types/user"]

    def test_generate_spec(self):
        analysis = self.engine.analyze_file(
            "app/api/users/route.ts",
            """
            import { prisma } from "@/lib/db"
            export async function GET() { return prisma.user.findMany() }
            """,
        )
        analysis["filepath"] = "app/api/users/route.ts"

        spec = self.engine.generate_spec(analysis)

        assert spec.startswith("---\n")
        assert 'spec_id: "reverse-ts-route"' in spec
        assert 'module: "ts-api-route"' in spec
        assert "generated_by: SpecGuard TSReverseEngine" in spec
        assert 'source_file: "app/api/users/route.ts"' in spec
        assert "## Confirmed Facts" in spec
        assert "- API methods: `GET`" in spec

    def test_router_role_detection(self):
        cases = {
            "page.tsx": "page",
            "layout.tsx": "layout",
            "route.ts": "api-route",
            "error.tsx": "error-boundary",
            "loading.tsx": "loading",
            "middleware.ts": "middleware",
            "actions.ts": "server-actions",
            "Widget.tsx": "component",
        }

        for filename, role in cases.items():
            analysis = self.engine.analyze_file(filename, "export default function Test() { return null }")
            assert analysis["router_role"] == role

    def test_vitest_coverage_parse(self, tmp_path):
        report_path = tmp_path / "coverage-summary.json"
        report_path.write_text(
            json.dumps({
                "total": {
                    "lines": {"pct": 91.5},
                    "functions": {"pct": 88.2},
                    "branches": {"pct": 75.0},
                    "statements": {"pct": 90.1},
                }
            }),
            encoding="utf-8",
        )

        coverage = parse_vitest_coverage(str(report_path))

        assert coverage == {
            "lines": 91.5,
            "functions": 88.2,
            "branches": 75.0,
            "statements": 90.1,
        }


class TestTypeScriptReverseAPI:
    def test_analyze_typescript_endpoint(self, tmp_path):
        source = tmp_path / "app" / "api" / "users"
        source.mkdir(parents=True)
        route = source / "route.ts"
        route.write_text("export async function GET() { return Response.json({}) }", encoding="utf-8")

        client = TestClient(app)
        response = client.post(
            "/api/v1/reverse/analyze-ts",
            json={"project_path": str(tmp_path), "files": ["app/api/users/route.ts"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["files_analyzed"] == 1
        assert data["results"][0]["filepath"] == "app/api/users/route.ts"
        assert data["results"][0]["http_methods"] == ["GET"]

"""Reverse engine tests."""
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services.reverse_engine import (
    CONFIRMED_FACT,
    CLARIFICATION_NEEDED,
    INFERRED_RULE,
    ReverseEngine,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_PATH = PROJECT_ROOT / "app"


class TestReverseEngine:
    def setup_method(self):
        self.engine = ReverseEngine(str(PROJECT_ROOT))

    def test_extracts_function_signatures(self):
        analysis = self.engine.analyze_file("app/routers/health.py")

        functions = {item["name"]: item for item in analysis["functions"]}

        assert "health_check" in functions
        assert functions["health_check"]["async"] is True

    def test_extracts_router_decorators(self):
        analysis = self.engine.analyze_file("app/routers/gate.py")

        routes = {(item["method"], item["path"]) for item in analysis["routes"]}

        assert ("POST", "/check") in routes

    def test_extracts_pydantic_models_and_fields(self):
        analysis = self.engine.analyze_file("app/models.py")

        models = {item["name"]: item for item in analysis["models"]}
        request_fields = {field["name"]: field for field in models["GateCheckRequest"]["fields"]}

        assert models["GateCheckRequest"]["is_pydantic"] is True
        assert request_fields["project_path"]["type"] == "str"
        assert request_fields["project_path"]["uses_field"] is True
        assert request_fields["project_path"]["description"] == "项目根目录路径"

    def test_extracts_import_graph(self):
        analysis = self.engine.analyze_file("app/routers/specs.py")

        imports = {(item["type"], item["module"], item["name"]) for item in analysis["imports"]}

        assert ("import", None, "re") in imports
        assert ("from_import", "pathlib", "Path") in imports

    def test_classifies_findings(self):
        assert self.engine.classify_finding({"source": "ast_function_signature"}) == CONFIRMED_FACT
        assert self.engine.classify_finding({"source": "router_decorator"}) == CONFIRMED_FACT
        assert self.engine.classify_finding({"source": "pydantic_field"}) == CONFIRMED_FACT
        assert self.engine.classify_finding({"source": "sql_statement"}) == INFERRED_RULE
        assert self.engine.classify_finding({"source": "if_else_branch"}) == INFERRED_RULE
        assert self.engine.classify_finding({"source": "unknown"}) == CLARIFICATION_NEEDED

    def test_analyzes_module_from_app_code(self):
        analyses = self.engine.analyze_module("app/routers")

        analyzed_files = {analysis["relative_path"] for analysis in analyses}

        assert "app/routers/health.py" in analyzed_files
        assert "app/routers/gate.py" in analyzed_files

    def test_generate_spec_contains_frontmatter(self):
        analysis = self.engine.analyze_file("app/routers/health.py")

        spec = self.engine.generate_spec(analysis)

        assert spec.startswith("---\n")
        assert "spec_id: reverse-app-health" in spec
        assert "module: \"app\"" in spec
        assert "status: draft" in spec
        assert "generated_by: SpecGuard ReverseEngine" in spec
        assert "source_file: \"app/routers/health.py\"" in spec
        assert "## Confirmed Facts" in spec


class TestReverseAPI:
    def test_reverse_analyze_and_result(self):
        client = TestClient(app)

        response = client.post(
            "/api/v1/reverse/analyze",
            json={"project_path": str(PROJECT_ROOT), "module": "app/routers/health.py"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["specs_generated"] == 1
        assert data["findings"]["routes"] == 1

        result_response = client.get(f"/api/v1/reverse/result/{data['job_id']}")
        assert result_response.status_code == 200
        result = result_response.json()
        assert result["status"] == "completed"
        assert result["specs"][0].startswith("---\n")

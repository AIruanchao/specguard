"""SpecGuard 测试"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# === 健康检查 ===
class TestHealth:
    def test_health(self):
        r = client.get("/api/v1/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "healthy"
        assert data["service"] == "specguard"
        assert data["version"] == "0.1.0"


# === 门禁引擎 ===
class TestGate:
    def test_gate_no_files(self):
        """无变更文件→PASS"""
        r = client.post("/api/v1/gate/check", json={
            "project_path": "/tmp",
            "changed_files": [],
            "pr_body": "",
            "pr_labels": [],
        })
        assert r.status_code == 200
        assert r.json()["passed"] is True

    def test_gate_business_no_spec(self):
        """业务变更无Spec→FAIL"""
        r = client.post("/api/v1/gate/check", json={
            "project_path": "/Users/maccc/projects/business-document-generator",
            "changed_files": ["app/services/smart_seal.py"],
            "pr_body": "修了个bug",
            "pr_labels": [],
        })
        assert r.status_code == 200
        assert r.json()["passed"] is False
        assert "seal-engine" in r.json()["affected_modules"]

    def test_gate_hotfix_exempt(self):
        """hotfix标签→PASS"""
        r = client.post("/api/v1/gate/check", json={
            "project_path": "/tmp",
            "changed_files": ["app/services/smart_seal.py"],
            "pr_body": "紧急修复",
            "pr_labels": ["hotfix-emergency"],
        })
        assert r.status_code == 200
        assert r.json()["passed"] is True

    def test_gate_docs_exempt(self):
        """docs-only标签→PASS"""
        r = client.post("/api/v1/gate/check", json={
            "project_path": "/tmp",
            "changed_files": ["README.md"],
            "pr_body": "",
            "pr_labels": ["docs-only"],
        })
        assert r.status_code == 200
        assert r.json()["passed"] is True

    def test_gate_unmatched_protected(self):
        """未匹配受保护文件→FAIL"""
        r = client.post("/api/v1/gate/check", json={
            "project_path": "/tmp",
            "changed_files": ["app/routes/new_module.py"],
            "pr_body": "",
            "pr_labels": [],
        })
        assert r.status_code == 200
        assert r.json()["passed"] is False

    def test_gate_with_spec(self):
        """业务变更+正确Spec→PASS"""
        r = client.post("/api/v1/gate/check", json={
            "project_path": "/Users/maccc/projects/business-document-generator",
            "changed_files": ["app/services/smart_seal.py"],
            "pr_body": "修复 Spec: sdd/domain-spec/seal-engine/spec.md",
            "pr_labels": [],
        })
        assert r.status_code == 200
        assert r.json()["passed"] is True
        assert "sdd/domain-spec/seal-engine/spec.md" in r.json()["spec_refs"]


# === CI检查 ===
class TestCI:
    def test_ci_status_no_token(self):
        """无Token→返回提示"""
        r = client.get("/api/v1/ci/status", params={"repo": "AIruanchao/specguard"})
        assert r.status_code == 200
        data = r.json()
        assert data["repo"] == "AIruanchao/specguard"


# === 覆盖率 ===
class TestCoverage:
    def test_coverage_nonexistent_project(self):
        """不存在的项目→0覆盖率"""
        r = client.get("/api/v1/coverage/nonexistent-project")
        assert r.status_code == 200
        data = r.json()
        assert data["project"] == "nonexistent-project"
        assert data["total_coverage"] == 0


# === Web UI ===
class TestWebUI:
    def test_dashboard_page(self):
        r = client.get("/")
        assert r.status_code == 200
        assert "SpecGuard" in r.text

    def test_coverage_page(self):
        r = client.get("/coverage")
        assert r.status_code == 200
        assert "覆盖率" in r.text

    def test_specs_page(self):
        r = client.get("/specs")
        assert r.status_code == 200
        assert "Spec" in r.text

    def test_gate_page(self):
        r = client.get("/gate")
        assert r.status_code == 200
        assert "门禁" in r.text

    def test_static_css(self):
        r = client.get("/static/style.css")
        assert r.status_code == 200


# === Specs API ===
class TestSpecs:
    def test_specs_list(self):
        r = client.get("/api/v1/specs/list", params={"project": "business-document-generator"})
        assert r.status_code == 200
        data = r.json()
        assert data["project"] == "business-document-generator"
        assert isinstance(data["specs"], list)

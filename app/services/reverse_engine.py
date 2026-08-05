"""Reverse engineering engine for generating specs from Python code."""
import ast
import json
import re
from pathlib import Path


CONFIRMED_FACT = "confirmed_fact"
INFERRED_RULE = "inferred_rule"
CLARIFICATION_NEEDED = "clarification_needed"


class ReverseEngine:
    """Extract spec information from Python source code."""

    ROUTE_METHODS = {"get", "post", "put", "delete", "patch"}

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)

    def analyze_file(self, filepath: str) -> dict:
        """Analyze one Python file and return functions, routes, models, and imports."""
        source_path = self._resolve_file(filepath)
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(source_path))
        relative_path = self._relative_to_project(source_path)

        analysis = {
            "file": str(source_path),
            "relative_path": relative_path,
            "module": self._module_name_from_path(source_path),
            "functions": [],
            "routes": [],
            "models": [],
            "imports": [],
            "findings": [],
        }

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                import_info = self._extract_import(node)
                analysis["imports"].append(import_info)
                analysis["findings"].append({
                    "source": "import",
                    "classification": CONFIRMED_FACT,
                    "data": import_info,
                })

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function_info = self._extract_function(node)
                analysis["functions"].append(function_info)
                analysis["findings"].append({
                    "source": "ast_function_signature",
                    "classification": self.classify_finding({"source": "ast_function_signature"}),
                    "data": function_info,
                })
                for route_info in self._extract_routes(node):
                    route_info["function"] = node.name
                    analysis["routes"].append(route_info)
                    analysis["findings"].append({
                        "source": "router_decorator",
                        "classification": self.classify_finding({"source": "router_decorator"}),
                        "data": route_info,
                    })
            elif isinstance(node, ast.ClassDef):
                model_info = self._extract_model(node)
                analysis["models"].append(model_info)
                analysis["findings"].append({
                    "source": "class_definition",
                    "classification": CONFIRMED_FACT,
                    "data": model_info,
                })
                for field_info in model_info["fields"]:
                    analysis["findings"].append({
                        "source": "pydantic_field",
                        "classification": self.classify_finding({"source": "pydantic_field"}),
                        "data": field_info,
                    })

        analysis["inferred_rules"] = self._extract_inferred_rules(tree)
        for rule in analysis["inferred_rules"]:
            analysis["findings"].append({
                "source": rule["source"],
                "classification": self.classify_finding(rule),
                "data": rule,
            })

        return analysis

    def analyze_module(self, module_name: str) -> list[dict]:
        """Analyze every Python file in a module path or matching module name."""
        target = self.project_path / module_name.replace(".", "/") if module_name else self.project_path
        files = []

        if target.is_file() and target.suffix == ".py":
            files = [target]
        elif target.is_dir():
            files = sorted(target.rglob("*.py"))
        else:
            normalized = re.sub(r"[^a-z0-9]+", "-", module_name.lower()).strip("-")
            for source_path in sorted(self.project_path.rglob("*.py")):
                haystack = re.sub(
                    r"[^a-z0-9]+",
                    "-",
                    str(source_path.relative_to(self.project_path)).lower(),
                )
                if normalized and normalized in haystack:
                    files.append(source_path)

        clean_files = [path for path in files if "__pycache__" not in path.parts]
        return [self.analyze_file(str(path)) for path in clean_files]

    def generate_spec(self, analysis: dict) -> str:
        """Generate spec.md content with YAML-compatible frontmatter."""
        module_name = analysis.get("module") or "unknown-module"
        relative_path = analysis.get("relative_path") or "unknown.py"
        spec_id = self._safe_slug(f"reverse-{module_name}-{Path(relative_path).stem}")
        title = f"Reverse Spec for {relative_path}"

        lines = [
            "---",
            f"spec_id: {spec_id}",
            f"title: {json.dumps(title, ensure_ascii=False)}",
            f"module: {json.dumps(module_name, ensure_ascii=False)}",
            "level: C",
            "status: draft",
            "owner: reverse-engine",
            "version: 0.1.0",
            "generated_by: SpecGuard ReverseEngine",
            f"source_file: {json.dumps(relative_path, ensure_ascii=False)}",
            "---",
            "",
            f"# {title}",
            "",
            "## Confirmed Facts",
        ]

        for import_info in analysis.get("imports", []):
            lines.append(f"- Import: `{import_info['name']}`")
        for function_info in analysis.get("functions", []):
            args = ", ".join(arg["name"] for arg in function_info["args"])
            returns = function_info.get("returns") or "None"
            lines.append(f"- Function `{function_info['name']}({args}) -> {returns}`")
        for route_info in analysis.get("routes", []):
            lines.append(
                f"- Route `{route_info['method']} {route_info['path']}` handled by `{route_info['function']}`"
            )
        for model_info in analysis.get("models", []):
            bases = ", ".join(model_info.get("bases", [])) or "object"
            lines.append(f"- Class `{model_info['name']}` extends `{bases}`")
            for field_info in model_info.get("fields", []):
                description = field_info.get("description") or ""
                suffix = f" — {description}" if description else ""
                lines.append(
                    f"  - Field `{field_info['name']}: {field_info.get('type') or 'Any'}`{suffix}"
                )

        lines.extend(["", "## Inferred Rules"])
        inferred_rules = analysis.get("inferred_rules", [])
        if inferred_rules:
            for rule in inferred_rules:
                lines.append(f"- {rule['description']}")
        else:
            lines.append("- None detected.")

        lines.extend([
            "",
            "## Clarifications Needed",
            "- Review inferred behavior and confirm business intent before promotion from draft.",
            "",
        ])
        return "\n".join(lines)

    def classify_finding(self, finding: dict) -> str:
        """Classify findings into confirmed facts, inferred rules, or clarification items."""
        source = finding.get("source", "")
        if source in {"ast_function_signature", "router_decorator", "pydantic_field"}:
            return CONFIRMED_FACT
        if source in {"sql_statement", "regex_match", "if_else_branch"}:
            return INFERRED_RULE
        return CLARIFICATION_NEEDED

    def _resolve_file(self, filepath: str) -> Path:
        path = Path(filepath)
        if not path.is_absolute():
            path = self.project_path / path
        if not path.exists():
            raise FileNotFoundError(f"Python file not found: {path}")
        if path.suffix != ".py":
            raise ValueError(f"Expected a Python file: {path}")
        return path.resolve()

    def _relative_to_project(self, source_path: Path) -> str:
        try:
            return str(source_path.relative_to(self.project_path.resolve()))
        except ValueError:
            return source_path.name

    def _module_name_from_path(self, source_path: Path) -> str:
        relative_path = self._relative_to_project(source_path)
        parts = Path(relative_path).with_suffix("").parts
        if len(parts) > 1:
            return parts[0]
        return parts[0] if parts else "unknown-module"

    def _extract_import(self, node: ast.Import | ast.ImportFrom) -> dict:
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
            return {"type": "import", "name": ", ".join(names), "module": None}
        names = [alias.name for alias in node.names]
        return {"type": "from_import", "name": ", ".join(names), "module": node.module or ""}

    def _extract_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict:
        return {
            "name": node.name,
            "async": isinstance(node, ast.AsyncFunctionDef),
            "args": self._extract_args(node.args),
            "returns": self._annotation_to_string(node.returns),
            "lineno": node.lineno,
        }

    def _extract_args(self, args: ast.arguments) -> list[dict]:
        defaults = [None] * (len(args.args) - len(args.defaults)) + list(args.defaults)
        extracted = []
        for arg, default in zip(args.args, defaults):
            extracted.append({
                "name": arg.arg,
                "type": self._annotation_to_string(arg.annotation),
                "default": self._node_to_string(default),
            })
        return extracted

    def _extract_routes(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[dict]:
        routes = []
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                continue
            method = decorator.func.attr.lower()
            if method not in self.ROUTE_METHODS:
                continue
            path = ""
            if decorator.args:
                path = self._literal_to_string(decorator.args[0])
            routes.append({"method": method.upper(), "path": path, "lineno": decorator.lineno})
        return routes

    def _extract_model(self, node: ast.ClassDef) -> dict:
        fields = []
        for child in node.body:
            if isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
                fields.append(self._extract_field(child))
        return {
            "name": node.name,
            "bases": [self._node_to_string(base) or "" for base in node.bases],
            "is_pydantic": any((self._node_to_string(base) or "").endswith("BaseModel") for base in node.bases),
            "fields": fields,
            "lineno": node.lineno,
        }

    def _extract_field(self, node: ast.AnnAssign) -> dict:
        field_name = node.target.id if isinstance(node.target, ast.Name) else "unknown"
        field_info = {
            "name": field_name,
            "type": self._annotation_to_string(node.annotation),
            "default": self._node_to_string(node.value),
            "description": None,
            "uses_field": False,
            "lineno": node.lineno,
        }
        if isinstance(node.value, ast.Call) and (self._node_to_string(node.value.func) or "").endswith("Field"):
            field_info["uses_field"] = True
            for keyword in node.value.keywords:
                if keyword.arg == "description":
                    field_info["description"] = self._literal_to_string(keyword.value)
                elif keyword.arg == "default":
                    field_info["default"] = self._node_to_string(keyword.value)
                elif keyword.arg == "default_factory":
                    field_info["default"] = f"default_factory={self._node_to_string(keyword.value)}"
        return field_info

    def _extract_inferred_rules(self, tree: ast.AST) -> list[dict]:
        rules = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                rules.append({
                    "source": "if_else_branch",
                    "classification": INFERRED_RULE,
                    "description": f"Conditional branch at line {node.lineno} may encode business behavior.",
                    "lineno": node.lineno,
                })
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                value = node.value.strip()
                if re.search(r"\bSELECT\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b", value, re.I):
                    rules.append({
                        "source": "sql_statement",
                        "classification": INFERRED_RULE,
                        "description": f"SQL-like statement at line {node.lineno} may encode persistence behavior.",
                        "lineno": node.lineno,
                    })
        return rules

    def _annotation_to_string(self, node: ast.AST | None) -> str | None:
        if node is None:
            return None
        return self._node_to_string(node)

    def _node_to_string(self, node: ast.AST | None) -> str | None:
        if node is None:
            return None
        try:
            return ast.unparse(node)
        except Exception:
            return None

    def _literal_to_string(self, node: ast.AST) -> str:
        try:
            value = ast.literal_eval(node)
            return str(value)
        except Exception:
            return self._node_to_string(node) or ""

    def _safe_slug(self, value: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
        return slug or "reverse-spec"

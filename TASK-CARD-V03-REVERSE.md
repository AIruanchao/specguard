# 任务卡: SpecGuard V0.3 逆向引擎MVP

## 背景

SpecGuard是企业级SDD治理平台（FastAPI Web服务）。V0.1(API)+V0.2(Web UI)已完成。
V0.3目标: 实现代码逆向解析引擎MVP——从存量Python代码自动生成spec.md。

## 项目位置

`/Users/maccc/projects/specguard`

## 需要开发的文件

```
specguard/
├── app/
│   ├── routers/
│   │   └── reverse.py          # 逆向引擎API路由
│   └── services/
│       └── reverse_engine.py   # 核心逆向引擎
├── tests/
│   └── test_reverse.py         # 逆向引擎测试
```

## 逆向引擎设计

### reverse_engine.py 核心类

```python
class ReverseEngine:
    """从Python代码逆向提取Spec信息"""
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
    
    def analyze_file(self, filepath: str) -> dict:
        """分析单个Python文件"""
        # 1. AST分析 → 函数签名、类型注解、import
        # 2. 路由提取 → @router.get/post装饰器
        # 3. 模型提取 → Pydantic Model字段
        # 返回: {functions, routes, models, imports}
    
    def analyze_module(self, module_name: str) -> list[dict]:
        """分析整个模块"""
    
    def generate_spec(self, analysis: dict) -> str:
        """生成spec.md内容（含frontmatter）"""
    
    def classify_finding(self, finding: dict) -> str:
        """三段式分类: 已确认事实/推断规则/待澄清项"""
```

### API端点

```
POST /api/v1/reverse/analyze
Body: {"project_path": "...", "module": "seal-engine"}
→ {"specs_generated": 3, "findings": {...}}

GET /api/v1/reverse/result/{job_id}
→ {"status": "completed", "specs": [...]}
```

## AST分析要求

用Python标准库`ast`模块（不引入第三方依赖）:

1. **函数签名提取**: `ast.FunctionDef` → 函数名/参数/返回类型注解
2. **类提取**: `ast.ClassDef` → 类名/基类(Pydantic BaseModel)
3. **路由装饰器**: 找`@router.get/post/put/delete` → HTTP方法+路径
4. **Pydantic字段**: 找`Field()`调用 → 字段名/类型/默认值/描述
5. **import图**: `ast.Import` → 依赖关系

## 三段式分类规则

| 来源 | 分类 |
|------|------|
| ast函数签名/类型注解 | 已确认事实 |
| @router装饰器 | 已确认事实 |
| Pydantic Model字段 | 已确认事实 |
| SQL语句/正则匹配 | 推断规则 |
| if-else分支 | 推断规则 |
| 无法确定 | 待澄清项 |

## 测试要求

- 测试用`/Users/maccc/projects/specguard/app/`自身的代码作为分析目标
- 至少6个测试用例（每个提取器至少1个）
- 测试必须验证生成的spec.md包含正确的frontmatter

## 约束

- 只用Python标准库(ast/json/re/pathlib)，不引入第三方AST工具
- 不修改app/main.py以外的现有文件
- 全英文代码注释
- 在main.py中挂载reverse路由

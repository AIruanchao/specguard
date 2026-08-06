# SpecGuard ERP接入方案 V3.0（Spike验证版）

> **V2→V3**: Spike用ERP真实代码验证6项 → ts-morph降级为可选 / 正则先行 / 工期2周
> **V1→V3轨迹**: V1(20分/0 APPROVE) → V2(26分/2 APPROVE) → V3(Spike数据修正)

---

## V2→V3 修正摘要

| # | V2问题 | V2方案 | V3修正(Spike数据) |
|---|--------|--------|------------------|
| ① | ts-morph必须（4模型质疑过度设计） | ts-morph作为唯一方案 | **正则先行（83%准确率），ts-morph可选增强** |
| ② | 工期3-4周（GPT-5.4说低估） | 3-4周 | **2周（正则方案更简单）** |
| ③ | Spike未跑就估工期 | Spike计划1周 | **Spike已完成，6项验证5项100%** |
| ④ | 环境变量检查会误报 | "不同环境值不一致=critical" | **改为检查变量齐全性+格式合法性** |
| ⑤ | Server Actions未管控 | 未提及 | **新增"use server"指令门禁** |
| ⑥ | middleware.ts未管控 | 未提及 | **新增middleware.ts门禁** |

---

## 一、Spike验证数据（V3核心依据）

> 完整报告见 `SPIKE-REPORT.md`

| 验证项 | 正则准确率 | 实际ERP代码模式 |
|--------|-----------|----------------|
| API Route HTTP方法 | 100% | `export async function GET/POST`（标准格式，无箭头函数） |
| Prisma调用 | 100% | `prisma.model.operation()`（固定模式） |
| import依赖 | 100% | 标准ES模块 `import from "@/lib/xxx"` |
| Server/Client检测 | 100% | `"use client"`指令在文件头 |
| Prisma model | 100% | `grep '^model '`（271个model） |
| React hooks | 80% | 误匹配自定义`use`开头的函数（低风险） |

### Spike结论

ERP代码模式**高度规范化**——所有文件用标准格式，没有箭头函数组件/HOC/类组件。正则方案够用，ts-morph是过度设计。GPT-5.6Luna的BLOCK理由（箭头函数/HOC/类型推导不稳定）在ERP实际代码中**不成立**。

---

## 二、逆向引擎方案（正则先行）

### 2.1 TypeScript逆向引擎

```python
def analyze_typescript(filepath: str, content: str) -> dict:
    """TypeScript/TSX逆向分析（正则方案，Spike验证83%准确率）"""

    # 1. Server/Client Component检测（100%准确率）
    is_client = '"use client"' in content[:200] or "'use client'" in content[:200]
    is_server_action = '"use server"' in content[:200]

    # 2. API Route提取（100%准确率）
    http_methods = re.findall(r'export\s+async\s+function\s+(GET|POST|PUT|DELETE|PATCH)\s*\(', content)

    # 3. Prisma调用提取（100%准确率）
    prisma_calls = re.findall(r'prisma\.(\w+)\.(\w+)\s*\(', content)
    prisma_models_used = set(m for m, _ in prisma_calls)

    # 4. import依赖图（100%准确率）
    imports = re.findall(r'import\s+(?:type\s+)?(?:\{[^}]+\}|\w+|.+?from)\s+["\']([^"\']+)', content)
    # 区分type-only import
    type_imports = re.findall(r'import\s+type\s+\{[^}]+\}\s+from\s+["\']([^"\']+)', content)

    # 5. React组件名（文件名推断 + 函数定义匹配）
    filename = Path(filepath).stem
    components = []
    if filepath.endswith('page.tsx'):
        components.append({"name": filename, "type": "page", "isServer": not is_client})
    elif filepath.endswith('layout.tsx'):
        components.append({"name": filename, "type": "layout", "isServer": not is_client})
    elif filepath.endswith('route.ts'):
        components.append({"name": filename, "type": "api-route", "methods": http_methods})
    else:
        # 普通组件：提取export default function/component
        default_export = re.search(r'export\s+default\s+function\s+(\w+)', content)
        if default_export:
            components.append({"name": default_export.group(1), "type": "component", "isServer": not is_client})

    # 6. Server Actions检测（V3新增）
    if is_server_action:
        actions = re.findall(r'async\s+function\s+(\w+)\s*\(', content)
        components.append({"type": "server-actions", "actions": actions})

    return classify_findings({
        "filepath": filepath,
        "is_client": is_client,
        "is_server_action": is_server_action,
        "http_methods": http_methods,
        "prisma_calls": prisma_calls,
        "prisma_models": prisma_models_used,
        "imports": imports,
        "type_imports": type_imports,
        "components": components,
    })
```

### 2.2 三段式分类规则（适配TS）

| 来源 | 分类 | Spike准确率 |
|------|------|------------|
| API Route export function | ✅ 已确认事实 | 100% |
| Prisma调用 | ✅ 已确认事实 | 100% |
| import依赖 | ✅ 已确认事实 | 100% |
| "use client"/"use server"指令 | ✅ 已确认事实 | 100% |
| 文件名→路由角色（page/layout/route） | ✅ 已确认事实 | 100% |
| React hooks使用 | ⚠️ 推断规则 | 80% |
| 组件间调用关系 | ⚠️ 推断规则 | 需ts-morph |

---

## 三、App Router + Server Actions + Middleware门禁

### V3新增的门禁规则

```yaml
# specguard/app/data/router_conventions.yml
rules:
  # V2已有
  - pattern: "src/app/**/page.tsx"
    role: "page"
    constraints: ["必须导出default React Component"]
    
  - pattern: "src/app/**/layout.tsx"
    role: "layout"
    constraints: ["必须接收children prop", "禁止'use client'"]
    
  - pattern: "src/app/api/**/route.ts"
    role: "api-route"
    constraints: ["必须导出至少一个HTTP方法"]
    
  - pattern: "prisma/schema.prisma"
    role: "database-schema"
    constraints: ["变更必须引用erp-prisma/spec.md"]
    
  # V3新增
  - pattern: "src/app/**/actions.ts"
    role: "server-actions"
    constraints:
      - "文件头必须有'use server'指令"
      - "每个export async function是一个Server Action"
      - "Spec必须标注副作用（DB写入/外部API调用）"
    spec_required: "domain-spec/{module}/actions-spec.md"
    
  - pattern: "src/middleware.ts"
    role: "middleware"
    constraints:
      - "涉及鉴权/路由重定向=高风险"
      - "Spec必须标注所有重定向规则"
    spec_required: "domain-spec/erp-auth/middleware-spec.md"
    
  - pattern: "**/error.tsx"
    role: "error-boundary"
    constraints: ["必须是Client Component", "必须接收error和reset props"]
```

---

## 四、环境变量检查修正

### V2问题（GPT-5.4指出）

"DATABASE_URL在不同环境出现不同值本来就是正常现象，把'不同环境值不一致'判成critical会制造大量误报"

### V3修正

```python
def check_env_quality(project_path):
    """环境变量质量检查（不检查值一致性，只检查齐全性+格式）"""
    debts = []
    
    critical_vars = ["DATABASE_URL", "NEXTAUTH_URL", "NEXTAUTH_SECRET", "BUILD_MACHINE"]
    
    # 1. .env.example必须包含所有关键变量
    env_example = parse_env(os.path.join(project_path, ".env.example"))
    for var in critical_vars:
        if var not in env_example:
            debts.append({"check": "env_missing", "severity": "auto_fixable", 
                         "detail": f".env.example缺少{var}"})
    
    # 2. 格式合法性检查
    for env_file in [".env", ".env.production"]:
        path = os.path.join(project_path, env_file)
        if os.path.exists(path):
            env = parse_env(path)
            for var in critical_vars:
                val = env.get(var, "")
                if var == "DATABASE_URL" and val and not val.startswith(("postgresql://", "postgres://")):
                    debts.append({"check": "env_format", "severity": "critical",
                                 "detail": f"{env_file}: DATABASE_URL格式不合法"})
                if var == "NEXTAUTH_SECRET" and val and len(val) < 16:
                    debts.append({"check": "env_weak_secret", "severity": "critical",
                                 "detail": f"{env_file}: NEXTAUTH_SECRET长度<16"})
    
    return debts
```

---

## 五、修正后工期估算

| V2估算 | V3估算 | 理由 |
|--------|--------|------|
| Spike: 1周 | **已完成** | 6项验证跑完 |
| V1.5: 3-4周 | **2周** | 正则方案（不需要ts-morph集成+Node.js子进程） |
| 接入: 5-7天 | **4天** | ERP代码规范，逆向引擎直接跑 |
| **总计** | **2周+4天=18天** | V1的18天估算在Spike后证明可行 |

---

## 六、V3 vs V1 vs V2对比

| 维度 | V1 | V2 | V3 |
|------|-----|-----|-----|
| TS逆向 | 正则（被批评） | ts-morph（过度设计） | **正则+Spike验证** |
| App Router门禁 | 无 | router_conventions.yml | **+Server Actions+middleware.ts** |
| Prisma管控 | 只要求引用spec | schema diff+migration | **+prisma migrate diff CLI** |
| 环境变量 | 无 | 一致性检查（误报） | **齐全性+格式检查** |
| Spike | 无 | 计划1周 | **已完成** |
| 工期 | 18天 | 4-5周 | **18天（Spike验证后）** |
| 投票 | 20分/0 APPROVE | 26分/2 APPROVE | **待投** |

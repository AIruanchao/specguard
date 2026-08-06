# SpecGuard ERP接入方案 V2.0（4模型盲审修正版）

> **V1→V2修正**: 4模型盲审均分20.0/35，0 APPROVE 1 BLOCK → 3项致命缺陷逐条修正
> **核心改动**: ts-morph替代正则 / App Router文件约定门禁 / Spike先行 / 工期重估

---

## V1→V2 修正摘要

| # | V1致命缺陷 | 模型一致度 | V2修正 |
|---|-----------|-----------|--------|
| ① | TS逆向引擎用正则=把TS当Python写 | 4/4一致 | **ts-morph（TS Compiler API封装）替代正则** |
| ② | Next.js App Router文件路由未管控 | 4/4一致 | **文件约定门禁（page.tsx/layout.tsx/route.ts有特殊语义）** |
| ③ | 2周V1.5工期严重低估 | 3/4一致 | **改为Spike(1周)→评估→定工期** |
| ④ | Prisma迁移管控太浅 | 2/4 | **schema diff+migration规范+破坏性变更检测** |
| ⑤ | 环境变量治理缺失 | 2/4 | **.env/NEXTAUTH_URL/DATABASE_URL一致性检查** |
| ⑥ | WSL编译约束时机错误 | 1/4(Claude) | **从prebuild脚本改为SpecGuard门禁检查** |

---

## 一、TS逆向引擎重设计（ts-morph方案）

### V1问题：正则提取

```python
# V1（被BLOCK）
findings = {
    "components": re.findall(r'function\s+(\w+)\s*\(', content),  # ❌ 无法区分React组件/普通函数/Server Component
    "types": re.findall(r'interface\s+(\w+)', content),            # ❌ 无法提取继承关系/泛型/联合类型
}
```

Claude-S4.5精准批评："把TypeScript当Python写了"

### V2方案：ts-morph

```typescript
// V2 — 通过Node.js子进程调用ts-morph
// specguard/app/services/ts_reverse_engine.ts

import { Project, SyntaxKind, StructureType } from "ts-morph";

export function analyzeTypeScript(filePath: string): AnalysisResult {
  const project = new Project({ tsConfigFilePath: "./tsconfig.json" });
  const sourceFile = project.addSourceFileAtPath(filePath);

  // 1. React组件提取（区分Server/Client Component）
  const components = sourceFile.getFunctions()
    .filter(f => isReactComponent(f))
    .map(f => ({
      name: f.getName() || "anonymous",
      isServer: !hasUseClientDirective(sourceFile),  // "use client"检测
      isClient: hasUseClientDirective(sourceFile),
      props: extractPropsType(f),                     // ts-morph类型推导
      hooks: extractHooksUsed(f),                     // useState/useEffect/useMemo...
    }));

  // 2. Next.js App Router约定文件检测
  const fileName = path.basename(filePath);
  const routerRole = detectRouterRole(fileName);      // page.tsx→"page" / layout.tsx→"layout" / route.ts→"api"

  // 3. API Route提取（GET/POST/PUT/DELETE导出函数）
  const apiHandlers = sourceFile.getFunctions()
    .filter(f => ["GET","POST","PUT","DELETE","PATCH"].includes(f.getName() || ""))
    .map(f => ({
      method: f.getName(),
      isAsync: f.isAsync(),
      params: extractParams(f),                       // ts-morph参数类型
      returnType: f.getReturnType().getText(),         // 推导返回类型
    }));

  // 4. Prisma Model引用检测
  const prismaCalls = sourceFile.getDescendantsOfKind(SyntaxKind.CallExpression)
    .filter(call => call.getText().includes("prisma."))
    .map(call => ({
      model: extractPrismaModel(call),                 // prisma.user.findMany → model="user"
      operation: extractPrismaOperation(call),          // findMany/create/update/delete
    }));

  // 5. TypeScript类型系统完整提取
  const interfaces = sourceFile.getInterfaces().map(i => ({
    name: i.getName(),
    properties: i.getProperties().map(p => ({
      name: p.getName(),
      type: p.getType().getText(),                     // 完整类型推导（含泛型/联合）
      optional: p.hasQuestionToken(),
    })),
    extends: i.getExtends().map(e => e.getText()),     // 继承关系
  }));

  // 6. import依赖图（含类型导入）
  const imports = sourceFile.getImportDeclarations().map(imp => ({
    source: imp.getModuleSpecifierValue(),
    namedImports: imp.getNamedImports().map(n => n.getName()),
    defaultImport: imp.getDefaultImport()?.getText(),
    isTypeOnly: imp.isTypeOnly(),                      // import type vs import
  }));

  return classifyFindings({
    components, routerRole, apiHandlers, prismaCalls, interfaces, imports
  });
}
```

### ts-morph vs 正则 对比

| 能力 | 正则(V1) | ts-morph(V2) |
|------|---------|-------------|
| 区分Server/Client Component | ❌ | ✅ "use client"指令检测 |
| 类型推导（含泛型/联合） | ❌ | ✅ getType().getText() |
| Prisma调用提取 | ❌ 只能grep "prisma." | ✅ CallExpression AST精确提取 |
| 继承关系 | ❌ | ✅ getExtends() |
| import类型导入区分 | ❌ | ✅ isTypeOnly() |
| App Router约定文件 | ❌ | ✅ 文件名→路由角色映射 |
| 依赖 | 零 | Node.js + ts-morph npm包 |

---

## 二、Next.js App Router文件约定门禁

### V1问题：module_paths.json只有路径glob

Claude-S4.5指出："page.tsx/layout.tsx/route.ts有特殊语义，module_paths的glob无法表达"

### V2方案：文件约定规则引擎

```yaml
# specguard/app/data/router_conventions.yml
rules:
  - pattern: "src/app/**/page.tsx"
    role: "page"
    constraints:
      - "必须导出default React Component"
      - "Server Component（无'use client'）除非显式标记"
    spec_required: "domain-spec/{module}/page-spec.md"
    
  - pattern: "src/app/**/layout.tsx"
    role: "layout"
    constraints:
      - "必须导出default React Component"
      - "必须接收children prop"
      - "Server Component（禁止'use client'）"
    spec_required: "domain-spec/{module}/layout-spec.md"
    
  - pattern: "src/app/api/**/route.ts"
    role: "api-route"
    constraints:
      - "必须导出至少一个HTTP方法（GET/POST/PUT/DELETE/PATCH）"
      - "每个导出函数必须标注请求/响应类型"
    spec_required: "domain-spec/{module}/api-spec.md"
    
  - pattern: "src/app/**/loading.tsx"
    role: "loading"
    constraints:
      - "必须导出default React Component"
    spec_required: false  # 不需要独立Spec
    
  - pattern: "src/app/**/error.tsx"
    role: "error-boundary"
    constraints:
      - "必须是Client Component（'use client'）"
      - "必须接收error和reset props"
    spec_required: "domain-spec/{module}/error-spec.md"
    
  - pattern: "prisma/schema.prisma"
    role: "database-schema"
    constraints:
      - "变更必须引用domain-spec/erp-prisma/spec.md"
      - "破坏性变更（删字段/改类型）必须ADR+全团队评审"
    spec_required: "domain-spec/erp-prisma/spec.md"

  - pattern: "prisma/migrations/**"
    role: "database-migration"
    constraints:
      - "migration文件名必须符合YYYYMMDDHHMMSS_description格式"
      - "必须有对应的down.sql或回滚说明"
    spec_required: "domain-spec/erp-prisma/migration-spec.md"
```

### 门禁执行逻辑

```python
def check_router_convention(filepath, changed_files):
    """检查变更文件是否违反App Router约定"""
    for rule in load_router_conventions():
        if match_pattern(filepath, rule["pattern"]):
            # 1. 检查Spec引用
            if rule.get("spec_required"):
                if not has_spec_reference(changed_files, rule["spec_required"]):
                    return FAIL(f"文件 {filepath} 违反约定: 需要 {rule['spec_required']}")
            
            # 2. 检查文件约束（调用ts-morph验证）
            violations = verify_constraints(filepath, rule["constraints"])
            if violations:
                return FAIL(f"文件 {filepath} 约束违反: {violations}")
    
    return PASS
```

---

## 三、Prisma迁移管控深化

### V1问题：只要求"引用spec.md"

GPT-5.4指出："缺少schema diff、migration name规范、破坏性变更识别、回滚检查"

### V2方案：Prisma变更全生命周期管控

```python
def check_prisma_changes(project_path, changed_files):
    """Prisma变更全生命周期检查"""
    debts = []
    
    # 1. schema.prisma变更 → schema diff
    if "prisma/schema.prisma" in changed_files:
        diff = generate_prisma_schema_diff(project_path)
        
        # 破坏性变更检测
        breaking = detect_breaking_changes(diff)
        if breaking:
            for change in breaking:
                if change.type in ("removed_field", "changed_type", "removed_model"):
                    debts.append({
                        "check": "prisma_breaking_change",
                        "severity": "critical",
                        "detail": f"破坏性变更: {change.model}.{change.field} {change.type}",
                        "requires": "ADR + 全团队评审"
                    })
        
        # 关系名一致性检查（PIT-41防护）
        relations = extract_relations(diff)
        for rel in relations:
            if not rel.is_consistent:
                debts.append({
                    "check": "prisma_relation_naming",
                    "severity": "critical", 
                    "detail": f"关系名不一致: {rel.name} (大写定义 vs 小写引用)",
                    "pit": "PIT-41 Prisma关系名大小写崩溃"
                })
    
    # 2. migration文件检查
    migration_files = [f for f in changed_files if f.startswith("prisma/migrations/")]
    for mf in migration_files:
        # 文件名规范
        if not re.match(r'^\d{14}_\w+/', mf):
            debts.append({
                "check": "migration_name",
                "severity": "auto_fixable",
                "detail": f"migration文件名不规范: {mf}"
            })
        
        # 回滚方案存在性
        migration_dir = os.path.dirname(mf)
        if not os.path.exists(os.path.join(project_path, migration_dir, "down.sql")):
            debts.append({
                "check": "migration_rollback",
                "severity": "info",
                "detail": f"migration无回滚方案: {mf}"
            })
    
    return debts
```

### Prisma变更风险等级

| 变更类型 | 风险等级 | 要求 |
|---------|---------|------|
| 新增model/字段 | 🟢 低 | spec.md引用 |
| 新增索引 | 🟢 低 | spec.md引用 |
| 修改字段类型 | 🟡 中 | ADR + 测试 |
| 删除字段/model | 🔴 高 | ADR + 全团队评审 + 回滚方案 |
| 修改关系名 | 🔴 高 | ADR + Prisma Client运行验证（PIT-41） |

---

## 四、环境变量治理

### V1问题：完全缺失

GPT-5.4指出：".env、NEXTAUTH_URL、DATABASE_URL、build-time env和runtime env不一致"

### V2方案：环境变量一致性检查

```python
def check_env_consistency(project_path):
    """检查环境变量跨环境一致性"""
    debts = []
    
    # 关键变量清单
    critical_vars = [
        "DATABASE_URL",
        "NEXTAUTH_URL", 
        "NEXTAUTH_SECRET",
        "BUILD_MACHINE",  # WSL编译约束
    ]
    
    # 收集各环境的值
    envs = {}
    for env_file in [".env", ".env.local", ".env.production", ".env.example"]:
        path = os.path.join(project_path, env_file)
        if os.path.exists(path):
            envs[env_file] = parse_env_file(path)
    
    # 检查一致性
    for var in critical_vars:
        values = {f: e.get(var) for f, e in envs.items() if var in e}
        unique_values = set(v for v in values.values() if v)
        
        if len(unique_values) > 1:
            debts.append({
                "check": "env_inconsistency",
                "severity": "critical",
                "detail": f"{var} 在不同环境不一致: {values}"
            })
        
        # .env.example必须包含所有关键变量
        if var not in envs.get(".env.example", {}):
            debts.append({
                "check": "env_example_missing",
                "severity": "auto_fixable",
                "detail": f".env.example缺少 {var}"
            })
    
    return debts
```

---

## 五、WSL编译约束修正

### V1问题：prebuild脚本在cloud4上exit 1

Claude-S4.5指出："会导致GitHub Actions/systemd自动部署全崩"

### V2方案：SpecGuard门禁层检查（非运行时阻断）

```python
# 不在prebuild脚本里exit 1
# 改为SpecGuard门禁检查Dockerfile/部署脚本中是否有WSL编译步骤

def check_build_constraint(changed_files):
    """检查编译约束在SpecGuard门禁层"""
    debts = []
    
    # 如果修改了Dockerfile或部署脚本
    deploy_files = [f for f in changed_files if f in ("Dockerfile", "deploy.sh", ".github/workflows/deploy.yml")]
    
    for f in deploy_files:
        content = read_file(f)
        # 检查是否在非WSL环境执行了next build
        if "next build" in content and "WSL" not in content and "wsl" not in content.lower():
            debts.append({
                "check": "build_machine",
                "severity": "critical",
                "detail": f"{f}中next build未标注WSL环境约束",
                "constraint": "BUILD_MACHINE=wsl (ERP编译铁律)"
            })
    
    return debts
```

---

## 六、Spike计划（V1.5前置验证）

### 模型共识：先验证再全量推进

GPT-5.6Luna(BLOCK)："必须先完成受控Spike和安全架构补全后再接入生产"

### Spike范围（1周）

| 天 | 任务 | 验证目标 | Pass标准 |
|----|------|---------|---------|
| 1 | ts-morph安装+对ERP真实代码跑analyze | TS逆向引擎能否提取React组件/Prisma调用/类型 | ≥80%准确率 |
| 2 | App Router约定门禁验证 | page.tsx/route.ts/layout.tsx变更能否正确检测 | 0误报0漏报 |
| 3 | jest --coverage集成验证 | ERP jest覆盖率能否被SpecGuard解析 | JSON报告解析成功 |
| 4 | Prisma schema diff验证 | 破坏性变更检测是否可靠 | 手动删字段→正确检出 |
| 5 | ERP逆向引擎真实跑（1个A级模块） | 从erp-auth代码→spec.md完整生成 | spec.md通过人工核验 |
| 6-7 | Spike报告+V1.5工期重估 | 基于Spike数据定真实工期 | 5模型投票通过 |

### Spike Pass/Fail标准

| 指标 | Pass | Fail |
|------|------|------|
| ts-morph组件提取准确率 | ≥80% | <80% → 需要更强方案 |
| App Router门禁误报率 | ≤5% | >5% → 规则需要调优 |
| jest覆盖率解析 | 成功 | 失败 → 需要替代方案 |
| Prisma diff检测 | 可靠 | 不可靠 → 需要prisma migrate diff |
| 真实逆向spec.md质量 | 人工核验通过 | 不通过 → 引擎需优化 |

---

## 七、修正后路线图

| 版本 | 功能 | 时间 | 前置条件 |
|------|------|------|---------|
| **Spike** | TS逆向+App Router+jest+Prisma验证 | **1周** | 本方案投票通过 |
| V1.5 | 多项目+TS支持（基于Spike数据） | **Spike后定** | Spike全Pass |
| V1.6 | ERP接入（sdd/目录+门禁+逆向） | **4天** | V1.5完成 |
| V2.0 | GitHub App+多语言扩展 | 2周 | V1.6稳定 |

**关键变化：V1的"2周V1.5+4天接入" → V2的"Spike 1周→评估→定工期"**

---

## 八、修正后工期估算

| V1估算 | V2估算 | 理由 |
|--------|--------|------|
| V1.5: 2周 | V1.5: 3-4周(Spike后定) | ts-morph集成+App Router门禁+Prisma管控远比Python复杂 |
| 接入: 4天 | 接入: 5-7天 | Next.js项目结构+Prisma迁移历史+环境变量比商务系统复杂 |
| **总计: 18天** | **总计: 4-5周** | 诚实估算 |

---

## 九、修正后的ERP模块风险矩阵（不变）

V1的8模块分级在V2中保持不变（GPT-5.4和GLM-5.2都给了≥4分）。

---

## 投票结果透明披露

| 模型 | V1总分 | V1结论 | V1主要问题 |
|------|--------|--------|-----------|
| GLM-5.2 | 26/35 | CONCERNS | TS逆向过于理想化 |
| GPT-5.6Luna | 19/35 | BLOCK | 不成熟工具放进强门禁 |
| Claude-S4.5 | 18/35 | CONCERNS | "把TS当Python写" |
| GPT-5.4 | 17/35 | CONCERNS | 工期估轻+约束不完整 |

**V1均分20.0/35 (🟡偏低) → V2已逐条修正6项问题。**

# SpecGuard ERP接入方案 V1.0

> **目标**: 七色米ERP（Next.js全栈）接入SpecGuard SDD治理
> **前提**: SpecGuard V1.5多项目+多语言支持
> **项目**: MacMini 10.31.1.177:3000(dev) + Cloud4 124.222.170.89:3000(prod)

---

## 一、ERP现状

| 维度 | 现状 |
|------|------|
| 技术栈 | Next.js 15 + Prisma + PostgreSQL |
| AI参与 | ✅ Cursor写代码 + CC审计 |
| 测试 | bats 12/12 + 部分jest |
| SDD | ❌ 未接入 |
| 部署 | dev=MacMini / prod=Cloud4 |
| 编译 | CCC WSL(10.31.1.203)编译→Cloud4部署 |

### ERP的AI编码风险

| 风险 | 证据 | SDD解法 |
|------|------|---------|
| Cursor即兴编码 | ERP历史42个bug(DH Pipeline实测) | Spec先行，PR无Spec拒绝 |
| 修A坏B | P7.5:277按钮中27.2%死按钮 | Spec门禁+零欠项检查 |
| 编译必须在WSL | cloud4本地build=OOM | Spec标注BUILD_MACHINE约束 |
| Prisma schema变更无管控 | 关系名大小写崩溃(PIT-41) | domain-spec/schema.md + 迁移Spec |

---

## 二、SpecGuard改造需求（V1.0→V1.5）

### 2.1 多语言适配

| 当前(仅Python) | V1.5(+Next.js) |
|----------------|----------------|
| module_paths.json: `app/services/*.py` | + `src/app/**/*.tsx` `src/lib/**/*.ts` |
| 逆向引擎: Python `ast` | + TypeScript `ts-morph`或正则提取 |
| pytest --cov | + `jest --coverage` |
| py_compile语法检查 | + `tsc --noEmit`类型检查 |
| bandit安全扫描 | + `eslint --security` |

### 2.2 module_paths.json扩展

```json
{
  "erp-inventory": [
    "src/app/inventory/**/*.tsx",
    "src/lib/inventory/**/*.ts",
    "prisma/schema.prisma:model Inventory"
  ],
  "erp-sales": [
    "src/app/sales/**/*.tsx",
    "src/lib/sales/**/*.ts"
  ],
  "erp-auth": [
    "src/app/api/auth/**/*.ts",
    "src/lib/auth.ts"
  ],
  "erp-prisma": [
    "prisma/schema.prisma",
    "prisma/migrations/**"
  ]
}
```

### 2.3 ERP模块风险矩阵

| 模块 | 完整性 | 文件 | 输入 | 权限 | 追责 | 关键性 | 频度 | 总分 | 级别 |
|------|--------|------|------|------|------|--------|------|------|------|
| erp-auth | 5 | 1 | 4 | 5 | 5 | 4 | 2 | 3.80 | A |
| erp-prisma | 5 | 1 | 2 | 3 | 5 | 5 | 2 | 3.60 | A |
| erp-inventory | 4 | 2 | 4 | 3 | 4 | 5 | 4 | 3.70 | A |
| erp-sales | 4 | 2 | 4 | 3 | 4 | 5 | 4 | 3.70 | A |
| erp-customers | 3 | 1 | 3 | 2 | 3 | 3 | 2 | 2.45 | B |
| erp-suppliers | 3 | 1 | 3 | 2 | 3 | 3 | 2 | 2.45 | B |
| erp-dashboard | 2 | 1 | 2 | 1 | 2 | 3 | 2 | 1.90 | B |
| erp-settings | 1 | 1 | 2 | 3 | 2 | 2 | 1 | 1.65 | C |

### 2.4 ERP特有的Spec约束

```yaml
# sdd/enterprise-spec/erp-constraints.md
erp_build_constraint:
  rule: "next build必须在CCC WSL(10.31.1.203)执行"
  reason: "Cloud4 4C/8G build会OOM"
  enforcement: "prebuild脚本检测hostname, cloud4上exit 1"
  spec_required: true

erp_prisma_constraint:
  rule: "Prisma schema变更必须走Spec→ADR→migration流程"
  reason: "关系名大小写/迁移遗漏=PIT-41级崩溃"
  enforcement: "prisma/migrations/路径变更→必须引用domain-spec/erp-prisma/spec.md"
  spec_required: true

erp_deploy_constraint:
  rule: "生产部署必须是next start, 禁止next dev"
  reason: "next dev无优化+热重载=性能灾难"
  enforcement: "systemd ExecStart检查"
  spec_required: true
```

---

## 三、ERP SDD目录结构

```
七色米ERP/
├── sdd/
│   ├── enterprise-spec/
│   │   ├── constitution.md          # ERP宪法（复用商务系统的+ERP约束）
│   │   ├── security-baseline.md     # 安全基线（NextAuth+Prisma注入防护）
│   │   ├── error-codes.md           # ERP错误码
│   │   ├── risk-matrix.md           # ERP模块风险矩阵
│   │   └── erp-constraints.md       # ERP特有约束(build/prisma/deploy)
│   ├── domain-spec/
│   │   ├── erp-auth/                # A级: NextAuth鉴权
│   │   ├── erp-prisma/              # A级: 数据模型
│   │   ├── erp-inventory/           # A级: 库存
│   │   ├── erp-sales/               # A级: 销售
│   │   ├── erp-customers/           # B级
│   │   ├── erp-suppliers/           # B级
│   │   └── erp-state-machine.md     # 跨模块状态机(库存→销售→出库)
│   ├── change-log/
│   ├── test-cases/
│   ├── CONTEXT.md                   # ERP术语词典
│   ├── ADR/
│   │   ├── ADR-001-nextjs-prisma.md # 为什么选Next.js+Prisma
│   │   ├── ADR-002-sqlite-to-pg.md  # SQLite→PostgreSQL迁移决策
│   │   └── ADR-003-build-wsl.md     # WSL编译决策
│   └── template/
│       ├── spec-template-ears.md    # 复用商务系统模板
│       └── spec-template-bdd.md     # 复用商务系统模板
├── .github/
│   └── workflows/
│       └── sdd-gate.yml             # SpecGuard GitHub Actions
└── prisma/
    └── migrations/                   # 已有，纳入Spec管控
```

---

## 四、SpecGuard改造清单（V1.0→V1.5）

### 4.1 后端改造

| 文件 | 改动 | 说明 |
|------|------|------|
| `app/config.py` | +`MANAGED_PROJECTS`支持多项目 | 每个项目独立配置 |
| `app/routers/gate.py` | +TS文件匹配(`.ts/.tsx`) | module_paths支持glob |
| `app/routers/coverage.py` | +`jest --coverage`支持 | 检测jest.config.js→用jest |
| `app/routers/reverse.py` | +TypeScript逆向 | 正则提取React组件/Prisma model |
| `app/services/reverse_engine.py` | +`analyze_typescript()`方法 | ts-morph或正则方案 |
| `app/data/module_paths.json` | +ERP模块映射 | 多项目配置 |

### 4.2 多项目API

```
GET  /api/v1/projects                    # 项目列表
POST /api/v1/projects                    # 注册项目
GET  /api/v1/{project}/coverage          # 指定项目覆盖率
POST /api/v1/{project}/gate/check        # 指定项目门禁检查
POST /api/v1/{project}/reverse/analyze   # 指定项目逆向分析
```

### 4.3 TypeScript逆向引擎

```python
def analyze_typescript(filepath: str) -> dict:
    """分析TypeScript/TSX文件"""
    content = read_file(filepath)
    
    findings = {
        "components": re.findall(r'(?:export\s+)?(?:default\s+)?function\s+(\w+)\s*\(', content),
        "hooks": re.findall(r'export\s+(?:async\s+)?function\s+(use\w+)\s*\(', content),
        "api_routes": re.findall(r'export\s+(?:async\s+)?function\s+(GET|POST|PUT|DELETE|PATCH)\s*\(', content),
        "prisma_models": re.findall(r'model\s+(\w+)\s*\{', content),
        "imports": re.findall(r'import\s+.*?from\s+[\'"]([^\'"]+)', content),
        "types": re.findall(r'(?:export\s+)?(?:interface|type)\s+(\w+)', content),
    }
    
    return classify_findings(findings)
```

### 4.4 覆盖率适配

```python
def get_coverage_tool(project_path):
    """自动检测覆盖率工具"""
    if exists(project_path / "jest.config.js"):
        return "jest", ["npx", "jest", "--coverage", "--json"]
    elif exists(project_path / "pytest.ini"):
        return "pytest", ["python", "-m", "pytest", "--cov"]
    else:
        return None, []
```

---

## 五、接入步骤（SpecGuard V1.5完成后）

| 步骤 | 动作 | 时间 |
|------|------|------|
| 1 | SpecGuard V1.5多项目+TS支持 | 2周 |
| 2 | ERP创建sdd/目录+CONTEXT.md+constitution | 0.5天 |
| 3 | ERP逆向引擎跑一次（Prisma schema→spec.md） | 0.5天 |
| 4 | 4个A级模块spec.md逆向生成+人工核验 | 2天 |
| 5 | ERP GitHub Actions sdd-gate.yml部署 | 0.5天 |
| 6 | ERP Cursor/Coder PR门禁验证 | 1天 |
| 7 | 生产Cloud4同步sdd/目录 | 0.5天 |

**总计: SpecGuard V1.5开发2周 + ERP接入4天**

---

## 六、ERP Cursor编码红线

接入SDD后，ERP的Cursor编码流程：

```
Cursor写代码
  ↓
PR提交
  ↓
SpecGuard门禁检查
  ├── 有Spec引用 → ✅ 通过
  ├── 无Spec引用 → ❌ 拒绝（A级strict）
  └── hotfix标签 → ⚠️ 豁免（72h补Spec）
  ↓
零欠项检查（编排器Phase 7.5）
  ├── git clean + 测试全绿 + push → ✅
  └── 有欠项 → 🔧 自动修复/重派coder
  ↓
CC审计（A级模块）
  ↓
部署到Cloud4
```

---

## 七、与商务系统的复用

| 资产 | 商务系统已有 | ERP复用方式 |
|------|-------------|------------|
| constitution.md | ✅ | 复用+加ERP约束 |
| security-baseline.md | ✅ | 复用+加NextAuth安全 |
| spec-template-ears.md | ✅ | 直接复用 |
| spec-template-bdd.md | ✅ | 直接复用 |
| risk-matrix评分标准 | ✅ | 直接复用 |
| spec_gate.py核心逻辑 | ✅ | 多项目配置化 |
| 逆向引擎Python部分 | ✅ | 直接复用 |
| 逆向引擎TS部分 | ❌ | 新开发 |

**复用率: 70%**，30%需要新开发（TS逆向+jest覆盖率+多项目API）。

---

## 八、投票验证（待V1.5完成后）

此方案需在SpecGuard V1.5开发完成后，用5模型投票验证：
1. TS逆向引擎可靠性
2. 多项目API设计合理性
3. ERP模块风险矩阵准确性
4. 接入步骤可行性

# ERP + DH工厂 SDD部署方案 V1.0

> **目标**: 七色米ERP + DH企业工厂 接入SpecGuard SDD治理
> **前提**: SpecGuard V1.0(Python) + V1.5(TS)已完成，本机launchd常驻运行

---

## 一、DH企业工厂 SDD部署（Python项目，SpecGuard直接可用）

### 1.1 DH工厂现状

| 维度 | 值 |
|------|-----|
| 技术栈 | Python + Shell + YAML |
| AI参与 | ✅ Cursor+CC |
| Python文件 | 57个 |
| Gate脚本 | 37个(G00-G38) |
| 管理项目 | 7个(doc-generator/erp/tz/memservice/qdrant) |
| pytest | ✅ 已有 |
| 测试 | test_factory.py |
| SDD | ❌ 未部署 |

### 1.2 DH工厂模块风险矩阵

| 模块 | 完整性 | 文件 | 输入 | 权限 | 追责 | 关键性 | 频度 | 总分 | 级别 |
|------|--------|------|------|------|------|--------|------|------|------|
| orchestrator/ (编排核心) | 5 | 1 | 4 | 3 | 5 | 5 | 4 | **4.10** | A |
| ops_executor.py (运维执行) | 5 | 1 | 3 | 4 | 5 | 5 | 3 | **4.00** | A |
| lib/dh_lib.py (核心库) | 5 | 1 | 2 | 2 | 4 | 5 | 3 | **3.55** | A |
| vote/vote_gate.py (投票) | 4 | 1 | 3 | 2 | 5 | 4 | 3 | **3.40** | A |
| gates/ (37个门禁脚本) | 4 | 1 | 3 | 3 | 5 | 5 | 2 | **3.60** | A |
| dispatch_api.py (调度API) | 4 | 1 | 5 | 3 | 4 | 4 | 4 | **3.85** | A |
| smart_engine.py | 3 | 1 | 3 | 2 | 3 | 4 | 3 | **2.85** | B |
| btn-full-auto.py | 3 | 1 | 3 | 1 | 3 | 3 | 3 | **2.55** | B |
| ceiling_v4_flow.py | 3 | 1 | 2 | 1 | 3 | 4 | 2 | **2.40** | B |

### 1.3 DH工厂SDD目录结构

```
/opt/dh-enterprise-factory/
├── sdd/
│   ├── enterprise-spec/
│   │   ├── constitution.md          # DH工厂宪法
│   │   ├── security-baseline.md     # 安全基线(LLM调用+SSH+文件操作)
│   │   ├── error-codes.md           # DH错误码
│   │   └── risk-matrix.md           # 模块风险矩阵
│   ├── domain-spec/
│   │   ├── orchestrator/            # A级: 编排核心
│   │   ├── ops-executor/            # A级: 运维执行器
│   │   ├── dh-lib/                  # A级: 核心库
│   │   ├── vote-gate/               # A级: 多模型投票
│   │   ├── gates/                   # A级: 37门禁脚本
│   │   └── dispatch-api/            # A级: 调度API
│   ├── change-log/
│   ├── test-cases/
│   ├── CONTEXT.md                   # DH术语词典
│   ├── ADR/
│   │   ├── ADR-001-dh-factory.md    # 为什么建DH工厂
│   │   ├── ADR-002-gate-system.md   # 37门禁设计
│   │   └── ADR-003-orchestrator.md  # 编排器架构
│   └── template/                    # 复用商务系统模板
├── .github/workflows/
│   └── sdd-gate.yml                 # SpecGuard GitHub Actions
└── (现有代码不动)
```

### 1.4 DH工厂module_paths.json

```json
{
  "orchestrator": [
    "orchestrator/dispatch_api.py",
    "orchestrator/smart_engine.py",
    "orchestrator/archive/orchestrator.py"
  ],
  "ops-executor": [
    "ops_executor.py"
  ],
  "dh-lib": [
    "lib/dh_lib.py"
  ],
  "vote-gate": [
    "vote/vote_gate.py"
  ],
  "gates": [
    "gates/G00_meta_gate.sh",
    "gates/G01_project_preflight.sh",
    "gates/G02_build_gate.sh",
    "gates/G03_lint_type_gate.sh",
    "gates/G04_unit_gate.sh",
    "gates/G05_coverage_gate.sh",
    "gates/G06_security_gate.sh",
    "gates/G13_deploy_gate.sh"
  ],
  "dispatch-api": [
    "orchestrator/dispatch_api.py"
  ]
}
```

### 1.5 DH工厂接入步骤（3天）

| 天 | 动作 |
|----|------|
| 1 | 创建sdd/目录 + constitution + CONTEXT + 风险矩阵 + module_paths.json |
| 2 | 逆向引擎跑6个A级模块 → spec.md草稿 + 人工核验 |
| 3 | GitHub Actions sdd-gate.yml部署 + Cursor PR门禁验证 |

---

## 二、七色米ERP SDD部署（Next.js项目，SpecGuard V1.5支持）

### 2.1 ERP现状（Spike已验证）

| 维度 | 值 |
|------|-----|
| 技术栈 | Next.js 15 + Prisma + PostgreSQL |
| AI参与 | ✅ Cursor+CC |
| Prisma models | 271个 |
| API Route | 10+个 |
| Page文件 | 10+个 |
| 测试 | vitest + Playwright |
| 代码位置 | MacMini 10.31.1.177:/Users/mac/erp-project |
| Spike | ✅ 6项验证完成(5项100%准确) |
| V1.5 TS引擎 | ✅ 32测试全过 |

### 2.2 ERP模块风险矩阵（V3方案已定义）

8个模块：4个A级(auth/prisma/inventory/sales) + 3个B级(customers/suppliers/dashboard) + 1个C级(settings)。

### 2.3 ERP SDD目录结构

```
/Users/mac/erp-project/ (MacMini)
├── sdd/
│   ├── enterprise-spec/
│   │   ├── constitution.md
│   │   ├── security-baseline.md     # NextAuth+Prisma注入+XSS
│   │   ├── error-codes.md
│   │   ├── risk-matrix.md
│   │   └── erp-constraints.md       # WSL编译/Prisma/部署约束
│   ├── domain-spec/
│   │   ├── erp-auth/                # A级
│   │   ├── erp-prisma/              # A级
│   │   ├── erp-inventory/           # A级
│   │   ├── erp-sales/               # A级
│   │   ├── erp-customers/           # B级
│   │   ├── erp-state-machine.md     # 跨模块状态机
│   │   └── router-conventions.yml   # App Router文件约定门禁
│   ├── change-log/
│   ├── test-cases/
│   ├── CONTEXT.md
│   ├── ADR/
│   └── template/
├── .github/workflows/
│   └── sdd-gate.yml
└── (现有代码不动)
```

### 2.4 ERP接入步骤（4天）

| 天 | 动作 |
|----|------|
| 1 | SSH MacMini创建sdd/目录 + constitution + erp-constraints + 风险矩阵 |
| 2 | TS逆向引擎跑4个A级模块(SSH拉代码→本地分析→生成spec.md→推回MacMini) |
| 3 | router-conventions.yml配置 + GitHub Actions sdd-gate.yml |
| 4 | Cursor PR门禁验证 + 生产Cloud4同步 |

### 2.5 ERP特有约束（V3方案已定义）

- **WSL编译约束**: next build必须在CCC WSL(10.31.1.203)
- **Prisma迁移管控**: 破坏性变更=ADR+全团队评审
- **环境变量治理**: 齐全性+格式检查(不检查值一致性)
- **Server Actions门禁**: "use server"指令+副作用标注
- **middleware.ts门禁**: 鉴权/重定向=高风险

---

## 三、SpecGuard注册两个项目

```bash
# DH工厂
curl -X POST http://127.0.0.1:8700/api/v1/specs/register \
  -d '{"project": "dh-factory", "path": "/opt/dh-enterprise-factory"}'

# 七色米ERP
curl -X POST http://127.0.0.1:8700/api/v1/specs/register \
  -d '{"project": "erp-qisemi", "path": "/Users/mac/erp-project"}'
```

---

## 四、复用资产

| 资产 | 来源 | DH复用 | ERP复用 |
|------|------|--------|---------|
| constitution.md | 商务系统 | ✅ 复用+DH约束 | ✅ 复用+ERP约束 |
| security-baseline.md | 商务系统 | ✅ 复用 | ✅ 复用+NextAuth |
| spec-template-ears.md | 商务系统 | ✅ 直接 | ✅ 直接 |
| spec-template-bdd.md | 商务系统 | ✅ 直接 | ✅ 直接 |
| risk-matrix评分标准 | 商务系统 | ✅ 直接 | ✅ 直接 |
| spec_gate.py | SpecGuard | ✅ 配置化 | ✅ 配置化 |
| Python逆向引擎 | SpecGuard V0.3 | ✅ 直接 | ❌ 用TS引擎 |
| TS逆向引擎 | SpecGuard V1.5 | ❌ | ✅ 直接 |

**DH复用率: 80%**（纯Python，和商务系统同栈）
**ERP复用率: 70%**（Next.js需要TS引擎+router-conventions）

---

## 五、工期

| 项目 | 工期 | 前置 |
|------|------|------|
| DH工厂 | **3天** | SpecGuard V1.0(已完成) |
| 七色米ERP | **4天** | SpecGuard V1.5(已完成) |
| **总计** | **7天** | 可并行 |

---

## 六、投票验证

此方案需5模型投票验证：
1. DH工厂模块风险矩阵准确性
2. ERP接入步骤可行性
3. 工期估算
4. 复用率

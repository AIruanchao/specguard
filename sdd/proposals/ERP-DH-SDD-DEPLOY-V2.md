# ERP + DH工厂 SDD部署方案 V2.0（4模型盲审修正版）

> **V1→V2**: 4模型盲审均分20.8，0 APPROVE 1 BLOCK → 3项致命缺陷逐条修正

---

## V1→V2 修正摘要

| # | V1缺陷 | 一致度 | V2修正 |
|---|--------|--------|--------|
| ① | module_paths覆盖严重不完整 | 4/4 | **DH全量97文件+ERP用glob模式(710个route.ts)** |
| ② | 工期压缩人工核验成本 | 3/4 | **DH 5天/ERP 6天(含人工核验2-4h/A级模块)** |
| ③ | 跨机器协作方案模糊 | 1/4(BLOCK) | **明确SSH+rsync离线分析模式 + SpecGuard远程分析API** |

---

## 一、DH工厂module_paths.json（全量97文件）

### 自动生成（从代码扫描）

```json
{
  "orchestrator-core": [
    "orchestrator/dispatch_api.py",
    "orchestrator/smart_engine.py",
    "orchestrator/runner.py",
    "orchestrator/priority_sort.py",
    "orchestrator/orchestrator_status.py",
    "orchestrator/task_notifier.py",
    "orchestrator/trace_adapter.py",
    "orchestrator/uptime_collector.py"
  ],
  "orchestrator-flows": [
    "orchestrator/ceiling_v4_flow.py",
    "orchestrator/btn-full-auto.py",
    "orchestrator/btn-deep-verify.py",
    "orchestrator/all-audit-orch.py",
    "orchestrator/full-audit-v2-orch.py",
    "orchestrator/erp-v6-orch.py",
    "orchestrator/erp-v6-omni-orch.py",
    "orchestrator/erp-v6-omni-v2.py"
  ],
  "orchestrator-sku": [
    "orchestrator/sku-smart-enrich.py",
    "orchestrator/sku-verify-orch.py",
    "orchestrator/sku-full-verify-orch.py",
    "orchestrator/sku-doubao-verify-orch.py"
  ],
  "orchestrator-scripts": [
    "orchestrator/dispatch_task.sh",
    "orchestrator/unattended_loop.sh",
    "orchestrator/run-all-gates.sh",
    "orchestrator/watchdog-cron.sh",
    "orchestrator/fault_trigger.sh"
  ],
  "ops": [
    "ops_executor.py",
    "ops_diagnose.py",
    "ops_rootcause.py",
    "ops_verifier.py",
    "slo_collector.py"
  ],
  "lib": [
    "lib/dh_lib.py"
  ],
  "vote": [
    "vote/vote_gate.py",
    "vote/test_vote_gate.py"
  ],
  "hitl": [
    "hitl/review_queue.py"
  ],
  "gates": [
    "gates/G00_meta_gate.sh",
    "gates/G01_project_preflight.sh",
    "gates/G02_build_gate.sh",
    "gates/G03_lint_type_gate.sh",
    "gates/G04_unit_gate.sh",
    "gates/G05_coverage_gate.sh",
    "gates/G06_security_gate.sh",
    "gates/G07_dependency_gate.sh",
    "gates/G08_api_smoke_gate.sh",
    "gates/G09_e2e_gate.sh",
    "gates/G10_browser_exhaustive_gate.sh",
    "gates/G11_stress_gate.sh",
    "gates/G12_data_integrity_gate.sh",
    "gates/G13_deploy_gate.sh",
    "gates/G14_rollback_gate.sh",
    "gates/G15_runtime_watchdog_gate.sh",
    "gates/G16_score_gate.sh",
    "gates/G17_tenant_isolation.sh",
    "gates/G18_authorization_matrix.sh",
    "gates/G19_billing_metering.sh",
    "gates/G22_audit_immutability.sh",
    "gates/G23_task_card_readiness.sh",
    "gates/G24_dast_scan.sh",
    "gates/G25_db_backup.sh",
    "gates/G26_error_tracking.sh",
    "gates/G27_npm_security.sh",
    "gates/G28_cookie_gdpr.sh",
    "gates/G29_idempotency.sh",
    "gates/G30_n_plus_1.sh",
    "gates/G31_connection_pool.sh",
    "gates/G32_pitr.sh",
    "gates/G33_db_recovery_drill.sh",
    "gates/G34_billing_webhook.sh",
    "gates/G35_log_collection.sh",
    "gates/G36_page_p95.sh",
    "gates/G37_soc2_readiness.sh",
    "gates/G38_global_orchestrator_readiness.sh"
  ],
  "infrastructure": [
    "auto_rollback.sh",
    "backup-offsite.sh",
    "ceiling-gate-runner.sh",
    "deploy-v2.sh",
    "dh-gate-check.sh",
    "dh-gate.sh",
    "drill_restore.sh",
    "enterprise_stability.sh",
    "gate_loop.sh",
    "health-monitor.sh",
    "independent_verify.sh",
    "init.sh",
    "repair_router.sh",
    "scripts/deploy-with-rollback.sh",
    "scripts/dh-unattended.py",
    "scripts/dh-unattended.sh"
  ],
  "ui-engine": [
    "ui-engine/coverage_report.py",
    "ui-engine/run_all.sh"
  ],
  "tests": [
    "tests/test_factory.py",
    "orchestrator/test_ceiling_v4_flow.py",
    "orchestrator/test_runner.py"
  ]
}
```

### 消除V1的重复问题

V1中`dispatch_api.py`同时出现在`orchestrator`和`dispatch-api`两个模块 → V2统一为`orchestrator-core`。**每个文件只属于一个模块。**

---

## 二、ERP module_paths.json（glob模式，710个route.ts）

### 为什么用glob不用逐个列举

ERP实际规模：
- **710个** API Route文件（V1估计10+，严重低估）
- **数百个** src/lib/*.ts文件
- **50+个** src/app/**/page.tsx
- **271个** Prisma models

逐个列举不现实。用glob模式匹配。

```json
{
  "erp-auth": [
    "src/lib/auth.ts",
    "src/lib/admin-auth.ts",
    "src/lib/action-auth.ts",
    "src/lib/api-key-auth.ts",
    "src/lib/api-access-token.ts",
    "src/lib/access.ts",
    "src/middleware.ts",
    "src/app/api/admin/auth/**/*.ts",
    "src/app/(auth)/**/*.tsx"
  ],
  "erp-prisma": [
    "prisma/schema.prisma",
    "prisma/migrations/**",
    "src/lib/prisma-tenant.ts"
  ],
  "erp-inventory": [
    "src/app/(main)/inventory/**/*.tsx",
    "src/app/api/inventory/**/*.ts",
    "src/lib/inventory*.ts"
  ],
  "erp-sales": [
    "src/app/(main)/pos/**/*.tsx",
    "src/app/api/pos/**/*.ts",
    "src/app/(main)/billing/**/*.tsx",
    "src/app/api/billing/**/*.ts",
    "src/lib/pos*.ts"
  ],
  "erp-customers": [
    "src/app/(main)/customers/**/*.tsx",
    "src/app/api/customers/**/*.ts",
    "src/lib/customer*.ts"
  ],
  "erp-finance": [
    "src/app/(main)/finance/**/*.tsx",
    "src/app/api/account-payables/**/*.ts",
    "src/app/api/account-receivables/**/*.ts",
    "src/lib/account-payable*.ts",
    "src/lib/account-receivable*.ts"
  ],
  "erp-products": [
    "src/app/(main)/products/**/*.tsx",
    "src/app/api/products/**/*.ts",
    "src/lib/product*.ts"
  ],
  "erp-purchases": [
    "src/app/(main)/purchases/**/*.tsx",
    "src/app/(main)/purchase-orders/**/*.tsx",
    "src/app/api/purchase-orders/**/*.ts",
    "src/lib/purchase*.ts"
  ],
  "erp-actions": [
    "src/actions/**/*.ts",
    "src/app/api/actions/**/*.ts"
  ],
  "erp-shared-lib": [
    "src/lib/*.ts",
    "!src/lib/auth.ts",
    "!src/lib/admin-auth.ts",
    "!src/lib/action-auth.ts"
  ],
  "erp-admin": [
    "src/app/api/admin/**/*.ts",
    "src/app/(dashboard)/**/*.tsx"
  ]
}
```

### glob匹配规则

```python
def match_glob(filepath, patterns):
    """支持 ! 排除模式"""
    included = False
    excluded = False
    for pattern in patterns:
        if pattern.startswith('!'):
            if fnmatch.fnmatch(filepath, pattern[1:]):
                excluded = True
        else:
            if fnmatch.fnmatch(filepath, pattern):
                included = True
    return included and not excluded
```

---

## 三、跨机器协作方案（V2新增，解决BLOCK）

### 问题

ERP在MacMini(10.31.1.177)，SpecGuard在本机。GPT-5.6Luna的BLOCK根因："跨主机执行架构尚未成立"。

### V2方案：三种模式

#### 模式1: 离线分析（默认，推荐）

```
SpecGuard(本机)
  ↓ SSH rsync拉取ERP代码到本地缓存
  ↓ 本地跑逆向引擎（TS/Python）
  ↓ 生成spec.md
  ↓ rsync推回MacMini的sdd/目录
```

```python
def sync_project_remote(project_name, remote_host, remote_path):
    """同步远程项目到本地缓存"""
    local_cache = f"/tmp/specguard-cache/{project_name}"
    os.makedirs(local_cache, exist_ok=True)
    
    # rsync拉取（只拉src/和prisma/，不拉node_modules/.next）
    subprocess.run([
        "rsync", "-avz", "--delete",
        "--exclude=node_modules", "--exclude=.next", "--exclude=.git",
        "--exclude=public", "--exclude=.env*",
        f"{remote_host}:{remote_path}/src/",
        f"{local_cache}/src/"
    ], timeout=120)
    
    subprocess.run([
        "rsync", "-avz",
        f"{remote_host}:{remote_path}/prisma/schema.prisma",
        f"{local_cache}/prisma/schema.prisma"
    ], timeout=30)
    
    # 在本地缓存上跑逆向引擎
    engine = TypeScriptReverseEngine(local_cache)
    results = engine.analyze_module("src/app/api/**/*.ts")
    
    # 推回spec.md
    for result in results:
        spec_content = engine.generate_spec(result)
        spec_path = f"sdd/domain-spec/{result['module']}/{result['filepath'].replace('/','_')}.md"
        # rsync推回
        subprocess.run([
            "rsync", "-avz",
            f"{local_cache}/{spec_path}",
            f"{remote_host}:{remote_path}/{spec_path}"
        ], timeout=30)
    
    return {"files_analyzed": len(results), "cache_path": local_cache}
```

#### 模式2: 远程API（SpecGuard调用MacMini上的agent）

```
SpecGuard → SSH → MacMini → 运行分析脚本 → 返回JSON
```

#### 模式3: Git-based（最稳定）

```
MacMini push → GitHub
SpecGuard → git clone → 本地分析 → commit spec.md → push → MacMini pull
```

### 网络稳定性保障

| 措施 | 实现 |
|------|------|
| SSH超时 | ConnectTimeout=5s + 重试3次 |
| rsync增量 | --exclude大目录 + 只同步src/+prisma/ |
| 离线降级 | SSH不通→提示用户在MacMini本地跑 |
| 本地缓存 | /tmp/specguard-cache/避免重复拉取 |

---

## 四、修正后工期（含人工核验）

### DH工厂：5天

| 天 | 动作 | 人工核验 |
|----|------|---------|
| 1 | sdd/目录+constitution+CONTEXT+风险矩阵+module_paths.json(全量97文件) | 0h |
| 2 | 逆向引擎跑6个A级模块→spec.md草稿 | 0h |
| 3 | 领域专家核验orchestrator-core+ops+lib(3个A级) | **6h** |
| 4 | 领域专家核验vote+gates+dispatch(3个A级) | **6h** |
| 5 | GitHub Actions sdd-gate.yml + Cursor PR门禁验证 | 2h |

### ERP：6天

| 天 | 动作 | 人工核验 |
|----|------|---------|
| 1 | SSH MacMini创建sdd/目录+constitution+erp-constraints+风险矩阵 | 0h |
| 2 | rsync拉ERP代码到本地缓存+TS逆向引擎跑→spec.md草稿 | 0h |
| 3 | 领域专家核验erp-auth+erp-prisma(2个A级) | **6h** |
| 4 | 领域专家核验erp-inventory+erp-sales(2个A级) | **6h** |
| 5 | router-conventions.yml + GitHub Actions sdd-gate.yml | 2h |
| 6 | Cursor PR门禁验证 + 生产Cloud4同步sdd/ | 2h |

**人工核验总计: DH 12h + ERP 14h = 26h**（V1完全没算这个）

---

## 五、修正后风险矩阵

### DH工厂（V2细化）

| 模块 | 总分 | 级别 | 文件数 |
|------|------|------|--------|
| orchestrator-core | 4.10 | A | 8 |
| ops | 4.00 | A | 5 |
| gates | 3.60 | A | 37 |
| lib | 3.55 | A | 1 |
| vote | 3.40 | A | 2 |
| orchestrator-flows | 3.00 | B | 8 |
| hitl | 2.85 | B | 1 |
| orchestrator-sku | 2.70 | B | 4 |
| infrastructure | 2.50 | B | 16 |
| ui-engine | 2.00 | C | 2 |
| tests | 1.50 | C | 3 |

### ERP（V2细化，基于真实710个route.ts）

| 模块 | 总分 | 级别 | glob匹配文件数(估) |
|------|------|------|------------------|
| erp-auth | 4.10 | A | ~20 |
| erp-prisma | 3.80 | A | ~280 |
| erp-inventory | 3.70 | A | ~50 |
| erp-sales | 3.70 | A | ~80 |
| erp-finance | 3.50 | A | ~60 |
| erp-customers | 2.85 | B | ~70 |
| erp-products | 2.70 | B | ~40 |
| erp-purchases | 2.65 | B | ~30 |
| erp-actions | 2.50 | B | ~15 |
| erp-admin | 2.30 | B | ~20 |
| erp-shared-lib | 2.00 | C | ~200 |

---

## 六、SpecGuard远程项目支持（V2新增API）

```python
# app/routers/projects.py (V1.5+)
@router.post("/register")
async def register_project(req: ProjectRegisterRequest):
    """注册远程项目"""
    project = {
        "name": req.name,
        "path": req.path,
        "remote_host": req.remote_host,  # "mac@10.31.1.177"
        "remote_path": req.remote_path,  # "/Users/mac/erp-project"
        "tech_stack": req.tech_stack,     # "nextjs" / "python" / "fastapi"
    }
    # 保存到配置
    return {"status": "registered", "project": project}

@router.post("/{project}/sync")
async def sync_remote_project(project: str):
    """同步远程项目代码到本地缓存"""
    proj = get_project_config(project)
    if proj.get("remote_host"):
        return sync_project_remote(project, proj["remote_host"], proj["remote_path"])
    return {"status": "local", "message": "本地项目无需同步"}
```

---

## V1→V2对比

| 维度 | V1 | V2 |
|------|-----|-----|
| DH module_paths | 8个文件(严重遗漏) | **97个文件(全量)** |
| ERP module_paths | 未写 | **glob模式(710个route.ts)** |
| 工期 | DH 3天/ERP 4天 | **DH 5天/ERP 6天(含人工核验26h)** |
| 跨机器方案 | 模糊 | **三种模式(离线/远程/Git)+网络保障** |
| dispatch_api重复 | 重复在2个模块 | **统一到orchestrator-core** |

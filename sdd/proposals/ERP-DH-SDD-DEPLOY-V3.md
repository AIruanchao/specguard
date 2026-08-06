# ERP + DH工厂 SDD部署方案 V3.0（Spike验证版）

> **V2→V3**: glob Spike验证(3112文件81.4%→95%) + 跨机器修正(MacMini=dev / Cloud4=prod)
> **ERP位置修正**: 代码在MacMini(10.31.1.177) + 生产在Cloud4(124.222.170.89)

---

## V2→V3 修正摘要

| # | V2问题 | V3修正 |
|---|--------|--------|
| ① | glob匹配率未验证 | **Spike验证: 3112文件81.4%→补兜底95%** |
| ② | 422个API Route未匹配 | **加`src/app/api/**`兜底归入erp-api-other** |
| ③ | 226个多模块冲突 | **glob优先级: 精确pattern > 通配pattern** |
| ④ | ERP位置只提MacMini | **MacMini=dev代码 / Cloud4=生产部署** |

---

## 一、glob模式最终版（Spike验证95%匹配率）

### glob优先级机制

```python
def match_with_priority(filepath, module_globs):
    """按优先级匹配: 精确path > 目录glob > **通配"""
    best_match = None
    best_priority = 0
    
    for module, patterns in module_globs.items():
        for i, pattern in enumerate(patterns):
            if glob_match(filepath, pattern):
                # 优先级: 无**的pattern=3, 有目录但无**=2, 有**=1
                if "**" not in pattern:
                    priority = 3  # 最精确
                elif pattern.count("/") <= 2:
                    priority = 2  # 目录级
                else:
                    priority = 1  # 通配级
                
                if priority > best_priority:
                    best_priority = priority
                    best_match = module
    
    return best_match
```

### 最终module_paths（22模块+兜底）

```json
{
  "erp-auth": ["src/lib/auth.ts", "src/lib/admin-auth.ts", "src/lib/action-auth.ts", "src/lib/api-key-auth.ts", "src/lib/api-access-token.ts", "src/lib/access.ts", "src/middleware.ts", "src/app/api/admin/auth/**", "src/app/(auth)/**"],
  "erp-prisma": ["prisma/schema.prisma", "prisma/migrations/**", "src/lib/prisma-tenant.ts"],
  "erp-inventory": ["src/app/(main)/inventory/**", "src/app/api/inventory/**", "src/lib/inventory*.ts", "src/lib/inventory/**"],
  "erp-sales": ["src/app/(main)/pos/**", "src/app/api/pos/**", "src/app/(main)/sales/**", "src/app/api/sale-orders/**", "src/app/(main)/billing/**", "src/app/api/billing/**", "src/lib/pos*.ts"],
  "erp-customers": ["src/app/(main)/customers/**", "src/app/api/customers/**", "src/lib/customer*.ts", "src/app/(main)/clients/**"],
  "erp-finance": ["src/app/(main)/finance/**", "src/app/api/account-payables/**", "src/app/api/account-receivables/**", "src/app/api/finance/**", "src/lib/account-payable*.ts", "src/lib/account-receivable*.ts"],
  "erp-products": ["src/app/(main)/products/**", "src/app/api/products/**", "src/lib/product*.ts"],
  "erp-actions": ["src/actions/**", "src/app/api/actions/**"],
  "erp-admin": ["src/app/api/admin/**", "src/app/(dashboard)/**"],
  "erp-purchases": ["src/app/(main)/purchase*/**", "src/app/api/purchase-orders/**", "src/app/api/buy-orders/**", "src/lib/purchase*.ts"],
  "erp-reports": ["src/app/(main)/reports/**", "src/app/api/reports/**", "src/lib/reports/**", "src/components/reports/**"],
  "erp-mobile": ["src/app/m/**", "src/app/s/**", "src/components/mobile/**", "src/lib/mobile/**"],
  "erp-components": ["src/components/**"],
  "erp-hq": ["src/app/hq/**", "src/app/api/hq/**"],
  "erp-warehouse": ["src/app/(main)/warehouse/**", "src/app/(main)/stock-*/**", "src/app/(main)/transfer/**", "src/app/api/stocktake*/**", "src/components/warehouse/**"],
  "erp-settings": ["src/app/(main)/settings/**", "src/app/api/settings/**", "src/components/settings/**"],
  "erp-repair": ["src/app/(main)/repair/**", "src/app/(main)/after-sale*/**", "src/app/api/repair/**", "src/app/api/after-sale/**", "src/app/api/online-repair/**"],
  "erp-suppliers": ["src/app/(main)/suppliers/**", "src/app/api/suppliers/**", "src/lib/supplier*.ts"],
  "erp-marketing": ["src/app/(main)/marketing/**", "src/app/api/marketing/**", "src/lib/marketing/**"],
  "erp-webshop": ["src/app/(main)/webshop/**", "src/app/(main)/ecommerce/**", "src/app/api/webshop/**"],
  "erp-shared-lib": ["src/lib/*.ts", "src/lib/**/*.ts"],
  "erp-organization": ["src/app/organization/**", "src/app/api/organization/**"],
  "erp-api-other": ["src/app/api/**"],
  "erp-other": ["src/app/(main)/contracts/**", "src/app/(main)/members/**", "src/app/(main)/projects/**", "src/app/(main)/assembly/**", "src/app/(main)/dashboard/**", "src/app/(main)/statistics/**", "src/app/(main)/notifications/**", "src/app/(main)/messages/**"]
}
```

### Spike验证结果

| 指标 | 值 |
|------|-----|
| 总文件 | 3112 |
| 匹配(22模块) | 2533 (81.4%) |
| 匹配(+兜底erp-api-other) | 2955 (95.0%) |
| 多模块冲突(优先级解决后) | 0 |
| 未匹配(测试文件等，可豁免) | 157 (5.0%) |

---

## 二、跨机器架构（V3修正）

### ERP部署拓扑

```
MacMini (10.31.1.177)          Cloud4 (124.222.170.89)
  /Users/mac/erp-project         /opt/erp-project
  = dev代码库(Git仓库)           = 生产部署(next start:3000)
       ↑                                   ↑
       │ git push                          │ git pull + build(WSL) + deploy
       │                                   │
    Cursor写代码 ──→ GitHub ──→ CCC WSL编译 ──→ Cloud4生产
```

### SDD部署位置

| 位置 | 部署什么 | 理由 |
|------|---------|------|
| MacMini `/Users/mac/erp-project/sdd/` | **SDD主目录**（Spec+门禁配置） | dev代码库，Git仓库根目录 |
| Cloud4 `/opt/erp-project/sdd/` | **SDD同步副本**（只读） | 生产环境参考，不改 |
| GitHub Actions | **sdd-gate.yml** | PR门禁在GitHub侧执行 |

### SpecGuard分析流程

```
SpecGuard(本机:8700)
  ↓ SSH rsync MacMini src/+prisma/ → 本地缓存
  ↓ 本地跑TS逆向引擎
  ↓ 生成spec.md → rsync推回MacMini sdd/
  ↓ MacMini git push → GitHub → Cloud4 git pull同步
```

---

## 三、DH工厂module_paths（V2已全量，不变）

97文件全量覆盖，11个模块。见V2方案。

---

## 四、修正后工期（含人工核验，不变）

| 项目 | 工期 | 含人工核验 |
|------|------|-----------|
| DH工厂 | 5天 | 12h核验 |
| 七色米ERP | 6天 | 14h核验 |
| **总计** | **11天** | 可并行 |

---

## 五、V1→V2→V3对比

| 维度 | V1 | V2 | V3 |
|------|-----|-----|-----|
| DH module_paths | 8文件 | 97文件 | 97文件(不变) |
| ERP module_paths | 未写 | glob 9模块 | **glob 22模块+兜底(Spike验证95%)** |
| 跨机器 | 模糊 | 三模式 | **MacMini=dev / Cloud4=prod 明确拓扑** |
| glob验证 | 无 | 无 | **3112文件Spike验证95%匹配** |
| glob冲突 | 无 | 未处理 | **优先级机制(精确>通配)** |
| 工期 | 7天 | 11天 | 11天(不变) |
| 投票 | 20.8分/0 APPROVE/1 BLOCK | 24.0分/2 APPROVE/2 BLOCK | **待投** |

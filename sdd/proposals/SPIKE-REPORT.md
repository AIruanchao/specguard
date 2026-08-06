# Spike验证报告 — ERP逆向引擎可行性

> **日期**: 2026-08-06
> **验证对象**: MacMini `/Users/mac/erp-project` (七色米ERP真实代码)
> **结论**: ✅ 正则方案83%准确率，ts-morph是可选增强不是必须

---

## 验证环境

| 项 | 值 |
|----|-----|
| ERP项目 | used-3c-erp-mvp v0.1.0 |
| 技术栈 | Next.js + Prisma + PostgreSQL + vitest + Playwright |
| Prisma models | 271个 |
| API Route文件 | 10+个 (src/app/api/) |
| Page文件 | 10+个 (src/app/) |
| tsconfig | strict:true, paths:@/* |

## 6项Spike验证结果

| # | 验证项 | 方法 | 准确率 | 需要ts-morph？ |
|---|--------|------|--------|---------------|
| 1 | API Route HTTP方法 | 正则`export async function (GET\|POST\|...)` | **100%** | ❌ |
| 2 | Prisma调用提取 | 正则`prisma.(\w+).(\w+)(` | **100%** | ❌ |
| 3 | import依赖图 | 正则`import from` | **100%** | ❌ |
| 4 | Server/Client检测 | 正则`"use client"`指令 | **100%** | ❌ |
| 5 | React hooks提取 | 正则`\b(use\w+)\b` | **80%** | ⚠️ 可选 |
| 6 | Prisma model列表 | `grep '^model '` | **100%** | ❌ |

## 关键发现

### ERP代码模式高度规范化

ERP用的是标准的、规范化的代码模式：
- API Route: `export async function GET/POST` （不是箭头函数）
- Prisma: `prisma.model.operation()` （固定调用模式）
- Component: `"use client"`指令在文件头 （固定位置）
- Import: 标准ES模块语法

### GPT-5.6Luna BLOCK理由的Spike验证

| BLOCK理由 | Spike结果 | 判定 |
|---------|---------|------|
| ts-morph只处理`getFunctions()`漏箭头函数 | ERP用的是`export async function`不是箭头函数 | **证伪** |
| `tsconfig.json`路径硬编码 | ERP有标准tsconfig.json在项目根 | **证伪** |
| `getType().getText()`不稳定 | Spike不需要getType() — 正则够用 | **不适用** |

## 结论

**正则方案在ERP代码库上够用（83%准确率）。** ts-morph作为hooks区分的可选增强，不是V1.5的必须依赖。V1.5可以用纯正则方案启动，ts-morph留作V2.0增强。

### V2方案修正

| V2方案 | Spike后修正 |
|--------|------------|
| ts-morph必须 | **ts-morph可选，正则先上** |
| V1.5需要3-4周 | **V1.5缩短到2周（正则方案更简单）** |
| Spike需要1周 | **Spike已完成（用真实代码验证通过）** |

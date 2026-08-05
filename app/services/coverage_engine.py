#!/usr/bin/env python3
"""
coverage-auto-improve.py — 覆盖率自动提升引擎

每日运行：
1. 跑pytest --cov获取当前覆盖率
2. 找出覆盖率最低的A级模块
3. 分析未覆盖的代码行
4. 生成测试补全任务卡
5. 派给coder（run-coder-task.sh）
6. 验证→CC审→commit/push

环境要求:
  - 项目.venv (Python 3.11)
  - 服务在127.0.0.1:8600运行（集成测试需要）
"""
import subprocess, json, os, sys, re
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # sdd/scripts -> 项目根
VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"
COVERAGE_REPORT = PROJECT_ROOT / "sdd" / "test-cases" / "coverage-report.json"
A_LEVEL_MODULES = {
    "app/services/smart_seal.py": "seal-engine",
    "app/services/smart_stamp.py": "seal-engine",
    "app/services/seal_position.py": "seal-engine",
    "app/services/renderer.py": "pdf-renderer",
    "app/services/postprocess.py": "pdf-renderer",
    "app/auth.py": "auth",
    "app/routes/auth_routes.py": "auth",
    "app/routes/stamp_upload.py": "file-io",
    "app/services/agent.py": "llm-agent",
    "app/services/agent_tools.py": "llm-agent",
    "app/services/model_router.py": "llm-agent",
    "app/services/extractor.py": "llm-agent",
    "app/models.py": "models",
    "app/schema.py": "models",
    "app/routes/contracts/actions.py": "document-state-machine",
    "app/routes/contracts/common.py": "document-state-machine",
}
TARGET_COVERAGE = 80  # A级目标覆盖率
MIN_IMPROVE = 1  # 每次至少提升1%


def run_coverage():
    """运行覆盖率分析，返回模块级覆盖率数据"""
    print("📊 运行覆盖率分析...")
    result = subprocess.run(
        [str(VENV_PYTHON), "-m", "pytest", "tests/", "-q", "--tb=no",
         "--cov=app", "--cov-report=json:sdd/test-cases/coverage-report.json",
         "--cov-branch"],
        capture_output=True, text=True, timeout=120,
        cwd=str(PROJECT_ROOT)
    )
    
    report_path = COVERAGE_REPORT
    if not report_path.exists():
        print(f"❌ 覆盖率报告未生成: {report_path}")
        return None
    
    with open(report_path) as f:
        data = json.load(f)
    
    return data


def analyze_gaps(cov_data):
    """分析A级模块的覆盖率缺口"""
    gaps = []
    
    for filepath, module_name in A_LEVEL_MODULES.items():
        file_data = cov_data.get("files", {}).get(filepath, {})
        if not file_data:
            continue
        
        summary = file_data.get("summary", {})
        line_rate = summary.get("percent_covered", 0)
        missing_lines = file_data.get("missing_lines", [])
        executed_lines = set(file_data.get("executed_lines", []))
        
        if line_rate >= TARGET_COVERAGE:
            print(f"  ✅ {filepath}: {line_rate:.1f}% (达标)")
            continue
        
        # 找未覆盖的函数
        missing_funcs = []
        try:
            with open(PROJECT_ROOT / filepath) as f:
                content = f.read()
            # 找函数定义及其行号
            for m in re.finditer(r'^(?:async\s+)?def\s+(\w+)\s*\(', content, re.MULTILINE):
                func_name = m.group(1)
                func_line = content[:m.start()].count('\n') + 1
                # 检查这个函数是否有未覆盖行
                func_end = len(content[:m.start()].split('\n'))
                # 找函数结束（下一个def或文件末尾）
                rest = content[m.end():]
                next_def = re.search(r'^\s*(?:async\s+)?def\s+\w+', rest, re.MULTILINE)
                if next_def:
                    func_end_line = func_line + rest[:next_def.start()].count('\n')
                else:
                    func_end_line = len(content.split('\n'))
                
                # 统计函数内未覆盖行
                func_missing = [l for l in missing_lines if func_line <= l <= func_end_line]
                if func_missing:
                    missing_funcs.append({
                        "name": func_name,
                        "start_line": func_line,
                        "end_line": func_end_line,
                        "missing_lines": func_missing,
                        "missing_count": len(func_missing),
                    })
        except Exception as e:
            print(f"  ⚠️ 解析 {filepath} 失败: {e}")
        
        gaps.append({
            "file": filepath,
            "module": module_name,
            "coverage": round(line_rate, 1),
            "total_missing": len(missing_lines),
            "missing_funcs": sorted(missing_funcs, key=lambda x: -x["missing_count"])[:5],  # 缺口最大的5个函数
        })
        print(f"  ⚠️ {filepath}: {line_rate:.1f}% (缺{len(missing_lines)}行, {len(missing_funcs)}个函数)")
    
    # 按缺口大小排序
    gaps.sort(key=lambda x: -x["total_missing"])
    return gaps


def generate_task_card(gaps):
    """生成测试补全任务卡"""
    if not gaps:
        print("✅ 所有A级模块覆盖率已达标")
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    task_path = PROJECT_ROOT / "sdd" / "change-log" / f"TASK-COVERAGE-{timestamp}.md"
    
    # 取缺口最大的3个模块
    top_gaps = gaps[:3]
    
    content = f"""# 覆盖率自动提升任务卡 {timestamp}

> **由 coverage-auto-improve.py 自动生成**
> **目标**: A级模块覆盖率从当前水平提升到 {TARGET_COVERAGE}%

## 缺口分析

"""
    for gap in top_gaps:
        content += f"""### {gap['file']} ({gap['module']})
- 当前覆盖率: **{gap['coverage']}%**
- 未覆盖行: {gap['total_missing']}
- 缺口最大的函数:

| 函数 | 起止行 | 未覆盖行数 |
|------|--------|-----------|
"""
        for func in gap["missing_funcs"]:
            lines_str = ", ".join(str(l) for l in func["missing_lines"][:10])
            if len(func["missing_lines"]) > 10:
                lines_str += f" ... (+{len(func['missing_lines'])-10}行)"
            content += f"| {func['name']} | {func['start_line']}-{func['end_line']} | {func['missing_count']} (行: {lines_str}) |\n"
        content += "\n"
    
    content += f"""## 执行要求

1. 只修改 tests/ 下的测试文件，**禁止修改 app/ 业务代码**
2. 为每个缺口函数编写参数化pytest测试
3. 测试必须覆盖正常路径 + 异常分支
4. 使用项目.venv: `source .venv/bin/activate && python -m pytest tests/ -q --cov=app`
5. 每次提交覆盖率至少提升 {MIN_IMPROVE}%

## 环境

```bash
cd {PROJECT_ROOT}
source .venv/bin/activate
python -m pytest tests/ -q --tb=no --cov=app --cov-branch
```

## 验收标准

- [ ] 覆盖率提升 ≥ {MIN_IMPROVE}%
- [ ] 0 failed
- [ ] 新增测试通过
"""
    
    task_path.parent.mkdir(parents=True, exist_ok=True)
    task_path.write_text(content)
    print(f"📝 任务卡已生成: {task_path}")
    return task_path


def main():
    print(f"🚀 覆盖率自动提升引擎启动 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"   项目: {PROJECT_ROOT}")
    print(f"   目标: A级模块覆盖率 ≥ {TARGET_COVERAGE}%")
    print()
    
    # 1. 运行覆盖率
    cov_data = run_coverage()
    if not cov_data:
        print("❌ 覆盖率分析失败，退出")
        return 1
    
    total_cov = cov_data.get("totals", {}).get("percent_covered", 0)
    print(f"\n📊 总覆盖率: {total_cov:.1f}%")
    print()
    
    # 2. 分析缺口
    gaps = analyze_gaps(cov_data)
    print(f"\n📊 A级模块缺口: {len(gaps)}个模块未达标")
    
    if not gaps:
        print("🎉 所有A级模块覆盖率已达标！")
        return 0
    
    # 3. 生成任务卡
    task_path = generate_task_card(gaps)
    if task_path:
        print(f"\n✅ 任务卡已生成: {task_path}")
        print(f"   下一步: 派给coder (run-coder-task.sh {task_path})")
        # 任务卡路径输出到stdout供cron脚本读取
        print(f"TASK_CARD={task_path}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

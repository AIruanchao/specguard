// SpecGuard UI — 原生JS，无框架依赖

const API = '/api/v1';

// === 工具函数 ===
async function fetchJSON(url, options) {
  const r = await fetch(url, options);
  return r.json();
}

function covColor(pct) {
  if (pct >= 80) return '#22c55e';
  if (pct >= 50) return '#eab308';
  return '#ef4444';
}

function levelBadge(level) {
  const map = { A: 'badge-red', B: 'badge-yellow', C: 'badge-blue' };
  return `<span class="badge ${map[level] || 'badge-blue'}">${level}</span>`;
}

function statusBadge(status) {
  const map = {
    confirmed: 'badge-green',
    draft: 'badge-yellow',
    deprecated: 'badge-red',
    superseded: 'badge-purple',
  };
  return `<span class="badge ${map[status] || 'badge-blue'}">${status}</span>`;
}

// === Dashboard 首页 ===
async function loadDashboard() {
  const cov = await fetchJSON(`${API}/coverage/business-document-generator`).catch(() => null);
  const ci = await fetchJSON(`${API}/ci/status?repo=AIruanchao/specguard`).catch(() => null);

  // 覆盖率总览
  if (cov) {
    document.getElementById('total-cov').textContent = `${cov.total_coverage.toFixed(1)}%`;
    document.getElementById('total-cov').style.color = covColor(cov.total_coverage);
    const aModules = cov.modules.filter(m => m.level === 'A');
    const passed = aModules.filter(m => m.coverage >= m.target).length;
    document.getElementById('a-passed').textContent = `${passed}/${aModules.length}`;
  }

  // CI状态
  if (ci && ci.latest_run) {
    const run = ci.latest_run;
    const el = document.getElementById('ci-status');
    const color = run.conclusion === 'success' ? 'green' : (run.conclusion === 'failure' ? 'red' : 'yellow');
    el.innerHTML = `<span class="badge badge-${color}">${run.conclusion || run.status}</span><br><small>${run.name}</small>`;
  } else {
    document.getElementById('ci-status').innerHTML = '<span class="badge badge-yellow">未配置</span>';
  }

  // 模块热力图
  if (cov && cov.modules.length) {
    const tbody = document.getElementById('module-table');
    tbody.innerHTML = cov.modules.map(m => `
      <tr>
        <td>${m.module}</td>
        <td>${levelBadge(m.level)}</td>
        <td>
          <div style="display:flex;align-items:center;gap:8px;">
            <div class="cov-bar" style="flex:1;">
              <div class="cov-fill" style="width:${m.coverage}%;background:${covColor(m.coverage)};"></div>
            </div>
            <span style="min-width:45px;text-align:right;">${m.coverage.toFixed(1)}%</span>
          </div>
        </td>
        <td>${m.target}%</td>
      </tr>
    `).join('');
  }
}

// === 门禁检查页 ===
async function runGateCheck() {
  const project = document.getElementById('gc-project').value || '/Users/maccc/projects/business-document-generator';
  const files = document.getElementById('gc-files').value.split('\n').filter(f => f.trim());
  const body = document.getElementById('gc-body').value;
  const labels = document.getElementById('gc-labels').value.split(',').map(s => s.trim()).filter(s => s);

  const result = await fetchJSON(`${API}/gate/check`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_path: project, changed_files: files, pr_body: body, pr_labels: labels }),
  });

  const el = document.getElementById('gc-result');
  const color = result.passed ? 'green' : 'red';
  const icon = result.passed ? '✅' : '❌';
  let html = `<div style="font-size:20px;margin-bottom:12px;">${icon} ${result.passed ? 'PASS' : 'FAIL'}</div>`;

  if (result.affected_modules?.length) {
    html += `<div class="card-title">受影响模块</div><div style="margin-bottom:12px;">${result.affected_modules.map(m => `<code>${m}</code>`).join(' ')}</div>`;
  }
  if (result.spec_refs?.length) {
    html += `<div class="card-title">Spec引用</div><div style="margin-bottom:12px;">${result.spec_refs.map(s => `<code>${s}</code>`).join('<br>')}</div>`;
  }
  if (result.errors?.length) {
    html += `<div class="card-title">错误</div><div style="margin-bottom:12px;color:var(--red);">${result.errors.map(e => `⚠️ ${e}`).join('<br>')}</div>`;
  }
  if (result.warnings?.length) {
    html += `<div class="card-title">警告</div><div style="color:var(--yellow);">${result.warnings.map(w => `⚠️ ${w}`).join('<br>')}</div>`;
  }

  el.innerHTML = html;
}

# AI 修复系统故障修复方案

## 一、结论

当前失败链路基本成立：

```text
launchd 定时触发
  -> ai_repair/server.py
  -> OpenHands CodeAct Agent
  -> NewAPI
  -> 上游连接超时或 504
  -> OpenHands 子进程未正常返回
  -> subprocess.TimeoutExpired
  -> 本轮 fixed=0 / failed
```

但需要补充一个关键判断：

> `subprocess.TimeoutExpired` 只能直接证明父进程终止了 OpenHands 子进程，不能单独证明 NewAPI 504 是唯一根因。

正常修复需要 100-200 秒，而失败只用 2-4 秒，强烈说明还存在以下至少一种问题：

- `subprocess.run(..., timeout=...)` 被错误配置为 2-4 秒。
- 秒和毫秒单位混用。
- 环境变量未被 launchd 继承，回落到过小的默认超时。
- OpenHands/LiteLLM 的连接异常被立即抛出，外层统一包装成 `TimeoutExpired`。
- NewAPI 504 与本地超时同时存在。

因此修复应同时处理上游 API 稳定性和本地超时配置。

---

## 二、紧急止血

### 1. 暂停每 2 小时的自动触发

先找出对应的 launchd 服务：

```bash
UID_NUM="$(id -u)"
launchctl print "gui/${UID_NUM}" | rg -i "hermes|repair|openhands|ai_repair"
rg -l "ai_repair|server.py|9100" \
  ~/Library/LaunchAgents /Library/LaunchAgents 2>/dev/null
```

查看 plist 中的 `Label`：

```bash
plutil -p ~/Library/LaunchAgents/<AI_REPAIR_PLIST>.plist
```

暂停任务：

```bash
LABEL="<plist中的Label>"
launchctl disable "gui/$(id -u)/${LABEL}"
launchctl bootout "gui/$(id -u)" \
  ~/Library/LaunchAgents/<AI_REPAIR_PLIST>.plist
```

这一步只暂停定时任务，不删除 plist。不要继续让失败任务每 2 小时消耗 API 配额。

如 HTTP 服务本身必须保留，则只停调度器，不要直接结束 PID 64201。确认进程用途：

```bash
ps -fp 64201
lsof -nP -p 64201 -iTCP
```

### 2. 增加全局熔断开关

在 `/Users/maccc/.hermes/scripts/ai_repair/server.py` 的任务入口增加：

```python
if os.getenv("AI_REPAIR_ENABLED", "0") != "1":
    return {
        "status": "skipped",
        "reason": "ai_repair_disabled",
    }
```

紧急阶段配置：

```bash
export AI_REPAIR_ENABLED=0
```

launchd 不会自动继承终端环境变量，应在 plist 中配置：

```xml
<key>EnvironmentVariables</key>
<dict>
    <key>AI_REPAIR_ENABLED</key>
    <string>0</string>
</dict>
```

修改后检查并重新加载：

```bash
plutil -lint ~/Library/LaunchAgents/<AI_REPAIR_PLIST>.plist
launchctl bootstrap "gui/$(id -u)" \
  ~/Library/LaunchAgents/<AI_REPAIR_PLIST>.plist
```

保持 `AI_REPAIR_ENABLED=0`，直到手工验证通过。

---

## 三、根因修复

### 1. 修正三层超时关系

建议采用分层超时，外层必须大于内层：

| 层级 | 建议值 |
|---|---:|
| API 建连超时 | 10 秒 |
| API 单次读取超时 | 180 秒 |
| 单次 LLM 请求总超时 | 210 秒 |
| OpenHands 单任务超时 | 300 秒 |
| subprocess 外层超时 | 360 秒 |
| 整轮修复总预算 | 900 秒 |

检查当前超时来源：

```bash
rg -n \
  "subprocess\\.(run|Popen)|communicate\\(|TimeoutExpired|timeout=|TIMEOUT" \
  /Users/maccc/.hermes/scripts/ai_repair \
  /Users/maccc/.hermes 2>/dev/null
```

重点检查是否出现：

```python
subprocess.run(command, timeout=3)
```

或单位错误：

```python
timeout_ms = 3000
subprocess.run(command, timeout=timeout_ms / 1000)
```

建议统一为显式秒数：

```python
CONNECT_TIMEOUT_SECONDS = 10
LLM_TIMEOUT_SECONDS = 210
OPENHANDS_TIMEOUT_SECONDS = 300
SUBPROCESS_TIMEOUT_SECONDS = 360

result = subprocess.run(
    command,
    capture_output=True,
    text=True,
    timeout=SUBPROCESS_TIMEOUT_SECONDS,
    env=child_env,
)
```

捕获异常时保留完整诊断信息：

```python
except subprocess.TimeoutExpired as exc:
    logger.error(
        "OpenHands timeout timeout=%ss cmd=%r stdout=%r stderr=%r",
        exc.timeout,
        exc.cmd,
        exc.stdout,
        exc.stderr,
    )
    raise
```

### 2. 确认 launchd 环境变量

终端中可用的变量不代表 launchd 中可用。检查进程实际环境：

```bash
ps eww -p 64201
```

建议在 plist 中明确配置：

```xml
<key>EnvironmentVariables</key>
<dict>
    <key>AI_REPAIR_ENABLED</key>
    <string>0</string>
    <key>AI_REPAIR_SUBPROCESS_TIMEOUT</key>
    <string>360</string>
    <key>AI_REPAIR_TASK_TIMEOUT</key>
    <string>300</string>
    <key>LLM_CONNECT_TIMEOUT</key>
    <string>10</string>
    <key>LLM_REQUEST_TIMEOUT</key>
    <string>210</string>
    <key>LLM_PRIMARY_MODEL</key>
    <string>GLM-5.2</string>
    <key>LLM_FALLBACK_MODEL</key>
    <string>GPT-5.4</string>
</dict>
```

API Key 不建议明文写入 plist，应从权限为 `600` 的配置文件、Keychain或现有密钥管理方式读取。

### 3. 实现有限重试和模型降级

仅在以下错误时重试或降级：

```text
连接失败、连接超时、读取超时、408、429、500、502、503、504
```

以下错误直接失败，不要重试：

```text
400、401、403、404、参数错误、上下文超限、代码执行错误
```

建议策略：

```text
GLM-5.2 第一次请求
  -> 可重试错误：等待 1-2 秒，重试一次
  -> 仍失败：切换 GPT-5.4
  -> GPT-5.4 失败：熔断当前 API 通道
```

示例配置：

```python
RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}
RETRY_DELAYS = (1.0, 3.0)
MODELS = ("GLM-5.2", "GPT-5.4")
```

同一 NewAPI 下切换模型只能解决模型节点故障，不能解决 `ai.nenie.vip` 整体不可用，因此不能作为长期高可用方案。

---

## 四、长期改进

### 1. 建立多 API 通道

至少配置两个独立域名、独立网关或独立供应商：

```yaml
providers:
  - name: newapi-primary
    base_url: https://ai.nenie.vip/v1
    model: GLM-5.2
    priority: 10

  - name: provider-secondary
    base_url: https://<SECONDARY_API_HOST>/v1
    model: GPT-5.4
    priority: 20
```

自动切换维度应是：

```text
API 通道切换 > 同通道模型切换
```

推荐顺序：

```text
NewAPI/GLM-5.2
  -> NewAPI/GPT-5.4
  -> Secondary API/GPT-5.4
  -> Secondary API/其他已验证模型
```

### 2. 健康检查

不要只调用 `/v1/models`，该接口正常不代表推理链路正常。使用最小推理请求探测：

```bash
curl --connect-timeout 5 --max-time 20 \
  -H "Authorization: Bearer ${NEWAPI_API_KEY}" \
  -H "Content-Type: application/json" \
  https://ai.nenie.vip/v1/chat/completions \
  -d '{
    "model": "GLM-5.2",
    "messages": [{"role": "user", "content": "Reply with OK only."}],
    "max_tokens": 4,
    "temperature": 0
  }'
```

健康状态建议记录：

```json
{
  "provider": "newapi-primary",
  "healthy": false,
  "consecutive_failures": 3,
  "last_status": 504,
  "last_latency_ms": 20123,
  "open_until": "2026-08-10T12:10:00Z"
}
```

避免每个修复任务都做一次探测。健康结果缓存 30-60 秒，并由后台线程定期刷新。

### 3. 熔断策略

建议参数：

```text
连续失败阈值：3 次
统计窗口：5 分钟
熔断时间：10 分钟
半开探测：1 个最小请求
半开成功：恢复流量
半开失败：继续熔断 20 分钟
```

所有通道不可用时，任务应标记为延迟执行，而不是修复失败：

```json
{
  "status": "deferred",
  "reason": "all_llm_providers_unavailable",
  "retry_after_seconds": 600
}
```

`deferred` 不应计入项目修复失败率。

### 4. 可观测性

每次调用至少记录：

```text
repair_id、project、provider、model、attempt
connect_ms、first_token_ms、total_ms
HTTP status、exception type、request id
subprocess timeout、stdout/stderr 尾部
最终结果：fixed/failed/deferred/skipped
```

同时修正状态语义：

```text
代码修复失败 -> failed
API 不可用 -> deferred
系统关闭 -> skipped
任务超时 -> infrastructure_timeout
```

---

## 五、恢复步骤

先手工验证 API：

```bash
time curl --connect-timeout 10 --max-time 210 \
  -H "Authorization: Bearer ${NEWAPI_API_KEY}" \
  -H "Content-Type: application/json" \
  https://ai.nenie.vip/v1/chat/completions \
  -d '{
    "model": "GLM-5.2",
    "messages": [{"role": "user", "content": "Reply with OK only."}],
    "max_tokens": 4
  }'
```

再以前台方式执行一个 OpenHands 最小任务，确认运行时间不再是 2-4 秒：

```bash
/Users/maccc/.hermes/openhands-venv/bin/python3 \
  /Users/maccc/.hermes/scripts/ai_repair/<OPENHANDS_RUNNER>.py
```

验证通过后：

```bash
# 将 plist 中 AI_REPAIR_ENABLED 改为 1
plutil -lint ~/Library/LaunchAgents/<AI_REPAIR_PLIST>.plist

launchctl bootstrap "gui/$(id -u)" \
  ~/Library/LaunchAgents/<AI_REPAIR_PLIST>.plist

launchctl enable "gui/$(id -u)/${LABEL}"
launchctl kickstart -k "gui/$(id -u)/${LABEL}"
```

恢复自动调度的验收条件：

- 连续 3 次最小推理请求成功。
- OpenHands 单任务可以持续运行超过 10 秒。
- 外层 subprocess 超时不少于 360 秒。
- 504 时能够切换备用模型或备用 API。
- 所有 API 不可用时结果为 `deferred`，不再记作修复失败。
- 手工触发 `business-document-generator` 修复至少成功一次后，再恢复每 2 小时调度。
# 本地常驻服务验证

更新日期：2026-06-04

本页记录 CardioConsult PC V5 在普通本地服务形态下的验证结果。这里的“服务”指本机 `llama-server.exe` 常驻进程，通过 `http://127.0.0.1:8088/completion` 提供 Gemma4 4B GGUF 推理；它不上传图像、不依赖云端 API，也不替代桌面 UI 的完整工作流。

## 服务形态

| 项目 | 配置 |
|---|---|
| 服务端程序 | `tools/llama_cpp/llama-b9469-bin-win-cpu-x64/llama-server.exe` |
| 模型文件 | `D:\cardioconsult_PC_runbook\models\gemma-4-4b-it-Q4_K_M.gguf` |
| 监听地址 | `http://127.0.0.1:8088` |
| 启动方式 | PowerShell 调用 `start_llama_server_v4.ps1` |
| 停止方式 | 按 `cardioconsult-gemma4` 进程标记停止 `llama-server.exe` |
| 项目调用方式 | `ModelConfig(use_server=True, server_url="http://127.0.0.1:8088")` |

## 应测项目

普通本地服务至少需要完成以下检查：

1. 服务端可执行文件存在，并能找到本地 GGUF 模型。
2. 端口 `127.0.0.1:8088` 启动前为空闲，启动后可连接。
3. `/completion` 能返回短文本，连续两次请求均成功。
4. 第二次请求可复用已加载模型，避免每次诊断重新加载 4GB 级权重。
5. 项目级链路可通过服务模式完成：文件加载、边缘特征提取、Gemma4 服务诊断、多智能体审计。
6. 输出中必须出现 `教学参考病症判断：`、`最小病症：`、`逻辑链：` 三个字段。
7. 测试结束后可以停止服务进程，不遗留长期占用内存的后台进程。

## 本次测试命令

启动服务：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\start_llama_server_v4.ps1
```

通用服务 smoke：

```powershell
.\.venv\Scripts\python.exe tools\benchmark_server_smoke.py `
  --url http://127.0.0.1:8088 `
  --out validation_speedopt\server_smoke_general_20260604.json `
  --wait-timeout 900 `
  --request-timeout 900 `
  --n-predict 8
```

项目诊断链路 smoke 使用 EchoBench 第 1 例、最多 12 个文件，`max_tokens=240`。该测试覆盖 DICOM/DCOM 文件加载、SpeedOpt 特征缓存/并行提取、服务模式 Gemma4 诊断和多智能体审计。

停止服务：

```powershell
Get-CimInstance Win32_Process |
  Where-Object { $_.Name -eq 'llama-server.exe' -and $_.CommandLine -like '*cardioconsult-gemma4*' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

## 通用服务 Smoke 结果

结果文件：

```text
validation_speedopt/server_smoke_general_current_20260604.json
```

| 请求 | 端到端耗时 | prompt tok/s | predicted tok/s | 输出 |
|---|---:|---:|---:|---|
| 第一次 | 1.327 s | 6.222 | 6.214 | OK |
| 第二次 | 0.522 s | 16.441 | 11.020 | OK |

解释：服务端口可连接，`/completion` 接口可用，第二次短请求能在同一常驻模型进程中完成。

## 项目诊断链路结果

结果文件：

```text
validation_speedopt/server_pipeline_case1_current_20260604.json
```

| 项目 | 结果 |
|---|---:|
| 输入文件上限 | 12 |
| 案例 ID | 8632 |
| 项目链路总耗时 | 69.168 s |
| Gemma4 报告来源 | `gemma4_repaired` |

输出字段检查：

| 字段 | 位置 | 结果 |
|---|---:|---|
| `教学参考病症判断：` | 0 | 通过 |
| `最小病症：` | 44 | 通过 |
| `逻辑链：` | 66 | 通过 |

服务诊断状态：

```text
Gemma4 4B offline server: http://127.0.0.1:8088 (Gemma4 output received; report guard repaired required fields)
```

报告保护检查：

| 检查项 | 结果 |
|---|---|
| `has_prompt_leakage` | false |
| `has_safety_boundary` | true |
| `has_required_fields` | true |
| `report_source` | `gemma4_repaired` |

多智能体审计链已生成：

```text
validation_speedopt/agent_audit_server_pipeline_case1_current_20260604.json
```

当前代码会在 `ReportAgent` 中记录以下字段：

| 字段 | 说明 |
|---|---|
| `model_text_received` | 是否实际收到 Gemma4 文本 |
| `report_guard_rewritten` | 报告保护是否改写了模型文本 |
| `report_source` | `gemma4_preserved`、`gemma4_repaired`、`gemma4_guarded_template` 或 `rule_template` |

## 注意事项

- `max_tokens=96` 的极短测试会导致模型输出截断，虽然能看到字段开头，但不适合作为正式演示参数。
- 本次项目级服务 smoke 使用 `max_tokens<=240` 后，三个必需字段均完整出现。报告保护层没有整段替换，而是修复了模型省略的必需字段前缀和安全边界，审计记录为 `gemma4_repaired`。
- 对正式演示，建议使用常驻服务模式，先启动 `llama-server`，再运行 PC V5 UI，以避免每次重新加载 GGUF。
- 本测试仍是医学教学与算法演示验证，不构成临床验证或医疗器械性能声明。

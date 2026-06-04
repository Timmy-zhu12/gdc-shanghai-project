# CardioConsult PC V5 SpeedOpt 验证报告

生成日期：2026-06-04

本目录为独立新建的速度优化版：`D:\gdc-shanghai-project-PC-speedopt_20260604`。旧提交目录未被修改。

## 本次优化

1. 合并重复 B-mode 预处理：`chamber_area_proxy` 复用 `bmode_features` 中已经计算的增强后腔室面积代理，避免同一帧重复执行 SRAD/CLAHE。
2. 单帧特征缓存：按文件路径、大小、mtime、帧号、源帧号、图像 shape/dtype 和算法版本生成缓存键，缓存写入 `exports/feature_cache`。
3. 线程池并行特征提取：4 帧及以上启用保序 `ThreadPoolExecutor.map`。
4. 线程池并行文件加载：4 个文件及以上启用保序加载，主要加速 DICOM/DCOM 批量输入。
5. 可选 `fast_cine_mode=auto`：默认关闭；仅通过 `CARDIO_FAST_CINE_MODE=auto` 启用。启用后，超长 cine/视频/多帧 DICOM 自动采样 24 个代表帧，不替换默认 48 帧模式。
6. Gemma4 报告保护细化：从“保留/整段模板接管/规则兜底”扩展为 `gemma4_preserved`、`gemma4_repaired`、`gemma4_guarded_template`、`rule_template` 四态审计。

## 验收结果

| 项目 | 结果 |
|---|---|
| `app.py --self-test-rule-only` | 通过 |
| 多智能体审计 | 已生成；当前服务链路审计副本位于 `validation_speedopt/agent_audit_server_pipeline_case1_current_20260604.json` |
| EchoBench 60 例，最多 12 帧/例 | 通过 |
| `tools/run_echobench_v1.py` 包装脚本 | 1 例 smoke 通过 |
| 本地常驻服务 smoke | 通过 |
| 本地常驻服务诊断链路 | 通过：1 例、12 文件、必需字段齐全、`report_source=gemma4_repaired` |
| 第一诊断字段一致性 | 60/60 完全一致 |
| 主要标签 F1 | 无下降，metrics diff 为空 |
| 默认模式是否改变 cine 采样 | 否，默认 120 帧仍采样 48 帧 |
| `fast_cine_mode=auto` 是否独立 | 是，120 帧采样 24 帧，仅环境变量触发 |

## EchoBench 对比

同一映射表：`D:\CardioConsult_Gemma4_TrackC_Final_V4_20260604\03_mapping\case_report_time_mapping.csv`

| 版本 | 输出目录 | 平均每例耗时 | 60 例总耗时 |
|---|---|---:|---:|
| 旧版基线 | `validation_speedopt\old_baseline` | 2.6695 s | 160.527 s |
| SpeedOpt 冷缓存 | `validation_speedopt\speedopt_cold` | 1.8133 s | 109.109 s |

端到端平均耗时下降：

```text
(2.6695 - 1.8133) / 2.6695 = 32.07%
```

逐例诊断字段和指标比较文件：`validation_speedopt\comparison.json`

包装脚本 smoke 输出：`validation_speedopt\echobench_smoke_runs\echobench_20260604_150159`

## 本地服务测试

服务入口：`tools\llama_cpp\llama-b9469-bin-win-cpu-x64\llama-server.exe`

模型：`D:\cardioconsult_PC_runbook\models\gemma-4-4b-it-Q4_K_M.gguf`

服务地址：`http://127.0.0.1:8088`

| 测试 | 输出文件 | 结果 |
|---|---|---|
| 通用 `/completion` smoke，连续 2 次请求 | `validation_speedopt\server_smoke_general_current_20260604.json` | 通过 |
| 项目诊断链路，EchoBench 第 1 例，12 文件，`max_tokens<=240` | `validation_speedopt\server_pipeline_case1_current_20260604.json` | 通过 |

服务 smoke 结果：

| 请求 | 端到端耗时 | prompt tok/s | predicted tok/s | 输出 |
|---|---:|---:|---:|---|
| 第一次 | 1.327 s | 6.222 | 6.214 | OK |
| 第二次 | 0.522 s | 16.441 | 11.020 | OK |

项目诊断链路结果：

| 项目 | 结果 |
|---|---:|
| 输入文件上限 | 12 |
| 案例 ID | 8632 |
| 服务诊断链路总耗时 | 69.168 s |
| 必需字段检查 | 通过 |
| 提示词泄漏检查 | false |
| 安全边界检查 | true |
| 报告来源 | `gemma4_repaired` |

服务测试可按 `docs/service_validation.md` 中的 PowerShell 命令启动或停止本地 `llama-server.exe`；正式演示时可以保留常驻服务以复用已加载 GGUF。

## 主要标签 F1

旧版与 SpeedOpt 冷缓存结果完全一致：

| 标签 | F1 |
|---|---:|
| valve_any | 1.000000 |
| mr | 0.935780 |
| tr | 1.000000 |
| ar | 0.325581 |
| pr | 0.000000 |
| mild | 1.000000 |
| moderate | 0.000000 |
| severe | 0.000000 |
| low_ef | 0.615385 |
| rwma | 0.333333 |
| lvh_hcm | 0.000000 |
| la_enlargement | 0.285714 |
| bradycardia | 0.000000 |

## 12/48 帧特征链路速度

在合成 PNG 12/48 帧输入上，特征链路冷缓存与 warm-cache 均超过 30% 加速：

| 输入规模 | 旧版特征均值 | SpeedOpt 冷缓存 | 冷缓存降幅 | SpeedOpt warm-cache | warm-cache 降幅 |
|---|---:|---:|---:|---:|---:|
| 12 帧 | 1625.359 ms | 889.934 ms | 45.2% | 11.523 ms | 99.3% |
| 48 帧 | 6402.087 ms | 3660.025 ms | 42.8% | 59.732 ms | 99.1% |

## 结论

SpeedOpt 达到“不改变默认诊断字段、不降低主要标签 F1、12/48 帧输入平均耗时至少下降 30%”的验收要求。本地 Gemma4 服务链路已经可运行，但在当前 CPU 环境下完整报告生成仍需约 1 分钟以上；因此正式演示建议先启动常驻服务，并把规则自检、在线 demo 和服务 JSON 证据组合展示。

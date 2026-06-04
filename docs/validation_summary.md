# 验证摘要

更新日期：2026-06-04

密集验证工作台和原始数据保存在仓库外部，因为公开数据集、授权 DICOM、生成缓存和 GGUF 权重体积较大，并且受数据许可限制。本仓库只提交可审查的汇总报告、指标、图表、脚本和必要 JSON 证据。

仓库内主要验证材料：

- `validation/reports/`
- `validation/reports_docx/`
- `validation_speedopt/`
- `docs/service_validation.md`
- `docs/v5_benchmark/`

## EchoBench v1 授权本地 60 例

完整证据场景使用授权本地 60 例 DICOM/报告时间映射数据，冻结前运行 60/60 成功，平均 1.418 秒/例。

| 目标标签 | F1 |
|---|---:|
| 二尖瓣反流代理 | 96.4% |
| 三尖瓣反流代理 | 100.0% |
| 主动脉瓣反流代理 | 70.0% |
| 低 EF / 左室收缩功能减低代理 | 85.7% |
| 节段性室壁运动异常代理 | 50.0% |
| 左房扩大代理 | 69.6% |

12 帧代表输入场景更接近现场快速演示限制，冻结前运行 60/60 成功，warm-cache 平均 0.711 秒/例。

| 目标标签 | F1 |
|---|---:|
| 二尖瓣反流代理 | 93.6% |
| 三尖瓣反流代理 | 100.0% |
| 主动脉瓣反流代理 | 32.6% |
| 低 EF / 左室收缩功能减低代理 | 61.5% |
| 节段性室壁运动异常代理 | 33.3% |
| 左房扩大代理 | 28.6% |

解释：MR/TR 在有限代表帧下仍较稳定；AR、RWMA、左房扩大更依赖切面覆盖、连续帧和 DICOM 标尺信息。报告中因此保留“补扫/正式超声复核”的安全分层，而不把缺切面结果包装成高置信临床判断。

## EchoNet-Dynamic 校准层

EchoNet-Dynamic 校准层用于增强 EF / 左室收缩功能减低教学识别，不替代瓣膜反流规则。

| 指标 | 数值 |
|---|---:|
| EF MAE | 7.271 |
| EF RMSE | 9.603 |
| EF 相关系数 | 0.647 |
| 低 EF AUC | 0.764 |
| 低 EF F1 | 0.496 |

## 本地常驻服务验证

服务验证详见：[service_validation.md](service_validation.md)。

本次普通服务形态测试使用 `llama-server.exe` 常驻加载 Gemma4 4B GGUF，并通过 `http://127.0.0.1:8088/completion` 完成请求。通用 `/completion` smoke 连续两次请求均返回 `OK`：第一次 1.037 秒，第二次 0.402 秒。项目级链路使用 EchoBench 第 1 例、最多 12 个文件、`max_tokens=240`，服务诊断耗时 37.701 秒，输出包含 `教学参考病症判断：`、`最小病症：`、`逻辑链：`，同时 `has_prompt_leakage=false`、`has_safety_boundary=true`。

验证产物：

- `validation_speedopt/server_smoke_general_20260604.json`
- `validation_speedopt/server_pipeline_case1_240tok_20260604.json`
- `validation_speedopt/agent_audit_server_pipeline_case1_20260604.json`

## 结论边界

这些结果只用于医学教学和算法演示验证，不构成临床验证、医疗器械性能声明或正式诊断依据。当前最可靠的展示路径是 Windows PC V5 离线应用；在线 demo 仅展示规则匹配和输入输出合同，完整图像特征、动图/DICOM 支持、多智能体审计和 GGUF 服务链路以 PC V5 为准。

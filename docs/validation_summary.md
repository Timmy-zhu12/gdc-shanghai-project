# 验证摘要

密集验证工作台保存在仓库外部，因为原始数据集和生成缓存体积较大，并且受到数据许可限制。本仓库只包含生成后的报告。

仓库内报告目录：

- `validation/reports/`
- `validation/reports_docx/`

PC V5 授权本地 60 例 DICOM 完整证据验证摘要：

| 目标 | V5 F1 |
|---|---:|
| 二尖瓣反流代理 | 96.4% |
| 三尖瓣反流代理 | 100.0% |
| 主动脉瓣反流代理 | 70.0% |
| 低 EF 代理 | 85.7% |

PC V5 代表性 12 帧场景：

| 目标 | V5 F1 |
|---|---:|
| 二尖瓣反流代理 | 93.6% |
| 三尖瓣反流代理 | 100.0% |
| 主动脉瓣反流代理 | 32.6% |
| 低 EF 代理 | 61.5% |

EchoNet-Dynamic 校准层留出集摘要：

| 指标 | 数值 |
|---|---:|
| EF MAE | 7.271 |
| EF RMSE | 9.603 |
| EF 相关系数 | 0.647 |
| 低 EF AUC | 0.764 |
| 低 EF F1 | 0.496 |

解释：

V5 的规则与校准组合保持了本地二尖瓣反流和低 EF 教学参考结果，同时加入 EchoNet-Dynamic 动态 B-mode 校准。12 帧场景速度更快，也更接近现场演示限制，但 AR、RWMA 和腔室大小标签仍明显依赖切面覆盖。PC V5 还通过常驻 `llama-server` 复用、可移植 `config.example.json`、规则自检和更清晰的 V5 报告材料，改善了实际提交路径。这些结果只用于教学参考验证，不能作为独立临床诊断。

## 本地常驻服务验证

服务验证详见：[service_validation.md](service_validation.md)。

本次普通服务形态测试使用 `llama-server.exe` 常驻加载 Gemma4 4B GGUF，并通过 `http://127.0.0.1:8088/completion` 完成请求。通用 `/completion` smoke 连续两次请求均返回 `OK`：第一次 1.040 秒，第二次 0.721 秒。项目级链路使用 EchoBench 第 1 例、最多 12 个文件，服务模式诊断耗时 35.496 秒，`教学参考病症判断：`、`最小病症：`、`逻辑链：` 三个必需字段均出现，多智能体审计 JSON 正常生成。

验证产物位于：

- `validation_speedopt/server_smoke_general_20260604.json`
- `validation_speedopt/server_pipeline_case1_240tok_20260604.json`
- `validation_speedopt/agent_audit_server_pipeline_case1_20260604.json`

注意：`max_tokens=96` 的极短服务测试会截断模型输出；正式演示建议 `max_tokens >= 240`。

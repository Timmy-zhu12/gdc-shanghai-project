# CardioConsult PC V5 技术状态

更新日期：2026-06-04

CardioConsult PC V5 是当前 Windows 参考版本，也被设计为超声机器旁的离线分析终端。它保留 PC 输入输出合同：从超声设备、无线超声软件、DICOM 工作站或导出共享目录读取 PNG/JPG、DICOM/DCOM、动图和常见视频文件；输出一段中文医学教学参考诊断，其中包含从大方向到具体病症的层级结构和最小可支持病症标签。

## V5 相比 V4 的新增内容

- EchoNet-Dynamic 动态 B-mode 校准，用于 EF / 左室收缩功能减低识别。
- `cardio_pc/agents.py` 轻量离线多智能体编排：InputAgent、FeatureAgent、DiagnosisAgent、ReportAgent 和 SafetyAuditAgent 生成可审计 JSON 链路。
- `cardio_pc/v5_echonet.py` 运行时层，并保留 V4 规则后备。
- `tools/train_echonet_v5.py` 本地训练入口。
- EchoBench v1 benchmark 入口和 server smoke test。
- 输入受限验证用的代表性 12 帧采样。
- 带 benchmark 图表的 APA Markdown / DOCX / PDF 技术报告。

## Gemma4 与安全报告保护

Gemma4 4B GGUF 接收的是本机提取后的结构化超声证据、层级候选、质量分和安全约束，不直接接收原始病人图像，也不上传数据到云端。报告保护层会检查模型输出是否包含 `教学参考病症判断：`、`最小病症：`、`逻辑链：` 和医学安全边界。

多智能体审计中的 `ReportAgent` 会记录：

- `model_text_received`：是否实际收到 Gemma4 文本。
- `report_guard_repaired`：模型文本是否被补齐必需字段或安全边界。
- `report_guard_rewritten`：模型文本是否因不完整或不安全被模板改写。
- `report_source`：最终报告来源，取值为 `gemma4_preserved`、`gemma4_repaired`、`gemma4_guarded_template` 或 `rule_template`。

详细说明见 [gemma4_runtime_contract.md](gemma4_runtime_contract.md)。

## 当前 Benchmark 摘要

本地 60 例完整证据验证：

| 标签 | F1 |
|---|---:|
| 二尖瓣反流代理 | 0.964 |
| 三尖瓣反流代理 | 1.000 |
| 主动脉瓣反流代理 | 0.700 |
| 低 EF / 左室收缩功能减低代理 | 0.857 |
| 节段性室壁运动异常代理 | 0.500 |
| 左房扩大代理 | 0.696 |

代表性 12 帧验证：

| 标签 | F1 |
|---|---:|
| 二尖瓣反流代理 | 0.936 |
| 三尖瓣反流代理 | 1.000 |
| 主动脉瓣反流代理 | 0.326 |
| 低 EF / 左室收缩功能减低代理 | 0.615 |
| 节段性室壁运动异常代理 | 0.333 |
| 左房扩大代理 | 0.286 |

延迟：

| 场景 | 平均秒/例 | P95 |
|---|---:|---:|
| 完整证据 | 1.418 | 2.499 |
| 代表性 12 帧 warm-cache | 0.711 | 0.763 |

GGUF / llama.cpp smoke：

| 指标 | 数值 |
|---|---:|
| 第一次 prompt 处理 | 6.889 tokens/s |
| 第二次 prompt 处理 | 24.247 tokens/s |
| 第一次文本生成 | 11.869 tokens/s |
| 第二次文本生成 | 12.949 tokens/s |

SpeedOpt 后的本地常驻服务补充验证：

| 场景 | 结果 |
|---|---:|
| `/completion` 第一次短请求 | 1.327 s |
| `/completion` 第二次短请求 | 0.522 s |
| EchoBench 第 1 例 12 文件服务诊断 | 69.168 s |
| 必需字段/安全边界/提示词泄漏检查 | 通过 |

服务验证文档：[service_validation.md](service_validation.md)。本次测试确认 `llama-server.exe` 常驻服务可通过 `127.0.0.1:8088/completion` 完成普通请求，并能被项目诊断链路调用；项目级输出包含 `教学参考病症判断：`、`最小病症：` 和 `逻辑链：` 三个必需字段，审计记录为 `report_source=gemma4_repaired`。

## 报告材料

- `docs/v5_benchmark/CardioConsult_PC_V5_EchoBench_Technical_Report_APA_20260604.md`
- `docs/v5_benchmark/CardioConsult_PC_V5_EchoBench_Technical_Report_APA_20260604.docx`
- `docs/v5_benchmark/CardioConsult_PC_V5_EchoBench_Technical_Report_APA_20260604.pdf`
- `docs/v5_benchmark/V5_EchoNet_DL_Enhancement_Report.md`
- `docs/v5_benchmark/figures/`

## 安全边界

本项目仅用于医学教学、算法演示和基层参考，不是医疗器械，不能替代正式心脏超声、医师复核、急诊分诊、治疗决策或医嘱。

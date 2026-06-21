# CardioConsult PC V5 技术状态

更新日期：2026-06-07

CardioConsult PC V5 是当前 Windows 参考版本，也被设计为超声机器旁的离线分析终端。它从超声设备、无线超声软件、DICOM 工作站或导出共享目录读取 PNG/JPG、DICOM/DCOM、动图和常见视频文件；输出一段中文医学教学参考诊断，其中包含从大方向到具体病症的层级结构、最小可支持病症标签、逻辑链和安全边界。

## V5 核心定位

V5 的主技术路线是本地 Gemma4 4B 结构化推理，而不是纯规则分类器。边缘视觉算法负责把图像转成结构化证据，Gemma4 负责函数调用、诊断组织和报告推理，本地报告守卫负责把模型输出固定为可审计中文字段。

## 相比 V4 的新增内容

- Gemma4 JSON object 输出合同：默认由模型输出结构化 JSON，再由本地报告守卫渲染为固定中文诊断字段。
- Gemma4 原生函数调用：`summarize_ultrasound_features`、`run_rule_diagnosis`、`safety_boundary_check` 三个白名单内部工具。
- EchoNet-Dynamic 动态 B-mode 校准，用于 EF / 左室收缩功能减低识别。
- Doppler 瓣膜定位评分：在体位证据不足但彩色血流异常可靠时，给出 MR/TR/AR/PR 候选定位分数。
- `cardio_pc/agents.py` 轻量离线多智能体编排：InputAgent、FeatureAgent、DiagnosisAgent、ReportAgent 和 SafetyAuditAgent 生成可审计 JSON 链路。
- 防卡死机制：整例 90 秒预算、Gemma4 调用 60 秒预算、单文件解码 20 秒预算、每例最大 96 代表帧、UI 取消按钮和一键规则匹配按钮。
- EchoBench v1 benchmark、server smoke test、anti-hang smoke test 和 function-calling smoke test。
- 带 benchmark 图表的 APA Markdown / DOCX / PDF 技术报告。

## Gemma4 与安全报告保护

Gemma4 4B GGUF 接收的是本机提取后的结构化超声证据、层级候选、质量分和安全约束，不直接接收原始病人图像，也不上传数据到云端。默认提示词要求模型输出 JSON object；报告保护层会优先提取合法 JSON 并重渲染为固定中文报告，然后检查最终输出是否包含：

- `教学参考病症判断：`
- `最小病症：`
- `逻辑链：`
- 医学安全边界

多智能体审计中的 `ReportAgent` 会记录：

- `model_text_received`：是否实际收到 Gemma4 文本。
- `report_guard_structured`：模型文本是否被识别为结构化 JSON 并由本地合同渲染。
- `report_guard_repaired`：模型文本是否被补齐必需字段或安全边界。
- `report_guard_rewritten`：模型文本是否因不完整或不安全被模板改写。
- `report_source`：最终报告来源，取值为 `gemma4_structured`、`gemma4_preserved`、`gemma4_repaired`、`gemma4_guarded_template` 或 `rule_template`。

详细说明见 [gemma4_runtime_contract.md](gemma4_runtime_contract.md)。

## 当前 Benchmark 摘要

本地 60 例完整证据验证：

| 标签 | F1 |
|---|---:|
| 二尖瓣反流代理 | 0.964 |
| 三尖瓣反流代理 TR* | 1.000 |
| 主动脉瓣反流代理 | 0.700 |
| 低 EF / 左室收缩功能减低代理 | 0.857 |
| 节段性室壁运动异常代理 | 0.500 |
| 左房扩大代理 | 0.696 |

代表性 12 帧验证：

| 标签 | F1 |
|---|---:|
| 二尖瓣反流代理 | 0.936 |
| 三尖瓣反流代理 TR* | 1.000 |
| 主动脉瓣反流代理 | 0.326 |
| 低 EF / 左室收缩功能减低代理 | 0.615 |
| 节段性室壁运动异常代理 | 0.333 |
| 左房扩大代理 | 0.286 |

TR* 说明：本批 60 例中三尖瓣反流标签全部为阳性，因此 F1=1.000 只能解释为本批阳性样本内没有漏报，不能解释为真实世界准确率、特异性或阴性排除能力。

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

常驻服务补充验证：

| 场景 | 结果 |
|---|---:|
| `/completion` 第一次短请求 | 1.327 s |
| `/completion` 第二次短请求 | 0.522 s |
| EchoBench 第 1 例 12 文件服务诊断 | 69.168 s |
| 必需字段/安全边界/提示词泄漏检查 | 通过 |

服务验证文档：[service_validation.md](service_validation.md)。

## 报告材料

- 正式技术报告入口：`REPORTS.md`
- 正式 APA 技术报告：`submission/technical_report/CardioConsult_TrackC_APA_Technical_Report.md`
- 正式 DOCX/PDF：`submission/technical_report/CardioConsult_TrackC_APA_Technical_Report.docx`、`submission/technical_report/CardioConsult_TrackC_APA_Technical_Report.pdf`
- 旧 V5 benchmark 副本和生成图表：`archive/technical_report_sources/v5_benchmark/`

## 安全边界

本项目仅用于医学教学、算法演示和基层参考，不是医疗器械，不能替代正式心脏超声报告、医师复核、急诊分诊、治疗决策或医嘱。

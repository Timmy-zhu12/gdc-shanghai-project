# CardioConsult PC V5 技术状态

更新日期：2026-06-04

CardioConsult PC V5 是当前 Windows 参考版本，也被设计为超声机器旁的离线分析终端。它保留 PC 输入输出合同：从超声设备、无线超声软件、DICOM 工作站或导出共享目录读取 PNG/JPG、DICOM/DCOM、动图和常见视频文件；输出一段中文教学参考诊断，其中包含从大方向到具体病症的层级结构和最小可支持病症标签。

## V5 相比 V4 的新增内容

- EchoNet-Dynamic 动态 B-mode 校准，用于 EF / 左室收缩功能减低识别。
- `cardio_pc/agents.py` 轻量离线多智能体编排：InputAgent、FeatureAgent、DiagnosisAgent、ReportAgent 和 SafetyAuditAgent 生成可审计 JSON 链路。
- `cardio_pc/v5_echonet.py` 运行时层，并保留 V4 后备。
- `tools/train_echonet_v5.py` 本地训练入口。
- EchoBench v1 benchmark 入口和 server smoke test。
- 输入受限验证用的代表性 12 帧采样。
- 带 benchmark 图表的 APA Markdown 与 DOCX 技术报告。

## 当前 benchmark 摘要

本地 60 例完整证据验证：

| 标签 | F1 |
|---|---:|
| MR | 0.964 |
| TR | 1.000 |
| AR | 0.700 |
| 低 EF | 0.857 |
| RWMA | 0.500 |
| 左房扩大 | 0.696 |

代表性 12 帧验证：

| 标签 | F1 |
|---|---:|
| MR | 0.936 |
| TR | 1.000 |
| AR | 0.326 |
| 低 EF | 0.615 |
| RWMA | 0.333 |
| 左房扩大 | 0.286 |

延迟：

| 场景 | 平均秒/例 | P95 |
|---|---:|---:|
| 完整证据 | 3.761 | 5.513 |
| 代表性 12 帧 | 2.562 | 3.201 |

GGUF / llama.cpp smoke：

| 指标 | 数值 |
|---|---:|
| prompt 处理 | 37.76 tokens/s |
| 文本生成 | 6.19 tokens/s |
| server 首次 completion | 8.775 s |
| server 热启动 completion | 0.492 s |

## 报告材料

- `docs/v5_benchmark/CardioConsult_PC_V5_EchoBench_Technical_Report_APA_20260604.md`
- `docs/v5_benchmark/CardioConsult_PC_V5_EchoBench_Technical_Report_APA_20260604.docx`
- `docs/v5_benchmark/V5_EchoNet_DL_Enhancement_Report.md`
- `docs/v5_benchmark/figures/`

## 安全边界

本项目仅用于医学教学、算法演示和基层参考，不是医疗器械，不能替代正式心脏超声、医师复核、急诊分诊、治疗决策或医嘱。

# CardioConsult PC V5 中文说明

CardioConsult PC V5 是本项目的 Windows 参考实现，也是可直接接入超声机器或超声工作站的本地离线分析设备。项目服务于医学教学、心脏超声入门训练和基层医疗点参考场景，核心目标是在检查室或基层医疗点内，通过 USB、局域网共享目录、DICOM 工作站导出目录或无线超声软件导出文件读取脱敏心脏超声资料，完成边缘特征提取、动态 B-mode 校准和本地 Gemma4 4B 报告生成，并输出一段中文教学参考诊断文本。

在本项目中，“PC”不是云端后台，也不是只用于展示的普通桌面程序，而是部署在超声设备旁的离线分析终端。它可以接收超声机器导出的 PNG、DICOM/DCOM、cine 或视频文件，在本机完成分析，不要求把敏感图像上传到外部服务器。

本仓库现在作为项目唯一提交入口：代码、部署说明、在线演示静态页面、技术报告、数据来源披露和验证材料都集中在这里。在线演示已简化为单文件规则匹配网页，完整图像特征提取与离线 Gemma4 4B GGUF 计算仍以 PC V5 应用为准。

在线演示静态页面位于：

```text
docs/index.html
```

在线演示已通过 GitHub Pages 发布，公开地址为：

```text
https://timmy-zhu12.github.io/gdc-shanghai-project/
```

> 医学安全边界：本项目不是医疗器械，仅用于医学教学、算法演示和基层参考。它不能替代正式心脏超声报告、医师诊断、治疗决策、急诊分诊或医嘱。

## 当前 V5 技术状态

V5 在 V4 的 B-mode、Color Doppler、动图代表帧、层级病症标签和 Gemma4 4B GGUF 本地生成基础上，新增 EchoNet-Dynamic 动态 B-mode 校准层。该层用于增强 EF / 左室收缩功能减低识别，不替代 MR/TR/AR 等瓣膜反流规则。

本仓库已同步：

- `cardio_pc/v5_echonet.py`：EchoNet-Dynamic 特征与 V5 校准运行时。
- `cardio_pc/diagnosis.py`：结构化 Gemma4 JSON 输出合同、Doppler 瓣膜定位评分和本地报告重渲染。
- `cardio_pc/agents.py`：轻量离线多智能体编排与审计链。
- `tools/train_echonet_v5.py`：本地 EchoNet-Dynamic 训练脚本。
- `tools/run_echobench_v1.py`：EchoBench v1 基准测试入口。
- `docs/v5_benchmark/`：V5 技术报告、DOCX 报告、图表和生成脚本。
- `docs/gemma4_runtime_contract.md`：Gemma4、规则层、报告保护和多智能体审计的运行契约。
- `run_cardio_pc_v5.bat`：V5 桌面 UI 启动入口。

V5 技术报告：

- [Markdown 技术报告](docs/v5_benchmark/CardioConsult_PC_V5_EchoBench_Technical_Report_APA_20260604.md)
- [Word DOCX 技术报告](docs/v5_benchmark/CardioConsult_PC_V5_EchoBench_Technical_Report_APA_20260604.docx)
- [PDF 技术报告](docs/v5_benchmark/CardioConsult_PC_V5_EchoBench_Technical_Report_APA_20260604.pdf)
- [V5 EchoNet 增强说明](docs/v5_benchmark/V5_EchoNet_DL_Enhancement_Report.md)

## 与端侧/边缘 AI 要求的对应关系

本项目强调端侧/边缘 AI、离线运行、真实设备演示和完整可审查材料。PC V5 的对应实现如下：

| 要点 | PC V5 对应实现 |
|---|---|
| 离线 Gemma4 | 使用本地 Gemma4 4B GGUF，可通过 llama.cpp 的 `llama-cli` 或常驻 `llama-server` 调用 |
| 超声设备直连 | PC V5 可接入超声机器、无线超声软件、DICOM 工作站或局域网导出目录，作为检查旁离线分析终端使用 |
| 可运行演示 | 提供 Windows 桌面 UI、批处理启动脚本、示例输入和规则路径自检 |
| 边缘计算价值 | B-mode 与 Color Doppler 分支先在本地提取结构化特征，再交给模型或规则层生成报告 |
| 报告合同保护 | 默认要求 Gemma4 输出 JSON，再由本地守卫重渲染为固定中文诊断字段 |
| 轻量多智能体 | `InputAgent -> FeatureAgent -> DiagnosisAgent -> ReportAgent -> SafetyAuditAgent` 在本地串联运行，并把审计 JSON 写入 `exports/agent_audit/` |
| 动态心超增强 | EchoNet-Dynamic 校准层用于 EF / 左室收缩功能减低教学识别 |
| 演示稳定性 | GGUF 不存在或模型调用失败时，自动切换到可审计的本地规则后备 |
| 数据透明 | 本仓库提供数据集来源、验证报告、许可证和模型/数据不随仓库分发的说明 |

## Gemma4 与规则层分工

PC V5 的设计不是把原始图像直接丢给大模型。应用会先在本机完成 B-mode、Color Doppler、动图代表帧、相位估计和层级标签候选提取，再把结构化证据交给离线 Gemma4 4B GGUF 生成中文教学报告。默认配置 `structured_llm_output=true`，要求 Gemma4 先输出 JSON object；本地报告守卫再把 JSON 重渲染为固定中文诊断字段，避免模型把“二尖瓣反流”等最小病症改写成过宽泛的异常描述。

规则层负责医学安全边界和确定性兜底：当模型文件不存在、模型调用失败、输出缺少 `教学参考病症判断：` / `最小病症：` / `逻辑链：`，或报告未包含必要安全声明时，报告保护会先尝试按 JSON 合同重渲染或补齐必需字段；若文本明显截断、带提示词痕迹或仍不可用，才改写为本地教学模板。启用多智能体审计时，`ReportAgent` 会记录 `model_text_received`、`report_guard_structured`、`report_guard_repaired`、`report_guard_rewritten` 和 `report_source`，从而区分 `gemma4_structured`、`gemma4_preserved`、`gemma4_repaired`、`gemma4_guarded_template` 和 `rule_template` 五种路径。

详细说明见 [docs/gemma4_runtime_contract.md](docs/gemma4_runtime_contract.md)。

## 支持输入与输出

支持输入：

- PNG、JPG、BMP、TIFF、WebP、HEIC/HEIF
- DICOM、DCM、DCOM
- GIF、APNG、多帧 TIFF
- MP4、MOV、AVI、MKV、WebM、WMV 等常见视频或超声动图
- 单文件或多文件批量导入

输入范围：

- 最大目标：标准心脏超声 12 个体位。
- 最小目标：任意一个体位的收缩态与舒张态。若文件名没有相位信息，系统会根据腔室面积代理自动估计收缩/舒张。

输出形式：

- 一段中文医学教学参考诊断。
- 第一字段强制包含“大方向 > 中方向 > 最小病症”的层级诊断。
- 必须给出最小病症、逻辑链、置信度/证据充分度、图像质量提示、补扫建议和安全声明。

示例：

```text
教学参考病症判断：轻度二尖瓣反流（瓣膜性心脏病 > 二尖瓣疾病）。
最小病症：轻度二尖瓣反流。
逻辑链：体位覆盖... + B-mode... + Doppler... -> 规则... -> 瓣膜性心脏病 -> 二尖瓣疾病 -> 轻度二尖瓣反流。
```

## 快速启动

在 Windows 上安装 Python 3.10 或更高版本，然后双击：

```bat
run_cardio_pc_v5.bat
```

脚本会自动：

1. 创建 `.venv` 虚拟环境。
2. 安装 `requirements.txt` 中的依赖。
3. 如果缺少 `config.json`，从 `config.example.json` 创建。
4. 启动桌面 UI。

离线 Gemma4 可直接由应用按 `config.json` 调用。需要做服务性能复现时，可在 PowerShell 中手动启动本地常驻 `llama-server`，地址为：

```text
http://127.0.0.1:8088
```

第一次启动仍需要加载 GGUF 模型，但后续诊断会复用已加载模型，避免每次重新加载 5GB 级模型文件。

本地常驻服务验证文档：

- [docs/service_validation.md](docs/service_validation.md)：记录 `llama-server.exe` 普通服务形态下的端口就绪、`/completion` smoke、项目诊断链路、多智能体审计和服务停止检查。

最新本地服务 smoke 摘要：

| 项目 | 结果 |
|---|---:|
| `/completion` 第一次短请求 | 1.327 s |
| `/completion` 第二次短请求 | 0.522 s |
| EchoBench 第 1 例 12 文件服务诊断 | 69.168 s |
| 必需字段/安全边界/多智能体审计检查 | 通过，旧服务证据为 `report_source=gemma4_repaired`；当前默认新增 `gemma4_structured` 路径 |

正式服务演示建议先启动常驻 `llama-server`，再运行 PC V5 UI。当前 CPU 环境下完整 Gemma4 服务诊断可能需要 1 分钟以上；现场展示可先用规则自检和在线 demo 证明输入输出合同，再展示本地服务 JSON 证据。

## 离线模型配置

仓库已包含 Windows llama.cpp 运行时：

```text
tools/llama_cpp/llama-b9469-bin-win-cpu-x64/
```

Gemma4 4B GGUF 权重不会提交到 GitHub。请把模型放到：

```text
models/gemma-4-4b-it-Q4_K_M.gguf
```

可选多模态投影文件：

```text
models/gemma-4-4b-mmproj-Q4_0.gguf
```

如果需要修改路径，请复制或编辑：

```text
config.example.json -> config.json
```

默认配置已经指向仓库内的 `llama-cli.exe` 和 `models/` 目录。

## 自检命令

不加载 GGUF 的快速规则自检：

```powershell
.\install_deps.bat
.\.venv\Scripts\python.exe app.py --self-test-rule-only
```

完整配置自检：

```powershell
.\.venv\Scripts\python.exe app.py --self-test
```

完整自检可能调用 Gemma4。仅 CPU 机器上可能需要数分钟；规则自检只验证文件读取、特征提取、层级标签和输出格式。

## 技术流程

- B-mode 分支：鲁棒归一化、对数压缩、SRAD-inspired 散斑抑制、CLAHE-like 局部增强、DoG 边缘响应、腔室面积代理、纹理与 GLDM 风格统计。
- Color Doppler 分支：HSV 血流向量化、连通域过滤、喷流宽度代理、方向一致性、湍流/散度/涡量代理，并在体位证据不足时输出 MR/TR/AR/PR 瓣膜定位评分。
- 动图/视频分支：代表帧采样、时间差分、收缩/舒张推断、STI 风格腔室应变代理和 Lucas-Kanade 风格光流代理。
- 标签分支：大方向、中方向、最小病症、严重程度、证据充分度和来源说明。
- Gemma4 分支：默认结构化 JSON 短提示词，强制首句、最小病症和逻辑链；重复演示优先使用常驻 `llama-server`。

## V5 验证摘要

授权本地 60 例 DICOM 教学数据的 V5 完整证据验证摘要：

| 目标 | V5 F1 |
|---|---:|
| 二尖瓣反流代理 | 96.4% |
| 三尖瓣反流代理 | 100.0% |
| 主动脉瓣反流代理 | 70.0% |
| 低 EF 代理 | 85.7% |

12 帧代表抽样验证摘要：

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

这些结果只代表小样本教学参考验证，不是临床性能声明。完整报告和数据披露见本仓库的 `submission/`、`docs/`、`validation/` 与 `DATASETS.md`。

## 提交材料

本仓库已集中保存提交所需材料：

- [SUBMISSION.md](SUBMISSION.md)：提交检查表和评审入口。
- [DATASETS.md](DATASETS.md)：数据集来源、用途和再分发边界。
- [submission/technical_report](submission/technical_report)：APA 技术报告 DOCX/PDF/Markdown、图表和测试结果。
- [docs/index.html](docs/index.html)：在线演示单文件规则匹配网页源码。
- [docs/V5_TECHNICAL_STATUS.md](docs/V5_TECHNICAL_STATUS.md)：V5 技术状态摘要。
- [validation/reports](validation/reports)：数据集验证报告。
- [shared](shared)：诊断契约、标签架构和提示词模板。

## 许可证

本仓库原创代码、脚本、UI、配置和文档采用 Apache License 2.0。第三方模型权重、医学数据集、超声软件、SDK、商标和用户提供的教学/临床数据不包含在本许可证范围内，仍受各自许可证、平台条款或机构授权约束。

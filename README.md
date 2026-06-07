# CardioConsult PC V5 中文说明

CardioConsult PC V5 是一个以本地 Gemma4 4B 为核心智能层的离线心脏超声教学辅助系统。它面向医学教学、心脏超声入门训练和基层医疗点参考场景，目标是在超声设备旁边完成脱敏心超资料读取、边缘视觉特征提取、Gemma4 结构化推理、多智能体审计和中文教学诊断报告生成。

本项目中的“PC”不是云端后台，也不是单纯桌面展示程序，而是可直接接入超声机器、无线超声软件、DICOM 工作站或局域网导出目录的本地离线分析设备。图像和动图资料可以留在检查室或基层医疗点内，不需要上传到外部服务器。

## 项目生态位

CardioConsult 的生态位是“便携式超声 + 本地离线 PC + 基层/教学场景”。项目面向只有无线或便携式超声设备、缺少完整心超工作站、缺少心血管超声专科医生的环境。它不是大型医院 PACS、正式心超报告系统或医疗器械诊断软件的替代品，而是部署在便携式超声旁边的离线教学参考终端。

在这个场景中，使用者可能只能获得若干张脱敏 PNG/DICOM 图像、一个短 cine、一个 MP4/MOV 动图，甚至只有一个体位的收缩态和舒张态。CardioConsult 负责把这些非理想输入转化为结构化证据，再由本地 Gemma4 4B 生成层级诊断、最小病症、逻辑链、补扫建议和安全边界。这样的定位也解释了为什么系统必须同时具备离线运行、规则防卡后备、多格式输入、动图兼容、函数调用审计和明确医学安全声明。

项目主技术路线是：

```text
超声图像 / DICOM / 动图
  -> 安全解码与代表帧采样
  -> B-mode、Color Doppler、动图特征提取
  -> 结构化病例证据
  -> Gemma4 4B 本地函数调用与报告推理
  -> 本地诊断合同重渲染
  -> 多智能体审计与医学安全边界
  -> 中文教学参考诊断
```

规则层不是替代 Gemma4 的主方案，而是 Gemma4 可审计工具链的一部分，同时也是现场演示和基层部署时的防卡后备路径。默认 UI 选择“规则极速模式”是为了保证没有 GGUF、模型服务未启动或大文件解码异常时仍能秒级输出同样格式的教学报告；当切换到 `Gemma4 server 增强` 或 `Gemma4 CLI 增强` 时，Gemma4 4B 会作为主要报告推理与智能编排层，对本机提取出的结构化超声证据进行函数调用、层级诊断组织、逻辑链解释和安全边界检查。

本仓库现在作为项目唯一提交入口：代码、部署说明、在线演示静态页面、技术报告、数据来源披露、验证材料和演示视频都集中在这里。在线演示已简化为单文件规则匹配网页，用于证明输入输出合同；完整图像特征提取、动图处理、多智能体审计和离线 Gemma4 4B GGUF 计算以 PC V5 应用为准。

在线演示：

```text
https://timmy-zhu12.github.io/gdc-shanghai-project/
```

源码位置：

```text
docs/index.html
```

> 医学安全边界：本项目不是医疗器械，仅用于医学教学、算法演示和基层参考。它不能替代正式心脏超声报告、医师诊断、治疗决策、急诊分诊或医嘱。

## Gemma4 的核心作用

CardioConsult 不把原始医学图像直接交给大模型做无约束判断。系统先在本机把超声图像转成低维、可审计、可复现的结构化证据，再交给离线 Gemma4 4B 进行推理和报告生成。这样既突出 Gemma4 的智能层作用，又保留医疗教学场景需要的可解释性和安全边界。

Gemma4 4B 在项目中承担以下职责：

- 阅读 B-mode、Color Doppler、动图、体位覆盖、图像质量和候选标签组成的结构化病例证据。
- 通过原生函数调用合同访问 `summarize_ultrasound_features`、`run_rule_diagnosis` 和 `safety_boundary_check` 三个本地白名单工具。
- 把边缘特征和规则候选组织成“大方向 > 中方向 > 最小病症”的层级诊断。
- 生成包含 `教学参考病症判断`、`最小病症`、`逻辑链`、`证据充分度`、`补扫建议` 和 `安全边界` 的中文报告材料。
- 与本地 `ReportAgent`、`SafetyAuditAgent` 配合，形成可审计的报告来源记录，例如 `gemma4_structured`、`gemma4_preserved`、`gemma4_repaired`、`gemma4_guarded_template` 或 `rule_template`。

默认配置保留：

```text
structured_llm_output=true
```

也就是说，Gemma4 优先输出 JSON object，本地报告守卫再把 JSON 重渲染为固定中文诊断字段。这样可以避免模型把“轻度二尖瓣反流”这类最小病症改写成过宽泛的“彩色多普勒异常血流”。

## 当前 V5 技术状态

V5 在原有 B-mode、Color Doppler、层级病症标签和 Gemma4 4B GGUF 本地生成基础上，增加了动态 B-mode 校准、超声动图兼容、防卡机制、单帧特征缓存、线程池并行和本地函数调用合同。

关键文件：

- `app.py`：桌面应用入口与命令行自检入口。
- `cardio_pc/ui.py`：Windows 桌面 UI，包含推理模式选择和“一键规则匹配”演示按钮。
- `cardio_pc/image_io.py`：PNG、DICOM/DCOM、GIF、TIFF、MP4、MOV、AVI 等输入的安全读取和代表帧采样。
- `cardio_pc/features.py`：B-mode、Color Doppler、动图差分、纹理和光流代理特征。
- `cardio_pc/diagnosis.py`：层级病症标签、Doppler 瓣膜定位评分、规则诊断、Gemma4 报告守卫和本地重渲染。
- `cardio_pc/agents.py`：轻量离线多智能体编排与审计链。
- `cardio_pc/function_calling.py`：Gemma4 原生函数调用白名单、tool manifest 和本地执行器。
- `cardio_pc/v5_echonet.py`：EchoNet-Dynamic 风格的 EF / 左室收缩功能减低校准层。
- `tools/submission_preflight.py`：提交前程序预检。
- `tools/anti_hang_smoke.py`：防卡死 smoke test。
- `tools/function_calling_smoke.py`：Gemma4 函数调用合同 smoke test。
- `run_cardio_pc_v5.bat`：PC V5 桌面 UI 启动入口。
- `stop_llama_server.bat`：停止本地 llama-server 的辅助脚本。

核心文档：

- [Gemma4 运行契约](docs/gemma4_runtime_contract.md)
- [Gemma4 函数调用合同](docs/gemma4_function_calling_contract.md)
- [架构说明](docs/architecture.md)
- [技术亮点](docs/competitive_edge.md)
- [数据与模型政策](docs/data_and_model_policy.md)
- [本地服务验证](docs/service_validation.md)
- [V5 技术状态](docs/V5_TECHNICAL_STATUS.md)

正式技术报告：

- [报告入口说明](REPORTS.md)
- [PDF 正式技术报告](submission/technical_report/CardioConsult_TrackC_APA_Technical_Report.pdf)
- [Word DOCX 正式技术报告](submission/technical_report/CardioConsult_TrackC_APA_Technical_Report.docx)
- [Markdown 正式技术报告](submission/technical_report/CardioConsult_TrackC_APA_Technical_Report.md)
- [中文 LaTeX 报告源](submission/technical_report/CardioConsult_Chinese_LaTeX_Report.tex)

历史 benchmark 副本、旧图表和阶段性报告没有删除，统一保存在 [archive](archive)。

演示材料：

- [demo.mp4](submission/demo_video/demo.mp4)，约 2 分 02 秒。
- [5 分钟演示脚本](submission/demo_video/CardioConsult_5min_demo_script_CN.md)

## 与端侧/边缘 AI 的对应关系

| 要点 | PC V5 对应实现 |
|---|---|
| 本地 Gemma4 主智能层 | 使用本地 Gemma4 4B GGUF，通过 `llama-cli` 或常驻 `llama-server` 完成结构化推理和报告生成 |
| 超声设备直连 | PC V5 可接入超声机器、无线超声软件、DICOM 工作站或局域网导出目录 |
| 边缘视觉工具链 | B-mode、Color Doppler 和动图分支先提取低维结构化证据，再交给 Gemma4 推理 |
| 原生函数调用 | `cardio_pc/function_calling.py` 提供 `summarize_ultrasound_features`、`run_rule_diagnosis`、`safety_boundary_check` 三个白名单工具 |
| 报告合同保护 | Gemma4 默认输出 JSON object，本地守卫重渲染为固定中文诊断字段 |
| 轻量多智能体 | `InputAgent -> FeatureAgent -> DiagnosisAgent -> ReportAgent -> SafetyAuditAgent` 串联运行并写入 `exports/agent_audit/` |
| 医学安全边界 | 安全声明、补扫建议、高危提示和“非医疗器械输出”由本地代码强制保留 |
| 演示稳定性 | 规则极速模式作为防卡后备；Gemma4 路径有硬超时，失败后自动降级为可审计报告 |
| 数据透明 | 数据来源、再分发边界、模型权重不随仓库发布的说明写入 `DATASETS.md` 和 `docs/data_and_model_policy.md` |

## 支持输入与输出

支持输入：

- PNG、JPG、BMP、TIFF、WebP、HEIC/HEIF
- DICOM、DCM、DCOM
- GIF、APNG、多帧 TIFF
- MP4、MOV、AVI、MKV、WebM、WMV 等常见视频或超声动图
- 单文件或多文件批量导入

输入范围：

- 最大目标：标准心脏超声 12 个体位。
- 最小目标：任意一个体位的收缩态与舒张态。
- 若文件名没有相位信息，系统会根据腔室面积代理自动估计收缩/舒张。
- 对 MP4/MOV 等动图，系统会按公平采样策略抽取代表帧，避免长视频导致 UI 长时间等待。

输出形式：

- 一段中文医学教学参考诊断。
- 第一字段强制包含“大方向 > 中方向 > 最小病症”的层级诊断。
- 必须给出最小病症、逻辑链、置信度/证据充分度、图像质量提示、补扫建议和安全声明。
- 对未携带 A4C/A2C/A3C 等标准切面名的 MP4 动态 B-mode 输入，若多帧腔室代理、低彩色多普勒干扰和低 EF 校准共同支持低 EF，规则层会输出“左心室收缩功能减低”作为最小病症。

示例：

```text
教学参考病症判断：轻度二尖瓣反流（瓣膜性心脏病 > 二尖瓣疾病）。
最小病症：轻度二尖瓣反流。
逻辑链：体位覆盖... + B-mode... + Doppler... -> Gemma4 tool-call/run_rule_diagnosis -> 瓣膜性心脏病 -> 二尖瓣疾病 -> 轻度二尖瓣反流。
```

## 快速启动

在 Windows 上安装 Python 3.10 或更高版本。首次使用先双击：

```bat
install_deps.bat
```

依赖安装完成后，日常启动双击：

```bat
run_cardio_pc_v5.bat
```

启动脚本会：

1. 创建 `.venv` 虚拟环境。
2. 如果缺少 `config.json`，从 `config.example.json` 创建。
3. 快速检查依赖是否已安装。
4. 启动桌面 UI。

`run_cardio_pc_v5.bat` 不会在后台静默运行 `pip install`，避免网络或镜像源变慢时看起来像卡死。缺少依赖时它会明确提示先运行 `install_deps.bat`。

## 推理模式

UI 提供三种模式：

| 模式 | 用途 |
|---|---|
| 规则极速模式 | 默认演示和防卡后备路径；不等待 GGUF，秒级返回同样格式的教学报告 |
| Gemma4 server 增强 | 推荐的完整离线 Gemma4 路径；复用常驻 `llama-server`，避免每例重新加载模型 |
| Gemma4 CLI 增强 | 兼容路径；每次通过 `llama-cli` 调用本地 GGUF，适合最小环境复现 |

默认选择规则极速模式，是为了保证真实导入超大 DICOM、视频或异常动图时不会无限等待。需要展示完整 Gemma4 4B 技术路线时，请先启动本地常驻服务，再在 UI 中切换到 `Gemma4 server 增强`。

启动本地常驻服务：

```powershell
powershell -ExecutionPolicy Bypass -File .\start_llama_server_v4.ps1
```

停止本地常驻服务：

```powershell
.\stop_llama_server.bat
```

服务默认地址：

```text
http://127.0.0.1:8088
```

教学演示中，如果现场曾经切到 Gemma4 增强路径但希望立即回到稳定输出，可以点击 UI 右侧操作区的“一键规则匹配”按钮。该按钮会切回 `rule_only`，停止当前慢任务等待，并把后续分析固定到本地层级规则路径，便于稳定展示“教学参考病症判断 / 最小病症 / 逻辑链”三个核心字段。

防卡保护默认值：

| 项目 | 默认值 |
|---|---:|
| 整例总预算 | 90 s |
| Gemma4 调用预算 | 60 s |
| 单文件解码预算 | 20 s |
| 每例最大代表帧 | 96 |

## 离线模型配置

仓库已包含 Windows llama.cpp 运行时：

```text
tools/llama_cpp/llama-b9469-bin-win-cpu-x64/
```

Gemma4 4B GGUF 权重不会提交到 GitHub。请通过授权渠道自行获取，并放到：

```text
models/gemma-4-4b-it-Q4_K_M.gguf
```

可选多模态投影文件：

```text
models/gemma-4-4b-mmproj-Q4_0.gguf
```

如需修改模型路径，请复制或编辑：

```text
config.example.json -> config.json
```

## 自检命令

不加载 GGUF 的快速规则自检：

```powershell
.\install_deps.bat
.\.venv\Scripts\python.exe app.py --self-test-rule-only
```

Gemma4 函数调用合同自检：

```powershell
.\.venv\Scripts\python.exe tools\function_calling_smoke.py
```

防卡 smoke：

```powershell
.\.venv\Scripts\python.exe tools\anti_hang_smoke.py
```

提交前程序预检：

```powershell
.\.venv\Scripts\python.exe tools\submission_preflight.py
```

完整配置自检：

```powershell
.\.venv\Scripts\python.exe app.py --self-test
```

完整自检可能调用 Gemma4。仅 CPU 机器上可能需要数分钟；规则自检只验证文件读取、特征提取、层级标签和输出格式。

## 技术流程

- B-mode 分支：鲁棒归一化、对数压缩、SRAD-inspired 散斑抑制、CLAHE-like 局部增强、DoG 边缘响应、腔室面积代理、纹理与 GLDM 风格统计。
- Color Doppler 分支：HSV 血流向量化、连通域过滤、喷流宽度代理、方向一致性、湍流/散度/涡量代理，并在体位证据不足时输出 MR/TR/AR/PR Doppler 瓣膜定位评分。
- 动图/视频分支：代表帧采样、时间差分、收缩/舒张推断、STI 风格腔室应变代理和 Lucas-Kanade 风格光流代理。
- 层级标签分支：大方向、中方向、最小病症、严重程度、证据充分度和来源说明。
- Gemma4 分支：通过结构化 JSON、原生函数调用和本地报告合同，把边缘证据组织成可审计中文教学报告。
- 多智能体审计分支：InputAgent、FeatureAgent、DiagnosisAgent、ReportAgent 和 SafetyAuditAgent 记录输入、特征、诊断、报告来源与安全边界。

## V5 验证摘要

授权本地 60 例 DICOM 教学数据的 V5 完整证据验证摘要：

| 目标 | V5 F1 |
|---|---:|
| 二尖瓣反流代理 | 96.4% |
| 三尖瓣反流代理 TR* | 100.0% |
| 主动脉瓣反流代理 | 70.0% |
| 低 EF 代理 | 85.7% |

12 帧代表抽样验证摘要：

| 目标 | V5 F1 |
|---|---:|
| 二尖瓣反流代理 | 93.6% |
| 三尖瓣反流代理 TR* | 100.0% |
| 主动脉瓣反流代理 | 32.6% |
| 低 EF 代理 | 61.5% |

TR* 这项不能解释为真实世界准确率 100%。当前 60 例教学测试批次中三尖瓣反流样本全部为阳性，缺少阴性对照，因此 1.000 主要表示本批阳性样本内没有漏报，不能证明特异性、阴性排除能力或真实泛化能力。

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
- [REPORTS.md](REPORTS.md)：唯一正式技术报告入口和归档说明。
- [DATASETS.md](DATASETS.md)：数据集来源、用途和再分发边界。
- [submission/technical_report](submission/technical_report)：APA 技术报告 DOCX/PDF/Markdown、图表和测试结果。
- [submission/demo_video/demo.mp4](submission/demo_video/demo.mp4)：演示视频。
- [docs/index.html](docs/index.html)：在线演示单文件规则匹配网页源码。
- [docs/V5_TECHNICAL_STATUS.md](docs/V5_TECHNICAL_STATUS.md)：V5 技术状态摘要。
- [validation/reports](validation/reports)：数据集验证报告。
- [shared](shared)：诊断契约、标签架构和提示词模板。

## 许可证

本仓库原创代码、脚本、UI、配置和文档采用 Apache License 2.0。第三方模型权重、医学数据集、超声软件、SDK、商标和用户提供的教学/临床数据不包含在本许可证范围内，仍受各自许可证、平台条款或机构授权约束。

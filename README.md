# CardioConsult PC V6

CardioConsult PC V6 是在 PC V5 参赛版基础上继续升级的离线心脏超声教学与基层辅助工作站。它不是另起炉灶的新规则系统，而是保留 V5 的本地 Gemma4 4B、B-mode / Color Doppler / 动图特征、多智能体审计、函数调用和中文报告合同，再新增一层面向真实心超工作流的临床规则手册、结构化测量值、病例级验证和防卡死机制。

一句话定位：**在只有便携式超声硬件、缺少心超专科医生或需要教学质控的环境中，把导出的 DICOM/DCOM/PNG/视频转成可审计证据，并由本地 Gemma4 4B 组织成带安全边界的中文教学参考报告。**

本项目仅用于医学教学、质量控制、算法研发和基层辅助参考，不作为临床最终诊断、治疗建议、急诊分诊或医嘱。

## 从 V5 到 V6

V5 已经完成了参赛版主干能力：本地离线 Gemma4 4B、超声图像边缘特征、动图处理、多智能体审计、函数调用、报告守卫、在线演示和提交材料。V6 的目标不是削弱这些能力，而是把 V5 变成更接近真实基层心超工作站的版本。

| V5 已有优势 | V6 升级方式 |
| --- | --- |
| 本地 Gemma4 4B 作为报告推理和智能编排层 | 保留 Gemma4 server / CLI 增强路径；规则层作为 Gemma4 可调用、可审计的工具链和防卡后备 |
| B-mode、Color Doppler、动态图特征提取 | 继续复用 V5 特征，并接入 temporal diff、STI 代理、optical flow、shared-EK、coupled-EK 和 EchoNet-Dynamic 低 EF 校准 |
| 层级病症输出和中文报告合同 | V6 固定输出“教学参考病症判断 / 最小病症 / 逻辑链”，避免 Gemma4 把具体病症泛化成模糊异常 |
| 多智能体审计与函数调用白名单 | 继续保留 `cardio_pc/agents.py` 和 `cardio_pc/function_calling.py`，记录报告来源、规则证据和安全边界 |
| DICOM/PNG/动图/视频导入 | 增加公平采样、并行解码、单文件超时、整例预算和 UI 急停 |
| V5 小样本验证和技术报告 | 新增规则书 smoke、病例级近临床验证和公开临床手册映射说明 |

详细升级说明见：[V6 从 V5 升级说明](docs/V6_UPGRADE_FROM_V5.md)。

## 适用场景

CardioConsult 的生态位是：**基层或教学环境中已经有便携式超声硬件，但图像采集质量、报告表达和初步判读经验不足**。

典型使用者包括：

- 基层全科医生、急诊/ICU/床旁超声使用者。
- 正在学习心脏超声的住培医生、医学生和规培带教团队。
- 需要做图像质控、报告规范化训练和病例复盘的教学场景。
- 需要离线部署、不能把敏感图像上传云端的本地工作站。

## 推荐启动

Windows 下进入仓库根目录：

```powershell
install_deps.bat
run_preflight.bat
run_cardio_pc_v6.bat
```

常用入口：

| 脚本 | 用途 |
| --- | --- |
| `run_cardio_pc_v6.bat` | 推荐入口，V5 技术底座 + V6 临床规则手册 UI |
| `run_ui.bat` | 兼容入口，当前会转到 V6 UI |
| `run_cardio_pc_v5.bat` | V5 原版兼容 UI，用于对照历史参赛版行为 |
| `run_v5_original_ui.bat` | 与 `run_cardio_pc_v5.bat` 等价的旧 UI 入口 |
| `run_self_test_rule_only.bat` | 规则路径自检，不等待 GGUF |
| `run_media_smoke_test.bat` | 用仓库样例跑一次媒体分析 |
| `run_gemma_emergency_stop_smoke.bat` | 验证 Gemma4 急停不会卡死 |
| `run_preflight.bat` | 检查本地交付完整性 |

第一次只想确认能否运行，可以先执行：

```powershell
run_self_test_rule_only.bat
run_media_smoke_test.bat
```

## 离线 Gemma4 4B

V6 仍然保留 V5 的 Gemma4 主线。完整技术路径不是“规则替代模型”，而是：

```text
超声输入
  -> V5 边缘视觉特征
  -> V6 临床规则手册与结构化证据
  -> Gemma4 4B 本地函数调用 / 报告推理
  -> 报告合同守卫
  -> 多智能体审计
  -> 中文教学参考诊断
```

默认 UI 选择“规则极速模式”，是为了保证没有 GGUF、模型服务未启动或输入大文件异常时仍能稳定输出。需要展示完整 Gemma4 技术路线时，先启动本地 server，再在 UI 中切换到 `Gemma4 server 增强`。

模型文件建议放在：

```text
models\gemma-4-4b-it-Q4_K_M.gguf
```

如果早期版本已经下载过模型，也可以在 UI 中继续指向旧路径，例如：

```text
D:\cardioconsult_PC_runbook\models\gemma-4-4b-it-Q4_K_M.gguf
```

启动和停止本地模型服务：

```powershell
start_llama_server_v4.bat
stop_llama_server.bat
```

Gemma4 运行中如果变慢或卡住，UI 提供两个演示安全按钮：

- `急停 Gemma`：中断当前 llama-cli 或尝试停止本地 llama-server。
- `紧急规则模式`：放弃当前 Gemma4 等待，立刻回到纯规则报告。

## 输入与输出

一次输入应对应一个病人或一次检查，可以选择多个文件，也可以选择一个文件夹。

支持格式：

```text
.dcm .dicom .dcom .png .jpg .jpeg .gif .tif .tiff .mp4 .mov .avi
```

建议输入：

- 最理想：标准心脏超声多切面动态图或 DICOM 序列。
- 可接受：PNG/JPG 截图、多帧 GIF、MP4/MOV/AVI 动图。
- 最小输入：任意一个体位的收缩态与舒张态，系统会尝试自动区分相位。

固定核心输出字段：

```text
教学参考病症判断
最小病症
逻辑链
```

同时输出规则命中表、证据等级、缺失证据、补扫建议、B-mode / Doppler / 动态代理特征、文件解码摘要、医生填写或系统自动填充的临床测量值、安全边界和多智能体审计摘要。

示例输出逻辑：

```text
教学参考病症判断：心肌与心功能异常 > 左室收缩功能减低 > 轻度左室收缩功能减低
最小病症：轻度左室收缩功能减低
逻辑链：规则 lv_systolic_function_reduced_v1 -> 证据等级 A -> EF=43% 命中 mild
```

## V6 新增临床规则手册

V6 的规则书位于：

```text
config\clinical_rulebook_v0.1.json
```

当前覆盖：

- 左室收缩功能减低 / EF 相关判断。
- 二尖瓣反流、三尖瓣反流、主动脉瓣反流、主动脉瓣狭窄。
- 二尖瓣反流合并三尖瓣反流组合代理判断。
- 肺动脉瓣反流代理判断。
- 心包积液、右心负荷 / 肺高压提示。
- 舒张功能异常或左室充盈压升高提示。
- 节段性室壁运动异常代理判断。
- 左室肥厚倾向、左房增大。

规则书把证据分成两层：

- `临床量化指标`：EF、VC、EROA、TRV、Vmax、mean gradient、AVA、LAVI、IVS/LVPW 等医生或设备提供的测量值，证据等级更高。
- `图像代理特征`：来自 V5 图像处理、Doppler 向量化、动图差分、STI/光流代理和本地校准器，适合教学提示和补扫建议。

公开手册映射见：[public_manual_mapping.md](docs/public_manual_mapping.md)。V5 经验补齐记录见：[v5_rule_completion_20260621.md](docs/v5_rule_completion_20260621.md)。

## UI 与防卡

V6 UI 在 V5 的输入输出合同上增加了更接近现场使用的控制：

- 推理模式：`规则极速模式`、`Gemma4 server 增强`、`Gemma4 CLI 增强`。
- Gemma4 急停和紧急规则模式。
- 多文件公平采样，默认最多 12 个代表文件。
- 最大代表帧、单文件解码超时、Gemma4 超时和整例预算。
- 医生可手填 EF、MR VC、MR EROA、TR VC、TRV、AS Vmax、AVA、AR VC、E/e'、LAVI、IVS/LVPW 等测量值。
- 分析结束后，系统可根据规则命中自动填充空白测量项，但不会覆盖医生手填内容。

自动填充值只用于教学演示和规则审计，不等同于真实标尺、频谱或正式定量测量。

## 代码结构

V6 的目录结构刻意保留 V5 主干，并在其上加规则手册层：

| 路径 | 角色 |
| --- | --- |
| `cardio_pc/` | V5 运行底座：图像处理、DICOM/视频读取、诊断经验、多智能体、Gemma4 函数调用、V5 UI |
| `src/` | V6 临床规则手册层：规则引擎、媒体适配器、新 UI、命令行分析入口 |
| `config/clinical_rulebook_v0.1.json` | V6 规则书与阈值、证据等级、引用来源 |
| `shared/` | V5/V6 共用诊断合同、特征 schema、病症标签 |
| `prompts/` | Gemma4 层级诊断和报告守卫提示词 |
| `docs/` | 技术说明、函数调用合同、规则映射、V6 升级说明 |
| `submission/` | 演示视频、技术报告和提交材料 |
| `validation/` | smoke、EchoBench 归档、病例级近临床验证摘要 |

因此，V6 的工程关系是：

```text
cardio_pc/ V5 core
  + src/ V6 rulebook adapter
  + config/clinical_rulebook_v0.1.json
  + Gemma4 report and audit contract
```

## 精度与验证

### 规则书 smoke

```powershell
python tools\rulebook_accuracy_smoke.py
```

本分支实跑结果：

| 测试项 | 结果 |
| --- | ---: |
| 测试病例数 | 14 |
| Top label 命中数 | 14 / 14 |
| Exact top-label accuracy | 1.000 |
| Macro F1，不含 normal | 1.000 |

这是规则引擎集成 smoke，使用合成 patient-level feature payload 检查每条主要规则能否稳定触发，**不是临床泛化准确率**。

### 病例级近临床验证

```powershell
python tools\clinical_like_validation.py --case-limit 20 --max-files-per-case 12 --max-loaded-frames 48
```

该测试以一个患者检查 / 一个 DICOM zip 为分析单位，输入为真实本地 DICOM 文件，金标准标签来自同批报告表中的 `诊断结果` 与 `检查所见` 字段。脚本不把原始 DICOM、报告全文或患者信息写入仓库，只输出脱敏统计结果。

| 模式 | 病例数 | OK | Macro F1 | 任一支持异常敏感性 | 平均耗时/例 | P95 耗时/例 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| image_only | 20 | 20 | 0.482 | 1.000 | 7.085s | 7.894s |
| measurement_assisted | 20 | 20 | 0.542 | 1.000 | 7.085s | 7.894s |

这轮验证的价值不在于宣称临床准确率，而是暴露真实 DICOM 下代理特征的风险：旧代理容易过度触发心包积液、右心负荷和局部室壁运动异常。因此 V6 已收紧这些代理阈值，并优先使用医生/设备提供的结构化测量值作为高证据等级输入。

输出文件：

```text
validation\clinical_like_20260621\clinical_like_validation_report.md
validation\clinical_like_20260621\clinical_like_metrics.csv
validation\clinical_like_20260621\clinical_like_summary.json
```

### 归档 EchoBench 60 例

V5/V4 归档验证位于：

```text
archive\performance_runs\validation_speedopt\freeze_runs_full\echobench_20260604_180638
```

该归档为 60 例、纯规则/V4 校准、不调用 GGUF 的结果：

| 标签 | F1 | Sensitivity | Specificity |
| --- | ---: | ---: | ---: |
| valve_any | 1.000 | 1.000 | 0.000 |
| MR | 0.964 | 0.964 | 0.600 |
| TR | 1.000 | 1.000 | 0.000 |
| AR | 0.700 | 0.724 | 0.677 |
| low EF | 0.857 | 1.000 | 0.963 |
| RWMA | 0.500 | 0.333 | 1.000 |
| LA enlargement | 0.696 | 1.000 | 0.865 |

这些指标用于工程验证和教学原型评估；若进入真实临床研究，需要多中心、前瞻性、专家盲审和正式统计方案。

## 提交材料入口

- [SUBMISSION.md](SUBMISSION.md)：提交检查表和评审入口。
- [REPORTS.md](REPORTS.md)：正式技术报告入口和归档说明。
- [DATASETS.md](DATASETS.md)：数据集来源、用途和再分发边界。
- [submission/technical_report](submission/technical_report)：APA 技术报告 DOCX/PDF/Markdown、图表和测试结果。
- [submission/demo_video/demo.mp4](submission/demo_video/demo.mp4)：演示视频。
- [docs/index.html](docs/index.html)：在线演示单文件规则匹配网页源码。
- [docs/V6_UPGRADE_FROM_V5.md](docs/V6_UPGRADE_FROM_V5.md)：V6 相对 V5 的技术升级说明。
- [docs/gemma4_runtime_contract.md](docs/gemma4_runtime_contract.md)：Gemma4 运行契约。
- [docs/gemma4_function_calling_contract.md](docs/gemma4_function_calling_contract.md)：Gemma4 函数调用合同。
- [docs/service_validation.md](docs/service_validation.md)：本地服务验证。

## 开发者验证

推荐提交前运行：

```powershell
python -m py_compile app.py legacy_v5_app.py src\image_case_adapter.py src\clinical_rule_engine.py src\rulebook_ui.py cardio_pc\diagnosis.py cardio_pc\ui.py tools\rulebook_accuracy_smoke.py tools\clinical_like_validation.py tools\submission_preflight.py
run_self_test_rule_only.bat
run_media_smoke_test.bat
run_gemma_emergency_stop_smoke.bat
run_preflight.bat
```

## 项目边界

CardioConsult 当前是医学教学、算法演示和基层辅助参考系统。它强调：

- 可审计规则优先于黑箱输出。
- Gemma4 负责结构化推理、函数调用、教学解释和报告组织，但不能越过报告合同任意改写核心病症字段。
- 医生手填量化指标优先于代理特征。
- 图像质量或切面不足时，必须提示补扫或复核。
- 正式诊断仍需完整标准切面、DICOM 标尺、连续动态帧、病史、体征和有资质医师报告。

## 许可证

本项目使用 Apache-2.0 License。第三方依赖、数据集、模型权重、超声软件、SDK、商标和用户提供的教学/临床数据不包含在本许可证范围内，仍受各自许可证、平台条款或机构授权约束。

相关文件：

- [LICENSE](LICENSE)
- [NOTICE](NOTICE)
- [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)
- [DATASETS.md](DATASETS.md)

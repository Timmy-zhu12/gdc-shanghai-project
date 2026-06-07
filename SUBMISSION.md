# Gemma4 离线心超项目提交检查表

本文件是评审进入 CardioConsult 项目的中文总入口。

官方页面：[Gemma 4 Hackathon 2026](https://hackathon.googdg.cn/?lang=en)

本仓库采用 Windows PC V5 作为唯一稳定、可复现的离线参考实现。PC V5 被定义为可直接接入超声机器或超声工作站的本地分析终端，可通过 USB、局域网共享目录、DICOM 工作站导出目录或无线超声软件导出文件读取资料，并在本机完成边缘视觉特征提取、Gemma4 4B 结构化推理、函数调用、多智能体审计、规则防卡后备、技术报告和在线演示。

## 核心技术叙事

CardioConsult 的主线不是“规则系统外加一个模型润色器”，而是“本地 Gemma4 4B 作为医学教学报告推理和多智能体编排层，规则/特征工程作为它的可审计工具链与防卡后备路径”。

实际链路如下：

```text
超声输入
  -> B-mode / Doppler / 动图边缘特征
  -> 结构化病例证据
  -> Gemma4 原生函数调用
  -> 本地规则诊断工具与安全检查工具
  -> Gemma4 报告组织
  -> 本地报告合同重渲染
  -> 审计 JSON 与中文教学参考诊断
```

默认规则极速模式用于保证现场不卡。完整技术演示应重点展示 Gemma4 server 增强路径、函数调用 smoke、`gemma4_structured` 报告来源和本地审计链。

## 必交材料

| 要求 | CardioConsult 对应材料 | 状态 |
|---|---|---|
| 代码仓库 | 本仓库：`https://github.com/Timmy-zhu12/gdc-shanghai-project` | 已准备 |
| 5 分钟内演示视频 | [submission/demo_video/demo.mp4](submission/demo_video/demo.mp4)；录制脚本见 [submission/demo_video/CardioConsult_5min_demo_script_CN.md](submission/demo_video/CardioConsult_5min_demo_script_CN.md) 与 DOCX 版 | 已准备 |
| 技术报告 | [DOCX](submission/technical_report/CardioConsult_TrackC_APA_Technical_Report.docx)、[PDF](submission/technical_report/CardioConsult_TrackC_APA_Technical_Report.pdf)、[Markdown](submission/technical_report/CardioConsult_TrackC_APA_Technical_Report.md)、[中文 LaTeX 源](submission/technical_report/CardioConsult_Chinese_LaTeX_Report.tex) | 已准备 |
| 在线演示链接 | 单文件规则匹配网页已发布：`https://timmy-zhu12.github.io/gdc-shanghai-project/`；源码位于 [docs/index.html](docs/index.html) | 已上线 |
| 训练/验证数据来源披露 | [DATASETS.md](DATASETS.md) 和 [docs/data_and_model_policy.md](docs/data_and_model_policy.md) | 已准备 |
| 技术亮点说明 | [docs/competitive_edge.md](docs/competitive_edge.md) | 已准备 |
| Gemma4 运行契约 | [docs/gemma4_runtime_contract.md](docs/gemma4_runtime_contract.md)，说明模型输入、规则工具、报告保护和审计字段 | 已准备 |
| 原生函数调用 | [docs/gemma4_function_calling_contract.md](docs/gemma4_function_calling_contract.md) 与 `cardio_pc/function_calling.py`，展示 Gemma4 tool manifest、白名单函数和非法工具拒绝逻辑 | 已准备 |
| 本地服务验证 | [docs/service_validation.md](docs/service_validation.md)，包含 `llama-server` 端口、`/completion` smoke、项目诊断链路和多智能体审计检查 | 已通过 |
| 提交前程序预检 | `python tools/submission_preflight.py`，检查关键材料、仓库卫生、规则自检、防卡 smoke、函数调用 smoke、旧模型词和乱码标记 | 已准备 |
| 许可证 | [Apache License 2.0](LICENSE) 与 [NOTICE](NOTICE) | 已准备 |

## 仓库范围

本仓库就是当前提交仓库。PC V5 是本次提交中唯一积极维护、可直接运行的版本；较早的平台原型只作为后续迁移方向，不作为评审复现当前结果的必要材料。

## 评审维度对应关系

| 评审维度 | 权重 | 建议检查内容 |
|---|---:|---|
| 真实影响 | 30% | 医学教学与基层心脏超声参考流程；PC 可部署在超声设备旁直接读取导出资料；本地处理脱敏图像；README 和 UI 中的安全边界 |
| 技术能力 | 25% | 本地 Gemma4 4B、原生函数调用、结构化 JSON 合同、多智能体审计、B-mode GLDM/纹理代理、Color Doppler HSV/向量代理、Doppler 瓣膜定位评分、动图/DICOM 支持、EchoNet-Dynamic EF 校准 |
| 完整性 | 20% | 可运行 PC V5 仓库、在线规则演示、演示视频、技术报告、数据披露、启动脚本、规则自检、防卡 smoke、函数调用 smoke |
| 创新性 | 15% | 把 Gemma4 4B 放在离线医学教学报告推理层，而不是云端聊天；用函数调用和本地审计把医学规则、视觉特征和安全边界连接起来 |
| 展示质量 | 10% | APA 技术报告、DOCX/PDF/Markdown/LaTeX、多图表验证材料、README 部署说明、单文件在线演示和 5 分钟演示视频 |

## 离线演示路径

建议评审演示顺序：

1. 打开在线演示链接，先看到产品输入输出合同。
2. 克隆或打开本仓库，运行 `run_cardio_pc_v5.bat`。
3. 展示 PC V5 从超声机器/工作站导出目录读取 PNG、DICOM、DCOM、cine/视频输入，以及一致的诊断输出字段。
4. 先用“规则极速模式”证明真实演示不卡，再切换到 `Gemma4 server 增强` 展示离线模型推理链路。
5. 运行 `python tools\function_calling_smoke.py`，展示 Gemma4 原生函数调用白名单和非法工具拒绝。
6. 展示 `exports/agent_audit/` 中的审计 JSON，说明报告来源字段如何区分 `gemma4_structured`、`gemma4_repaired` 和 `rule_template`。
7. 说明模型权重和原始数据因许可证与隐私原因不随仓库分发，然后展示验证摘要、TR* 偏倚说明和医学安全边界。

## 技术强项

- Gemma4 主智能层：Gemma4 4B 负责结构化证据推理、函数调用、报告组织、层级诊断解释和安全边界整理。
- 边缘视觉工具链：B-mode、Color Doppler 和动图分支先在本地生成可审计低维特征，再交给 Gemma4 使用。
- 函数调用可复现：`tools/function_calling_smoke.py` 可在无 GGUF、无网络条件下验证 `summarize_ultrasound_features`、`run_rule_diagnosis` 和 `safety_boundary_check` 三个内部工具。
- 模型贡献可审计：多智能体审计会记录最终报告来自 `gemma4_structured`、`gemma4_preserved`、`gemma4_repaired`、`gemma4_guarded_template` 还是 `rule_template`。
- 离线优先：PC V5 可放在超声检查室或基层医疗点内，图像资料不需要上传到云端。
- 动态心超增强：EchoNet-Dynamic 校准层增强 EF / 左室收缩功能减低识别，同时保留可审计瓣膜反流规则。
- 防卡设计：规则极速模式、文件解码超时、Gemma4 调用超时和整例预算保证真实大文件输入不会无限等待。
- 层级医学输出：报告必须包含大方向、中方向、最小病症、分级、证据充分度和逻辑链。
- 数据透明：所有公开数据集和文献来源列于 `DATASETS.md`；原始数据、病人图像和模型权重不随仓库分发。

## 本地快速自检

Windows PC：

```powershell
git clone https://github.com/Timmy-zhu12/gdc-shanghai-project.git
Set-Location gdc-shanghai-project
.\install_deps.bat
.\.venv\Scripts\python.exe app.py --self-test-rule-only
.\.venv\Scripts\python.exe tools\anti_hang_smoke.py
.\.venv\Scripts\python.exe tools\function_calling_smoke.py
.\.venv\Scripts\python.exe tools\submission_preflight.py
.\run_cardio_pc_v5.bat
```

## 医学安全边界

CardioConsult 是医学教学和算法演示原型，不是医疗器械，不能作为最终临床诊断、治疗建议、急诊分诊指令或医嘱。正式判断仍需完整标准心脏超声切面、DICOM 标尺信息、连续动态帧、病史、体征和有资质医师复核。

## 提交前人工检查项

- 演示视频已放入 `submission/demo_video/demo.mp4`。
- 确认在线演示 URL `https://timmy-zhu12.github.io/gdc-shanghai-project/` 仍可访问。
- 确认本仓库为公开仓库，或评审可访问。
- 确认没有提交原始病人数据、模型权重、`config.json`、包含密钥的本地路径或数据集下载缓存。

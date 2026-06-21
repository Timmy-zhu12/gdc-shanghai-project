# CardioConsult 临床规则手册版（V5 对齐本地交付）

本目录是一个独立的本地交付版，位置为：

```text
D:\cardioconsult_rulebook_v5_aligned_20260620
```

它把新版“临床手册规则引擎”与 PC V5 的工程能力合并到一个目录中：新版负责按公开临床手册阈值输出可审计规则判断，V5 资产负责图像解码、B-mode/Color Doppler 特征提取、动图兼容、Gemma4 4B 可选增强、多智能体审计、样例数据、许可证和技术文档。旧目录没有被修改。

## 推荐启动方式

第一次使用建议先运行：

```powershell
cd /d D:\cardioconsult_rulebook_v5_aligned_20260620
install_deps.bat
run_preflight.bat
run_ui.bat
```

常用入口：

- `run_ui.bat`：新版临床规则手册 UI，推荐用于真实 DICOM/DCOM/PNG/视频输入；同一界面内支持规则极速模式、Gemma4 server 增强和 Gemma4 CLI 增强。
- `run_v5_original_ui.bat`：V5 原版兼容 UI，保留“规则极速模式 / Gemma4 server 增强 / Gemma4 CLI 增强”和“一键规则匹配”。
- `run_cardio_pc_v5.bat`：V5 命名兼容入口，等同于打开 `run_v5_original_ui.bat`。
- `run_self_test_rule_only.bat`：不启动 UI、不等待 GGUF，只跑规则自检。
- `run_media_smoke_test.bat`：用本目录自带样例图像跑一次媒体分析。
- `run_gemma_emergency_stop_smoke.bat`：模拟慢 `llama-cli`，验证 Gemma4 急停能在数秒内杀掉进程。
- `run_preflight.bat`：检查本地交付完整性，结果写入 `submission/preflight/current_preflight.md`。

## 输入与输出

输入以一个病人或一次检查为单位，可以同时选择多个文件或一个文件夹。支持格式包括：

```text
.dcm .dicom .dcom .png .jpg .jpeg .gif .tif .tiff .mp4 .mov .avi
```

输出保留项目的三个核心字段：

```text
教学参考病症判断
最小病症
逻辑链
```

同时输出规则命中表、证据等级、缺失证据、安全边界、代理特征、解码摘要，以及可选的医生填写/自动填充临床测量值。

## 与 V5 相比补齐的内容

本交付版已补齐 V5 的主要工程交付件：

- `cardio_pc/`：V5 图像处理、特征提取、诊断、UI、多智能体审计和函数调用模块。
- `samples/`：V5 合成 B-mode、彩色 Doppler、GIF、MP4、TIFF 样例。
- `tools/`：EchoBench、anti-hang smoke、函数调用 smoke、训练/验证脚本和 llama.cpp 本地运行器。
- `shared/`：疾病标签、特征 schema、诊断契约和 Gemma4 report prompt。
- `prompts/`：层级诊断系统提示词。
- `calibration/`：低 EF 校准样例。
- `models/`：模型放置说明和占位文件。
- `docs/v5_reference/`：V5 技术状态、部署矩阵、运行契约、在线 demo 文档等参考材料。
- `validation/`、`submission/technical_report/`：既有验证报告和技术报告材料。
- `LICENSE`、`NOTICE`、`THIRD_PARTY_NOTICES.md`：Apache-2.0 许可证和第三方说明。

## 新版规则手册能力

新版规则手册 UI 在 V5 的图像处理基础上增加了更接近临床手册的规则层：

- EF / 左室收缩功能下降。
- 二尖瓣反流、三尖瓣反流、主动脉瓣反流。
- 二尖瓣反流伴三尖瓣反流组合代理判断。
- 肺动脉瓣反流代理判断。
- 主动脉瓣狭窄。
- 心包积液。
- 右心负荷增加或肺高压提示。
- 舒张功能异常或左室充盈压升高提示。
- 节段性室壁运动异常代理判断。
- 左室肥厚倾向。
- 左房增大。

规则优先使用医生填写或 DICOM 可提取的临床测量值；如果缺少真实测量值，则使用 B-mode、Color Doppler 和动态图代理特征，并明确标注 `proxy_only` 或证据等级下降。

2026-06-21 已进一步补齐 V5 诊断经验：图像适配层重新接入 temporal diff、STI 代理、optical flow、shared-EK、coupled-EK、EchoNet-Dynamic 低 EF 校准，以及心包暗带、右心大小和室间隔压扁代理量。详细记录见 `docs/v5_rule_completion_20260621.md`。

## 临床测量值填写与自动填充

左侧“可选临床测量值”支持两种来源：

- 医生在分析前手动填写，系统不会覆盖。
- 分析结束后，系统根据规则命中和严重度自动填充空白项，并标注来源，例如“自动估算-规则”或“自动估算-代理”。

这些自动值只用于教学演示和规则审计，不等同于真实标尺、频谱或定量测量。

## 大文件防卡策略

默认 UI 使用极速安全设置：

- 最大代表帧：48。
- 单文件解码超时：6 秒。
- 代表文件数：12。
- 并行解码数：4。

如果一次输入 22 个 DCOM 文件，系统会先做公平采样和并行解码，避免逐个 DICOM 完整阻塞。若需要全量解码，可把“代表文件数”改为 `0`，但耗时会明显增加。

## Gemma4 4B 离线增强

默认诊断不等待 GGUF，优先走可审计规则路径。若要启用离线 Gemma4 4B，请把模型放到：

```text
models\gemma-4-4b-it-Q4_K_M.gguf
```

也可以继续使用最早版本的本地缓存路径：

```text
D:\cardioconsult_PC_runbook\models\gemma-4-4b-it-Q4_K_M.gguf
```

启动 server：

```powershell
start_llama_server_v4.bat
```

停止 server：

```powershell
stop_llama_server.bat
```

随后打开 `run_ui.bat`，在左侧 `Gemma4 离线增强` 中选择 `Gemma4 server 增强` 或 `Gemma4 CLI 增强`。新版 UI 的运行顺序固定为：

```text
安全解码与公平采样 -> B-mode/Doppler 特征 -> 临床规则引擎 -> 可选 Gemma4 教学解释增强
```

Gemma4 不能改写规则引擎给出的 `教学参考病症判断 / 最小病症 / 逻辑链`，只能围绕已命中的规则、证据等级、缺失项、补扫建议和安全边界做教学解释。`run_v5_original_ui.bat` 仍保留为 V5 原版兼容入口。

新版规则手册 UI 和 V5 原版兼容 UI 均保留应急能力：

- `急停 Gemma`：分析过程中如果 Gemma4 CLI 或本地 llama-server 卡住，立即发出取消信号，并终止活动的 `llama-cli` 进程；如果使用本地 server，会尝试停止 8088 端口上的 `llama-server`。
- `紧急规则模式`：中断 Gemma4 后立刻切换为纯规则模式。如果 B-mode/Doppler 特征已经提取完成，会直接用已有特征生成规则报告；如果还没到特征阶段，会取消当前任务并以纯规则模式重新分析。

## 安全边界

本项目仅用于医学教学、质量控制、算法研发和基层辅助参考，不作为临床最终诊断、治疗建议或医嘱。任何输出都应结合完整标准切面、DICOM 标尺、连续动态帧、病史、体征和有资质医师报告复核。

# CardioConsult V5 对齐状态

生成日期：2026-06-20

## 对齐目标

在不修改历史 V5 目录的前提下，将新版临床规则手册测试版补齐到接近 PC V5 的本地交付状态：单目录可启动、可自检、可读取真实 DICOM/DCOM/PNG/动图/视频、可保留 Gemma4 4B 离线增强路径、可追溯规则证据、可保留技术报告和许可证。

## 已补齐内容

| 模块 | 状态 | 说明 |
|---|---:|---|
| V5 图像处理包 `cardio_pc/` | 已补齐 | 包含 DICOM/PNG/视频读取、特征提取、诊断、UI、多智能体、函数调用模块。 |
| 新版规则手册引擎 `src/` | 已保留并增强 | 默认使用本目录 `cardio_pc`，不再依赖旧 V5 路径。 |
| UI | 已补齐 | `run_ui.bat` 为新版规则手册 + Gemma4 离线增强 UI；`run_v5_original_ui.bat` 和 `run_cardio_pc_v5.bat` 为 V5 原版兼容 UI。 |
| Gemma4 增强 | 已新增 | 新版规则手册 UI 支持 `规则极速模式`、`Gemma4 server 增强`、`Gemma4 CLI 增强`；Gemma4 只能解释规则结果，不能改写核心诊断字段。 |
| Gemma4 急停 | 已新增 | 新版规则手册 UI 和 V5 原版兼容 UI 均提供 `急停 Gemma` 与 `紧急规则模式`；底层支持中断 `llama-cli` 进程树和本地 8088 `llama-server`。 |
| DICOM/DCOM/PNG/视频兼容 | 已补齐 | 新版 UI 可直接选择多个文件或文件夹；默认公平采样、并行解码和超时保护。 |
| 规则极速模式 | 已补齐 | `run_self_test_rule_only.bat` 和新版 UI 默认不等待 GGUF。 |
| Gemma4 4B server/CLI 路径 | 已补齐 | 保留 `start_llama_server_v4.bat/.ps1`、`stop_llama_server.bat/.ps1`、`config.example.json`。 |
| llama.cpp 本地运行器 | 已补齐 | 从 V5 复制 `tools/llama_cpp/`。 |
| 样例文件 | 已补齐 | 从 V5 复制 `samples/`。 |
| 共享契约与提示词 | 已补齐 | 从 V5 复制 `shared/`、`prompts/`。 |
| 校准文件 | 已补齐 | 从 V5 复制 `calibration/`。 |
| 技术文档与验证材料 | 已补齐 | V5 文档放在 `docs/v5_reference/`，验证和技术报告材料放在 `validation/`、`submission/technical_report/`。 |
| 许可证 | 已补齐 | Apache-2.0 `LICENSE`、`NOTICE`、`THIRD_PARTY_NOTICES.md`。 |
| 本地预检 | 已新增 | `tools/submission_preflight.py` 改为本目录专用检查，`run_preflight.bat` 可直接运行。 |

## 新版相对 V5 的新增点

- 引入公开临床手册阈值映射：EF、瓣膜反流、主动脉瓣狭窄、心包积液、肺高压/右心负荷、舒张功能等。
- 将“临床量化指标”和“代理特征”分层处理，输出证据等级和缺失证据。
- UI 支持医生手填临床测量值，并在诊断后自动填充空白项，且不覆盖医生填写项。
- UI 支持在同一规则引擎工作流内启用 Gemma4 4B 离线增强，用于教学解释、复核重点和补扫建议。
- 多 DCOM 输入默认并行公平采样，减少真实导入大文件时的卡顿。
- 新版默认单目录依赖，不再把旧 V5 目录作为运行前提。

## 保留为可选的能力

- Gemma4 4B GGUF 推理：默认不等待模型；需要增强文本解释时再启动 server 或使用 V5 原版 UI。
- EchoNet V5 深度学习校准：保留训练/验证脚本和模型放置说明，缺少本地校准模型时回退规则路径。
- 技术报告和验证报告：作为参考材料保留，不会影响新版 UI 启动。

## 本地验收命令

```powershell
cd /d D:\cardioconsult_rulebook_v5_aligned_20260620
run_self_test_rule_only.bat
run_media_smoke_test.bat
run_gemma_emergency_stop_smoke.bat
run_preflight.bat
```

通过后即可使用：

```powershell
run_ui.bat
```

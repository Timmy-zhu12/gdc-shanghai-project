# 提交要求对应说明

已核对官方页面：[Gemma 4 Hackathon 2026](https://hackathon.googdg.cn/?lang=en)

## 已解析的提交要求

官方要求强调端侧/边缘 AI、可运行代码、真实设备演示、技术报告、在线演示链接和训练数据来源披露。本仓库把 Windows PC V5 作为唯一稳定复现入口，并把 PC 定义为可直接接入超声机器或工作站导出目录的离线分析终端。

## 已应用到 PC 仓库的改动

| 要求压力 | 仓库改动 |
|---|---|
| 可运行代码仓库 | V5 代码已同步到本 PC 仓库；旧启动脚本仅保留兼容用途 |
| 本地 Gemma4 4B | 提供 `config.example.json`、内置 llama.cpp 运行时、`llama-cli` 和常驻 `llama-server` 路径 |
| Gemma4 主路线 | README、SUBMISSION、架构和运行契约都明确 Gemma4 是结构化推理与报告生成主智能层 |
| 原生函数调用 | 新增 `cardio_pc/function_calling.py`、`docs/gemma4_function_calling_contract.md` 和 `tools/function_calling_smoke.py` |
| 完整性 | 提供 `app.py --self-test-rule-only`、`tools/anti_hang_smoke.py`、`tools/submission_preflight.py` |
| 展示质量 | README 补充部署步骤、模型放置、验证摘要、TR* 偏倚说明和安全边界 |
| 数据/模型合规 | `.gguf` 权重不进 Git，并明确 `models/` 放置方式 |
| 演示稳定性 | 默认规则极速模式；Gemma4 server/CLI 增强均有硬超时，失败自动降级 |
| 可控模型输出 | Gemma4 默认输出结构化 JSON，本地报告守卫负责渲染固定中文诊断字段并记录 `gemma4_structured` 审计来源 |
| 真实设备路径 | PC V5 可放置在超声检查室或基层医疗点，通过 USB、局域网共享目录、DICOM 工作站导出目录或无线超声软件导出文件读取资料 |
| 多智能体审计 | `cardio_pc/agents.py` 把输入、特征、诊断、报告和安全边界拆成可审计本地 agent 链路 |

## 提交前仍需人工确认

- 演示视频文件 `submission/demo_video/demo.mp4` 可播放。
- 在线演示链接 `https://timmy-zhu12.github.io/gdc-shanghai-project/` 可访问。
- 仓库没有提交原始病人资料、GGUF 权重、私有数据集缓存或本地 `config.json`。
- `python tools\submission_preflight.py` 通过。

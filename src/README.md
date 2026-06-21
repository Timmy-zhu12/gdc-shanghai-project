# V6 Rulebook Layer

`src/` 是 CardioConsult PC V6 在 V5 核心之上的临床规则手册层。它不替代 `cardio_pc/` 中的 V5 图像处理、Gemma4 推理、多智能体审计和函数调用能力，而是把这些能力整理成更接近真实心超工作流的病例级规则证据。

| 文件 | 职责 |
| --- | --- |
| `clinical_rule_engine.py` | 读取 `config/clinical_rulebook_v0.1.json`，输出病症层级、最小病症、证据等级和逻辑链 |
| `image_case_adapter.py` | 调用 V5 图像处理能力，把 DICOM/DCOM/PNG/视频整理为 patient-level evidence |
| `rulebook_ui.py` | V6 桌面 UI，保留 V5 输入输出合同，并新增测量值、急停、紧急规则模式和规则书解释 |
| `analyze_media_cli.py` | 命令行媒体分析入口，供 smoke、preflight 和自动验证调用 |

运行入口是仓库根目录的 `run_cardio_pc_v6.bat`。

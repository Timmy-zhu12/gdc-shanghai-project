# V5 Core Runtime

`cardio_pc/` 保留 CardioConsult PC V5 的核心运行能力，是 V6 的技术底座。

| 文件 | 职责 |
| --- | --- |
| `features.py` / `imaging.py` | B-mode、Color Doppler、DICOM、动态图和视频特征处理 |
| `diagnosis.py` | V5 层级诊断经验、Gemma4 调用、报告守卫和兼容规则 |
| `agents.py` | 离线多智能体审计链 |
| `function_calling.py` | Gemma4 函数调用白名单与本地工具执行 |
| `v5_echonet.py` | EchoNet-Dynamic 风格低 EF 校准层 |
| `ui.py` | V5 原版兼容 UI |

V6 不删除这些能力，而是在 `src/` 中增加临床规则手册层，并通过 `run_cardio_pc_v6.bat` 作为新的推荐入口。

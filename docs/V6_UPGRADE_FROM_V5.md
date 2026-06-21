# V6 从 V5 升级说明

本文说明当前 `v6-rulebook-aligned-20260621` 分支与 PC V5 参赛版的关系。V6 不是替换 V5 的新项目，而是在 V5 已有离线 Gemma4 4B、边缘图像特征、多智能体审计和提交材料基础上，增加临床规则手册、结构化测量值和接近真实输入的验证流程。

## 继承自 V5 的能力

| V5 模块 | V6 中的位置 | 说明 |
| --- | --- | --- |
| 图像和视频处理 | `cardio_pc/features.py`、`cardio_pc/imaging.py`、`src/image_case_adapter.py` | B-mode、Color Doppler、动态图代表帧、DICOM/PNG/视频读取继续复用 |
| 层级诊断经验 | `cardio_pc/diagnosis.py`、`shared/disease_labels.json` | 保留大方向、中方向、最小病症的输出合同 |
| Gemma4 本地推理 | `cardio_pc/diagnosis.py`、`docs/gemma4_runtime_contract.md` | 保留 server / CLI 两条离线增强路径 |
| 函数调用白名单 | `cardio_pc/function_calling.py`、`tools/function_calling_smoke.py` | Gemma4 只能调用登记工具，避免自由生成不可审计诊断 |
| 多智能体审计 | `cardio_pc/agents.py` | 记录报告来源、规则命中、安全边界和修复路径 |
| V5 原版 UI | `legacy_v5_app.py`、`run_cardio_pc_v5.bat` | 作为历史参赛版对照和兼容入口保留 |
| 提交材料 | `submission/`、`REPORTS.md`、`DATASETS.md` | 正式报告、demo、数据披露和在线演示继续保留 |

## V6 新增能力

| 新增层 | 文件 | 作用 |
| --- | --- | --- |
| 临床规则手册 | `config/clinical_rulebook_v0.1.json` | 把公开指南/手册阈值和项目代理特征拆成可审计规则 |
| 规则引擎 | `src/clinical_rule_engine.py` | 根据量化指标和图像代理特征输出病症、分级、证据等级和逻辑链 |
| 媒体适配器 | `src/image_case_adapter.py` | 将多格式输入整理为规则引擎可读取的病例证据 |
| V6 UI | `src/rulebook_ui.py`、`run_cardio_pc_v6.bat` | 在 V5 输入输出合同上增加测量值、规则书、Gemma4 急停和紧急规则模式 |
| 近临床验证 | `tools/clinical_like_validation.py` | 按患者检查 / DICOM zip 运行工程验证，只提交脱敏汇总 |
| 规则书 smoke | `tools/rulebook_accuracy_smoke.py` | 确认每条主要规则能稳定触发 |

## 为什么这样拆分

医疗教学和基层辅助场景不能让大模型直接自由读图下结论。V6 采用“V5 边缘特征 + V6 规则书 + Gemma4 报告推理”的结构：

```text
原始超声文件
  -> V5 图像/动图/Doppler 特征
  -> V6 临床规则手册
  -> 结构化候选诊断和证据等级
  -> Gemma4 4B 本地函数调用与报告组织
  -> 本地报告合同守卫
  -> 多智能体审计
```

这样可以同时满足三件事：

- 现场稳定：没有 GGUF 或 Gemma4 超时时，规则书仍能给出同格式报告。
- 医学可审计：每个病症判断都有阈值、代理特征、证据等级和缺失证据。
- 保留 Gemma4 价值：Gemma4 负责结构化推理、函数调用、教学解释、复核建议和安全边界，而不是被降级成普通润色器。

## 输入输出合同保持不变

V6 不改变 V5 面向用户的输入输出合同：

- 输入仍支持 DICOM/DCOM/PNG/JPG/GIF/TIFF/MP4/MOV/AVI。
- 输出仍必须包含 `教学参考病症判断`、`最小病症`、`逻辑链`。
- 安全边界仍强调教学参考和医生复核。
- 模型权重和敏感数据仍不随仓库发布。

## 当前验证状态

- `app.py --self-test-rule-only`：通过。
- `tools/rulebook_accuracy_smoke.py`：14/14 top-label 命中。
- `tools/clinical_like_validation.py`：20 例病例级近临床工程验证，measurement-assisted Macro F1 为 0.542，任一支持异常敏感性为 1.000。
- `tools/submission_preflight.py`：通过。

近临床验证仍是回顾性、单中心、小样本、报告文本抽取标签的工程验证，不等同于正式临床性能声明。它的主要价值是发现代理特征过度触发风险，并据此收紧心包积液、右心负荷和节段室壁运动异常等代理阈值。

## 推荐评审阅读顺序

1. `README.md`：了解 V6 是 V5 的升级版。
2. `SUBMISSION.md`：查看提交材料入口。
3. `docs/gemma4_runtime_contract.md`：查看 Gemma4 如何参与推理和审计。
4. `docs/gemma4_function_calling_contract.md`：查看函数调用白名单。
5. `docs/public_manual_mapping.md`：查看规则书与公开手册阈值的映射。
6. `validation/clinical_like_20260621/clinical_like_validation_report.md`：查看病例级近临床工程验证。

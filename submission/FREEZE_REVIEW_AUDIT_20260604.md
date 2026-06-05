# 冻结前评审视角检查

生成日期：2026-06-05

## 已补救

- 清理过时 BAT：仓库根目录只保留 `install_deps.bat` 和 `run_cardio_pc_v5.bat`。
- 诊断链报告保护层已上线：提示词泄漏、markdown 模板、AI 口吻和截断输出会回退到本地自然化教学报告。
- 已新增当前服务验证 JSON：`validation_speedopt/server_pipeline_case1_current_20260604.json` 记录 `has_prompt_leakage=false`、`has_required_fields=true` 和旧服务证据 `report_source=gemma4_repaired`；当前默认代码新增结构化 JSON 守卫，可在下一轮服务复现中记录 `report_source=gemma4_structured`。
- 冻结前 EchoBench 完整证据 60/60 通过，平均 1.418s/例。
- 冻结前 EchoBench 12 帧 60/60 通过，warm-cache 平均 0.711s/例。
- 本地 `llama-server` smoke 连续两次 OK，第二次 completion 0.522s。
- 技术报告已重写，包含医学指标、一般工程指标、成本模型、取舍、限制、APA 引用和 8 张 R 图表。

## 仍需在答辩中主动说明

- 当前系统是医学教学和算法演示工具，不是医疗器械，不用于正式临床诊断。
- 授权本地 60 例是报告链接标签，不是多专家盲评共识。
- TR 全阳性、PR/severe 样本不足，不能宣称这些标签的可靠特异性。
- AR、RWMA、左房扩大对切面覆盖敏感，12 帧输入下降明显。
- 在线 demo 只展示规则匹配和输入输出合同，完整边缘特征与 GGUF 以 PC V5 应用为准。

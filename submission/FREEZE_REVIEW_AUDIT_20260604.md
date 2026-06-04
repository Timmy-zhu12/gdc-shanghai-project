# 冻结前评审视角检查

生成日期：2026-06-04

## 已补救

- 清理过时 BAT：仓库根目录只保留 `install_deps.bat` 和 `run_cardio_pc_v5.bat` 两个普通入口。
- 修正 Gemma4 system prompt：`prompts/hierarchical_system_prompt.txt` 已恢复为清晰中文，并加入短报告契约。
- 诊断链报告保护层已细化：模型输出可被记录为 `gemma4_preserved`、`gemma4_repaired`、`gemma4_guarded_template` 或 `rule_template`。
- 已新增当前服务验证 JSON：`validation_speedopt/server_pipeline_case1_current_20260604.json` 记录 `has_prompt_leakage=false`、`has_required_fields=true` 和 `report_source=gemma4_repaired`。
- 已新增当前服务审计 JSON：`validation_speedopt/agent_audit_server_pipeline_case1_current_20260604.json`。
- 冻结前 EchoBench 完整证据 60/60 通过，平均 1.418 秒/例。
- 冻结前 EchoBench 12 帧 60/60 通过，warm-cache 平均 0.711 秒/例。
- 本地 `llama-server` smoke 连续两次 OK：1.327 秒和 0.522 秒。
- 技术报告已重建，包含医学指标、一般工程指标、成本模型、取舍、限制、APA 引用和 8 张 R 图表。
- Word DOCX 已渲染为页面 PNG 复查；图 5 已同步最新服务 smoke 数据。
- 已删除容易误导模型名称的上游模型专用辅助入口，项目仅使用通用 `llama-cli.exe` 和 `llama-server.exe`。

## 仍需在答辩中主动说明

- 当前系统是医学教学和算法演示工具，不是医疗器械，不用于正式临床诊断。
- 授权本地 60 例是报告链接标签，不是多专家盲评共识。
- TR 全阳性、PR/severe 等标签样本不足，不能宣称这些标签的可靠特异性。
- AR、RWMA、左房扩大对切面覆盖敏感，12 帧输入下降明显。
- 在线 demo 只展示规则匹配和输入输出合同；完整边缘特征、DICOM/DCOM、动图和 GGUF 服务链路以 PC V5 应用为准。
- 当前 CPU 环境下 Gemma4 完整服务诊断仍可能需要 1 分钟以上，演示时应先启动常驻服务。

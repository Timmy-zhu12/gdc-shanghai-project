# 报告入口说明

本仓库现在只保留一个正式技术报告入口，避免评审在多个历史版本之间犹豫。当前代码分支是 PC V6：它继承 PC V5 参赛版的正式技术报告、Gemma4 运行契约和提交材料，并新增 V6 规则手册升级说明与病例级近临床验证摘要。

## 正式技术报告

请优先阅读：

- [PDF 正式技术报告](submission/technical_report/CardioConsult_TrackC_APA_Technical_Report.pdf)
- [Word DOCX 正式技术报告](submission/technical_report/CardioConsult_TrackC_APA_Technical_Report.docx)
- [Markdown 正式技术报告](submission/technical_report/CardioConsult_TrackC_APA_Technical_Report.md)

同目录下的图表、CSV、JSON 和生成脚本是这份正式报告的可复现材料。

## 技术状态与部署说明

- [V6 从 V5 升级说明](docs/V6_UPGRADE_FROM_V5.md)
- [V5 技术状态](docs/V5_TECHNICAL_STATUS.md)
- [Gemma4 运行契约](docs/gemma4_runtime_contract.md)
- [Gemma4 函数调用合同](docs/gemma4_function_calling_contract.md)
- [本地服务验证](docs/service_validation.md)
- [数据来源披露](DATASETS.md)

## 验证附录

- [数据集验证 Markdown 报告](validation/reports)
- [病例级近临床验证](validation/clinical_like_20260621/clinical_like_validation_report.md)
- [验证摘要](docs/validation_summary.md)

## 历史材料归档

历史报告、阶段性验证、旧版 benchmark 副本、DOCX 打包件和性能运行记录没有删除，统一移入 [archive](archive)。这些材料用于追溯开发过程，不作为正式提交报告入口。

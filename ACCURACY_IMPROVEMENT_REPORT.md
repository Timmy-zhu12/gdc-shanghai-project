# CardioConsult PC Accuracy Improvement Report

## 改进来源

本版基于 `D:\cardioconsult_dense_validation` 的 CAMUS 验证结果改进。旧版端到端规则在 CAMUS EF<50 样本上过于保守，预测标签只有“未见明确心脏超声异常”，导致端到端粗粒度正确率较低。

## 主要改动

- 从 `D:\cardioconsult_PC_cine_runbook` 复制并保留原有 PC 端 UI、多格式输入、DICOM/PNG/动图/视频支持和离线 Gemma4 4B 接口。
- 新增 `calibration/camus_low_ef_bmode.json`，把 CAMUS B-mode case-level 特征训练出的低 EF 代理模型封装为离线 JSON 系数。
- 新增 `cardio_pc/calibration.py`，运行时不依赖 scikit-learn，仅用 JSON 系数计算低 EF 概率。
- 新增 `contractility_fraction_proxy`，把 ED/ES 绝对面积差扩展为相对收缩幅度代理。
- 在 `cardio_pc/diagnosis.py` 中把 B-mode 低 EF 校准接入本地规则后备，使左室相关体位在证据满足时输出“左心室收缩功能减低”。

## CAMUS 250 case 验证结果

| 项目 | 改进前 | 改进后 |
|---|---:|---:|
| 端到端 coarse accuracy | 0.320 | 0.744 |
| 端到端 coarse macro F1 | 0.242 | 0.636 |
| 预测标签种类 | 1 | 2 |
| 低收缩功能敏感性 | 0.000 | 0.947 |
| 正常样本特异性 | 1.000 | 0.312 |

改进后混淆矩阵按“低收缩功能 vs 正常/未见明确异常”统计：

|  | 预测低收缩功能 | 预测正常/未见明确异常 |
|---|---:|---:|
| 实际 low_contractility_proxy | 161 | 9 |
| 实际 normal | 55 | 25 |

## 解释

本次强化明显提高了低 EF 教学样本的召回能力，适合“基层医疗点和超声初学者不漏掉可疑异常”的教学场景。但它也带来了更多正常样本被提示为“左心室收缩功能减低”的假阳性，因此输出仍必须作为医学教学参考，不能作为临床诊断或治疗依据。

完整报告见：

- `D:\cardioconsult_dense_validation\reports\CAMUS_report.md`
- `D:\cardioconsult_dense_validation\results\CAMUS\end_to_end.csv`
- `D:\cardioconsult_dense_validation\results\CAMUS\features.csv`

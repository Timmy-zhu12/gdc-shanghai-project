# Clinical-like Validation Report

Run time: 2026-06-21T14:41:37

Dataset root: `D:\new training dataset`

Case limit: `20`; sampled files per case: `12`; max loaded frames: `48`.

## Design

- Unit of analysis: one patient study / one zip package.
- Gold standard: `诊断结果` and `检查所见` fields from the local report spreadsheet.
- Input to model: DICOM files extracted from each zip package.
- Evaluation modes:
  - `image_only`: image-derived features only.
  - `measurement_assisted`: same image features plus structured measurements parsed from `检查所见`.

## Summary

| Mode | Cases | OK | Macro F1 | Any supported abnormality sensitivity | Mean seconds/case | P95 seconds/case |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| image_only | 20 | 20 | 0.482 | 1.000 | 7.085 | 7.894 |
| measurement_assisted | 20 | 20 | 0.542 | 1.000 | 7.085 | 7.894 |

## Per-label Metrics

| Mode | Label | Gold + | Pred + | Sensitivity | Specificity | Precision | F1 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| image_only | mr | 20 | 20 | 1.000 | 0.000 | 1.000 | 1.000 |
| image_only | tr | 20 | 20 | 1.000 | 0.000 | 1.000 | 1.000 |
| image_only | ar | 11 | 0 | 0.000 | 1.000 | 0.000 | 0.000 |
| image_only | valve_any | 20 | 20 | 1.000 | 0.000 | 1.000 | 1.000 |
| image_only | low_ef | 3 | 4 | 0.667 | 0.882 | 0.500 | 0.571 |
| image_only | rwma | 2 | 0 | 0.000 | 1.000 | 0.000 | 0.000 |
| image_only | lvh_hcm | 1 | 1 | 0.000 | 0.947 | 0.000 | 0.000 |
| image_only | la_enlargement | 4 | 3 | 0.250 | 0.875 | 0.333 | 0.286 |
| measurement_assisted | mr | 20 | 20 | 1.000 | 0.000 | 1.000 | 1.000 |
| measurement_assisted | tr | 20 | 20 | 1.000 | 0.000 | 1.000 | 1.000 |
| measurement_assisted | ar | 11 | 0 | 0.000 | 1.000 | 0.000 | 0.000 |
| measurement_assisted | valve_any | 20 | 20 | 1.000 | 0.000 | 1.000 | 1.000 |
| measurement_assisted | low_ef | 3 | 3 | 1.000 | 1.000 | 1.000 | 1.000 |
| measurement_assisted | rwma | 2 | 0 | 0.000 | 1.000 | 0.000 | 0.000 |
| measurement_assisted | lvh_hcm | 1 | 1 | 0.000 | 0.947 | 0.000 | 0.000 |
| measurement_assisted | la_enlargement | 4 | 2 | 0.250 | 0.938 | 0.500 | 0.333 |

## Caveats

- 本测试以病例/检查为单位运行，使用真实本地 DICOM zip 和报告表中的诊断结果抽取金标准标签。
- image_only 模式只看图像；measurement_assisted 模式额外使用检查所见中的 EF、TRV、IVS/LVPW、LA 等测量值，模拟医生或设备已提供结构化测量。
- 该测试仍是回顾性、单中心、小样本验证；报告文本抽取的标签可能存在模板偏差，不等同于正式专家盲审。
- 心动过缓等非影像核心标签被记录为 out-of-scope，不纳入当前规则引擎准确率。

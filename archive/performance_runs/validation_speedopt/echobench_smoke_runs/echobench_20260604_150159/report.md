# CardioConsult EchoBench v1 Run Report

Run ID: `echobench_20260604_150159`

## Summary

| Metric | Value |
| --- | ---: |
| Cases attempted | 1 |
| Cases OK | 1 |
| Total runtime seconds | 0.958 |
| Mean case runtime seconds | 0.948 |
| Use GGUF | False |
| V4 enabled | True |

## Latency

| Percentile | Runtime seconds |
| --- | ---: |
| Mean | 0.948 |
| P50 | 0.948 |
| P90 | 0.948 |
| P95 | 0.948 |
| P99 | 0.948 |
| Max | 0.948 |

## Label Metrics

| Label | Accuracy | Sensitivity | Specificity | F1 |
| --- | ---: | ---: | ---: | ---: |
| valve_any | 1.000 | 1.000 | 0.000 | 1.000 |
| mr | 1.000 | 1.000 | 0.000 | 1.000 |
| tr | 1.000 | 1.000 | 0.000 | 1.000 |
| ar | 0.000 | 0.000 | 0.000 | 0.000 |
| pr | 1.000 | 0.000 | 1.000 | 0.000 |
| mild | 1.000 | 1.000 | 0.000 | 1.000 |
| moderate | 1.000 | 0.000 | 1.000 | 0.000 |
| severe | 1.000 | 0.000 | 1.000 | 0.000 |
| low_ef | 1.000 | 0.000 | 1.000 | 0.000 |
| rwma | 1.000 | 0.000 | 1.000 | 0.000 |
| lvh_hcm | 1.000 | 0.000 | 1.000 | 0.000 |
| la_enlargement | 1.000 | 0.000 | 1.000 | 0.000 |
| bradycardia | 0.000 | 0.000 | 0.000 | 0.000 |

## Provenance

- Project: `D:\gdc-shanghai-project-PC-speedopt_20260604`
- Mapping: `D:\CardioConsult_Gemma4_TrackC_Final_V4_20260604\03_mapping\case_report_time_mapping.csv`
- Model: `D:\gdc-shanghai-project-PC-speedopt_20260604\models\gemma-4-4b-it-Q4_K_M.gguf`
- Model SHA256: `None`
- Runtime backend: `python-rule-pipeline`
- Hardware: `Intel64 Family 6 Model 170 Stepping 4, GenuineIntel`, RAM 31.47 GB

## Notes

This is an educational benchmark for GDG/Gemma4 Track C development. It is not a regulatory clinical validation and does not support direct patient-care use.

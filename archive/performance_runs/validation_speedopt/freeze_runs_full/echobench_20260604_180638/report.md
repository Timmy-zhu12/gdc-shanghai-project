# CardioConsult EchoBench v1 Run Report

Run ID: `echobench_20260604_180638`

## Summary

| Metric | Value |
| --- | ---: |
| Cases attempted | 60 |
| Cases OK | 60 |
| Total runtime seconds | 85.323 |
| Mean case runtime seconds | 1.4177000000000002 |
| Use GGUF | False |
| V4 enabled | True |

## Latency

| Percentile | Runtime seconds |
| --- | ---: |
| Mean | 1.418 |
| P50 | 1.107 |
| P90 | 2.225 |
| P95 | 2.499 |
| P99 | 3.105 |
| Max | 3.394 |

## Label Metrics

| Label | Accuracy | Sensitivity | Specificity | F1 |
| --- | ---: | ---: | ---: | ---: |
| valve_any | 1.000 | 1.000 | 0.000 | 1.000 |
| mr | 0.933 | 0.964 | 0.600 | 0.964 |
| tr | 1.000 | 1.000 | 0.000 | 1.000 |
| ar | 0.700 | 0.724 | 0.677 | 0.700 |
| pr | 1.000 | 0.000 | 1.000 | 0.000 |
| mild | 1.000 | 1.000 | 0.000 | 1.000 |
| moderate | 0.967 | 0.000 | 1.000 | 0.000 |
| severe | 1.000 | 0.000 | 1.000 | 0.000 |
| low_ef | 0.967 | 1.000 | 0.963 | 0.857 |
| rwma | 0.967 | 0.333 | 1.000 | 0.500 |
| lvh_hcm | 0.983 | 0.000 | 1.000 | 0.000 |
| la_enlargement | 0.883 | 1.000 | 0.865 | 0.696 |
| bradycardia | 0.883 | 0.000 | 1.000 | 0.000 |

## Provenance

- Project: `D:\gdc-shanghai-project-PC-speedopt_20260604`
- Mapping: `D:\CardioConsult_Gemma4_TrackC_Final_V4_20260604\03_mapping\case_report_time_mapping.csv`
- Model: `D:\gdc-shanghai-project-PC-speedopt_20260604\models\gemma-4-4b-it-Q4_K_M.gguf`
- Model SHA256: `None`
- Runtime backend: `python-rule-pipeline`
- Hardware: `Intel64 Family 6 Model 170 Stepping 4, GenuineIntel`, RAM 31.47 GB

## Notes

This is an educational benchmark for local CardioConsult development. It is not a regulatory clinical validation and does not support direct patient-care use.

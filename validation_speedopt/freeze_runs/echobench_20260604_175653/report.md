# CardioConsult EchoBench v1 Run Report

Run ID: `echobench_20260604_175653`

## Summary

| Metric | Value |
| --- | ---: |
| Cases attempted | 60 |
| Cases OK | 60 |
| Total runtime seconds | 42.899 |
| Mean case runtime seconds | 0.7105 |
| Use GGUF | False |
| V4 enabled | True |

## Latency

| Percentile | Runtime seconds |
| --- | ---: |
| Mean | 0.711 |
| P50 | 0.705 |
| P90 | 0.749 |
| P95 | 0.763 |
| P99 | 0.858 |
| Max | 0.986 |

## Label Metrics

| Label | Accuracy | Sensitivity | Specificity | F1 |
| --- | ---: | ---: | ---: | ---: |
| valve_any | 1.000 | 1.000 | 0.000 | 1.000 |
| mr | 0.883 | 0.927 | 0.400 | 0.936 |
| tr | 1.000 | 1.000 | 0.000 | 1.000 |
| ar | 0.517 | 0.241 | 0.774 | 0.326 |
| pr | 1.000 | 0.000 | 1.000 | 0.000 |
| mild | 1.000 | 1.000 | 0.000 | 1.000 |
| moderate | 0.967 | 0.000 | 1.000 | 0.000 |
| severe | 1.000 | 0.000 | 1.000 | 0.000 |
| low_ef | 0.917 | 0.667 | 0.944 | 0.615 |
| rwma | 0.933 | 0.333 | 0.965 | 0.333 |
| lvh_hcm | 0.983 | 0.000 | 1.000 | 0.000 |
| la_enlargement | 0.750 | 0.375 | 0.808 | 0.286 |
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

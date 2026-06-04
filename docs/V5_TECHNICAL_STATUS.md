# CardioConsult PC V5 Technical Status

Updated: 2026-06-04

CardioConsult PC V5 is the current Windows reference build. It preserves the
PC input/output contract: PNG/JPG, DICOM/DCOM, animated images, and common video
files in; one Chinese teaching-reference diagnostic paragraph out, including a
broad-to-specific disease hierarchy and a minimum supported disease label.

## What V5 adds over V4

- EchoNet-Dynamic dynamic B-mode calibration for EF / LV systolic dysfunction.
- `cardio_pc/v5_echonet.py` runtime layer with V4 fallback.
- `tools/train_echonet_v5.py` local training entrypoint.
- EchoBench v1 benchmark runner and server smoke test.
- Representative 12-frame sampling for input-limited validation.
- APA-style technical report in Markdown and DOCX with benchmark figures.

## Current benchmark summary

Full-evidence local 60-case validation:

| Label | F1 |
|---|---:|
| MR | 0.964 |
| TR | 1.000 |
| AR | 0.700 |
| Low EF | 0.857 |
| RWMA | 0.500 |
| LA enlargement | 0.696 |

Representative 12-frame validation:

| Label | F1 |
|---|---:|
| MR | 0.936 |
| TR | 1.000 |
| AR | 0.326 |
| Low EF | 0.615 |
| RWMA | 0.333 |
| LA enlargement | 0.286 |

Latency:

| Scenario | Mean seconds/case | P95 |
|---|---:|---:|
| Full evidence | 3.761 | 5.513 |
| Representative 12-frame | 2.562 | 3.201 |

GGUF / llama.cpp smoke:

| Metric | Value |
|---|---:|
| Prompt processing | 37.76 tokens/s |
| Generation | 6.19 tokens/s |
| First server completion | 8.775 s |
| Warm server completion | 0.492 s |

## Report artifacts

- `docs/v5_benchmark/CardioConsult_PC_V5_EchoBench_Technical_Report_APA_20260604.md`
- `docs/v5_benchmark/CardioConsult_PC_V5_EchoBench_Technical_Report_APA_20260604.docx`
- `docs/v5_benchmark/V5_EchoNet_DL_Enhancement_Report.md`
- `docs/v5_benchmark/figures/`

## Safety boundary

This project is for medical education, algorithm demonstration, and grassroots
reference only. It is not a medical device and must not replace formal
echocardiography, physician review, emergency triage, treatment decisions, or
medical advice.

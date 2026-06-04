# Validation Summary

The dense validation workbench is kept outside this repository because raw datasets and generated caches are large and license-restricted. This repository includes generated reports only.

Included report folders:

- `validation/reports/`
- `validation/reports_docx/`

PC V5 authorized local 60-case DICOM validation snapshot, full-evidence scenario:

| Target | V5 F1 |
|---|---:|
| Mitral regurgitation proxy | 96.4% |
| Tricuspid regurgitation proxy | 100.0% |
| Aortic regurgitation proxy | 70.0% |
| Low-EF proxy | 85.7% |

PC V5 representative 12-frame scenario:

| Target | V5 F1 |
|---|---:|
| Mitral regurgitation proxy | 93.6% |
| Tricuspid regurgitation proxy | 100.0% |
| Aortic regurgitation proxy | 32.6% |
| Low-EF proxy | 61.5% |

EchoNet-Dynamic calibration held-out summary:

| Metric | Value |
|---|---:|
| EF MAE | 7.271 |
| EF RMSE | 9.603 |
| EF correlation | 0.647 |
| Low-EF AUC | 0.764 |
| Low-EF F1 | 0.496 |

Interpretation:

The V5 rule-and-calibration stack keeps the strong local MR and low-EF teaching-reference results while adding EchoNet-Dynamic dynamic B-mode calibration. The 12-frame scenario is faster and closer to live demo constraints, but AR, RWMA, and chamber-size labels remain sensitive to view coverage. PC V5 also improves the practical submission path by adding persistent `llama-server` reuse, a portable `config.example.json`, a rule-only smoke test, and clearer V5 report artifacts. These results are teaching-reference validation only and must not be used as standalone clinical diagnosis.

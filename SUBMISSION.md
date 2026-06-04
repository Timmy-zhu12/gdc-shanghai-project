# Gemma 4 Hackathon Track C Submission Checklist

This file is the judge-facing entry point for CardioConsult.

Official competition page: [Gemma 4 Hackathon 2026](https://hackathon.googdg.cn/?lang=en)

Track alignment: Track C - Edge AI. The official description requires fully offline deployment of E2B/E4B-class models on phones, Raspberry Pi, or embedded hardware with a real-device demo. This submission uses the Windows PC V5 repository as the single stable, reproducible offline reference implementation, with deterministic edge-feature fallback and a documented route for later mobile migration.

## Required Submission Items

| Requirement | CardioConsult Deliverable | Status |
|---|---|---|
| Code repository | This repository: `https://github.com/Timmy-zhu12/gdc-shanghai-project` | Ready |
| Demo video within 5 minutes | Final public video URL should be pasted into the submission form after upload | Pending final upload |
| Technical report | [DOCX](submission/technical_report/CardioConsult_TrackC_APA_Technical_Report.docx), [PDF](submission/technical_report/CardioConsult_TrackC_APA_Technical_Report.pdf), [Markdown](submission/technical_report/CardioConsult_TrackC_APA_Technical_Report.md) | Ready |
| Online demo URL | Static demo source is in [docs/index.html](docs/index.html); if GitHub Pages is enabled from `/docs`, use `https://timmy-zhu12.github.io/gdc-shanghai-project/` | Ready in repo |
| Training data disclosure | [DATASETS.md](DATASETS.md) and [docs/data_and_model_policy.md](docs/data_and_model_policy.md) | Ready |
| Competitive differentiators | [docs/competitive_edge.md](docs/competitive_edge.md) | Ready |
| License | [Apache License 2.0](LICENSE) with [NOTICE](NOTICE) | Ready |

## Repository Scope

This repository is the submission repository. PC V5 is the only actively maintained runnable build in this submission. Older platform prototypes are not required to evaluate the current submission and are treated as future migration routes rather than current deliverables.

## Judging Criteria Mapping

| Official Criterion | Weight | What To Inspect |
|---|---:|---|
| Real-world impact | 30% | Medical education and primary-care ultrasound reference workflow; safety boundary in README and UI; de-identified local workflow |
| Technical excellence | 25% | B-mode GLDM/texture proxies, SRAD/CLAHE preprocessing, Color Doppler HSV/vector proxies, cine/DICOM support, EchoNet-Dynamic EF calibration, offline Gemma4 4B via `llama-cli` or persistent `llama-server` |
| Completeness | 20% | Runnable PC V5 repository, online demo static page, sample files, validation reports, deployment scripts, technical report, rule-smoke test |
| Innovation | 15% | Hybrid edge-computing + Gemma4 report generation, hierarchical disease label output, offline-first medical teaching workflow |
| Presentation quality | 10% | APA technical report, validation bundle, README deployment guides, and static online demo |

## Offline Demo Path

Recommended judge demo path:

1. Open the static online demo from `docs/index.html` or the GitHub Pages URL if enabled.
2. Clone/open this repository and run `run_cardio_pc_v5.bat`.
3. Demonstrate PNG/DICOM/DCOM/cine input and the same diagnosis output contract.
4. For repeated local Gemma4 runs, start `run_cardio_pc_v4_fast_server.bat` first to reuse a warm llama.cpp server.
5. Explain that model weights and raw datasets are excluded for license/privacy reasons, then show validation summary and the safety boundary.

## What Makes This Track C Submission Strong

- Real offline edge path: PC V5 uses local Gemma4 4B GGUF through `llama-cli`; it also supports persistent `llama-server` reuse for faster repeated diagnoses.
- V5 dynamic echo calibration: EchoNet-Dynamic features add EF / left-ventricular systolic dysfunction calibration while preserving the auditable valve-regurgitation rules.
- Ultrasound-specific preprocessing: B-mode and Color Doppler are processed by different edge-feature branches before the LLM sees the structured evidence.
- Hierarchical medical teaching output: broad disease direction, middle category, smallest disease label, severity, evidence sufficiency, and logic chain.
- Demo robustness: deterministic fallback keeps the same input/output contract even if the large model file is not present during live judging.
- Data transparency: every public dataset or literature source used for validation or label design is listed in `DATASETS.md`; raw datasets and patient images are not redistributed.

## Local Smoke Test Commands

Windows PC:

```powershell
git clone https://github.com/Timmy-zhu12/gdc-shanghai-project.git
Set-Location gdc-shanghai-project
.\install_deps.bat
.\.venv\Scripts\python.exe app.py --self-test-rule-only
.\run_cardio_pc_v5.bat
```

## Safety Boundary

CardioConsult is a medical-education and algorithm-demonstration prototype. It is not a medical device and must not be used as a final clinical diagnosis, treatment recommendation, emergency triage instruction, or medical order. Formal diagnosis still requires complete standard echocardiographic views, DICOM scale metadata, cine clips, patient history, physical findings, and qualified clinician review.

## Final Manual Items Before Upload

- Record or upload the demo video and paste the public URL into the competition form.
- Confirm GitHub Pages is enabled from `/docs` on this repository if a public online demo URL is required.
- Confirm this repository is public or accessible to judges.
- Confirm no raw patient data, model weights, `config.json`, local paths with secrets, or dataset downloads are committed.

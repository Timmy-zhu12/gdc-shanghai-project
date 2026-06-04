# Deployment Notes

This repository is the single submission entry point. The maintained runnable target is the Windows PC V5 application; older platform prototypes are not needed to reproduce or review the current result.

| Target | Directory | Main entry | Status |
|---|---|---|---|
| Windows PC V5 app | Repository root | `run_cardio_pc_v5.bat` | Current maintained offline reference implementation |
| Warm GGUF inference server | Repository root | `run_cardio_pc_v4_fast_server.bat` | Optional persistent `llama-server` mode for repeated local Gemma4 4B calls |
| Rule-only smoke test | Repository root | `python app.py --self-test-rule-only` | Fast validation when GGUF weights are not present |
| Static online demo | `docs/` | `index.html` | Single-file browser rule-matching demonstration; can be served by GitHub Pages or opened directly |
| Technical report bundle | `submission/technical_report/` and `docs/v5_benchmark/` | `.docx`, `.pdf`, `.md`, figures | Submission report, benchmark narrative, and generated visuals |

Recommended demo order:

1. Open the static online demo from `docs/index.html` or the GitHub Pages URL after Pages is enabled.
2. Import PNG/DICOM/DCOM/cine samples and show the output contract.
3. Run `run_cardio_pc_v5.bat` for the full PC workflow.
4. Place the local Gemma4 4B GGUF file in `models/` and use `llama-cli` or the persistent `llama-server` launcher for offline generation.
5. Show `DATASETS.md`, `SUBMISSION.md`, and the technical report bundle to disclose data sources, validation limits, and safety boundaries.

# CardioConsult PC V4

CardioConsult PC V4 is the Windows reference implementation for the Gemma 4 Hackathon / GDG Track C submission. It is designed for medical education, ultrasound training, and primary-care reference workflows where privacy and offline execution matter.

This repository contains the runnable PC app code. The unified submission portal, online demo, technical report, dataset disclosure, and links to every platform repository are maintained in the main repository:

[Track-C-gdc-project-shanghai-Total-Repository](https://github.com/Timmy-zhu12/Track-C-gdc-project-shanghai-Total-Repository)

Public online demo:

[CardioConsult Track C Online Demo](https://timmy-zhu12.github.io/Track-C-gdc-project-shanghai-Total-Repository/)

> Safety boundary: this project is not a medical device. It is for medical teaching, algorithm demonstration, and grassroots reference only. It must not replace formal echocardiography, clinician diagnosis, treatment decisions, emergency triage, or medical orders.

## Why This Fits Track C

The official Gemma 4 Hackathon 2026 page defines Track C as Edge AI with fully offline deployment on phones, Raspberry Pi, or embedded hardware and a real-device demo requirement. It also requires a code repository, demo video within 5 minutes, technical report, online demo URL, and disclosure of training data sources.

CardioConsult PC V4 maps to those points as follows:

| Track C need | PC V4 implementation |
|---|---|
| Offline Gemma 4 use | Local Gemma4 4B GGUF through llama.cpp `llama-cli` or persistent `llama-server` |
| Runnable demo | Windows desktop UI, batch launchers, bundled sample ultrasound-like files, rule-only smoke test |
| Edge AI value | B-mode and Color Doppler features are computed locally before report generation |
| Robustness | If the GGUF model is absent, the same input/output contract falls back to the auditable local rule engine |
| Data transparency | Dataset and model policies are linked from the main repository; raw patient data and model weights are not committed |

## Inputs And Output

Supported inputs:

- PNG, JPG, BMP, TIFF, WebP, HEIC/HEIF
- DICOM, DCM, DCOM
- GIF/APNG and multi-frame TIFF
- MP4/MOV/AVI/MKV/WebM/WMV and common ultrasound cine/video containers
- One file or many files at once

Expected clinical-teaching scope:

- Up to the standard 12 echocardiographic views.
- Minimum usable input: one view with systolic and diastolic frames. If phase labels are missing, the app estimates systole/diastole from chamber-area proxies.

Output:

- One Chinese teaching-reference diagnostic paragraph.
- The first visible field is forced to include a broad-to-specific disease hierarchy.
- The app always includes a smallest disease label, logic chain, confidence/evidence level, image-quality notes, and safety warning.

Example field shape:

```text
教学参考病症判断：轻度二尖瓣反流（瓣膜性心脏病 > 二尖瓣疾病）。
最小病症：轻度二尖瓣反流。
逻辑链：体位覆盖... + B-mode... + Doppler... -> 规则... -> 瓣膜性心脏病 -> 二尖瓣疾病 -> 轻度二尖瓣反流。
```

## Quick Start

Install Python 3.10+ on Windows, then double-click:

```bat
run_cardio_pc_v4.bat
```

The launcher will:

1. Create `.venv` if needed.
2. Install Python dependencies from `requirements.txt`.
3. Create `config.json` from `config.example.json` if missing.
4. Start the desktop UI.

For the fastest offline Gemma4 demonstration, use:

```bat
run_cardio_pc_v4_fast_server.bat
```

This starts a persistent local `llama-server` at `http://127.0.0.1:8088` and then opens the UI. The first load still takes time, but later diagnoses reuse the already loaded GGUF model.

Manual server controls:

```bat
start_llama_server_v4.bat
stop_llama_server_v4.bat
```

Legacy launchers are kept as compatibility aliases and now route to V4:

```bat
run_cardio_pc.bat
run_cardio_pc_accuracy_improved.bat
run_cardio_pc_accuracy_v2_hierarchical.bat
run_cardio_pc_cine.bat
```

## Offline Model Setup

The repository includes the Windows llama.cpp runtime under:

```text
tools/llama_cpp/llama-b9469-bin-win-cpu-x64/
```

Gemma4 GGUF weights are not committed. Put the model here:

```text
models/gemma-4-4b-it-Q4_K_M.gguf
```

Optional multimodal projection file:

```text
models/gemma-4-4b-mmproj-Q4_0.gguf
```

Then copy or edit:

```text
config.example.json -> config.json
```

The default `config.example.json` already points to the bundled `llama-cli.exe` and the `models/` folder.

## Smoke Tests

Fast rule-only smoke test, suitable before judging or GitHub Actions:

```powershell
.\install_deps.bat
.\.venv\Scripts\python.exe app.py --self-test-rule-only
```

Full configured self-test:

```powershell
.\.venv\Scripts\python.exe app.py --self-test
```

The full self-test may invoke Gemma4 if `config.json` points to a valid local GGUF. On CPU-only machines this can take several minutes. The rule-only test verifies the image-loading, feature-extraction, hierarchical-label, and output-format pipeline without loading the model.

## Technical Pipeline

- B-mode branch: robust normalization, log compression, SRAD-inspired speckle suppression, CLAHE-like local contrast enhancement, DoG edge response, chamber-area proxy, texture and GLDM-style statistics.
- Color Doppler branch: HSV blood-flow vectorization, connected-component filtering, jet-width proxy, direction consistency, turbulence/divergence/vorticity proxies.
- Cine branch: representative frame sampling, temporal differencing, systole/diastole inference, STI-style chamber strain proxy, and Lucas-Kanade-style optical-flow proxy.
- Label branch: hierarchical disease taxonomy with broad direction, middle category, smallest disease, severity, evidence sufficiency, and source notes.
- Gemma4 branch: compact structured prompt with mandatory first sentence, minimum disease, and logic chain; persistent server mode is preferred for repeated runs.

## Validation Snapshot

The V4 reference validation on the authorized local 60-case DICOM set reported:

| Target | V4 F1 |
|---|---:|
| Mitral regurgitation proxy | 96.4% |
| Tricuspid regurgitation proxy | 100.0% |
| Aortic regurgitation proxy | 70.0% |
| Low-EF proxy | 85.7% |

These are small-dataset teaching-reference validation results, not clinical performance claims. Full reports and dataset disclosures are maintained in the main repository.

## Repository Boundary

This PC repository is the runnable Windows implementation. The main repository is the official submission entry and contains:

- online demo link
- APA-style technical report
- dataset disclosure
- validation reports
- demo video script
- links to Android, Linux, Apple, and HarmonyOS repositories

## License

Original source code and documentation in this repository are released under Apache License 2.0. Third-party model weights, medical datasets, ultrasound software, SDKs, and patient/teaching data are excluded and remain governed by their own licenses, terms, or institutional approvals.

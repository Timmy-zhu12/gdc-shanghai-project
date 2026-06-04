# CardioConsult PC V5 EchoNet-Dynamic Enhancement Report

Generated: 2026-06-04

## Goal

V5 adds local training and a lightweight dynamic echocardiography calibration layer while preserving the V4 input/output behavior. The goal is to improve coverage for cardiac problems detectable by echocardiography without moving away from local, low-cost, edge-computable design.

## What Changed

- Created isolated V5 development folder and then synchronized the runnable PC
  reference implementation into this repository.
- Copied V4 PC app behavior without modifying historical V4 snapshots.
- Added `cardio_pc/v5_echonet.py`.
- Added `tools/train_echonet_v5.py`.
- Added V5 launch and training BAT scripts.
- Added a trained model artifact: `models/echonet_v5_lowef_mlp.joblib`.
- Added V5 runtime fallback: if the trained model is unavailable, V5 behaves like V4.

## Dataset Use

The new dataset used here is EchoNet-Dynamic:

- `FileList.csv`: 10,030 videos with EF, ESV, EDV, FPS, frame count, and TRAIN/VAL/TEST split.
- `VolumeTracings.csv`: expert LV tracing frames.
- `Videos`: 10,030 A4C `.avi` echocardiography videos.

EchoNet-Dynamic is used only for dynamic B-mode EF / LV systolic function calibration. It is not used to train valve regurgitation labels.

## Model Design

The V5 feature vector contains:

- B-mode mean and standard deviation features.
- chamber-area and temporal-difference features.
- LV-focused dark-cavity area, centroid, width, and height features.
- low-dimensional thumbnails from minimum-area, maximum-area, and mean frames.

Candidate models:

- Ridge regression for EF baseline.
- HistGradientBoostingRegressor for EF.
- MLPRegressor as lightweight neural model for EF.
- LogisticRegression for low-EF classification.
- HistGradientBoostingClassifier for low-EF classification.
- RandomForestClassifier for low-EF classification.
- MLPClassifier as lightweight neural model for low EF.

Final selected models:

- EF: HistGradientBoostingRegressor.
- Low EF: LogisticRegression.

The MLP candidates were trained and evaluated, but final selection follows validation metrics rather than forcing a neural model when it is weaker.

## Training Runs

### Smoke Run

- train: 120
- validation: 40
- test: 40
- result: chain verified, but too small for stable conclusions.

### Balanced Run

- train: 600
- validation: 160
- test: 160
- EF test MAE: 7.82
- EF test correlation: 0.541
- Low-EF F1: 0.413
- Low-EF AUC: 0.697

### Large Run

- train: 1200
- validation: 300
- test: 300
- max frames/video: 16

Final large-run metrics:

| Metric | Value |
| --- | ---: |
| EF MAE | 7.271 |
| EF RMSE | 9.603 |
| EF correlation | 0.647 |
| Low-EF accuracy | 0.770 |
| Low-EF precision | 0.479 |
| Low-EF recall | 0.515 |
| Low-EF F1 | 0.496 |
| Low-EF AUC | 0.764 |

## Local 60-Case Regression

After enabling the V5 model, the local 60-case report-linked validation was rerun.

```json
{
  "cases_attempted": 60,
  "cases_ok": 60,
  "total_runtime_seconds": 221.564,
  "mean_case_runtime_seconds": 3.68785,
  "use_gguf": false,
  "v4": true
}
```

Key local metrics:

| Label | F1 |
| --- | ---: |
| Valve any | 1.000 |
| MR | 0.964 |
| TR | 1.000 |
| AR | 0.700 |
| Low EF | 0.857 |
| RWMA | 0.500 |
| LA enlargement | 0.696 |

The V5 dynamic calibration did not degrade the existing local valve-regurgitation results.

## Trade-Off

V5 does not train a large end-to-end CNN/Transformer because the local machine does not currently have PyTorch/TensorFlow/OpenCV installed and the project must remain runnable on low-cost local hardware. Instead, V5 uses a hybrid design:

- lightweight deep candidates are evaluated;
- validation selects the strongest candidate;
- the runtime model is small enough to load quickly;
- existing auditable rules remain active.

This trades off theoretical maximum accuracy for local deployability, reproducibility, and low operating cost.

## Current Limitation

The low-EF classifier is useful but not yet a clinical-grade EF estimator. It improves dynamic B-mode coverage and adds EchoNet-based evidence, but severe EF grading can still be conservative. The next improvement should be a true lightweight segmentation model or ONNX/TFLite model trained from EchoNet tracings, if the target device budget allows it.

## Recommended Use

Use V5 as the current PC experimental build for:

- dynamic B-mode/cine input,
- EF/left ventricular systolic dysfunction teaching labels,
- regression testing before mobile migration.

Use V4 as the stable fallback if only valve-regurgitation behavior is being demonstrated.

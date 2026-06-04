# CardioConsult PC V4 Runbook

## Location

Project folder:

```text
D:/CardioConsult_Gemma4_TrackC_Final_V4_20260604/05_pc_v4
```

Start command:

```bat
D:/CardioConsult_Gemma4_TrackC_Final_V4_20260604/05_pc_v4/run_cardio_pc_v4.bat
```

## Input

The UI accepts multiple files at once:

- PNG/JPG/BMP/TIFF/WebP/HEIC
- DICOM/DCOM/DICOM
- GIF/APNG
- MP4/MOV/AVI/MKV/WebM/WMV and related video files

The expected cardiac ultrasound input is one to twelve standard views, or at minimum systolic and diastolic frames from one view. Multi-frame DICOM is sampled automatically.

## Output

The report begins with:

```text
教学参考病症判断：<最小病症>（<大方向> > <中方向>）。
最小病症：<最小病症>。
逻辑链：<evidence> → <rule> → <大方向> → <中方向> → <最小病症>。
```

## Offline Gemma4 4B

V4 uses the local `llama-cli.exe` copied into this folder. The only external dependency allowed by design is the already downloaded GGUF pair in the earliest PC model folder:

```text
D:/cardioconsult_PC_runbook/models/gemma-4-4b-it-Q4_K_M.gguf
D:/cardioconsult_PC_runbook/models/gemma-4-4b-mmproj-Q4_0.gguf
```

The smoke test output is stored in:

```text
D:/CardioConsult_Gemma4_TrackC_Final_V4_20260604/00_audit/gguf_smoke_output.txt
```

## Validation Data

The newtraining DICOM archives were extracted into:

```text
D:/CardioConsult_Gemma4_TrackC_Final_V4_20260604/02_newtraining_archived/extracted
```

Mapping and metrics are in:

```text
D:/CardioConsult_Gemma4_TrackC_Final_V4_20260604/03_mapping
D:/CardioConsult_Gemma4_TrackC_Final_V4_20260604/04_validation/v4_rule_retuned
D:/CardioConsult_Gemma4_TrackC_Final_V4_20260604/06_reports
```

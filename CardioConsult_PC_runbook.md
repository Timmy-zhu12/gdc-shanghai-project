# CardioConsult PC Accuracy Improved Runbook

Project path:

```text
D:\cardioconsult_PC_runbook
```

Run:

```bat
D:\cardioconsult_PC_runbook\run_cardio_pc_accuracy_improved.bat
```

Self-test:

```bat
cd /d D:\cardioconsult_PC_runbook
.venv\Scripts\python.exe app.py --self-test
```

Supported inputs keep the original PC format and add cine/video formats:

- Static images: `.png`, `.jpg`, `.jpeg`, `.bmp`, `.tif`, `.tiff`, `.webp`, `.heic`, `.heif`
- Animated images: `.gif`, `.apng`, animated WebP when Pillow can decode it
- DICOM/DCOM: `.dcm`, `.dicom`, `.dcom`, including multi-frame when pydicom can decode pixel data
- Video: `.mp4`, `.m4v`, `.mov`, `.avi`, `.mkv`, `.webm`, `.wmv`, `.mpg`, `.mpeg`, `.ts`, `.mts`, `.m2ts`, `.3gp`, `.cine`
- Multiple files at once
- Intended maximum: standard 12 echocardiography views
- Intended minimum: any one view with systolic and diastolic frames

Default reused Gemma4 4B model path:

```text
D:\cardioconsult_PC_runbook\models\gemma-4-4b-it-Q4_K_M.gguf
```

The current PC edition integrates the original PC workflow, the mathematical improvement layer, the primary-care guidance layer, cine/video sampling, and the CAMUS B-mode low-EF calibration. It keeps the same final output style and remains a research/teaching prototype rather than a clinical diagnostic device.

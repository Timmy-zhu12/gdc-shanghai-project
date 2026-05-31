# CardioConsult PC

Windows desktop version of the CardioConsult research prototype.

## Run

```bat
D:\cardioconsult_PC_runbook\install_deps.bat
D:\cardioconsult_PC_runbook\run_cardio_pc.bat
```

## Inputs

- PNG/JPG/BMP/TIFF
- DICOM: `.dcm`, `.dicom`, `.dcom`
- Multiple files at once
- Intended maximum: 12 standard echocardiography views, each with systolic and diastolic frames
- Intended minimum: one view with systolic and diastolic frames

The app automatically estimates systole/diastole from filename hints or chamber-area proxy.

## Offline Gemma4 4B

The UI supports local llama.cpp execution. Configure:

- `llama-cli.exe`
- `D:\cardioconsult_PC_runbook\models\gemma-4-4b-it-Q4_K_M.gguf`

If the model or executable is missing, the app remains runnable and uses a deterministic local fallback. The output labels that mode clearly.

This is a research prototype and not clinical diagnosis or treatment advice.

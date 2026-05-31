# CardioConsult PC runbook

Project path:

```text
D:\cardioconsult_PC_runbook
```

Run:

```bat
D:\cardioconsult_PC_runbook\run_cardio_pc.bat
```

Install or refresh dependencies:

```bat
D:\cardioconsult_PC_runbook\install_deps.bat
```

Self-test:

```bat
cd /d D:\cardioconsult_PC_runbook
.venv\Scripts\python.exe app.py --self-test
```

Supported inputs:

- `.png`, `.jpg`, `.jpeg`, `.bmp`, `.tif`, `.tiff`
- `.dcm`, `.dicom`, `.dcom`
- Multiple files at once
- Intended maximum: standard 12 echocardiography views
- Intended minimum: any one view with systolic and diastolic frames

Offline Gemma4 4B:

- Put the GGUF model under:

```text
D:\cardioconsult_PC_runbook\models\gemma-4-4b-it-Q4_K_M.gguf
```

- Select `llama-cli.exe` in the UI.
- If the model or llama executable is missing, the app runs a deterministic local fallback and labels that mode.

Output:

- A single Chinese suspicious-diagnosis paragraph in the UI.
- Optional `.txt` export under:

```text
D:\cardioconsult_PC_runbook\exports
```

Safety:

This is a research prototype. The generated text is not clinical diagnosis or treatment advice.

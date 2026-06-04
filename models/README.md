# Offline Model Files

Place the local Gemma4 4B GGUF model in this folder:

```text
models/gemma-4-4b-it-Q4_K_M.gguf
```

Optional multimodal projection file, if your local runner requires it:

```text
models/gemma-4-4b-mmproj-Q4_0.gguf
```

Model binaries are intentionally not committed to Git because they are large
third-party artifacts governed by their own model license and distribution
terms. After placing the files here, copy `config.example.json` to
`config.json` or start the app once and let the launcher create it.

## V5 EchoNet calibration artifact

PC V5 can optionally load a small EchoNet-Dynamic calibration artifact for EF /
left-ventricular systolic dysfunction teaching labels:

```text
models/echonet_v5_lowef_mlp.joblib
```

This file is not committed by default because it is a trained artifact derived
from third-party research data. To recreate it locally, obtain EchoNet-Dynamic
under its own access terms, then run:

```bat
train_echonet_v5_balanced.bat
```

If the artifact is absent, the application still runs and falls back to the V4
rule/calibration behavior.

For the original development machine only, the V4 launcher also accepts the
legacy local cache path:

```text
D:/cardioconsult_PC_runbook/models/gemma-4-4b-it-Q4_K_M.gguf
```

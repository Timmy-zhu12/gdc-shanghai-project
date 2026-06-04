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

For the original development machine only, the V4 launcher also accepts the
legacy local cache path:

```text
D:/cardioconsult_PC_runbook/models/gemma-4-4b-it-Q4_K_M.gguf
```

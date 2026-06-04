# Third-Party Notices

This repository contains original CardioConsult source code plus a small set of
third-party runtime files needed for the offline Windows demo.

## llama.cpp Windows Runtime

- Location: `tools/llama_cpp/llama-b9469-bin-win-cpu-x64/`
- Purpose: local GGUF inference through `llama-cli.exe` and persistent
  `llama-server.exe`
- Upstream project: <https://github.com/ggml-org/llama.cpp>
- License: MIT License, as published by the upstream llama.cpp repository.
  Check the upstream repository for the authoritative current license text and
  release notes.

The bundled runtime does not include Gemma4 weights. Model files must be
downloaded or supplied separately according to their own model license and terms.

## Model Weights

Gemma4 GGUF model files are intentionally excluded from Git:

```text
models/gemma-4-4b-it-Q4_K_M.gguf
models/gemma-4-4b-mmproj-Q4_0.gguf
```

Users must obtain model files through authorized channels and comply with the
applicable model license, data-use rules, and local privacy requirements.

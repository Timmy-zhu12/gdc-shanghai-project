# 第三方组件说明

本仓库包含 CardioConsult 原创源代码，以及少量用于 Windows 离线演示的第三方运行时文件。

## llama.cpp Windows 运行时

- 位置：`tools/llama_cpp/llama-b9469-bin-win-cpu-x64/`
- 用途：通过 `llama-cli.exe` 和常驻 `llama-server.exe` 进行本地 GGUF 推理
- 上游项目：<https://github.com/ggml-org/llama.cpp>
- 许可证：MIT License。权威许可证文本和版本说明以 llama.cpp 上游仓库为准。

仓库内运行时不包含 Gemma4 权重。模型文件必须由使用者通过授权渠道另行获取，并遵守对应模型许可证和使用条款。

## 模型权重

Gemma4 GGUF 模型文件有意排除在 Git 之外：

```text
models/gemma-4-4b-it-Q4_K_M.gguf
models/gemma-4-4b-mmproj-Q4_0.gguf
```

使用者必须从授权渠道获取模型文件，并遵守适用的模型许可证、数据使用规则和本地隐私要求。

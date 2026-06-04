# 第三方组件说明

本仓库包含 CardioConsult 原创源代码、中文文档、验证摘要，以及少量用于 Windows 离线演示的第三方运行时文件。第三方组件仍受其原始许可证约束。

## llama.cpp Windows 运行时

- 位置：`tools/llama_cpp/llama-b9469-bin-win-cpu-x64/`
- 用途：通过 `llama-cli.exe` 或常驻 `llama-server.exe` 调用本地 Gemma4 4B GGUF 模型
- 上游项目：<https://github.com/ggml-org/llama.cpp>
- 许可证：MIT License。权威许可证文本、构建方式和版本说明以上游仓库为准。

本项目只依赖 llama.cpp 的通用 CLI 和 server 入口。仓库不使用、也不分发容易造成模型名称误解的上游模型专用辅助入口；所有项目配置均指向 `llama-cli.exe` 或 `llama-server.exe`。

## Gemma4 GGUF 模型权重

Gemma4 GGUF 模型文件不会提交到 GitHub。默认路径如下：

```text
models/gemma-4-4b-it-Q4_K_M.gguf
models/gemma-4-4b-mmproj-Q4_0.gguf
```

使用者必须从授权渠道自行获取模型文件，并遵守对应模型许可证、使用条款、数据政策和本地隐私要求。为了便于复现，建议在本地记录模型文件 SHA256：

```powershell
Get-FileHash .\models\gemma-4-4b-it-Q4_K_M.gguf -Algorithm SHA256
```

## 医学数据与公开数据集

仓库只保存数据来源说明、验证摘要、统计图表和人工编写的标签映射，不提交原始病人图像、完整 DICOM、下载缓存或未经许可再分发的数据集。公开数据集的引用、用途和再分发边界见 [DATASETS.md](DATASETS.md)。

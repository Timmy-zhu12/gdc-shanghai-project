# 离线模型文件

请把本地 Gemma4 4B GGUF 模型放在本目录：

```text
models/gemma-4-4b-it-Q4_K_M.gguf
```

如果本地运行器需要多模态投影文件，可选放置：

```text
models/gemma-4-4b-mmproj-Q4_0.gguf
```

模型二进制文件不会提交到 Git。它们体积很大，并且属于受各自模型许可证和分发条款约束的第三方资产。放置文件后，可将 `config.example.json` 复制为 `config.json`，或首次启动应用时让启动器自动创建。

## V5 EchoNet 校准文件

PC V5 可以选择加载一个小型 EchoNet-Dynamic 校准文件，用于 EF / 左室收缩功能减低教学标签：

```text
models/echonet_v5_lowef_mlp.joblib
```

该文件默认不提交，因为它是基于第三方研究数据训练得到的产物。若需本地重建，请先按 EchoNet-Dynamic 自身访问条款获取数据，然后运行：

```powershell
.\.venv\Scripts\python.exe tools\train_echonet_v5.py --train-limit 600 --val-limit 160 --test-limit 160 --max-frames 16
```

如果缺少该文件，应用仍可运行，并会回退到 V4 规则/校准行为。

仅对原开发机器，V4 启动器也接受旧本地缓存路径：

```text
D:/cardioconsult_PC_runbook/models/gemma-4-4b-it-Q4_K_M.gguf
```

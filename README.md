# CardioConsult PC V4 中文说明

CardioConsult PC V4 是本项目面向 Gemma 4 开发者大赛 / GDG Track C 的 Windows 参考实现。项目服务于医学教学、心脏超声入门训练和基层医疗点参考场景，核心目标是在本地离线环境中导入脱敏心脏超声文件，完成边缘特征提取，并输出一段中文教学参考诊断文本。

统一提交入口、在线演示、技术报告、数据来源披露和所有平台仓库链接见主仓库：

[Track-C-gdc-project-shanghai-Total-Repository](https://github.com/Timmy-zhu12/Track-C-gdc-project-shanghai-Total-Repository)

在线演示：

[CardioConsult Track C 在线演示](https://timmy-zhu12.github.io/Track-C-gdc-project-shanghai-Total-Repository/)

> 医学安全边界：本项目不是医疗器械，仅用于医学教学、算法演示和基层参考。它不能替代正式心脏超声报告、医师诊断、治疗决策、急诊分诊或医嘱。

## 与 Track C 的对应关系

Track C 强调端侧/边缘 AI、离线运行、真实设备演示和完整提交材料。PC V4 的对应实现如下：

| 竞赛要点 | PC V4 对应实现 |
|---|---|
| 离线 Gemma4 | 使用本地 Gemma4 4B GGUF，可通过 llama.cpp 的 `llama-cli` 或常驻 `llama-server` 调用 |
| 可运行演示 | 提供 Windows 桌面 UI、批处理启动脚本、示例输入和规则路径自检 |
| 边缘计算价值 | B-mode 与 Color Doppler 分支先在本地提取结构化特征，再交给模型或规则层生成报告 |
| 演示稳定性 | GGUF 不存在或模型调用失败时，自动切换到可审计的本地规则后备 |
| 数据透明 | 主仓库提供数据集来源、验证报告、许可证和模型/数据不随仓库分发的说明 |

## 支持输入与输出

支持输入：

- PNG、JPG、BMP、TIFF、WebP、HEIC/HEIF
- DICOM、DCM、DCOM
- GIF、APNG、多帧 TIFF
- MP4、MOV、AVI、MKV、WebM、WMV 等常见视频或超声动图
- 单文件或多文件批量导入

输入范围：

- 最大目标：标准心脏超声 12 个体位。
- 最小目标：任意一个体位的收缩态与舒张态。若文件名没有相位信息，系统会根据腔室面积代理自动估计收缩/舒张。

输出形式：

- 一段中文医学教学参考诊断。
- 第一字段强制包含“大方向 > 中方向 > 最小病症”的层级诊断。
- 必须给出最小病症、逻辑链、置信度/证据充分度、图像质量提示、补扫建议和安全声明。

示例：

```text
教学参考病症判断：轻度二尖瓣反流（瓣膜性心脏病 > 二尖瓣疾病）。
最小病症：轻度二尖瓣反流。
逻辑链：体位覆盖... + B-mode... + Doppler... -> 规则... -> 瓣膜性心脏病 -> 二尖瓣疾病 -> 轻度二尖瓣反流。
```

## 快速启动

在 Windows 上安装 Python 3.10 或更高版本，然后双击：

```bat
run_cardio_pc_v4.bat
```

脚本会自动：

1. 创建 `.venv` 虚拟环境。
2. 安装 `requirements.txt` 中的依赖。
3. 如果缺少 `config.json`，从 `config.example.json` 创建。
4. 启动桌面 UI。

若要进行最快的离线 Gemma4 演示，推荐使用：

```bat
run_cardio_pc_v4_fast_server.bat
```

它会先启动本地常驻 `llama-server`，地址为：

```text
http://127.0.0.1:8088
```

第一次启动仍需要加载 GGUF 模型，但后续诊断会复用已加载模型，避免每次重新加载 5GB 级模型文件。

手动启动或关闭模型服务：

```bat
start_llama_server_v4.bat
stop_llama_server_v4.bat
```

兼容旧入口仍保留，并已指向 V4 流程：

```bat
run_cardio_pc.bat
run_cardio_pc_accuracy_improved.bat
run_cardio_pc_accuracy_v2_hierarchical.bat
run_cardio_pc_cine.bat
```

## 离线模型配置

仓库已包含 Windows llama.cpp 运行时：

```text
tools/llama_cpp/llama-b9469-bin-win-cpu-x64/
```

Gemma4 4B GGUF 权重不会提交到 GitHub。请把模型放到：

```text
models/gemma-4-4b-it-Q4_K_M.gguf
```

可选多模态投影文件：

```text
models/gemma-4-4b-mmproj-Q4_0.gguf
```

如果需要修改路径，请复制或编辑：

```text
config.example.json -> config.json
```

默认配置已经指向仓库内的 `llama-cli.exe` 和 `models/` 目录。

## 自检命令

不加载 GGUF 的快速规则自检：

```powershell
.\install_deps.bat
.\.venv\Scripts\python.exe app.py --self-test-rule-only
```

完整配置自检：

```powershell
.\.venv\Scripts\python.exe app.py --self-test
```

完整自检可能调用 Gemma4。CPU-only 机器上可能需要数分钟；规则自检只验证文件读取、特征提取、层级标签和输出格式。

## 技术流程

- B-mode 分支：鲁棒归一化、对数压缩、SRAD-inspired 散斑抑制、CLAHE-like 局部增强、DoG 边缘响应、腔室面积代理、纹理与 GLDM 风格统计。
- Color Doppler 分支：HSV 血流向量化、连通域过滤、喷流宽度代理、方向一致性、湍流/散度/涡量代理。
- 动图/视频分支：代表帧采样、时间差分、收缩/舒张推断、STI 风格腔室应变代理和 Lucas-Kanade 风格光流代理。
- 标签分支：大方向、中方向、最小病症、严重程度、证据充分度和来源说明。
- Gemma4 分支：结构化短 prompt，强制首句、最小病症和逻辑链；重复演示优先使用常驻 `llama-server`。

## 验证摘要

授权本地 60 例 DICOM 教学数据的 V4 验证摘要：

| 目标 | V4 F1 |
|---|---:|
| 二尖瓣反流代理 | 96.4% |
| 三尖瓣反流代理 | 100.0% |
| 主动脉瓣反流代理 | 70.0% |
| 低 EF 代理 | 85.7% |

这些结果只代表小样本教学参考验证，不是临床性能声明。完整报告和数据披露见主仓库。

## 仓库边界

本仓库只保存 Windows PC 可运行实现。主仓库负责保存：

- 在线演示链接
- APA 格式技术报告
- 数据来源说明
- 验证报告
- 5 分钟演示视频脚本
- Android、Linux、Apple、HarmonyOS 仓库链接

## 许可证

本仓库原创代码、脚本、UI、配置和文档采用 Apache License 2.0。第三方模型权重、医学数据集、超声软件、SDK、商标和用户提供的教学/临床数据不包含在本许可证范围内，仍受各自许可证、平台条款或机构授权约束。

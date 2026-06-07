# CardioConsult PC V5 运行手册

## 位置

项目文件夹：

```text
D:/gdc-shanghai-project-PC-speedopt_20260604
```

启动命令：

```bat
D:/gdc-shanghai-project-PC-speedopt_20260604/run_cardio_pc_v5.bat
```

## 输入

UI 支持一次导入多个文件：

- PNG/JPG/BMP/TIFF/WebP/HEIC
- DICOM/DCOM/DCM
- GIF/APNG
- MP4/MOV/AVI/MKV/WebM/WMV 等相关视频文件

预期心脏超声输入为 1 到 12 个标准体位；最低输入可以是任意一个体位的收缩态和舒张态。多帧 DICOM 会自动抽样。

## 输出

报告开头保持以下格式：

```text
教学参考病症判断：<最小病症>（<大方向> > <中方向>）。
最小病症：<最小病症>。
逻辑链：<证据> → <规则> → <大方向> → <中方向> → <最小病症>。
```

## 离线 Gemma4 4B

V5 使用仓库内的 Windows llama.cpp runtime。按设计，GGUF 权重不上传到 GitHub；本机可继续复用最早 PC 模型目录里已经下载好的 GGUF 文件：

```text
D:/cardioconsult_PC_runbook/models/gemma-4-4b-it-Q4_K_M.gguf
D:/cardioconsult_PC_runbook/models/gemma-4-4b-mmproj-Q4_0.gguf
```

smoke test 输出保存在：

```text
D:/CardioConsult_Gemma4_TrackC_Final_V4_20260604/00_audit/gguf_smoke_output.txt
```

## 验证数据

newtraining DICOM 压缩包已解压到：

```text
D:/CardioConsult_Gemma4_TrackC_Final_V4_20260604/02_newtraining_archived/extracted
```

映射文件和指标位于：

```text
D:/CardioConsult_Gemma4_TrackC_Final_V4_20260604/03_mapping
D:/CardioConsult_Gemma4_TrackC_Final_V4_20260604/04_validation/v4_rule_retuned
D:/CardioConsult_Gemma4_TrackC_Final_V4_20260604/06_reports
```

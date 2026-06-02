# CardioConsult PC 精度二次改良版

这是 CardioConsult PC 版的第二次精度改良目录，基于 `D:\cardioconsult_PC_runbook` 复制而来，新增了数据库驱动的层级标签制度。

本版本仍保持原版输入输出合同：

- 输入：一个或多个 PNG、DICOM/DCOM、动图、视频或多帧超声文件。
- 输出：一段中文疑似诊断/医学教学参考文本。
- 模型：可离线调用本地 Gemma4 4B GGUF；模型不可用时使用本地规则后备。
- 目录：`D:\cardioconsult_PC_accuracy_v2_hierarchical_runbook`

## 新增能力

1. 新增 `大方向 → 中方向 → 小方向/具体问题 → 分级 → 证据充分度` 的层级标签输出。
2. 根据公开/可申请心脏超声数据库扩展标签：
   - CAMUS：左心室收缩功能、ED/ES、EF/容积代理。
   - EchoNet-Dynamic：A4C 视频、EF、EDV、ESV、LV tracing。
   - EchoNet-LVH：PLAX、室壁厚度、左室肥厚。
   - TMED-2：PLAX/PSAX/A2C/A4C/Other、主动脉瓣狭窄 none/early/significant。
   - HMC-QU：A4C/A2C、MI/non-MI、节段性室壁运动异常。
3. `教学参考病症判断` 字段本身始终先写具体病症，再用括号给出“大方向 > 中方向”，例如“轻度二尖瓣反流（瓣膜性心脏病 > 二尖瓣疾病）”。信息不足时，小方向写“证据不足，无法进一步细分”或“待排”。
4. 修复旧版部分中文输出编码损坏问题。
5. 新增 `prompts/hierarchical_system_prompt.txt`，并在 `run_diagnosis()` 返回前做层级字段后处理；即使 Gemma4 4B 或旧规则输出旧格式，也会被改写为层级格式。
6. System prompt 现在强制前三句为：层级诊断、最小病症、逻辑链。规则后备也会输出这三个字段。

## 启动

双击：

```text
run_cardio_pc_accuracy_v2_hierarchical.bat
```

或命令行：

```powershell
Set-Location D:\cardioconsult_PC_accuracy_v2_hierarchical_runbook
.\run_cardio_pc_accuracy_v2_hierarchical.bat
```

自检：

```powershell
Set-Location D:\cardioconsult_PC_accuracy_v2_hierarchical_runbook
D:\cardioconsult_PC_runbook\.venv\Scripts\python.exe app.py --self-test
```

## 重要文件

```text
cardio_pc/label_hierarchy.py
cardio_pc/diagnosis.py
cardio_pc/guidance.py
cardio_pc/calibration.py
cardio_pc/features.py
PRECISION_V2_HIERARCHICAL_LABELS.md
```

## 详细说明

请阅读：

```text
D:\cardioconsult_PC_accuracy_v2_hierarchical_runbook\PRECISION_V2_HIERARCHICAL_LABELS.md
```

## 安全声明

本项目仅用于医学教学、比赛演示和基层参考，不是医疗器械，不作为正式临床诊断、治疗建议或医嘱。所有输出必须由有资质医师结合完整标准切面、DICOM 标尺、连续动态帧、病史、体征和正式报告复核。

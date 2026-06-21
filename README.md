# CardioConsult PC

CardioConsult PC 是一个面向便携式/基层心脏超声场景的离线医学教学与辅助判读工作站。它的目标不是替代心超医生，而是在只有便携式超声设备、缺少心超专科医生或需要教学质控的环境中，帮助使用者完成：

- 标准心超图像/动图导入与安全解码。
- B-mode、Color Doppler 和动态图代理特征提取。
- 基于公开心超手册阈值的可审计规则判断。
- 离线 Gemma4 4B 教学解释增强。
- 输出结构化的“教学参考病症判断 / 最小病症 / 逻辑链”。

本项目仅用于医学教学、质量控制、算法研发和基层辅助参考，不作为临床最终诊断、治疗建议或医嘱。

## 适用场景

CardioConsult 的生态位是：**基层或教学环境中已经有便携式超声硬件，但图像采集质量、报告表达和初步判读经验不足**。

典型使用者包括：

- 基层全科医生、急诊/ICU/床旁超声使用者。
- 正在学习心脏超声的住培医生、医学生和规培带教团队。
- 需要做病例复盘、图像质控和报告规范化训练的教学场景。
- 需要离线部署、不能把敏感图像上传云端的本地工作站。

## 当前推荐版本

当前分支为：

```text
v6-rulebook-aligned-20260621
```

这是一个 **V5 对齐**后的增强分支。相比早期 PC V5 版，本版本新增了临床规则手册层，并补齐 V5 经验特征：

- 左室收缩功能减低 / EF 相关规则。
- 二尖瓣反流、三尖瓣反流、主动脉瓣反流、主动脉瓣狭窄。
- 二尖瓣反流伴三尖瓣反流组合代理判断。
- 肺动脉瓣反流代理判断。
- 心包积液、右心负荷/肺高压提示。
- 舒张功能异常或左室充盈压升高提示。
- 节段性室壁运动异常代理判断。
- 左室肥厚倾向、左房增大。
- temporal diff、STI 代理、optical flow、shared-EK、coupled-EK、EchoNet-Dynamic 低 EF 校准。
- Gemma4 急停、紧急切换纯规则模式、大文件防卡策略。

详细补齐记录见 `docs/v5_rule_completion_20260621.md`。

## 快速开始

在 Windows 上克隆仓库后，进入仓库根目录：

```powershell
install_deps.bat
run_preflight.bat
run_ui.bat
```

常用入口：

| 脚本 | 用途 |
| --- | --- |
| `run_ui.bat` | 推荐入口，新版临床规则手册 UI |
| `run_v5_original_ui.bat` | V5 原版兼容 UI |
| `run_self_test_rule_only.bat` | 规则路径自检，不等待 GGUF |
| `run_media_smoke_test.bat` | 用仓库样例跑一次媒体分析 |
| `run_gemma_emergency_stop_smoke.bat` | 验证 Gemma4 急停不会卡死 |
| `run_preflight.bat` | 检查本地交付完整性 |

如果只是想看系统能不能跑，建议先执行：

```powershell
run_self_test_rule_only.bat
run_media_smoke_test.bat
```

## 输入格式

一次输入应对应一个病人或一次检查，可以选择多个文件，也可以选择一个文件夹。

支持格式：

```text
.dcm .dicom .dcom .png .jpg .jpeg .gif .tif .tiff .mp4 .mov .avi
```

建议输入：

- 最理想：标准心脏超声多切面动态图或 DICOM 序列。
- 可接受：PNG/JPG 截图、多帧 GIF、MP4/MOV/AVI 动图。
- 最小输入：任意一个体位的收缩态与舒张态，系统会尝试自动区分相位。

## 输出内容

系统固定保留三个核心字段：

```text
教学参考病症判断
最小病症
逻辑链
```

同时输出：

- 规则命中表。
- 证据等级。
- 缺失证据与补扫建议。
- B-mode / Doppler / 动态代理特征。
- 文件解码与采样摘要。
- 医生填写或系统自动填充的临床测量值。
- 安全边界与复核提示。

示例输出逻辑：

```text
教学参考病症判断：心肌与心功能异常 > 左室收缩功能减低 > 轻度左室收缩功能减低
最小病症：轻度左室收缩功能减低
逻辑链：规则 lv_systolic_function_reduced_v1 → 证据等级 A → EF=43% 命中 mild
```

## 使用模式

### 规则极速模式

默认推荐。系统不等待 GGUF，直接使用图像特征和临床规则生成报告，适合教学演示、大文件导入和基层质控。

### Gemma4 server 增强

适合已经启动本地 llama-server 的离线演示。规则引擎先给出核心结论，Gemma4 只负责解释规则、补充教学语言和整理复核建议。

### Gemma4 CLI 增强

适合没有常驻 server 的单次演示，但冷启动会慢于 server 模式。

Gemma4 不能改写规则引擎给出的 `教学参考病症判断 / 最小病症 / 逻辑链`，只能围绕已命中的规则做解释。

## 离线 Gemma4 4B 配置

模型文件建议放在：

```text
models\gemma-4-4b-it-Q4_K_M.gguf
```

如果你已经在早期版本下载过模型，也可以在 UI 中继续指向原路径，例如：

```text
D:\cardioconsult_PC_runbook\models\gemma-4-4b-it-Q4_K_M.gguf
```

启动本地 server：

```powershell
start_llama_server_v4.bat
```

停止本地 server：

```powershell
stop_llama_server.bat
```

如果 Gemma4 运行中卡住，UI 中可以点击：

- `急停 Gemma`：中断当前 llama-cli 或尝试停止本地 llama-server。
- `紧急规则模式`：放弃 Gemma4，立刻回到纯规则报告。

## 大文件防卡策略

默认 UI 使用安全设置：

- 最大代表帧：48。
- 单文件解码超时：6 秒。
- 代表文件数：12。
- 并行解码数：4。

如果一次输入很多 DICOM/DCOM 文件，系统会先做公平采样和并行解码，避免完整逐帧解码导致 UI 长时间等待。若需要全量分析，可把“代表文件数”设为 `0`，但耗时会明显增加。

## 临床测量值

左侧“可选临床测量值”支持两种来源：

- 医生在分析前手动填写，系统不会覆盖。
- 分析结束后，系统根据规则命中和严重度自动填充空白项，并标注来源。

支持的常用字段包括：

- EF。
- MR VC / MR EROA。
- TR VC / TRV。
- AS Vmax / AS mean gradient / AVA。
- AR VC / PHT。
- 心包积液厚度。
- E/e'、LAVI、LA diameter。
- IVS / LVPW 厚度。

自动填充值只用于教学演示和规则审计，不等同于真实标尺、频谱或正式定量测量。

## 精度与验证

### 当前分支实跑 smoke accuracy

本分支新增了可复现的规则书精度 smoke：

```powershell
python tools\rulebook_accuracy_smoke.py
```

本次运行结果：

| 测试项 | 结果 |
| --- | ---: |
| 测试病例数 | 14 |
| 覆盖规则 | 左室功能、MR、TR、MR+TR、PR、AS、AR、心包积液、肺高压/右心负荷、舒张功能、RWMA、LVH、LA enlargement、未见明确异常 |
| Top label 命中数 | 14 / 14 |
| Exact top-label accuracy | 1.000 |
| Macro F1，不含 normal | 1.000 |

输出文件：

```text
validation\rulebook_accuracy_smoke\rulebook_accuracy_smoke_20260621.json
validation\rulebook_accuracy_smoke\rulebook_accuracy_smoke_20260621.md
```

注意：这是规则引擎集成 smoke，使用合成 patient-level feature payload 检查每条主要规则能否稳定触发，**不是临床泛化准确率**。

### 归档 EchoBench 60 例结果

仓库同时保留了早期基于授权 DICOM/report mapping 的 EchoBench 归档结果，路径为：

```text
archive\performance_runs\validation_speedopt\freeze_runs_full\echobench_20260604_180638
```

该归档为 60 例、纯规则/V4 校准、不调用 GGUF 的结果：

| 标签 | F1 | Sensitivity | Specificity |
| --- | ---: | ---: | ---: |
| valve_any | 1.000 | 1.000 | 0.000 |
| MR | 0.964 | 0.964 | 0.600 |
| TR | 1.000 | 1.000 | 0.000 |
| AR | 0.700 | 0.724 | 0.677 |
| low EF | 0.857 | 1.000 | 0.963 |
| RWMA | 0.500 | 0.333 | 1.000 |
| LA enlargement | 0.696 | 1.000 | 0.865 |

平均每例耗时约 `1.418s`，P95 约 `2.499s`。这些指标用于工程验证和教学原型评估；若进入真实临床研究，需要多中心、前瞻性、专家盲审和正式统计方案。

## 开发者验证

推荐提交前运行：

```powershell
python -m py_compile app.py legacy_v5_app.py src\image_case_adapter.py src\clinical_rule_engine.py src\rulebook_ui.py cardio_pc\diagnosis.py cardio_pc\ui.py tools\rulebook_accuracy_smoke.py tools\submission_preflight.py
run_self_test_rule_only.bat
run_media_smoke_test.bat
run_gemma_emergency_stop_smoke.bat
run_preflight.bat
```

## 项目边界

CardioConsult 当前是医学教学、算法演示和基层辅助参考系统。它强调：

- 可审计规则优先于黑箱输出。
- 医生手填量化指标优先于代理特征。
- 图像质量不足时必须提示补扫或复核。
- Gemma4 只做解释增强，不做不可追溯的最终诊断。

正式诊断仍需结合完整标准切面、DICOM 标尺、连续动态帧、病史、体征和有资质医师报告。

## 许可证

本项目使用 Apache-2.0 License。第三方依赖、数据集和模型说明见：

- `LICENSE`
- `NOTICE`
- `THIRD_PARTY_NOTICES.md`
- `DATASETS.md`

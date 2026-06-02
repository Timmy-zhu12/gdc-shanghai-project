# CardioConsult PC 精度二次改良版：层级标签体系

本目录是基于 `D:\cardioconsult_PC_runbook` 的二次改良版本，目标是在保持原版输入输出合同不变的前提下，引入“数据库驱动的标签扩展”和“诊断层级制度”。

## 运行方式

```powershell
Set-Location D:\cardioconsult_PC_accuracy_v2_hierarchical_runbook
.\run_cardio_pc_accuracy_v2_hierarchical.bat
```

自检：

```powershell
Set-Location D:\cardioconsult_PC_accuracy_v2_hierarchical_runbook
D:\cardioconsult_PC_runbook\.venv\Scripts\python.exe app.py --self-test
```

如果本目录没有 `.venv`，启动脚本会自动创建并安装依赖。Gemma4 4B GGUF 默认继续复用原 PC 版模型路径：

```text
D:\cardioconsult_PC_runbook\models\gemma-4-4b-it-Q4_K_M.gguf
D:\cardioconsult_PC_runbook\models\gemma-4-4b-mmproj-Q4_0.gguf
```

## 重新查询的数据库与可用标签

| 数据库 | 公开/访问状态 | 可用于扩展的标签 | 本次接入方式 |
|---|---|---|---|
| CAMUS | 公开挑战数据集，非商业研究许可 | A2C/A4C、ED/ES、LV 分割、EF/容积估计 | 已用于低 EF B-mode 校准；层级标签中支持“左心室收缩功能异常” |
| EchoNet-Dynamic | Stanford/AIMI research-use agreement | A4C 视频、EF、EDV、ESV、ED/ES LV tracing | 作为“左心室收缩功能异常”和心动周期标签设计依据 |
| EchoNet-LVH | Stanford/AIMI research-use agreement | PLAX 视频、IVS/LVID/LVPW、室壁厚度和心腔尺寸 | 新增“结构重构与容量负荷异常 > 左室肥厚/室壁增厚 > 左室肥厚倾向” |
| TMED-2 | Tufts open-access research dataset | PLAX/PSAX/A2C/A4C/Other 体位；AS none/early/significant | 新增“瓣膜性心脏病 > 主动脉瓣疾病 > 主动脉瓣狭窄” |
| HMC-QU | Kaggle/Academic Torrents 等入口，研究许可 | A4C/A2C；MI/non-MI；节段性 RWMA；LV wall segmentation | 新增“心肌与心功能异常 > 节段性室壁运动异常 > MI 相关室壁运动异常待排” |
| ASE/临床指南 | 公开指南文献 | 腔室量化、瓣膜反流/狭窄分级概念 | 用于把代理特征映射为轻/中/重教学分级，不作为临床定量 |

## 层级标签制度

每次输出都必须包含：

```text
大方向 → 中方向 → 小方向/具体问题 → 分级 → 证据充分度
```

规则：

1. 信息不足时，只给大方向，但小方向会写成“证据不足，无法进一步细分”或“待排”。
2. 信息足够时，输出具体病症和分级，例如“瓣膜性心脏病 > 二尖瓣疾病 > 二尖瓣反流 > 轻度”。
3. `教学参考病症判断` 字段本身必须先展示小方向/最小病症，再用括号展示大方向和中方向，避免只输出“轻度反流”这类缺上下文标签。
4. 所有分级均为教学代理分级。没有连续波多普勒峰速、平均压差、PISA、vena contracta、DICOM 标尺或完整专家标注时，不把结果写成正式临床定量。
5. 输出必须包含“最小病症”和“逻辑链”。最小病症是层级链最后一级；逻辑链必须展示“输入/图像证据 → 规则或模型依据 → 大方向 → 中方向 → 最小病症”。

## 当前标签树

```text
心肌与心功能异常
  ├─ 左心室收缩功能异常
  │   ├─ 左心室收缩功能减低
  │   └─ 左心室收缩功能异常待排
  └─ 节段性室壁运动异常
      ├─ 节段性室壁运动异常
      └─ 心肌梗死相关室壁运动异常待排

瓣膜性心脏病
  ├─ 二尖瓣疾病
  │   ├─ 二尖瓣反流
  │   └─ 二尖瓣狭窄待排
  ├─ 三尖瓣疾病
  │   ├─ 三尖瓣反流
  │   └─ 三尖瓣狭窄待排
  ├─ 主动脉瓣疾病
  │   ├─ 主动脉瓣狭窄
  │   └─ 主动脉瓣反流
  ├─ 肺动脉瓣疾病
  │   └─ 肺动脉瓣反流
  └─ 瓣膜异常待定位
      └─ 彩色多普勒异常血流

结构重构与容量负荷异常
  ├─ 左室肥厚/室壁增厚
  │   └─ 左室肥厚倾向
  └─ 心腔扩大或容量负荷
      ├─ 左心扩大倾向
      └─ 右心容量负荷增高倾向

证据不足或未见明确异常
  ├─ 证据不足
  │   └─ 心脏超声异常证据不足
  └─ 未见明确异常
      └─ 未见明确心脏超声异常
```

## 已修改的主要文件

```text
cardio_pc/label_hierarchy.py   # 新增标签来源、标签树、层级诊断对象
cardio_pc/diagnosis.py         # 重写规则层和 Gemma4 4B prompt
cardio_pc/guidance.py          # 修复基层提示中文输出
cardio_pc/calibration.py       # 修复 CAMUS 校准证据中文输出
cardio_pc/features.py          # 修复体位词表、相位词表、特征摘要中文输出
```

## 分级策略

### B-mode / 左室功能

- 使用 CAMUS 校准器和 ED/ES 面积代理。
- 输入包含 A2C/A3C/A4C 且有收缩/舒张配对时，才给出更具体的“左心室收缩功能减低”。
- 如果只有单帧或体位不足，则降级为“心功能异常待排”或“证据不足”。

### Color Doppler / 瓣膜病

- 使用 HSV 血流区域、最大连通域、喷流宽度、方向一致性、双向混叠、湍流/涡量代理。
- PLAX/A2C/A3C 或 A4C 方向代理偏左心侧：优先二尖瓣反流。
- A4C 方向代理偏右心侧：优先三尖瓣反流。
- A5C/PSAX-AV 且方向一致的高湍流喷流：主动脉瓣狭窄倾向。
- A5C/主动脉瓣相关输入且反向血流代理较高：主动脉瓣反流。
- 无法定位具体瓣膜时，只输出“瓣膜性心脏病 > 瓣膜异常待定位 > 彩色多普勒异常血流”。

### 室壁运动 / MI 待排

- A2C/A4C 等左室切面中，若边缘密度、纹理熵、对比增益异常升高，输出“节段性室壁运动异常/MI 相关改变待排”。
- 该标签受 HMC-QU 的 MI/RWMA 标签启发，但当前版本没有真正的心肌节段追踪，因此保持“待排”。

### 左室肥厚

- PLAX 下利用方向各向异性、边缘密度、左右亮度对称代理做弱提示。
- 该标签受 EchoNet-LVH 的 IVS/LVID/LVPW 标注启发，但当前版本未直接测量 IVS/LVPW，因此只输出“倾向”。

## 本地验证

已运行：

```powershell
D:\cardioconsult_PC_runbook\.venv\Scripts\python.exe -m py_compile app.py cardio_pc\diagnosis.py cardio_pc\label_hierarchy.py cardio_pc\guidance.py cardio_pc\calibration.py cardio_pc\features.py cardio_pc\imaging.py cardio_pc\ui.py
D:\cardioconsult_PC_runbook\.venv\Scripts\python.exe app.py --self-test
```

结果：编译通过，自检输出包含“大方向/中方向/小方向/分级/证据充分度”。

## 参考来源

- CAMUS: https://www.creatis.insa-lyon.fr/Challenge/camus/
- EchoNet-Dynamic: https://echonet.github.io/dynamic/
- EchoNet-LVH: https://echonet.github.io/lvh/
- TMED-2: https://tmed.cs.tufts.edu/tmed_v2.html
- HMC-QU: https://www.kaggle.com/datasets/aysendegerli/hmcqu-dataset
- ASE chamber quantification guideline: https://doi.org/10.1016/j.echo.2014.10.003
- ASE valvular regurgitation guideline: https://doi.org/10.1016/j.echo.2017.01.007

## 安全边界

本项目仍是医学教学和比赛原型，不是医疗器械，不作为临床诊断、治疗建议或医嘱。任何输出均应由有资质医师结合完整标准切面、DICOM 标尺、连续动态帧、病史、体征和正式报告复核。

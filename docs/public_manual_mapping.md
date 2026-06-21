# 公开临床手册要求映射

版本日期：2026-06-20

## 1. 综合 TTE 与 minimum dataset

公开手册来源：

- ASE comprehensive TTE 指南强调成人 TTE 的检查内容、技术执行、超声模态整合、测量和数据显示规范。
- BSE adult TTE minimum dataset 给出标准成人经胸超声的结构化采集顺序和最低数据集；如果发现异常，应增加病理相关切面和测量。

映射到 CardioConsult：

| 手册要求 | 测试版实现 |
|---|---|
| 标准切面覆盖 | `minimum_dataset.standard_views` |
| B-mode、Color、PW、CW、TDI 等模态 | `minimum_dataset.modalities` |
| 先质控再判断 | 每条规则检查 `quality_score`、动态配对、Doppler/频谱/TDI 是否存在 |
| 异常时补充专病测量 | 规则输出 `missing_or_blocking` 和 `warnings` |

## 2. 左室收缩功能

公开手册来源：

- ASE/EACVI chamber quantification 2015。

测试版规则：

| 指标 | 范围 |
|---|---|
| EF < 50% | 左室收缩功能减低筛查触发 |
| 41%-49% | 轻度 |
| 30%-40% | 中度 |
| <30% | 重度 |

PNG/动图无标尺时，使用 `contractility_fraction_proxy` 和 `contractility_proxy`，但标记为代理证据。

## 3. 瓣膜反流

公开手册来源：

- ASE valvular regurgitation 2017。

测试版纳入：

| 病症 | 临床量化指标 | 代理特征 |
|---|---|---|
| 二尖瓣反流 | VC、EROA、RVol | flow_active_ratio、jet_width_proxy、flow_turbulence_proxy |
| 三尖瓣反流 | VC、EROA、RVol | flow_active_ratio、jet_width_proxy |
| 主动脉瓣反流 | VC、EROA、RVol、PHT | flow_active_ratio、jet_width_proxy |

原则：如果只有 Color Doppler 活跃区但不能定位瓣膜，不能强行输出某个具体瓣膜反流。
测试版因此新增 `瓣膜反流待定位` 规则：仅在缺少明确瓣膜定位时作为 broad fallback，提示补充 PLAX/A4C/A2C/A5C 等切面。

## 4. 主动脉瓣狭窄

公开手册来源：

- ASE/EACVI valve stenosis guideline。

测试版规则：

| 分级 | Vmax | Mean gradient | AVA |
|---|---:|---:|---:|
| 轻度 | 2.0-2.9 m/s | <20 mmHg | >1.5 cm² |
| 中度 | 3.0-3.9 m/s | 20-39 mmHg | 1.0-1.5 cm² |
| 重度 | >=4.0 m/s | >=40 mmHg | <=1.0 cm² |

没有频谱多普勒时，只能输出“筛查提示”，不能输出临床级狭窄分级。

## 5. 心包积液

公开手册来源：

- ESC pericardial disease guideline。
- ASE pericardial multimodality imaging document。

测试版规则：

| 分级 | 最大无回声间隙 |
|---|---:|
| 轻度 | <10 mm |
| 中度 | 10-20 mm |
| 大量 | >20 mm |

没有 mm 测量值时，只能使用 `pericardial_echo_free_space_proxy`。

## 6. 肺高压或右心负荷提示

公开手册来源：

- BSE pulmonary hypertension echocardiography guideline。
- ASE right heart / pulmonary hypertension 2025。

测试版规则：

| 指标 | 用法 |
|---|---|
| TR peak velocity >=2.8 m/s | 肺高压可能性提示 |
| TR peak velocity >3.4 m/s | 高概率组成证据 |
| 支持征象 >=2 | 增强提示强度 |

输出必须写“肺高压提示/可能性”，不能写“确诊肺高压”。

## 7. 舒张功能

公开手册来源：

- ASE/EACVI diastolic function 2016。

测试版规则纳入：

| 指标 | 异常阈值 |
|---|---:|
| 平均 E/e' | >14 |
| Septal e' | <7 cm/s |
| Lateral e' | <10 cm/s |
| LA volume index | >34 mL/m² |
| TR velocity | >2.8 m/s |

若无组织多普勒和 LA/TRV 测量，输出“不可评估”，不使用纯图像代理强行判断舒张功能。

## 8. 参考来源

- American Society of Echocardiography. Guidelines for Performing a Comprehensive Transthoracic Echocardiographic Examination in Adults. https://www.onlinejase.com/article/S0894-7317(18)30318-3/fulltext
- British Society of Echocardiography. A minimum dataset for a standard adult transthoracic echocardiogram. https://pmc.ncbi.nlm.nih.gov/articles/PMC4676441/
- ASE/EACVI. Recommendations for Cardiac Chamber Quantification by Echocardiography in Adults. https://www.asecho.org/wp-content/uploads/2016/02/2015_ChamberQuantificationREV.pdf
- ASE. Recommendations for Noninvasive Evaluation of Native Valvular Regurgitation. https://www.asecho.org/wp-content/uploads/2017/04/2017VavularRegurgitationGuideline.pdf
- ASE/EACVI. Recommendations on the Echocardiographic Assessment of Aortic Valve Stenosis. https://www.asecho.org/wp-content/uploads/2017/04/2017ValveStenosisGuideline.pdf
- ASE/EACVI. Recommendations for the Evaluation of Left Ventricular Diastolic Function by Echocardiography. https://asecho.org/wp-content/uploads/2016/03/2016_LVDiastolicFunction.pdf
- BSE. Echocardiographic assessment of pulmonary hypertension. https://pmc.ncbi.nlm.nih.gov/articles/PMC6055509/
- ASE. Right Heart in Adults & Pulmonary Hypertension. https://www.asecho.org/guideline/right-heart-in-adults-pulmonary-hypertension/
- ESC. 2015 Guidelines for the diagnosis and management of pericardial diseases. https://pmc.ncbi.nlm.nih.gov/articles/PMC7539677/

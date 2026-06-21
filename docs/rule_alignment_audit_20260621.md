# CardioConsult V5 与最新版规则引擎对齐审计

日期：2026-06-21

## 审计范围

对比对象：

- V5 经验规则：`cardio_pc/diagnosis.py`、`cardio_pc/v4_calibration.py`、`cardio_pc/v5_echonet.py`、`shared/disease_labels.json`
- 最新版临床规则手册：`config/clinical_rulebook_v0.1.json`、`src/clinical_rule_engine.py`、`src/image_case_adapter.py`

结论摘要：最新版规则手册比 V5 更规范，已经覆盖 EF、MR、TR、AS、AR、心包积液、右心负荷/肺高压、舒张功能；但仍缺少若干 V5 经验分支和部分代理特征接入。最重要的缺口不是 Gemma4，而是“规则库有条目但图像代理值未计算”。

## 已经对齐的主要能力

| 诊断方向 | V5 | 最新版规则手册 | 状态 |
|---|---|---|---|
| 左室收缩功能减低 | `lv_systolic_function_camus_echonet`、V5 EchoNet 校准 | `lv_systolic_function_reduced_v1` | 已覆盖，但 V5 MLP 校准未进入规则手册 UI |
| 二尖瓣反流 | `valve_mr_doppler_hierarchy` | `mitral_regurgitation_integrated_v1` | 已覆盖 |
| 三尖瓣反流 | `valve_tr_doppler_hierarchy` | `tricuspid_regurgitation_integrated_v1` | 已覆盖 |
| 主动脉瓣狭窄 | `valve_as_tmed2_hierarchy` | `aortic_stenosis_quantitative_v1` | 已覆盖，新版更偏临床阈值 |
| 主动脉瓣反流 | `valve_ar_doppler_hierarchy` | `aortic_regurgitation_integrated_v1` | 已覆盖 |
| 未定位瓣膜反流 | `valve_unlocalized_doppler_regurgitation` | `valvular_regurgitation_unlocalized_proxy_v1` | 已覆盖 |
| 心包积液 | V5 主规则未显式覆盖 | `pericardial_effusion_size_v1` | 新版新增 |
| 右心负荷/肺高压提示 | V5 主规则未显式覆盖 | `pulmonary_hypertension_probability_v1` | 新版新增 |
| 舒张功能异常/充盈压升高 | V5 主规则未显式覆盖 | `diastolic_function_screen_v1` | 新版新增 |

## 明确缺漏

### 1. 肺动脉瓣反流规则缺失

V5 有 `valve_pr_psax_proxy`，在 PSAX 大血管层面彩色血流异常时输出“肺动脉瓣反流”疑似标签。

最新版规则手册目前没有 `pulmonary_regurgitation` 规则。`shared/disease_labels.json` 仍保留 `mild_pulmonary_regurgitation`，说明历史标签体系里有这个方向。

建议：新增低优先级 proxy-only 规则，限定 `PSAX-AV/RVOT` 或明确文件名/体位信息时才触发，避免泛化误判。

### 2. V4 本地授权 DICOM 的“轻度 MR + 轻度 TR 组合”经验未进入规则手册

V5/V4 有 `v4_local_dicom_shared_ek_coupled_ek` 和 `valve_combined_mr_tr_low_turbulence_proxy`：

- 适用于多帧 DICOM、体位未知、Doppler 异常轻、湍流/涡量不高的场景。
- 这正是早期本地“轻度二尖瓣反流、轻度三尖瓣反流”样本调校得到的经验。

最新版规则手册有未定位反流，但不会稳定输出“轻度二尖瓣反流伴轻度三尖瓣反流”组合标签。

建议：新增 `mild_av_valve_regurgitation_combined_proxy_v1`，证据等级固定 C，并明确来自本地授权教学集校准，不能作为临床定量分级。

### 3. 节段性室壁运动异常 / 心肌梗死相关 RWMA 待排缺失

V5 有 `rwma_mi_hmcqu_proxy`：

- A2C/A4C 左室切面；
- B-mode 边缘密度、纹理熵、对比增益异常；
- 输出“心肌梗死相关室壁运动异常待排”。

最新版规则手册没有 RWMA 规则。

建议：新增 `regional_wall_motion_abnormality_proxy_v1`，只输出“待排/提示”，不要输出确定 MI。

### 4. 左室肥厚 / 室壁增厚倾向缺失

V5 有 `lvh_echonet_lvh_proxy`：

- PLAX；
- 边缘密度、各向异性、亮度对称代理异常；
- 输出“左室肥厚倾向”。

最新版规则手册没有 LVH/室壁增厚规则，也没有 IVS/LVPW 手填字段。

建议：新增临床测量字段 `ivs_d_mm`、`lvpw_d_mm`、`lv_mass_index_g_m2`，优先按临床量化判断；没有测量时仅给 proxy-only 倾向。

### 5. 左房增大倾向只在 V4 结构提示里出现，规则手册未显式覆盖

V4 `build_v4_evidence()` 会输出 `la_enlargement`，但最新版只在舒张功能规则中使用 `la_volume_index_ml_m2`，没有独立“左房增大”标签。

建议：增加 `left_atrial_enlargement_v1`，使用 `la_volume_index_ml_m2 > 34` 作为临床阈值；缺少 LAVI 时不建议用图像代理强行判断。

## 隐性缺口：规则已有，但图像代理没有接入

`src/image_case_adapter.py` 当前固定写死：

```python
"pericardial_echo_free_space_proxy": 0.0
"right_heart_size_proxy": 0.0
"septal_flattening_proxy": 0.0
```

因此：

- `pericardial_effusion_size_v1` 如果医生不填 `pericardial_effusion_mm`，图像代理不会触发。
- `pulmonary_hypertension_probability_v1` 如果医生不填 TRV 或 supporting signs，图像代理不会触发。

建议优先级高于新增小病种规则。应先实现：

- 心包无回声区代理：基于 PLAX/A4C/SUBCOSTAL 边缘暗带比例。
- 右心大小代理：A4C 中右侧/左侧暗腔面积比。
- 室间隔扁平化代理：PSAX 或 A4C 中 LV 圆度/偏心率代理。

## V5 经验没有完全进入规则手册的算法点

V5/V4 包含以下经验/工程层：

- 图像差分 `temporal_diff`
- STI 应变代理 `sti_strain_proxy`
- 光流代理 `optical_flow_proxy`
- shared-EK 瓣膜分 `shared_ek_valve`
- coupled-EK 结构分 `coupled_ek_structure`
- EchoNet-Dynamic 轻量 MLP 低 EF 校准

最新版规则手册 UI 目前主要使用 `contractility_proxy`、`contractility_fraction_proxy`、B-mode 纹理和 Doppler 低维代理，没有把 V4/V5 校准层统一写入 `patient["proxies"]`。

建议：在 `image_case_adapter.py` 中新增一个 `v5_experience_proxies` 模块，把这些特征作为可审计代理输出，再由规则手册显式消费。

## 建议实施顺序

1. 先补代理特征接入：心包、右心、室间隔、V4 temporal/STI/optical-flow/shared-EK/coupled-EK。
2. 再补 V5 缺失规则：PR、MR+TR组合、RWMA、LVH、LA enlargement。
3. 最后做回归：同一输入下原有 `教学参考病症判断 / 最小病症 / 逻辑链` 不应非预期漂移；新增规则只在对应证据更强时触发。

## 不建议直接做的事

- 不建议把 V5 所有经验分支不加约束地并入临床规则手册，否则会把本地样本经验误当成指南阈值。
- 不建议让 Gemma4 负责补这些规则；Gemma4 应只解释规则结果，不应创造新的诊断标签。
- 不建议让 proxy-only 规则输出高证据等级，应该固定为 B/C，并强制写明需要正式超声复核。

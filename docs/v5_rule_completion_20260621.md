# V5 诊断经验补齐记录（2026-06-21）

本次补齐目标：将 V5 版本中已有但未进入最新版临床规则引擎的诊断经验、代理特征和 UI 自动填充逻辑并入 `D:\cardioconsult_rulebook_v5_aligned_20260620`，同时保持医生手填量化指标优先、规则路径可审计、Gemma4 仅作为可选解释增强。

## 已补齐的图像代理特征

- `pericardial_echo_free_space_proxy`：由图像暗带/心包外周无回声区代理估算，不再固定为 0。
- `right_heart_size_proxy`：由右心相关半区暗腔面积与不对称性估算，不再固定为 0。
- `septal_flattening_proxy`：由中央暗腔形态宽高比估算，不再固定为 0。
- `lvh_wall_thickening_proxy`：由边缘密度、方向各向异性和左右对称代理估算。
- `v4_temporal_diff`、`sti_strain_proxy`、`optical_flow_proxy`：复用 V4 图像差分、STI 代理和光流代理。
- `shared_ek_valve_score`、`coupled_ek_structure_score`：复用 V4 shared-EK / coupled-EK 经验特征。
- `v4_mr_flag`、`v4_tr_flag`、`v4_ar_flag`、`v4_low_ef_flag`、`v4_rwma_flag`、`v4_la_enlargement_flag`：复用 V4 本地授权数据经验标记。
- `combined_mr_tr_proxy`、`rwma_proxy`、`la_enlargement_proxy`：用于新版规则书的组合病症触发。
- `v5_low_ef_probability`、`v5_ef_pred_percent`、`v5_low_ef_positive`：接入 V5 EchoNet-Dynamic 轻量低 EF 校准器；模型缺失时自动回落为 0，不阻塞规则路径。

## 已补齐的诊断规则

- `combined_mitral_tricuspid_regurgitation_v5_proxy_v1`：轻度二尖瓣反流伴轻度三尖瓣反流组合代理规则。
- `pulmonary_regurgitation_psax_proxy_v1`：肺动脉瓣反流 PSAX/RVOT 代理规则。
- `regional_wall_motion_abnormality_proxy_v1`：节段性室壁运动异常代理规则。
- `left_ventricular_hypertrophy_proxy_v1`：左室肥厚倾向规则，支持 IVS/LVPW 手填量化。
- `left_atrial_enlargement_integrated_v1`：左房增大规则，支持 LAVI 和 LA diameter 手填量化。

同时，`lv_systolic_function_reduced_v1` 已补入 V5 低 EF 概率、coupled-EK 结构分和 V4 low-EF flag。

## UI 补齐

- 新增手填/自动填充字段：
  - `LA diameter (mm)`
  - `IVS 厚度 (mm)`
  - `LVPW 厚度 (mm)`
- 自动填充新增规则：
  - MR+TR 组合规则可同时回填 MR/TR 相关代理测量。
  - LVH 可回填 IVS/LVPW 代理值。
  - LA enlargement 可回填 LAVI/LA diameter 代理值。
  - 肺动脉瓣反流暂无稳定 UI 量化字段，不自动乱填 TRV 或其他无关指标。

## 验证结果

- `python -m py_compile`：通过。
- `run_self_test_rule_only.bat`：通过。
- `run_preflight.bat`：通过。
- `run_media_smoke_test.bat`：通过。
- `run_gemma_emergency_stop_smoke.bat`：通过。
- `run_smoke_test.bat`：通过。
- 合成病例验证：MR+TR、肺动脉瓣反流、RWMA、LVH、左房增大均可触发；医生手填量化指标仍优先形成 A 级证据。

## 安全边界

新增规则中来自 V4/V5 经验代理的结果均保持为教学/质控辅助判断。若没有 EF、VC、EROA、TRV、Vmax、LAVI、IVS/LVPW 等正式量化指标，报告仍应标注为代理证据，需要标准切面、频谱/测量和有资质医生复核。

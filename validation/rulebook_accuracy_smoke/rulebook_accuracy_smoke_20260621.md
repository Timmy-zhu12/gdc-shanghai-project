# Rulebook Accuracy Smoke

This is a deterministic integration smoke test for the clinical rulebook. It uses synthetic patient-level feature payloads and checks whether each major rule returns the expected top label. It is not a clinical accuracy claim.

| Metric | Value |
| --- | ---: |
| Cases | 14 |
| Correct top labels | 14 |
| Exact top-label accuracy | 1.000 |
| Macro F1, excluding normal | 1.000 |

| Case | Expected | Predicted | Result |
| --- | --- | --- | --- |
| LV_EF_MILD | reduced_lv_systolic_function | reduced_lv_systolic_function | PASS |
| MR_SEVERE | mitral_regurgitation | mitral_regurgitation | PASS |
| TR_SEVERE | tricuspid_regurgitation | tricuspid_regurgitation | PASS |
| MR_TR_PROXY | combined_mitral_tricuspid_regurgitation | combined_mitral_tricuspid_regurgitation | PASS |
| PR_PROXY | pulmonary_regurgitation | pulmonary_regurgitation | PASS |
| AS_MODERATE | aortic_stenosis | aortic_stenosis | PASS |
| AR_SEVERE | aortic_regurgitation | aortic_regurgitation | PASS |
| EFFUSION_MODERATE | pericardial_effusion | pericardial_effusion | PASS |
| PH_SUGGESTIVE | right_heart_load_or_pulmonary_hypertension | right_heart_load_or_pulmonary_hypertension | PASS |
| DIASTOLIC | diastolic_dysfunction_or_elevated_lv_filling_pressure | diastolic_dysfunction_or_elevated_lv_filling_pressure | PASS |
| RWMA_PROXY | regional_wall_motion_abnormality | regional_wall_motion_abnormality | PASS |
| LVH_MODERATE | left_ventricular_hypertrophy | left_ventricular_hypertrophy | PASS |
| LAE_MODERATE | left_atrial_enlargement | left_atrial_enlargement | PASS |
| NORMAL_PROXY | no_positive_rule | no_positive_rule | PASS |

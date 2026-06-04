# Diagnostic Contract

All platform implementations should keep this behavior consistent.

## Input

- One or more de-identified cardiac ultrasound media files.
- Supported clinical intent: teaching and research prototype only.
- Maximum target coverage: standard 12 echocardiography views.
- Minimum target coverage: one view with systolic and diastolic phases.

## Processing

- Detect or infer view labels where possible.
- Detect ED/ES or systole/diastole by filename first.
- If phase names are missing, use per-view chamber-area proxy to estimate phase.
- Extract B-mode and Color Doppler features.
- Generate a structured evidence summary.
- Use Gemma4 4B offline generation when available.
- Fall back to local rules when the model is unavailable.

## Output

The output must be one Chinese paragraph containing:

- A specific teaching-reference disease label.
- Confidence level.
- B-mode evidence.
- Doppler evidence.
- Recommended follow-up views for beginners or primary-care users.
- Safety statement that this is not a clinical diagnosis.

Examples of allowed labels:

- 轻度二尖瓣反流
- 中度二尖瓣反流
- 轻度三尖瓣反流
- 中度三尖瓣反流
- 主动脉瓣轻度狭窄倾向
- 轻度主动脉瓣反流
- 肺动脉瓣轻度反流
- 左心室收缩功能减低
- 节段性室壁运动异常
- 未见明确心脏超声异常
- 图像证据不足，倾向未见明确异常

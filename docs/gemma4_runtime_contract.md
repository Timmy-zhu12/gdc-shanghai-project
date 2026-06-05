# Gemma4 运行契约与报告保护

本页用于说明 PC V5 中 Gemma4 4B、超声特征层、层级规则层和安全报告保护之间的分工。这样做的目的不是削弱大模型，而是在医学教学场景中让每次输出都可复现、可审计、可解释。

## Gemma4 接收的输入

Gemma4 不直接接收原始病人图像，也不上传数据到云端。PC V5 先在本机完成以下步骤：

1. 读取 PNG、DICOM/DCOM、cine 或视频输入。
2. 对 B-mode 进行去噪、增强、边缘/纹理/腔室面积代理提取。
3. 对 Color Doppler 进行 HSV 血流向量化、连通域、喷流宽度、方向一致性、湍流和涡量代理提取；当体位证据不足时，同时生成 MR/TR/AR/PR 瓣膜定位评分。
4. 对动图进行代表帧采样、时间差分、收缩/舒张估计、STI 风格局部功能代理和光流代理提取。
5. 由层级标签规则给出候选大方向、中方向、最小病症、严重程度和证据充分度。
6. 将结构化证据、候选标签、质量分和安全约束压缩成 JSON 输出合同，交给本地 Gemma4 4B GGUF。

## Gemma4 负责的输出

Gemma4 的主要职责是把结构化证据组织成可控的教学报告材料。当前默认配置要求 Gemma4 只输出一个 JSON object，再由本地报告守卫重渲染为中文自然语言报告。这样可以让模型参与证据表达，同时避免最小病症被自由文本改写成过宽泛标签。

JSON 输出至少包含：

- `教学参考病症判断`
- `最小病症`
- `逻辑链`
- `证据摘要`
- `置信度说明`
- `基层补扫建议`
- `安全边界`

最终中文报告必须保持以下强制字段：

- `教学参考病症判断：`
- `最小病症：`
- `逻辑链：`
- 证据充分度、置信度、补扫建议和安全边界

报告必须用中文说明从大方向到具体问题的层级判断。如果证据不足以定位具体瓣膜，报告也必须说明为什么只能给出较宽泛的最小判断。

## 规则层负责的内容

规则层负责医学安全边界和确定性兜底：

- 当 Gemma4 权重不存在、模型调用失败或设备资源不足时，规则层仍输出同样的报告合同。
- 当 Gemma4 输出 JSON 时，报告保护会优先提取第一个合法 JSON object，并通过本地诊断合同重渲染报告。
- 当 Gemma4 输出自由文本且缺少必需字段、泄漏提示词、过短、未包含安全声明或明显未完成时，报告保护会先尝试轻量修复；仍不可用时改写为本地教学模板。
- 层级病症候选、危险提示和“不是医疗器械/不作为正式临床诊断”的边界声明始终由本地代码强制保证。

## 审计字段

每次启用多智能体审计时，`exports/agent_audit/` 会生成 JSON 文件。`ReportAgent` 中的关键字段包括：

| 字段 | 含义 |
|---|---|
| `backend` | 本次尝试使用的后端：`llama_server`、`llama_cli` 或 `rule_fallback` |
| `model_text_received` | 是否实际收到了 Gemma4 文本 |
| `report_guard_checked` | 是否执行了报告保护检查 |
| `report_guard_structured` | Gemma4 文本是否被识别为结构化 JSON 并由本地合同重渲染 |
| `report_guard_repaired` | Gemma4 文本是否被补齐必需字段或安全边界 |
| `report_guard_rewritten` | Gemma4 文本是否因安全/完整性问题被本地模板改写 |
| `report_source` | 最终报告来源：`gemma4_structured`、`gemma4_preserved`、`gemma4_repaired`、`gemma4_guarded_template` 或 `rule_template` |
| `has_judgment` | 是否包含教学参考病症判断字段 |
| `has_minimum_condition` | 是否包含最小病症字段 |
| `has_logic_chain` | 是否包含逻辑链字段 |

这套字段能区分“Gemma4 生成 JSON 并由本地合同渲染”“Gemma4 自由文本生成并保留”“Gemma4 生成并被轻量修复”“Gemma4 生成但被安全模板接管”和“未调用到模型、走规则兜底”五种情况。

## 推荐复现路径

快速规则自检：

```powershell
.\install_deps.bat
.\.venv\Scripts\python.exe app.py --self-test-rule-only
```

本地 Gemma4 服务复现：

```powershell
.\start_llama_server_v4.ps1
```

然后按 [service_validation.md](service_validation.md) 进行 `/completion` smoke 与项目链路检查。

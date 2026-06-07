# Gemma4 内部函数调用合同

本项目把离线 Gemma4 4B 放在主智能层位置：它负责阅读结构化超声证据、决定是否调用本地工具、组织层级诊断和生成报告材料。规则极速模式用于现场防卡和无模型复现；Gemma4 增强路径则保留原生函数调用合同，便于评审理解模型如何与本地边缘计算工具协作。

## 设计目标

- 只允许 Gemma4 调用本地白名单函数，不允许任意代码执行。
- 所有工具调用只读取当前病例的脱敏、已加载特征，不上传原始图像。
- 工具返回结构化 JSON，再由 Gemma4 组织报告材料，并由本地报告守卫生成固定中文诊断字段。
- 任一模型输出不符合合同，系统回退到可审计规则报告。

## Tool Manifest

核心实现位于 `cardio_pc/function_calling.py`，当前暴露三个内部工具：

| 工具名 | 作用 | 安全边界 |
|---|---|---|
| `summarize_ultrasound_features` | 返回 B-mode、Color Doppler、相位、体位和质量摘要 | 只返回低维代理特征，不返回原始像素 |
| `run_rule_diagnosis` | 返回确定性的层级规则诊断 | 不调用外部网络，不改变病例状态 |
| `safety_boundary_check` | 返回隐私、教学用途和转诊边界 | 固定安全文本，避免模型省略安全声明 |

Gemma4 如需调用工具，只能输出如下 JSON object：

```json
{
  "function_call": {
    "name": "summarize_ultrasound_features",
    "arguments": {}
  }
}
```

本地执行器会拒绝：

- 不在白名单里的工具名。
- 带额外参数的调用。
- 非 JSON object 的 tool-call。
- 任何试图读取文件系统、访问网络或执行 shell 的请求。

## 与现有流程的关系

```text
输入 PNG/DICOM/DCOM/MP4
  -> 安全解码与代表帧采样
  -> B-mode / Doppler / 动态相位特征
  -> 结构化病例证据
  -> Gemma4 function_call
  -> 本地白名单工具
  -> Gemma4 报告组织
  -> 本地报告守卫重渲染
  -> 教学参考病症判断 / 最小病症 / 逻辑链 / 安全边界
```

也就是说，Gemma4 负责“询问、整合和解释证据”，而不是绕过本地规则直接对图像做无约束判断。这可以同时满足端侧隐私、医学教学可解释性和现场演示稳定性。

## 快速验证

```powershell
python tools\function_calling_smoke.py
```

预期输出：

```json
{"function_calling_smoke": "ok", "...": "..."}
```

该 smoke 不需要 GGUF 模型，也不会访问网络；它只验证工具清单、白名单执行和非法工具拒绝逻辑。

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Callable

from .features import StudyAnalysis


@dataclass(frozen=True)
class ToolCallResult:
    name: str
    ok: bool
    payload: dict[str, Any]


def gemma4_tool_manifest() -> list[dict[str, Any]]:
    """Whitelisted local functions that Gemma4 may request in enhanced mode."""
    return [
        {
            "name": "summarize_ultrasound_features",
            "description": "Return bounded B-mode, Color Doppler, phase, view and quality features for the current study.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        {
            "name": "run_rule_diagnosis",
            "description": "Return the deterministic hierarchical teaching diagnosis selected by local rules.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        {
            "name": "safety_boundary_check",
            "description": "Return privacy, non-medical-device and escalation safety text for the current report.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    ]


def build_function_calling_prompt(base_prompt: str) -> str:
    manifest = json.dumps(gemma4_tool_manifest(), ensure_ascii=False, indent=2)
    return (
        f"{base_prompt}\n\n"
        "Gemma4 原生函数调用契约：如需调用本地工具，只能输出 JSON object，格式为 "
        '{"function_call":{"name":"工具名","arguments":{}}}。'
        "本地运行时只执行白名单工具，工具返回后再生成最终中文教学报告。\n"
        f"可用工具清单：\n{manifest}"
    )


def execute_tool_call(
    call: dict[str, Any],
    study: StudyAnalysis,
    rule_report_factory: Callable[[], str],
) -> ToolCallResult:
    function_call = call.get("function_call") if isinstance(call, dict) else None
    if not isinstance(function_call, dict):
        return ToolCallResult("invalid", False, {"error": "missing function_call object"})
    name = str(function_call.get("name", ""))
    arguments = function_call.get("arguments", {})
    if arguments not in ({}, None):
        return ToolCallResult(name, False, {"error": "arguments are not accepted by this offline tool contract"})

    if name == "summarize_ultrasound_features":
        return ToolCallResult(
            name,
            True,
            {
                "view_count": study.view_count,
                "input_count": study.input_count,
                "systole_count": study.systole_count,
                "diastole_count": study.diastole_count,
                "quality_score": round(study.quality_score, 3),
                "contractility_fraction_proxy": round(study.contractility_fraction_proxy, 3),
                "feature_summary": study.feature_summary,
            },
        )
    if name == "run_rule_diagnosis":
        return ToolCallResult(name, True, {"report": rule_report_factory()})
    if name == "safety_boundary_check":
        return ToolCallResult(
            name,
            True,
            {
                "privacy": "All ultrasound media stay on the local device; no cloud upload is required.",
                "medical_boundary": "Teaching and primary-care reference only; not a medical-device final diagnosis.",
                "escalation": "High-risk symptoms or low-quality/incomplete views require formal clinical workflow.",
            },
        )
    return ToolCallResult(name, False, {"error": f"tool is not whitelisted: {name}"})

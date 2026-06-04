from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path
from time import perf_counter
from typing import Callable, Any

from .features import StudyAnalysis
from .label_hierarchy import HierarchicalDiagnosis


@dataclass
class AgentStep:
    name: str
    role: str
    status: str
    elapsed_ms: float
    input_summary: str
    output_summary: str
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "status": self.status,
            "elapsed_ms": round(self.elapsed_ms, 3),
            "input_summary": self.input_summary,
            "output_summary": self.output_summary,
            "evidence": clean_json_value(self.evidence),
        }


@dataclass
class AgentAuditTrail:
    run_id: str
    created_at: str
    steps: list[AgentStep] = field(default_factory=list)
    audit_path: str = ""

    def add(self, step: AgentStep) -> None:
        self.steps.append(step)

    def compact_text(self) -> str:
        names = " -> ".join(step.name for step in self.steps)
        total_ms = sum(step.elapsed_ms for step in self.steps)
        return f"多智能体审计链：{names}；编排开销约 {total_ms:.1f} ms"

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "created_at": self.created_at,
            "audit_path": self.audit_path,
            "steps": [step.to_dict() for step in self.steps],
        }


@dataclass
class AgentDecisionState:
    decision: HierarchicalDiagnosis
    audit: AgentAuditTrail


class OfflineMultiAgentOrchestrator:
    """Small local agent chain for auditability; no network or extra model calls."""

    def __init__(self, audit_dir: Path, write_audit: bool = True) -> None:
        self.audit_dir = audit_dir
        self.write_audit = write_audit

    def run_until_decision(
        self,
        study: StudyAnalysis,
        decision_fn: Callable[[StudyAnalysis], HierarchicalDiagnosis],
    ) -> AgentDecisionState:
        run_id = datetime.now().strftime("agent_%Y%m%d_%H%M%S_%f")
        audit = AgentAuditTrail(run_id=run_id, created_at=datetime.now().isoformat(timespec="seconds"))

        audit.add(run_agent_step("InputAgent", "核对输入文件、体位覆盖、收缩/舒张配对", summarize_input_agent, study))
        audit.add(run_agent_step("FeatureAgent", "汇总 B-mode、Color Doppler 和动态图代理特征", summarize_feature_agent, study))

        start = perf_counter()
        decision = decision_fn(study)
        audit.add(
            AgentStep(
                name="DiagnosisAgent",
                role="执行层级标签规则、V4 校准和 V5 EchoNet 校准",
                status="ok",
                elapsed_ms=(perf_counter() - start) * 1000.0,
                input_summary=f"quality={study.quality_score:.3f}, views={study.view_count}, frames={study.input_count}",
                output_summary=decision.compact_label,
                evidence={
                    "label_path": decision.label_path,
                    "rule_id": decision.rule_id,
                    "confidence": decision.confidence,
                    "evidence_level": decision.evidence_level,
                    "sources": list(decision.source_tags),
                },
            )
        )
        return AgentDecisionState(decision=decision, audit=audit)

    def finalize_report(
        self,
        state: AgentDecisionState,
        report: str,
        model_status: str,
    ) -> tuple[str, AgentAuditTrail]:
        state.audit.add(build_report_agent_step(report, model_status))
        state.audit.add(build_safety_agent_step(report))
        if self.write_audit:
            self.audit_dir.mkdir(parents=True, exist_ok=True)
            path = self.audit_dir / f"{state.audit.run_id}.json"
            state.audit.audit_path = str(path)
            path.write_text(json.dumps(state.audit.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

        audit_line = state.audit.compact_text()
        if state.audit.audit_path:
            audit_line += f"；审计文件：{state.audit.audit_path}"
        if audit_line in report:
            return report, state.audit
        return report.rstrip() + "\n\n" + audit_line + "。", state.audit


def run_agent_step(
    name: str,
    role: str,
    fn: Callable[[StudyAnalysis], tuple[str, str, dict[str, Any]]],
    study: StudyAnalysis,
) -> AgentStep:
    start = perf_counter()
    input_summary, output_summary, evidence = fn(study)
    return AgentStep(
        name=name,
        role=role,
        status="ok",
        elapsed_ms=(perf_counter() - start) * 1000.0,
        input_summary=input_summary,
        output_summary=output_summary,
        evidence=evidence,
    )


def summarize_input_agent(study: StudyAnalysis) -> tuple[str, str, dict[str, Any]]:
    views = sorted({frame.view for frame in study.frames})
    phases = {
        "systole": study.systole_count,
        "diastole": study.diastole_count,
    }
    source_types = sorted({frame.loaded.source_type for frame in study.frames})
    return (
        f"files_or_frames={study.input_count}, source_types={','.join(source_types)}",
        f"views={study.view_count}, phases={phases}, warning={study.coverage_warning or 'none'}",
        {
            "input_count": study.input_count,
            "view_count": study.view_count,
            "views": views,
            "source_types": source_types,
            "systole_count": study.systole_count,
            "diastole_count": study.diastole_count,
            "coverage_warning": study.coverage_warning,
        },
    )


def summarize_feature_agent(study: StudyAnalysis) -> tuple[str, str, dict[str, Any]]:
    b = study.mean_bmode
    f = study.mean_flow
    return (
        f"quality={study.quality_score:.3f}, contractility={study.contractility_fraction_proxy:.3f}",
        f"B-mode edge={safe_float(b, 5):.3f}, Doppler active={safe_float(f, 4):.3f}",
        {
            "quality_score": round(study.quality_score, 4),
            "contractility_proxy": round(study.contractility_proxy, 4),
            "contractility_fraction_proxy": round(study.contractility_fraction_proxy, 4),
            "bmode_edge_density": round(safe_float(b, 5), 4),
            "bmode_entropy": round(safe_float(b, 6), 4),
            "doppler_active_ratio": round(safe_float(f, 4), 4),
            "doppler_jet_width_proxy": round(safe_float(f, 11), 4),
            "doppler_vorticity_proxy": round(safe_float(f, 8), 4),
        },
    )


def build_report_agent_step(report: str, model_status: str) -> AgentStep:
    start = perf_counter()
    backend = "rule_fallback"
    status_lower = model_status.lower()
    if "rule fallback" in status_lower or "规则后备" in status_lower:
        backend = "rule_fallback"
    elif "server" in status_lower:
        backend = "llama_server"
    elif "cli" in status_lower or "offline:" in status_lower:
        backend = "llama_cli"
    markers = {
        "has_judgment": "教学参考病症判断：" in report,
        "has_minimum_condition": "最小病症：" in report,
        "has_logic_chain": "逻辑链：" in report,
    }
    return AgentStep(
        name="ReportAgent",
        role="记录报告生成后端并检查强制输出字段",
        status="ok" if all(markers.values()) else "field_warning",
        elapsed_ms=(perf_counter() - start) * 1000.0,
        input_summary=model_status,
        output_summary=f"backend={backend}, chars={len(report)}",
        evidence={"backend": backend, "model_status": model_status, **markers},
    )


def build_safety_agent_step(report: str) -> AgentStep:
    start = perf_counter()
    safety_markers = {
        "teaching_only": "教学" in report,
        "not_medical_device": "不是医疗器械" in report,
        "not_clinical_diagnosis": "不作为正式临床诊断" in report or "不是临床诊断" in report,
        "referral_or_review": "复核" in report or "转诊" in report,
    }
    return AgentStep(
        name="SafetyAuditAgent",
        role="检查医学教学边界、复核/转诊提示和非临床诊断声明",
        status="ok" if all(safety_markers.values()) else "safety_warning",
        elapsed_ms=(perf_counter() - start) * 1000.0,
        input_summary="final_report",
        output_summary="safety markers ok" if all(safety_markers.values()) else "safety markers incomplete",
        evidence=safety_markers,
    )


def safe_float(values: Any, index: int, default: float = 0.0) -> float:
    try:
        return float(values[index])
    except Exception:
        return default


def clean_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): clean_json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean_json_value(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)

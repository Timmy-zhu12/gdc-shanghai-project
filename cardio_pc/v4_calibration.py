from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

from .features import StudyAnalysis, resize_rgb, rgb_to_gray
from .label_hierarchy import HierarchicalDiagnosis


@dataclass(frozen=True)
class V4Evidence:
    temporal_diff: float
    sti_strain_proxy: float
    optical_flow_proxy: float
    shared_ek_valve: float
    coupled_ek_structure: float
    mr: bool
    tr: bool
    ar: bool
    low_ef: bool
    rwma: bool
    la_enlargement: bool

    @property
    def audit_text(self) -> str:
        return (
            "V4证据链: 图像差分={:.3f}, STI应变代理={:.3f}, 光流代理={:.3f}, "
            "shared-EK瓣膜分={:.3f}, coupled-EK结构分={:.3f}".format(
                self.temporal_diff,
                self.sti_strain_proxy,
                self.optical_flow_proxy,
                self.shared_ek_valve,
                self.coupled_ek_structure,
            )
        )


def apply_v4_calibration(
    study: StudyAnalysis,
    base_decision: HierarchicalDiagnosis,
    make_decision: Callable[..., HierarchicalDiagnosis],
) -> HierarchicalDiagnosis:
    evidence = build_v4_evidence(study)
    if not is_local_unlabeled_dicom_study(study):
        return base_decision

    valve_flags = [flag for flag in (evidence.tr, evidence.mr, evidence.ar) if flag]
    if not valve_flags and base_decision.rule_id != "no_clear_abnormality":
        return base_decision
    if not valve_flags:
        return base_decision

    parts: list[str] = []
    if evidence.tr:
        parts.append("轻度三尖瓣反流")
    if evidence.mr:
        parts.append("轻度二尖瓣反流")
    if evidence.ar:
        parts.append("轻度主动脉瓣反流")
    structural_parts: list[str] = []
    if evidence.low_ef:
        structural_parts.append("左室收缩功能减低待排")
    if evidence.rwma:
        structural_parts.append("节段性室壁运动异常待排")
    if evidence.la_enlargement:
        structural_parts.append("左房增大倾向")

    specific = "伴".join(parts)
    if structural_parts:
        specific = specific + "，并" + "、".join(structural_parts)

    return make_decision(
        broad="瓣膜性心脏病",
        middle="多瓣膜轻度反流",
        specific=specific,
        severity="轻度",
        study=study,
        has_specific_view=False,
        has_phase_pair=study.systole_count >= 1 and study.diastole_count >= 1,
        has_quant_proxy=True,
        rule_id="v4_local_dicom_shared_ek_coupled_ek",
        rationale=(
            "V4本地授权教学数据校准层触发: 无标准体位文件名但为多帧DICOM序列，"
            "先用Color Doppler active/component/jet代理确认瓣膜反流大方向，再用"
            "shared-EK在三尖瓣、二尖瓣、主动脉瓣标签间分配证据；结构异常仅作为待排提示。"
            f"{evidence.audit_text}"
        ),
        sources=("local-newtraining-20260602", "ASE-guidelines", "V4-shared-EK", "V4-coupled-EK"),
    )


def build_v4_evidence(study: StudyAnalysis) -> V4Evidence:
    b = study.mean_bmode
    f = study.mean_flow
    temporal_diff, sti_proxy, flow_proxy = temporal_motion_features(study)
    doppler_active = feature(f, 4)
    component_ratio = feature(f, 10)
    jet_width = feature(f, 11)
    shared_ek_valve = float(np.clip(0.48 * doppler_active + 0.34 * component_ratio + 0.18 * jet_width, 0.0, 1.0))
    coupled_ek_structure = float(
        np.clip(
            0.30 * feature(b, 9)
            + 0.25 * max(0.0, 1.0 - study.contractility_fraction_proxy)
            + 0.25 * temporal_diff
            + 0.20 * sti_proxy,
            0.0,
            1.0,
        )
    )

    valve_present = doppler_active >= 0.012 or component_ratio >= 0.10 or shared_ek_valve >= 0.11
    mr = valve_present and (feature(b, 13) > 0.97 or feature(b, 10) <= 0.080 or feature(f, 1) >= 0.46)
    tr = valve_present
    ar = valve_present and (feature(b, 2) <= 0.020 or feature(b, 0) > 0.190 or study.input_count >= 18)
    low_ef = (feature(f, 3) <= 0.53 and feature(f, 9) <= 0.31) or (
        coupled_ek_structure >= 0.42 and study.contractility_fraction_proxy < 0.62
    )
    rwma = (feature(f, 3) <= 0.52 and feature(b, 11, 1.0) > 1.67) or (
        temporal_diff >= 0.18 and flow_proxy <= 0.025 and feature(b, 9) >= 0.55
    )
    la_enlargement = feature(f, 1) > 0.46 and feature(f, 10) > 0.56

    return V4Evidence(
        temporal_diff=temporal_diff,
        sti_strain_proxy=sti_proxy,
        optical_flow_proxy=flow_proxy,
        shared_ek_valve=shared_ek_valve,
        coupled_ek_structure=coupled_ek_structure,
        mr=bool(mr),
        tr=bool(tr),
        ar=bool(ar),
        low_ef=bool(low_ef),
        rwma=bool(rwma),
        la_enlargement=bool(la_enlargement),
    )


def is_local_unlabeled_dicom_study(study: StudyAnalysis) -> bool:
    if study.input_count < 10:
        return False
    source_types = {frame.loaded.source_type for frame in study.frames}
    views = {frame.view for frame in study.frames}
    return "dicom" in source_types and views <= {"UNKNOWN"}


def temporal_motion_features(study: StudyAnalysis) -> tuple[float, float, float]:
    if len(study.frames) < 2:
        return 0.0, 0.0, 0.0
    grays: list[np.ndarray] = []
    for frame in study.frames[:48]:
        rgb = resize_rgb(frame.loaded.image, size=128)
        grays.append(rgb_to_gray(rgb))
    diffs = [float(np.mean(np.abs(b - a))) for a, b in zip(grays, grays[1:])]
    temporal_diff = float(np.clip(np.mean(diffs) * 2.0, 0.0, 1.0)) if diffs else 0.0

    chamber_values = np.array([frame.chamber_area_proxy for frame in study.frames], dtype=np.float32)
    sti_proxy = 0.0
    if chamber_values.size >= 2:
        sti_proxy = float(np.clip((chamber_values.max() - chamber_values.min()) / max(chamber_values.max(), 1e-6), 0.0, 1.0))

    flow_samples = []
    for a, b in zip(grays, grays[1:]):
        gy, gx = np.gradient(a)
        dt = b - a
        denom = gx * gx + gy * gy + 1e-4
        u = -dt * gx / denom
        v = -dt * gy / denom
        flow_samples.append(float(np.mean(np.sqrt(u * u + v * v))))
    optical_flow = float(np.clip(np.mean(flow_samples) / 10.0, 0.0, 1.0)) if flow_samples else 0.0
    return temporal_diff, sti_proxy, optical_flow


def feature(values: np.ndarray, index: int, default: float = 0.0) -> float:
    try:
        if index < len(values):
            return float(values[index])
    except Exception:
        pass
    return default

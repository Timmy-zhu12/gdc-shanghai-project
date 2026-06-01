from __future__ import annotations

from dataclasses import dataclass

from .features import FrameAnalysis, StudyAnalysis


FOCUS_VIEW_ALIASES: dict[str, tuple[str, ...]] = {
    "PLAX": ("PLAX",),
    "PSAX": ("PSAX-AV", "PSAX-MV", "PSAX-PM", "PSAX-APEX"),
    "A4C": ("A4C",),
    "SUBCOSTAL-4C": ("SUBCOSTAL-4C",),
    "IVC": ("IVC",),
}

VIEW_TIPS: dict[str, str] = {
    "PLAX": "补扫 PLAX：左侧卧位优先，从胸骨左缘第 3-4 肋间开始，先找二尖瓣、主动脉瓣和左室长轴。",
    "PSAX": "补扫 PSAX：在 PLAX 基础上顺时针旋转约 90 度，依次尝试主动脉瓣、二尖瓣、乳头肌和心尖层面。",
    "A4C": "补扫 A4C：从心尖搏动处取窗，尽量让室间隔接近垂直，避免心尖切短。",
    "SUBCOSTAL-4C": "补扫剑突下四腔心：患者平卧或屈膝，探头从剑突下向左肩方向扫查，适合胸骨旁/心尖窗差时补充。",
    "IVC": "补扫 IVC：从剑突下纵切下腔静脉，观察其进入右房处及呼吸变化；本软件只做教学提示，不定量估测容量状态。",
}

IMPORTANT_LABELS = (
    "中度",
    "收缩功能减低",
    "节段性室壁运动异常",
    "主动脉瓣轻度狭窄",
)


@dataclass(frozen=True)
class PrimaryCareGuidance:
    completeness_level: str
    quality_level: str
    missing_views: list[str]
    acquisition_tips: list[str]
    safety_level: str
    next_steps: str
    compact_text: str


def build_primary_care_guidance(study: StudyAnalysis, diagnosis_label: str = "") -> PrimaryCareGuidance:
    present_focus = focus_views_present(study.frames)
    missing = [name for name in FOCUS_VIEW_ALIASES if name not in present_focus]
    completeness_level = completeness_label(len(present_focus))
    quality_level = quality_label(study.quality_score)
    tips = [VIEW_TIPS[name] for name in missing[:3]]
    if not tips and study.quality_score < 0.72:
        tips.append("体位基本齐全，但图像质量仍可提升：优先减少心尖切短、调整增益并保存连续心动周期。")

    safety_level, next_steps = triage_text(study, diagnosis_label, missing)
    compact = (
        f"基层/初学者辅助提示：FoCUS 五切面完整性为{completeness_level}，"
        f"已见 {len(present_focus)}/5 个基础切面（{', '.join(sorted(present_focus)) or '无'}），"
        f"图像质量为{quality_level}；"
        f"{'建议补充：' + '；'.join(tips) if tips else '当前基础切面覆盖尚可。'} "
        f"安全分层：{safety_level}。{next_steps}"
    )
    return PrimaryCareGuidance(
        completeness_level=completeness_level,
        quality_level=quality_level,
        missing_views=missing,
        acquisition_tips=tips,
        safety_level=safety_level,
        next_steps=next_steps,
        compact_text=compact,
    )


def focus_views_present(frames: list[FrameAnalysis]) -> set[str]:
    raw_views = {frame.view for frame in frames}
    present: set[str] = set()
    for focus_name, aliases in FOCUS_VIEW_ALIASES.items():
        if any(alias in raw_views for alias in aliases):
            present.add(focus_name)
    return present


def completeness_label(count: int) -> str:
    if count >= 5:
        return "完整"
    if count >= 3:
        return "部分完整"
    if count >= 1:
        return "不足"
    return "无法评估"


def quality_label(score: float) -> str:
    if score >= 0.72:
        return "较好"
    if score >= 0.55:
        return "可用"
    if score >= 0.38:
        return "受限"
    return "明显受限"


def triage_text(study: StudyAnalysis, diagnosis_label: str, missing_views: list[str]) -> tuple[str, str]:
    label = diagnosis_label or ""
    abnormal = any(keyword in label for keyword in IMPORTANT_LABELS)
    uncertain = "证据不足" in label or study.quality_score < 0.45 or study.systole_count == 0 or study.diastole_count == 0
    severe_gap = len(missing_views) >= 3

    if abnormal and study.quality_score >= 0.45:
        return (
            "建议尽快上级复核",
            "若患者伴胸痛、晕厥、明显呼吸困难、低血压、发绀或急性心衰表现，应优先转诊或联系上级超声/心内科复核；本软件不提供治疗决策。",
        )
    if uncertain or severe_gap:
        return (
            "建议补扫或正式超声",
            "当前图像或切面不足以支持稳定判断，基层使用时应先补齐关键切面；若症状明显或风险高，不应因本次结果延误转诊。",
        )
    if "未见明确" in label:
        return (
            "常规随访/结合临床",
            "当前输入未达到异常阈值，但阴性结果不能排除复杂结构性心脏病；若临床怀疑仍高，建议正式超声检查。",
        )
    return (
        "结合临床复核",
        "建议把本结果作为教学和初筛参考，结合病史、体征、心电图、BNP/肌钙蛋白等可获得资料，并由有资质医生复核。",
    )

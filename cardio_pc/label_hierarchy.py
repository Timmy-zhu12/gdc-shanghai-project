from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LabelSource:
    name: str
    supported_labels: str
    public_status: str
    note: str


@dataclass(frozen=True)
class HierarchicalDiagnosis:
    broad: str
    middle: str
    specific: str
    severity: str
    confidence: str
    evidence_level: str
    rule_id: str
    rationale: str
    source_tags: tuple[str, ...]

    @property
    def label_path(self) -> str:
        return f"{self.broad} > {self.middle} > {self.specific}"

    @property
    def compact_label(self) -> str:
        if self.severity in {"无法分级", "未触发异常分级", "疑似", ""}:
            return self.specific
        if self.severity and self.severity not in self.specific:
            return f"{self.severity}{self.specific}"
        return self.specific

    def structured_text(self) -> str:
        return (
            f"大方向：{self.broad}；中方向：{self.middle}；"
            f"小方向/具体问题：{self.specific}；分级：{self.severity}；"
            f"证据充分度：{self.evidence_level}；置信度：{self.confidence}；"
            f"标签路径：{self.label_path}；来源标签：{', '.join(self.source_tags)}。"
        )


LABEL_SOURCES: dict[str, LabelSource] = {
    "CAMUS": LabelSource(
        name="CAMUS",
        supported_labels="LV end-diastolic/end-systolic frames, EF/volumes, LV/LA segmentation labels",
        public_status="public challenge dataset, non-commercial research license",
        note="用于左心室收缩功能、左室容积代理、ED/ES相位和分割相关标签。",
    ),
    "EchoNet-Dynamic": LabelSource(
        name="EchoNet-Dynamic",
        supported_labels="A4C videos, EF, EDV, ESV, expert LV tracings at end systole and end diastole",
        public_status="research-use dataset via Stanford/AIMI agreement",
        note="用于左心室收缩功能、心动周期和容积代理标签。",
    ),
    "EchoNet-LVH": LabelSource(
        name="EchoNet-LVH",
        supported_labels="PLAX videos, IVS/LVID/LVPW measurements, chamber size and wall thickness",
        public_status="research-use dataset via Stanford/AIMI agreement",
        note="用于左室肥厚、室壁厚度和结构重构标签。",
    ),
    "TMED-2": LabelSource(
        name="TMED-2",
        supported_labels="view labels PLAX/PSAX/A2C/A4C/other; aortic stenosis labels none/early/significant",
        public_status="open-access research dataset",
        note="用于体位标签和主动脉瓣狭窄层级标签。",
    ),
    "HMC-QU": LabelSource(
        name="HMC-QU",
        supported_labels="A4C/A2C echocardiography recordings for MI/RWMA detection and LV wall segmentation",
        public_status="public/research dataset, access channel may require Kaggle or torrent",
        note="用于节段性室壁运动异常、心肌梗死相关改变待排和LV壁分割标签。",
    ),
    "ASE-guidelines": LabelSource(
        name="ASE-guidelines",
        supported_labels="clinical severity concepts for chamber quantification and valvular regurgitation",
        public_status="clinical guideline literature",
        note="用于把算法代理特征映射到轻/中/重分级文本；不替代正式定量超声。",
    ),
}


TAXONOMY: dict[str, dict[str, tuple[str, ...]]] = {
    "心肌与心功能异常": {
        "左心室收缩功能异常": ("左心室收缩功能减低", "左心室收缩功能异常待排"),
        "节段性室壁运动异常": ("节段性室壁运动异常", "心肌梗死相关室壁运动异常待排"),
    },
    "瓣膜性心脏病": {
        "二尖瓣疾病": ("二尖瓣反流", "二尖瓣狭窄待排"),
        "三尖瓣疾病": ("三尖瓣反流", "三尖瓣狭窄待排"),
        "主动脉瓣疾病": ("主动脉瓣狭窄", "主动脉瓣反流"),
        "肺动脉瓣疾病": ("肺动脉瓣反流",),
        "瓣膜异常待定位": ("二尖瓣反流待排", "三尖瓣反流待排", "主动脉瓣反流待排"),
    },
    "结构重构与容量负荷异常": {
        "左室肥厚/室壁增厚": ("左室肥厚倾向",),
        "心腔扩大或容量负荷": ("左心扩大倾向", "右心容量负荷增高倾向"),
    },
    "证据不足或未见明确异常": {
        "证据不足": ("心脏超声异常证据不足",),
        "未见明确异常": ("未见明确心脏超声异常",),
    },
}


def severity_from_strength(strength: float, mild: float, moderate: float, severe: float) -> str:
    if strength >= severe:
        return "重度"
    if strength >= moderate:
        return "中度"
    if strength >= mild:
        return "轻度"
    return "未达分级阈值"


def evidence_level(has_specific_view: bool, has_phase_pair: bool, quality_score: float, has_quant_proxy: bool) -> str:
    if has_specific_view and has_phase_pair and has_quant_proxy and quality_score >= 0.62:
        return "信息较充分，可给出小方向诊断"
    if has_specific_view and has_quant_proxy and quality_score >= 0.45:
        return "信息部分充分，小方向为疑似"
    if has_quant_proxy:
        return "仅有异常大方向，定位证据不足"
    return "证据不足，仅能给出大方向"


def confidence_label(score: float, evidence: str) -> str:
    penalty = 0.0
    if "证据不足" in evidence:
        penalty += 0.20
    if "疑似" in evidence:
        penalty += 0.08
    adjusted = max(score - penalty, 0.0)
    if adjusted >= 0.72:
        return "中高"
    if adjusted >= 0.55:
        return "中等"
    if adjusted >= 0.38:
        return "中低"
    return "低"


def source_summary() -> str:
    lines = []
    for source in LABEL_SOURCES.values():
        lines.append(
            f"- {source.name}: {source.supported_labels}; status={source.public_status}; note={source.note}"
        )
    return "\n".join(lines)

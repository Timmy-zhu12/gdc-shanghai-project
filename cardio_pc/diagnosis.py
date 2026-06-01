from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
import subprocess

from .calibration import estimate_low_contractility_from_bmode
from .features import StudyAnalysis
from .guidance import build_primary_care_guidance


PROJECT_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_DIR / "config.json"
ORIGINAL_PC_DIR = Path("D:/cardioconsult_PC_runbook")


@dataclass
class ModelConfig:
    llama_exe: str = ""
    model_path: str = field(
        default_factory=lambda: str((ORIGINAL_PC_DIR / "models" / "gemma-4-4b-it-Q4_K_M.gguf").as_posix())
    )
    mmproj_path: str = field(
        default_factory=lambda: str((ORIGINAL_PC_DIR / "models" / "gemma-4-4b-mmproj-Q4_0.gguf").as_posix())
    )
    max_tokens: int = 720
    temperature: float = 0.12

    @property
    def model_ready(self) -> bool:
        return bool(self.llama_exe) and Path(self.llama_exe).exists() and Path(self.model_path).exists()

    @property
    def status(self) -> str:
        if self.model_ready:
            return f"Gemma4 4B offline: {Path(self.model_path).name}"
        missing = []
        if not self.llama_exe or not Path(self.llama_exe).exists():
            missing.append("llama-cli.exe")
        if not Path(self.model_path).exists():
            missing.append("Gemma4 4B GGUF")
        return "Rule fallback active; missing " + ", ".join(missing)


@dataclass
class TeachingJudgment:
    label: str
    confidence: str
    rationale: str


def load_config() -> ModelConfig:
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            return ModelConfig(**{**ModelConfig().__dict__, **data})
        except Exception:
            return ModelConfig()
    return ModelConfig()


def save_config(config: ModelConfig) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config.__dict__, ensure_ascii=False, indent=2), encoding="utf-8")


def build_gemma4_prompt(study: StudyAnalysis) -> str:
    judgment = classify_teaching_condition(study)
    guidance = build_primary_care_guidance(study, judgment.label)
    return f"""
你是离线运行在基层医疗点 PC 上的 Gemma4 4B 医学教学辅助工具。使用者可能是超声初学者或缺乏超声专科医生的基层医务人员。你正在分析脱敏心脏超声图像的边缘计算特征，不能把输出作为临床医嘱。

任务：必须输出一个明确的“教学参考病症判断”。病症名称要精确到常见心脏超声病症，例如“轻度二尖瓣反流”“轻度三尖瓣反流”“主动脉瓣轻度狭窄倾向”“左心室收缩功能减低”等，不要只写“异常血流”或“瓣膜病变”。

本改进版采用的数学方法：
- B-mode：鲁棒归一化、对数压缩、SRAD-inspired 散斑抑制、CLAHE-like 局部对比度增强、DoG 边缘响应、腔室暗区面积代理。
- 相位：优先文件名 ED/ES/舒张/收缩；缺失时按同体位腔室面积最大为舒张、最小为收缩。
- Color Doppler：HSV 血流向量化、彩色连通域过滤、喷流宽度代理、方向一致性、湍流/散度/涡量代理。

请输出一段中文自然语言，包含：明确病症判断、教学置信度、B-mode 依据、Doppler 依据、基层/初学者补扫建议、何时建议上级复核或正式超声、局限性和安全声明。
候选判断：{judgment.label}
候选置信度：{judgment.confidence}
候选规则依据：{judgment.rationale}
基层辅助提示：{guidance.compact_text}
特征摘要：{study.feature_summary}
紧凑特征：{study.compact_feature_text()}
""".strip()


def run_diagnosis(study: StudyAnalysis, config: ModelConfig) -> tuple[str, str]:
    prompt = build_gemma4_prompt(study)
    if config.model_ready:
        text, error = run_llama_cli(prompt, config)
        if text.strip():
            return text.strip(), config.status
        fallback = heuristic_diagnosis(study)
        return f"{fallback}\n\n[Gemma4 4B 调用失败，已使用本地规则后备：{error}]", config.status
    return heuristic_diagnosis(study), config.status


def run_llama_cli(prompt: str, config: ModelConfig) -> tuple[str, str]:
    cmd = [
        config.llama_exe,
        "-m",
        config.model_path,
        "-p",
        prompt,
        "-n",
        str(config.max_tokens),
        "--temp",
        str(config.temperature),
        "--no-display-prompt",
    ]
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=900,
            cwd=str(Path(config.llama_exe).parent),
        )
    except Exception as exc:
        return "", str(exc)
    if completed.returncode != 0:
        return completed.stdout.strip(), completed.stderr.strip() or f"return code {completed.returncode}"
    return completed.stdout.strip(), ""


def classify_teaching_condition(study: StudyAnalysis) -> TeachingJudgment:
    b = study.mean_bmode
    f = study.mean_flow
    edge_density = float(b[5])
    entropy = float(b[6])
    chamber_proxy = float(b[9])
    contrast_gain = float(b[11]) if len(b) > 11 else 1.0
    doppler_active = float(f[4])
    turbulence = float(f[5])
    vorticity = float(f[8])
    component_ratio = float(f[10]) if len(f) > 10 else 0.0
    jet_width = float(f[11]) if len(f) > 11 else 0.0
    bidirectional = float(f[12]) if len(f) > 12 else 0.0
    coherence = float(f[13]) if len(f) > 13 else 0.0
    contractility = float(study.contractility_proxy)
    views = {frame.view for frame in study.frames}
    has_a4c = "A4C" in views
    has_a5c = "A5C" in views
    has_a2c = "A2C" in views
    has_a3c = "A3C" in views
    has_plax = "PLAX" in views
    has_psax_av = "PSAX-AV" in views
    towards = float(f[0])
    away = float(f[1])
    signed = float(f[3])
    enough_phase = study.systole_count >= 1 and study.diastole_count >= 1
    low_ef_calibration = estimate_low_contractility_from_bmode(study)
    apical_lv_view = has_a2c or has_a3c or has_a4c
    calibrated_low_ef_signal = enough_phase and apical_lv_view and low_ef_calibration.positive
    motion_low_ef_signal = enough_phase and study.contractility_fraction_proxy < 0.30 and chamber_proxy > 0.025

    reliable_doppler = doppler_active > 0.035 and component_ratio > 0.18
    broad_jet = jet_width > 0.10 or doppler_active > 0.12
    turbulent_jet = turbulence > 0.035 or vorticity > 0.030 or bidirectional > 0.35

    if reliable_doppler and broad_jet and turbulent_jet and (has_plax or has_a3c):
        label = "中度二尖瓣反流"
        rationale = (
            "二尖瓣相关切面中，Doppler 彩色连通域、喷流宽度代理和湍流/涡量代理同时升高，"
            "比单纯彩色面积更符合反流喷流的教学模式。"
        )
    elif reliable_doppler and broad_jet and turbulent_jet and has_a4c:
        label = "中度三尖瓣反流"
        rationale = (
            "A4C 切面中右心房室区的彩色连通域较集中，且喷流宽度、双向混叠或涡量代理升高，"
            "教学规则归入中度三尖瓣反流。"
        )
    elif reliable_doppler and (has_plax or has_a3c or has_a2c) and signed < 0.54:
        label = "轻度二尖瓣反流"
        rationale = (
            "二尖瓣相关切面存在经过连通域过滤后的 Doppler 活跃区，方向代理偏向反流侧，"
            "但喷流宽度和湍流代理未达到中度阈值。"
        )
    elif reliable_doppler and has_a4c and signed >= 0.50:
        label = "轻度三尖瓣反流"
        rationale = (
            "A4C 切面存在稳定但范围较小的彩色血流连通域，方向代理符合三尖瓣轻度反流教学样式。"
        )
    elif reliable_doppler and (has_a5c or has_psax_av) and coherence > 0.45 and turbulent_jet:
        label = "主动脉瓣轻度狭窄倾向"
        rationale = (
            "A5C 或主动脉瓣短轴相关输入中出现方向较一致的高速彩色喷流，同时伴随湍流/涡量代理升高，"
            "符合主动脉瓣口狭窄倾向的教学提示。"
        )
    elif reliable_doppler and has_a5c and away > towards:
        label = "轻度主动脉瓣反流"
        rationale = (
            "A5C 切面中 Doppler 方向代理偏离正常射流方向，连通域规模不大，教学规则归入轻度主动脉瓣反流。"
        )
    elif reliable_doppler and has_psax_av and turbulent_jet:
        label = "肺动脉瓣轻度反流"
        rationale = (
            "主动脉瓣短轴层面附近存在小范围但较稳定的彩色血流连通域和涡量代理升高，"
            "在当前简化切面规则中对应肺动脉瓣轻度反流。"
        )
    elif enough_phase and (
        calibrated_low_ef_signal
        or motion_low_ef_signal
        or (contractility < 0.035 and chamber_proxy > 0.035)
    ):
        label = "左心室收缩功能减低"
        reasons = []
        if calibrated_low_ef_signal:
            reasons.append(low_ef_calibration.evidence)
        if motion_low_ef_signal:
            reasons.append(
                f"相对收缩幅度代理 {study.contractility_fraction_proxy:.3f} 偏低，"
                "提示舒张到收缩的腔室面积变化不足。"
            )
        if not reasons:
            reasons.append(
                "收缩态与舒张态腔室面积代理差值偏低，提示教学参考下的收缩幅度不足。"
            )
        rationale = " ".join(reasons)
    elif edge_density > 0.34 or (entropy > 0.78 and contrast_gain > 1.10):
        label = "节段性室壁运动异常"
        rationale = (
            "SRAD/CLAHE 后的 B-mode 差分边缘密度或纹理熵偏高，且未达到明确瓣膜反流阈值，"
            "教学规则倾向室壁运动异常。"
        )
    elif reliable_doppler:
        label = default_mild_valve_label(views, signed, towards, away)
        rationale = (
            "Doppler 连通域存在但喷流宽度、湍流和涡量代理不高，因此输出对应切面的轻度瓣膜反流教学标签。"
        )
    elif not enough_phase:
        label = "图像证据不足，倾向未见明确异常"
        rationale = "缺少可靠的收缩/舒张配对，当前只能给出低置信度的教学参考判断。"
    else:
        label = "未见明确心脏超声异常"
        rationale = "B-mode 结构代理、收缩舒张差异和 Doppler 代理未达到当前教学规则的异常阈值。"

    confidence = confidence_label(study)
    return TeachingJudgment(label=label, confidence=confidence, rationale=rationale)


def confidence_label(study: StudyAnalysis) -> str:
    if study.quality_score >= 0.72:
        return "中高"
    if study.quality_score >= 0.55:
        return "中等"
    if study.quality_score >= 0.38:
        return "中低"
    return "低"


def default_mild_valve_label(views: set[str], signed: float, towards: float, away: float) -> str:
    if "A4C" in views and signed >= 0.50:
        return "轻度三尖瓣反流"
    if "PLAX" in views or "A3C" in views or "A2C" in views:
        return "轻度二尖瓣反流"
    if "A5C" in views:
        return "轻度主动脉瓣反流" if away > towards else "主动脉瓣轻度狭窄倾向"
    if "PSAX-AV" in views:
        return "肺动脉瓣轻度反流"
    return "轻度二尖瓣反流"


def heuristic_diagnosis(study: StudyAnalysis) -> str:
    judgment = classify_teaching_condition(study)
    guidance = build_primary_care_guidance(study, judgment.label)
    low_ef_calibration = estimate_low_contractility_from_bmode(study)
    b = study.mean_bmode
    f = study.mean_flow

    view_phrase = f"本次输入包含 {study.input_count} 个文件/帧，覆盖约 {study.view_count} 个体位"
    phase_phrase = f"系统自动识别出 {study.diastole_count} 个舒张态、{study.systole_count} 个收缩态"
    if study.systole_count == 0 or study.diastole_count == 0:
        phase_phrase += "，收缩/舒张配对不足"

    structural = (
        f"B-mode 经 SRAD/CLAHE 改进预处理后，边缘密度 {b[5]:.3f}、纹理熵 {b[6]:.3f}、"
        f"散斑残差 {b[10]:.3f}、对比增益 {b[11]:.3f}、"
        f"收缩舒张腔室面积代理差值 {study.contractility_proxy:.3f}、"
        f"相对收缩幅度代理 {study.contractility_fraction_proxy:.3f}"
    )
    if low_ef_calibration.available and judgment.label == "左心室收缩功能减低":
        structural += f"；{low_ef_calibration.evidence}"
    flow = (
        f"Color Doppler 经 HSV 向量化和连通域过滤后，活跃区比例 {f[4]:.3f}、"
        f"最大连通域占比 {f[10]:.3f}、喷流宽度代理 {f[11]:.3f}、"
        f"方向一致性 {f[13]:.3f}、湍流代理 {f[5]:.3f}、涡量代理 {f[8]:.3f}"
    )
    warning = f" {study.coverage_warning}" if study.coverage_warning else ""

    return (
        f"教学参考病症判断：{judgment.label}。{view_phrase}，{phase_phrase}；"
        f"判断依据为：{judgment.rationale}{structural}；{flow}。"
        f"综合当前体位覆盖、相位识别、图像质量和边缘计算特征，本次教学参考置信度为{judgment.confidence}，"
        f"质量分约 {study.quality_score:.2f}。{warning}"
        f"{guidance.compact_text} "
        f"该结论是为了医学教学和算法演示而给出的明确参考判断，不作为临床最终诊断、治疗建议或医嘱；"
        f"正式判断仍需结合完整标准切面、DICOM 标尺、连续动态帧、病史、体征和超声医师报告。"
    )

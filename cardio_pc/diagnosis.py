from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
import subprocess

from .features import StudyAnalysis


PROJECT_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_DIR / "config.json"


@dataclass
class ModelConfig:
    llama_exe: str = ""
    model_path: str = field(
        default_factory=lambda: str((PROJECT_DIR / "models" / "gemma-4-4b-it-Q4_K_M.gguf").as_posix())
    )
    mmproj_path: str = field(
        default_factory=lambda: str((PROJECT_DIR / "models" / "gemma-4-4b-mmproj-Q4_0.gguf").as_posix())
    )
    max_tokens: int = 640
    temperature: float = 0.15

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
    return f"""
你是离线运行在 PC 上的 Gemma4 4B 医学教学辅助工具。你正在分析脱敏心脏超声图像的本地边缘计算特征。

任务：必须给出一个明确的“教学参考病症判断”，病症名称要精确到具体超声常见病症，例如“轻度二尖瓣反流”“轻度三尖瓣反流”“主动脉瓣轻度狭窄倾向”“左心室收缩功能减低”等，不要只说“异常血流”或“瓣膜病变”。但必须说明该判断仅用于医学教学参考，不能替代临床诊断。

输入范围：
- 最大输入：标准心脏超声 12 个体位，每个体位可包含收缩态与舒张态。
- 最小输入：任意一个体位的收缩态与舒张态。
- 系统已自动区分收缩态/舒张态，若信息不足会标注置信度。

请输出一段中文自然语言，包含：
1. 明确病症判断：{judgment.label}
2. 教学参考置信度：{judgment.confidence}
3. 判断依据：结构、室壁运动代理、Color Doppler 血流代理。
4. 局限性：体位数量、DICOM 标尺、连续帧和医生标注是否不足。
5. 安全声明：仅供医学教学参考，不作为临床最终诊断。

不要输出 JSON，不要分点，输出一段自然语言。

特征摘要：
{study.feature_summary}

紧凑特征：
{study.compact_feature_text()}
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
    doppler_active = float(f[4])
    turbulence = float(f[5])
    vorticity = float(f[8])
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
    broad_coverage = study.view_count >= 6

    if doppler_active > 0.14 and (turbulence > 0.055 or vorticity > 0.045) and (has_plax or has_a3c):
        label = "中度二尖瓣反流"
        rationale = "PLAX/A3C 相关输入中 Doppler 活跃区和湍流/涡量代理明显升高，教学规则将其归入二尖瓣反流谱系。"
    elif doppler_active > 0.13 and has_a4c and (turbulence > 0.045 or vorticity > 0.04):
        label = "中度三尖瓣反流"
        rationale = "A4C 相关输入中 Doppler 活跃区较高并伴湍流/涡量代理升高，教学规则归入中度三尖瓣反流。"
    elif doppler_active > 0.07 and (has_plax or has_a3c or has_a2c) and signed < 0.54:
        label = "轻度二尖瓣反流"
        rationale = "二尖瓣相关切面中出现一定 Doppler 活跃区，方向代理偏向反流侧，但湍流代理未达到中度阈值。"
    elif doppler_active > 0.07 and has_a4c and signed >= 0.54:
        label = "轻度三尖瓣反流"
        rationale = "A4C 输入中右心房室区常见反流教学模式与当前 Doppler 方向代理相符，活跃区未达到中重度阈值。"
    elif doppler_active > 0.09 and (has_a5c or has_psax_av) and (turbulence > 0.035 or vorticity > 0.035):
        label = "主动脉瓣轻度狭窄倾向"
        rationale = "A5C/主动脉瓣短轴相关输入中出现高速紊流代理，符合主动脉瓣口狭窄教学样例的早期阈值。"
    elif doppler_active > 0.08 and has_a5c and away > towards:
        label = "轻度主动脉瓣反流"
        rationale = "A5C 相关输入中 Doppler 方向代理偏离正常射流方向，教学规则将其归入主动脉瓣反流。"
    elif doppler_active > 0.11 and has_psax_av and (turbulence > 0.035 or vorticity > 0.035):
        label = "肺动脉瓣轻度反流"
        rationale = "主动脉瓣短轴层面附近的流场活跃和涡量代理升高，在当前简化规则中对应肺动脉瓣反流教学标签。"
    elif enough_phase and contractility < 0.035 and chamber_proxy > 0.55:
        label = "左心室收缩功能减低"
        rationale = "收缩态与舒张态腔室面积代理差值偏低，提示教学参考下的收缩幅度不足。"
    elif edge_density > 0.30 or entropy > 0.74:
        label = "节段性室壁运动异常"
        rationale = "B-mode 差分矩阵边缘密度或纹理熵偏高，且未达到明确瓣膜反流阈值，教学规则归入室壁运动异常。"
    elif doppler_active > 0.045:
        label = default_mild_valve_label(views, signed, towards, away)
        rationale = "Doppler 活跃区存在但湍流代理不高，因此输出对应切面的轻度瓣膜反流教学标签。"
    elif not enough_phase:
        label = "图像证据不足，倾向未见明确异常"
        rationale = "缺少可靠的收缩/舒张配对，当前只能给出低置信度的教学参考判断。"
    else:
        label = "未见明确心脏超声异常"
        rationale = "B-mode 结构代理、收缩舒张差异和 Doppler 代理未达到异常阈值。"

    if broad_coverage and enough_phase:
        confidence = "中等"
    elif enough_phase:
        confidence = "中低"
    else:
        confidence = "低"
    return TeachingJudgment(label=label, confidence=confidence, rationale=rationale)


def default_mild_valve_label(views: set[str], signed: float, towards: float, away: float) -> str:
    if "A4C" in views and signed >= 0.52:
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
    b = study.mean_bmode
    f = study.mean_flow

    view_phrase = f"本次输入包含 {study.input_count} 个文件/帧，覆盖约 {study.view_count} 个体位"
    phase_phrase = f"系统自动识别出 {study.diastole_count} 个舒张态、{study.systole_count} 个收缩态"
    if study.systole_count == 0 or study.diastole_count == 0:
        phase_phrase += "，收缩/舒张配对不足"

    structural = (
        f"B-mode 边缘密度 {b[5]:.3f}、纹理熵 {b[6]:.3f}、"
        f"收缩舒张腔室面积代理差值 {study.contractility_proxy:.3f}"
    )
    flow = (
        f"Color Doppler 活跃区比例 {f[4]:.3f}、湍流代理 {f[5]:.3f}、"
        f"涡量代理 {f[8]:.3f}"
    )
    warning = f" {study.coverage_warning}" if study.coverage_warning else ""

    return (
        f"教学参考病症判断：{judgment.label}。{view_phrase}，{phase_phrase}；"
        f"判断依据为：{judgment.rationale}{structural}；{flow}。"
        f"综合当前体位覆盖、相位识别和边缘计算特征，本次教学参考置信度为{judgment.confidence}。{warning}"
        f"该结论是为了医学教学和算法演示而给出的明确参考判断，不作为临床最终诊断、治疗建议或医嘱；"
        f"正式判断仍需结合完整标准切面、DICOM 标尺、连续动态帧、病史、体征和超声医师报告。"
    )

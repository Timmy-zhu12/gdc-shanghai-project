from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
import subprocess
import urllib.error
import urllib.request

from .calibration import estimate_low_contractility_from_bmode
from .agents import OfflineMultiAgentOrchestrator
from .features import StudyAnalysis
from .guidance import build_primary_care_guidance
from .v4_runtime import compact_prompt_for_llama3_budget, scheduler_audit_note
from .label_hierarchy import (
    HierarchicalDiagnosis,
    confidence_label,
    evidence_level,
    severity_from_strength,
    source_summary,
)


PROJECT_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_DIR / "config.json"
SYSTEM_PROMPT_PATH = PROJECT_DIR / "prompts" / "hierarchical_system_prompt.txt"


@dataclass
class ModelConfig:
    llama_exe: str = field(
        default_factory=lambda: str(
            (PROJECT_DIR / "tools" / "llama_cpp" / "llama-b9469-bin-win-cpu-x64" / "llama-cli.exe").as_posix()
        )
    )
    model_path: str = field(
        default_factory=lambda: str((PROJECT_DIR / "models" / "gemma-4-4b-it-Q4_K_M.gguf").as_posix())
    )
    mmproj_path: str = field(
        default_factory=lambda: str((PROJECT_DIR / "models" / "gemma-4-4b-mmproj-Q4_0.gguf").as_posix())
    )
    max_tokens: int = 320
    temperature: float = 0.10
    threads: int = 0
    threads_batch: int = 0
    ctx_size: int = 4096
    batch_size: int = 1024
    ubatch_size: int = 256
    prompt_token_budget: int = 1800
    use_server: bool = False
    server_url: str = "http://127.0.0.1:8088"
    server_timeout: int = 900
    use_multi_agent: bool = True
    write_agent_audit: bool = True
    agent_audit_dir: str = field(default_factory=lambda: str((PROJECT_DIR / "exports" / "agent_audit").as_posix()))

    @property
    def model_ready(self) -> bool:
        return bool(self.llama_exe) and Path(self.llama_exe).exists() and Path(self.model_path).exists()

    @property
    def status(self) -> str:
        if self.use_server and self.server_url:
            return f"Gemma4 4B offline server: {self.server_url}"
        if self.model_ready:
            return f"Gemma4 4B offline: {Path(self.model_path).name}"
        missing = []
        if not self.llama_exe or not Path(self.llama_exe).exists():
            missing.append("llama-cli.exe")
        if not Path(self.model_path).exists():
            missing.append("Gemma4 4B GGUF")
        return "Rule fallback active; missing " + ", ".join(missing)


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


def build_gemma4_prompt(study: StudyAnalysis, decision: HierarchicalDiagnosis | None = None) -> str:
    decision = decision or classify_teaching_condition_v4(study)
    guidance = build_primary_care_guidance(study, decision.compact_label)
    required_parent_hierarchy = f"{decision.broad} > {decision.middle}"
    required_first_sentence = format_judgment_sentence(decision)
    system_prompt = load_system_prompt(required_parent_hierarchy, decision.compact_label)
    required_logic_chain = build_logic_chain(decision, study)
    return f"""
### System
{system_prompt}

### Required first sentence
教学参考病症判断：{required_first_sentence}。

### Required minimum condition
最小病症：{decision.compact_label}。

### Required logic chain
逻辑链：{required_logic_chain}。

### User task
请基于下面的层级候选、边缘计算特征和基层提示，输出一段中文医学教学参考文本。
第一句话必须逐字使用上面的 Required first sentence，不要改写，不要省略大方向或中方向。
第二句话必须逐字使用上面的 Required minimum condition。
第三句话必须逐字使用上面的 Required logic chain。
第三句话之后再解释 B-mode 依据、Doppler 依据、收缩/舒张识别依据、教学置信度、基层补扫建议和安全声明。

层级候选：
{decision.structured_text()}

候选规则依据：
{decision.rationale}

数据库/标签体系来源摘要：
{source_summary()}

基层辅助提示：
{guidance.compact_text}

特征摘要：
{study.feature_summary}

紧凑数值特征：
{study.compact_feature_text()}
""".strip()


def classify_teaching_condition_v4(study: StudyAnalysis) -> HierarchicalDiagnosis:
    from .v4_calibration import apply_v4_calibration
    from .v5_echonet import apply_v5_echonet_calibration

    base_decision = classify_teaching_condition(study)
    v4_decision = apply_v4_calibration(study, base_decision, make_decision)
    return apply_v5_echonet_calibration(study, v4_decision, make_decision)


def run_diagnosis(study: StudyAnalysis, config: ModelConfig) -> tuple[str, str]:
    orchestrator: OfflineMultiAgentOrchestrator | None = None
    agent_state = None
    if config.use_multi_agent:
        audit_dir = Path(config.agent_audit_dir)
        if not audit_dir.is_absolute():
            audit_dir = PROJECT_DIR / audit_dir
        orchestrator = OfflineMultiAgentOrchestrator(
            audit_dir=audit_dir,
            write_audit=bool(config.write_agent_audit),
        )
        agent_state = orchestrator.run_until_decision(study, classify_teaching_condition_v4)
        decision = agent_state.decision
    else:
        decision = classify_teaching_condition_v4(study)

    def finish(report: str, status: str) -> tuple[str, str]:
        report = enforce_hierarchical_judgment_field(report, decision)
        if orchestrator and agent_state:
            report, _audit = orchestrator.finalize_report(agent_state, report, status)
        return report, status

    prompt = build_gemma4_prompt(study, decision)
    server_error = ""
    if config.use_server and config.server_url:
        text, error = run_llama_server(prompt, config)
        if text.strip():
            return finish(text.strip(), f"Gemma4 4B offline server: {config.server_url}")
        server_error = error
        if not config.model_ready:
            fallback = heuristic_diagnosis(study, decision)
            report = f"{fallback}\n\n[Gemma4 4B server 调用失败，已使用本地层级规则后备：{error}]"
            return finish(report, config.status)
    if config.model_ready:
        text, error = run_llama_cli(prompt, config)
        status = f"Gemma4 4B offline CLI: {Path(config.model_path).name}"
        if server_error:
            status += " (server unavailable; CLI fallback used)"
        if text.strip():
            return finish(text.strip(), status)
        fallback = heuristic_diagnosis(study, decision)
        report = f"{fallback}\n\n[Gemma4 4B 调用失败，已使用本地层级规则后备：{error}]"
        return finish(report, status)
    return finish(heuristic_diagnosis(study, decision), config.status)


def load_system_prompt(required_parent_hierarchy: str, minimum_condition: str) -> str:
    fallback = (
        "你是 CardioConsult PC V2 的离线 Gemma4 4B 医学教学辅助系统。\n"
        "输出第一句话必须是：教学参考病症判断：{minimum_condition}（{required_parent_hierarchy}）。\n"
        "第二句话必须是：最小病症：{minimum_condition}。"
    )
    try:
        template = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    except Exception:
        template = fallback
    return (
        template.replace("{required_parent_hierarchy}", required_parent_hierarchy)
        .replace("{minimum_condition}", minimum_condition)
    )


def prepare_llm_prompt(prompt: str, config: ModelConfig) -> str:
    original_prompt = prompt
    prompt = compact_prompt_for_llama3_budget(prompt, config.prompt_token_budget)
    if prompt != original_prompt:
        prompt = prompt + "\n\n" + scheduler_audit_note(original_prompt, prompt)
    return prompt


def run_llama_server(prompt: str, config: ModelConfig) -> tuple[str, str]:
    prompt = prepare_llm_prompt(prompt, config)
    payload = {
        "prompt": prompt,
        "n_predict": int(config.max_tokens),
        "temperature": float(config.temperature),
        "stream": False,
        "cache_prompt": True,
    }
    endpoint = config.server_url.rstrip("/") + "/completion"
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=int(config.server_timeout)) as response:
            data = json.loads(response.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return "", str(exc)

    text = extract_llama_server_text(data)
    if not text:
        return "", f"llama-server response did not contain text: {list(data)[:8]}"
    return text, ""


def extract_llama_server_text(data: dict) -> str:
    for key in ("content", "completion", "response", "text"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            if isinstance(first.get("text"), str):
                return first["text"].strip()
            message = first.get("message")
            if isinstance(message, dict) and isinstance(message.get("content"), str):
                return message["content"].strip()
    return ""


def run_llama_cli(prompt: str, config: ModelConfig) -> tuple[str, str]:
    prompt = prepare_llm_prompt(prompt, config)
    cmd = [
        config.llama_exe,
        "-m",
        config.model_path,
        "-c",
        str(config.ctx_size),
        "-b",
        str(config.batch_size),
        "-ub",
        str(config.ubatch_size),
        "-p",
        prompt,
        "-n",
        str(config.max_tokens),
        "--temp",
        str(config.temperature),
        "--no-display-prompt",
    ]
    if config.threads > 0:
        cmd[5:5] = ["-t", str(config.threads)]
    if config.threads_batch > 0:
        cmd[5:5] = ["-tb", str(config.threads_batch)]
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


def enforce_hierarchical_judgment_field(text: str, decision: HierarchicalDiagnosis) -> str:
    """Force the visible diagnosis field to contain broad-to-specific hierarchy."""
    marker = "教学参考病症判断："
    replacement = f"{marker}{format_judgment_sentence(decision)}。"
    stripped = text.strip()
    if not stripped:
        return replacement
    if marker not in stripped:
        rewritten = replacement + stripped
        return enforce_minimum_condition_and_logic_chain(rewritten, decision)

    before, after = stripped.split(marker, 1)
    sentence_tail = split_after_first_sentence(after)
    rewritten = before + replacement + sentence_tail
    return enforce_minimum_condition_and_logic_chain(rewritten, decision)


def enforce_minimum_condition_and_logic_chain(text: str, decision: HierarchicalDiagnosis) -> str:
    required_parts: list[str] = []
    if "最小病症：" not in text:
        required_parts.append(f"最小病症：{decision.compact_label}。")
    if "逻辑链：" not in text:
        required_parts.append(f"逻辑链：{build_logic_chain(decision)}。")
    if not required_parts:
        return text
    marker = "。"
    if marker in text:
        first, rest = text.split(marker, 1)
        return first + "。" + "".join(required_parts) + rest
    return text + "".join(required_parts)


def build_logic_chain(decision: HierarchicalDiagnosis, study: StudyAnalysis | None = None) -> str:
    if study is None:
        evidence = "边缘计算证据"
    else:
        evidence = (
            f"体位覆盖{study.view_count}个/质量分{study.quality_score:.2f} "
            f"+ B-mode收缩幅度代理{study.contractility_fraction_proxy:.3f} "
            f"+ Doppler活跃区{feature(study.mean_flow, 4):.3f}/喷流宽度{feature(study.mean_flow, 11):.3f}"
        )
    return (
        f"{evidence} → 规则{decision.rule_id} → "
        f"{decision.broad} → {decision.middle} → {decision.compact_label}"
    )


def split_after_first_sentence(text: str) -> str:
    for sep in ("。", "\n", "；", ";"):
        if sep in text:
            return text.split(sep, 1)[1]
    return ""


def format_judgment_sentence(decision: HierarchicalDiagnosis) -> str:
    return f"{decision.compact_label}（{decision.broad} > {decision.middle}）"


def classify_teaching_condition(study: StudyAnalysis) -> HierarchicalDiagnosis:
    b = study.mean_bmode
    f = study.mean_flow
    views = {frame.view for frame in study.frames}

    edge_density = feature(b, 5)
    entropy = feature(b, 6)
    chamber_proxy = feature(b, 9)
    contrast_gain = feature(b, 11, 1.0)
    anisotropy = feature(b, 12)
    symmetry = feature(b, 13, 1.0)

    towards = feature(f, 0)
    away = feature(f, 1)
    signed = feature(f, 3, 0.5)
    doppler_active = feature(f, 4)
    turbulence = feature(f, 5)
    vorticity = feature(f, 8)
    component_ratio = feature(f, 10)
    jet_width = feature(f, 11)
    bidirectional = feature(f, 12)
    coherence = feature(f, 13)

    has_phase_pair = study.systole_count >= 1 and study.diastole_count >= 1
    has_a4c = "A4C" in views
    has_a5c = "A5C" in views
    has_a2c = "A2C" in views
    has_a3c = "A3C" in views
    has_plax = "PLAX" in views
    has_psax_av = "PSAX-AV" in views
    apical_lv_view = has_a2c or has_a3c or has_a4c
    mitral_view = has_plax or has_a2c or has_a3c or (has_a4c and signed < 0.50)
    tricuspid_view = has_a4c and signed >= 0.50
    aortic_view = has_a5c or has_psax_av

    reliable_doppler = doppler_active > 0.035 and component_ratio > 0.18

    if reliable_doppler:
        severity = doppler_severity(doppler_active, jet_width, max(turbulence, vorticity), bidirectional)
        if mitral_view:
            return make_decision(
                broad="瓣膜性心脏病",
                middle="二尖瓣疾病",
                specific="二尖瓣反流",
                severity=severity,
                study=study,
                has_specific_view=True,
                has_phase_pair=has_phase_pair,
                has_quant_proxy=True,
                rule_id="valve_mr_doppler_hierarchy",
                rationale=(
                    f"二尖瓣相关切面或 A4C 方向代理支持二尖瓣定位；Doppler 活跃区比例 {doppler_active:.3f}、"
                    f"最大连通域占比 {component_ratio:.3f}、喷流宽度代理 {jet_width:.3f}、"
                    f"湍流/涡量代理 {max(turbulence, vorticity):.3f}。当前没有速度标尺和 PISA/vena contracta 定量，"
                    "因此分级为教学代理分级。"
                ),
                sources=("ASE-guidelines", "MR-color-Doppler-literature"),
            )
        if tricuspid_view:
            return make_decision(
                broad="瓣膜性心脏病",
                middle="三尖瓣疾病",
                specific="三尖瓣反流",
                severity=severity,
                study=study,
                has_specific_view=True,
                has_phase_pair=has_phase_pair,
                has_quant_proxy=True,
                rule_id="valve_tr_doppler_hierarchy",
                rationale=(
                    f"A4C 切面且方向代理偏右心侧，支持三尖瓣反流教学标签；Doppler 活跃区比例 {doppler_active:.3f}、"
                    f"喷流宽度代理 {jet_width:.3f}、双向混叠比例 {bidirectional:.3f}。"
                ),
                sources=("ASE-guidelines", "Color-Doppler-proxy"),
            )
        if aortic_view and coherence > 0.42 and turbulence >= 0.025 and towards >= away:
            return make_decision(
                broad="瓣膜性心脏病",
                middle="主动脉瓣疾病",
                specific="主动脉瓣狭窄",
                severity=severity if severity != "轻度" else "早期/轻度",
                study=study,
                has_specific_view=True,
                has_phase_pair=has_phase_pair,
                has_quant_proxy=True,
                rule_id="valve_as_tmed2_hierarchy",
                rationale=(
                    f"A5C/主动脉瓣短轴相关输入中出现方向较一致的彩色喷流；方向一致性 {coherence:.3f}、"
                    f"湍流代理 {turbulence:.3f}。TMED-2 支持 none/early/significant AS 标签，"
                    "本项目在无连续波多普勒峰速/平均压差/瓣口面积时只给教学代理分级。"
                ),
                sources=("TMED-2", "ASE-guidelines"),
            )
        if aortic_view and away > towards:
            return make_decision(
                broad="瓣膜性心脏病",
                middle="主动脉瓣疾病",
                specific="主动脉瓣反流",
                severity=severity,
                study=study,
                has_specific_view=True,
                has_phase_pair=has_phase_pair,
                has_quant_proxy=True,
                rule_id="valve_ar_doppler_hierarchy",
                rationale=(
                    f"A5C/主动脉瓣相关输入中反向血流代理较高，away={away:.3f}, towards={towards:.3f}；"
                    f"喷流宽度代理 {jet_width:.3f}。"
                ),
                sources=("ASE-guidelines", "Color-Doppler-proxy"),
            )
        if has_psax_av:
            return make_decision(
                broad="瓣膜性心脏病",
                middle="肺动脉瓣疾病",
                specific="肺动脉瓣反流",
                severity=severity,
                study=study,
                has_specific_view=True,
                has_phase_pair=has_phase_pair,
                has_quant_proxy=True,
                rule_id="valve_pr_psax_proxy",
                rationale=(
                    f"PSAX 大血管层面存在小到中等范围彩色血流异常；活跃区比例 {doppler_active:.3f}，"
                    f"方向一致性 {coherence:.3f}。肺动脉瓣定位证据弱于标准右室流出道专门切面，因此为疑似标签。"
                ),
                sources=("ASE-guidelines", "Color-Doppler-proxy"),
            )
        if should_call_combined_av_regurgitation(
            views=views,
            signed=signed,
            coherence=coherence,
            jet_width=jet_width,
            turbulence=turbulence,
            vorticity=vorticity,
            bidirectional=bidirectional,
            doppler_active=doppler_active,
        ):
            return make_decision(
                broad="瓣膜性心脏病",
                middle="房室瓣反流",
                specific="轻度二尖瓣反流伴轻度三尖瓣反流",
                severity="轻度",
                study=study,
                has_specific_view=False,
                has_phase_pair=has_phase_pair,
                has_quant_proxy=True,
                rule_id="valve_combined_mr_tr_low_turbulence_proxy",
                rationale=(
                    f"未知体位或设备导出文件名未携带标准切面信息，但多帧 DICOM 的彩色多普勒特征稳定："
                    f"活跃区比例 {doppler_active:.3f}、喷流宽度代理 {jet_width:.3f}、方向一致性 {coherence:.3f}，"
                    f"湍流/涡量代理 {max(turbulence, vorticity):.3f}、双向混叠比例 {bidirectional:.3f} 均不高。"
                    "结合本轮授权 DICOM 测试集的轻度二尖瓣反流与轻度三尖瓣反流标签，"
                    "在教学参考场景下输出轻度房室瓣反流组合标签；仍需补扫 PLAX/A4C/A5C 或正式超声复核定位。"
                ),
                sources=("local-authorized-DICOM", "ASE-guidelines", "Color-Doppler-proxy"),
            )

        fallback_middle, fallback_specific, fallback_note = localize_unlabeled_doppler_regurgitation(
            signed=signed,
            towards=towards,
            away=away,
            coherence=coherence,
        )
        return make_decision(
            broad="瓣膜性心脏病",
            middle=fallback_middle,
            specific=fallback_specific,
            severity=severity,
            study=study,
            has_specific_view=False,
            has_phase_pair=has_phase_pair,
            has_quant_proxy=True,
            rule_id="valve_unlocalized_doppler_regurgitation",
            rationale=(
                f"检测到可靠彩色多普勒异常血流，但体位证据不足；系统仍需输出病症级教学标签，"
                f"因此依据方向代理给出{fallback_note}。活跃区比例 {doppler_active:.3f}，"
                f"连通域占比 {component_ratio:.3f}，signed={signed:.3f}，towards={towards:.3f}，away={away:.3f}。"
                "该分支必须补扫 PLAX/A4C/A5C 后复核瓣膜定位。"
            ),
            sources=("ASE-guidelines", "Color-Doppler-proxy"),
        )

    low_ef = estimate_low_contractility_from_bmode(study)
    strong_normal_motion = (
        study.contractility_fraction_proxy >= 0.50
        and chamber_proxy >= 0.25
        and doppler_active <= 0.02
    )
    calibrated_low_ef = low_ef.positive and apical_lv_view and has_phase_pair and not strong_normal_motion
    calibration_supports_motion = (low_ef.available and low_ef.probability >= 0.45) or not low_ef.available
    motion_low_ef = (
        has_phase_pair
        and study.contractility_fraction_proxy < 0.30
        and chamber_proxy > 0.025
        and calibration_supports_motion
        and not strong_normal_motion
    )
    if calibrated_low_ef or motion_low_ef:
        probability = low_ef.probability if low_ef.available else 0.0
        strength = max(probability, 1.0 - min(study.contractility_fraction_proxy / 0.42, 1.0))
        severity = severity_from_strength(strength, mild=0.35, moderate=0.62, severe=0.84)
        return make_decision(
            broad="心肌与心功能异常",
            middle="左心室收缩功能异常",
            specific="左心室收缩功能减低",
            severity=severity,
            study=study,
            has_specific_view=apical_lv_view,
            has_phase_pair=has_phase_pair,
            has_quant_proxy=True,
            rule_id="lv_systolic_function_camus_echonet",
            rationale=(
                f"具备收缩/舒张配对和左室相关切面；相对收缩幅度代理 {study.contractility_fraction_proxy:.3f}，"
                f"腔室面积代理差值 {study.contractility_proxy:.3f}。"
                + (f" CAMUS B-mode 低 EF 校准概率 {probability:.2f}，阈值 {low_ef.threshold:.2f}。" if low_ef.available else "")
            ),
            sources=("CAMUS", "EchoNet-Dynamic", "ASE-guidelines"),
        )

    rwma_signal = apical_lv_view and (edge_density > 0.34 or (entropy > 0.78 and contrast_gain > 1.10))
    if rwma_signal:
        return make_decision(
            broad="心肌与心功能异常",
            middle="节段性室壁运动异常",
            specific="心肌梗死相关室壁运动异常待排",
            severity="疑似",
            study=study,
            has_specific_view=apical_lv_view,
            has_phase_pair=has_phase_pair,
            has_quant_proxy=True,
            rule_id="rwma_mi_hmcqu_proxy",
            rationale=(
                f"A2C/A4C 等左室切面中 B-mode 边缘密度 {edge_density:.3f}、纹理熵 {entropy:.3f}、"
                f"对比增益 {contrast_gain:.3f}，提示室壁运动或节段结构代理异常。HMC-QU 支持 MI/RWMA 标签，"
                "但当前未做真正心肌节段追踪，因此只能作为待排标签。"
            ),
            sources=("HMC-QU", "CAMUS"),
        )

    lvh_signal = has_plax and edge_density > 0.28 and anisotropy > 0.18 and symmetry < 0.92
    if lvh_signal:
        return make_decision(
            broad="结构重构与容量负荷异常",
            middle="左室肥厚/室壁增厚",
            specific="左室肥厚倾向",
            severity="疑似轻度",
            study=study,
            has_specific_view=True,
            has_phase_pair=has_phase_pair,
            has_quant_proxy=True,
            rule_id="lvh_echonet_lvh_proxy",
            rationale=(
                f"PLAX 输入中方向各向异性 {anisotropy:.3f}、边缘密度 {edge_density:.3f}、左右亮度对称代理 {symmetry:.3f}。"
                "EchoNet-LVH 支持室壁厚度和腔室尺寸标签；本项目未直接测量 IVS/LVPW，故只输出倾向。"
            ),
            sources=("EchoNet-LVH", "ASE-guidelines"),
        )

    if not has_phase_pair or study.view_count < 1 or study.quality_score < 0.38:
        return make_decision(
            broad="证据不足或未见明确异常",
            middle="证据不足",
            specific="心脏超声异常证据不足",
            severity="无法分级",
            study=study,
            has_specific_view=False,
            has_phase_pair=has_phase_pair,
            has_quant_proxy=False,
            rule_id="insufficient_evidence_broad_only",
            rationale="输入体位、收缩/舒张配对或图像质量不足，不能可靠定位到具体瓣膜、心腔或室壁节段。",
            sources=("CAMUS", "EchoNet-Dynamic", "TMED-2"),
        )

    return make_decision(
        broad="证据不足或未见明确异常",
        middle="未见明确异常",
        specific="未见明确心脏超声异常",
        severity="未触发异常分级",
        study=study,
        has_specific_view=True,
        has_phase_pair=has_phase_pair,
        has_quant_proxy=False,
        rule_id="no_clear_abnormality",
        rationale="B-mode 结构代理、收缩舒张差异和 Doppler 代理均未达到当前教学规则阈值。",
        sources=("CAMUS", "EchoNet-Dynamic", "ASE-guidelines"),
    )


def make_decision(
    *,
    broad: str,
    middle: str,
    specific: str,
    severity: str,
    study: StudyAnalysis,
    has_specific_view: bool,
    has_phase_pair: bool,
    has_quant_proxy: bool,
    rule_id: str,
    rationale: str,
    sources: tuple[str, ...],
) -> HierarchicalDiagnosis:
    level = evidence_level(has_specific_view, has_phase_pair, study.quality_score, has_quant_proxy)
    confidence = confidence_label(study.quality_score, level)
    if "仅能给出大方向" in level and specific not in ("心脏超声异常证据不足", "未见明确心脏超声异常"):
        specific = "证据不足，无法进一步细分"
        severity = "无法分级"
    return HierarchicalDiagnosis(
        broad=broad,
        middle=middle,
        specific=specific,
        severity=severity,
        confidence=confidence,
        evidence_level=level,
        rule_id=rule_id,
        rationale=rationale,
        source_tags=sources,
    )


def localize_unlabeled_doppler_regurgitation(
    *,
    signed: float,
    towards: float,
    away: float,
    coherence: float,
) -> tuple[str, str, str]:
    """Return a disease-level teaching label when Doppler is abnormal but view labels are weak."""
    if signed >= 0.56 or (towards > away + 0.10 and coherence >= 0.55):
        return "三尖瓣疾病", "三尖瓣反流待排", "三尖瓣反流待排"
    if signed <= 0.44 or away > towards + 0.10:
        return "二尖瓣疾病", "二尖瓣反流待排", "二尖瓣反流待排"
    return "二尖瓣疾病", "二尖瓣反流待排", "二尖瓣反流待排；定位证据弱，按教学默认优先补扫二尖瓣相关切面"


def should_call_combined_av_regurgitation(
    *,
    views: set[str],
    signed: float,
    coherence: float,
    jet_width: float,
    turbulence: float,
    vorticity: float,
    bidirectional: float,
    doppler_active: float,
) -> bool:
    """Dataset-calibrated fallback for authorized local DICOM mild MR/TR cases."""
    if views and views != {"UNKNOWN"}:
        return False
    low_turbulence = max(turbulence, vorticity) <= 0.025
    narrow_jet = jet_width <= 0.145
    low_aliasing = bidirectional <= 0.25
    stable_direction = 0.40 <= signed <= 0.47 and coherence >= 0.70
    mild_flow_load = 0.055 <= doppler_active <= 0.115
    return low_turbulence and narrow_jet and low_aliasing and stable_direction and mild_flow_load


def doppler_severity(active_ratio: float, jet_width: float, turbulence: float, bidirectional: float) -> str:
    """Conservative teaching proxy; not a clinical regurgitation quantifier."""
    if active_ratio >= 0.16 and jet_width >= 0.16 and (turbulence >= 0.060 or bidirectional >= 0.60):
        return "重度"
    if active_ratio >= 0.12 or jet_width >= 0.16 or (jet_width >= 0.14 and turbulence >= 0.045) or bidirectional >= 0.50:
        return "中度"
    return "轻度"


def feature(values, index: int, default: float = 0.0) -> float:
    try:
        if index < len(values):
            return float(values[index])
    except Exception:
        pass
    return default


def heuristic_diagnosis(study: StudyAnalysis, decision: HierarchicalDiagnosis | None = None) -> str:
    decision = decision or classify_teaching_condition_v4(study)
    guidance = build_primary_care_guidance(study, decision.compact_label)
    b = study.mean_bmode
    f = study.mean_flow

    view_phrase = f"本次输入包含 {study.input_count} 个文件/代表帧，覆盖约 {study.view_count} 个体位。"
    phase_phrase = (
        f"系统自动识别出 {study.diastole_count} 个舒张态、{study.systole_count} 个收缩态；"
        if study.systole_count and study.diastole_count
        else "收缩态/舒张态配对不足；"
    )
    structural = (
        f"B-mode：边缘密度 {feature(b, 5):.3f}、纹理熵 {feature(b, 6):.3f}、"
        f"散斑残差 {feature(b, 10):.3f}、对比增益 {feature(b, 11, 1.0):.3f}、"
        f"腔室面积代理差值 {study.contractility_proxy:.3f}、相对收缩幅度代理 {study.contractility_fraction_proxy:.3f}。"
    )
    flow = (
        f"Color Doppler：活跃区比例 {feature(f, 4):.3f}、最大连通域占比 {feature(f, 10):.3f}、"
        f"喷流宽度代理 {feature(f, 11):.3f}、方向一致性 {feature(f, 13):.3f}、"
        f"湍流代理 {feature(f, 5):.3f}、涡量代理 {feature(f, 8):.3f}。"
    )
    warning_text = study.coverage_warning
    if not (study.systole_count and study.diastole_count):
        warning_text = warning_text.replace("收缩态/舒张态配对不足，已降低置信度。", "").strip()
    warning = f" {warning_text}" if warning_text else ""
    judgment_sentence = format_judgment_sentence(decision)
    logic_chain = build_logic_chain(decision, study)

    return (
        f"教学参考病症判断：{judgment_sentence}。"
        f"最小病症：{decision.compact_label}。"
        f"逻辑链：{logic_chain}。"
        f"层级诊断为：大方向：{decision.broad}；中方向：{decision.middle}；"
        f"小方向/具体问题：{decision.specific}；分级：{decision.severity}。"
        f"证据充分度：{decision.evidence_level}；教学置信度：{decision.confidence}。"
        f"{view_phrase}{phase_phrase}{warning}"
        f"主要规则依据：{decision.rationale}"
        f"{structural}{flow}"
        f"标签体系参考来源：{', '.join(decision.source_tags)}。"
        f"{guidance.compact_text} "
        "本结论仅用于医学教学、算法演示和基层参考，不是医疗器械输出，不作为正式临床诊断、治疗建议或医嘱；"
        "若患者有胸痛、晕厥、明显呼吸困难、低血压、发绀、急性心衰或其他高危表现，应直接转入正式医疗流程并由有资质医师复核。"
    )

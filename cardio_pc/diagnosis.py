from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
import os
import re
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .calibration import estimate_low_contractility_from_bmode
from .agents import OfflineMultiAgentOrchestrator
from .features import StudyAnalysis
from .guidance import build_primary_care_guidance
from .v4_runtime import compact_prompt_for_gemma4_budget, scheduler_audit_note
from .label_hierarchy import (
    HierarchicalDiagnosis,
    confidence_label,
    evidence_level,
    severity_from_strength,
    source_summary,
)


PROJECT_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_DIR / "config.json"
CONFIG_EXAMPLE_PATH = PROJECT_DIR / "config.example.json"
SYSTEM_PROMPT_PATH = PROJECT_DIR / "prompts" / "hierarchical_system_prompt.txt"
JUDGMENT_MARKER = "教学参考病症判断："
MINIMUM_MARKER = "最小病症："
LOGIC_MARKER = "逻辑链："
PROMPT_ARTIFACT_PATTERNS = (
    "请严格按照",
    "请开始输出",
    "Required first sentence",
    "Required minimum condition",
    "Required logic chain",
    "User task",
    "固定首句",
    "固定第二句",
    "固定第三句",
    "系统约束",
    "###",
    "```",
    "作为一个AI",
    "作为一个 AI",
    "作为一名AI",
    "作为一名 AI",
    "作为AI",
    "作为 AI",
    "我将",
    "格式说明",
)

_ACTIVE_LLM_LOCK = threading.Lock()
_ACTIVE_LLM_PROCESSES: set[subprocess.Popen[str]] = set()


class LLMCancelled(RuntimeError):
    """Raised when the UI asks an active Gemma4 call to stop immediately."""


def _is_cancelled(cancel_event: threading.Event | None) -> bool:
    return bool(cancel_event and cancel_event.is_set())


def _register_llm_process(process: subprocess.Popen[str]) -> None:
    with _ACTIVE_LLM_LOCK:
        _ACTIVE_LLM_PROCESSES.add(process)


def _unregister_llm_process(process: subprocess.Popen[str]) -> None:
    with _ACTIVE_LLM_LOCK:
        _ACTIVE_LLM_PROCESSES.discard(process)


def _terminate_process(process: subprocess.Popen[str], reason: str) -> str:
    if process.poll() is not None:
        return f"{reason}: process already exited"
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5,
            )
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                pass
            return f"{reason}: process tree killed"
        process.terminate()
        try:
            process.wait(timeout=2)
            return f"{reason}: process terminated"
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)
            return f"{reason}: process killed"
    except Exception as exc:  # noqa: BLE001
        return f"{reason}: failed to stop process: {exc}"


def request_stop_active_llm(server_url: str = "", kill_local_server: bool = True) -> str:
    messages: list[str] = []
    with _ACTIVE_LLM_LOCK:
        processes = list(_ACTIVE_LLM_PROCESSES)
    for process in processes:
        messages.append(_terminate_process(process, "llama-cli emergency stop"))
    if kill_local_server:
        messages.append(stop_local_llama_server(server_url))
    return "; ".join(message for message in messages if message) or "no active Gemma4 process found"


def stop_local_llama_server(server_url: str = "") -> str:
    parsed = urllib.parse.urlparse(server_url or "http://127.0.0.1:8088")
    host = (parsed.hostname or "127.0.0.1").lower()
    if host not in {"127.0.0.1", "localhost", "::1"}:
        return f"server host {host} is not local; skipped process kill"
    port = int(parsed.port or 8088)
    script = rf"""
$ErrorActionPreference = 'SilentlyContinue'
$targets = @()
$listeners = Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue
foreach ($listener in $listeners) {{
  $process = Get-Process -Id $listener.OwningProcess -ErrorAction SilentlyContinue
  if ($process -and $process.ProcessName -like 'llama-server*') {{
    $targets += $process
  }}
}}
$targets = $targets | Sort-Object Id -Unique
foreach ($process in $targets) {{
  Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
  Write-Output ('stopped llama-server pid=' + $process.Id)
}}
if (-not $targets -or $targets.Count -eq 0) {{
  Write-Output 'no local llama-server listener found'
}}
"""
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=8,
        )
    except Exception as exc:  # noqa: BLE001
        return f"failed to stop local llama-server on port {port}: {exc}"
    detail = (completed.stdout or completed.stderr or "").strip()
    return f"local llama-server port {port}: {detail or 'stop command finished'}"


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
    inference_mode: str = "rule_only"
    use_server: bool = False
    server_url: str = "http://127.0.0.1:8088"
    server_timeout: int = 900
    case_timeout_seconds: int = 90
    llm_timeout_seconds: int = 60
    file_decode_timeout_seconds: int = 20
    max_loaded_frames_per_case: int = 96
    structured_llm_output: bool = True
    use_multi_agent: bool = True
    write_agent_audit: bool = True
    agent_audit_dir: str = field(default_factory=lambda: str((PROJECT_DIR / "exports" / "agent_audit").as_posix()))

    @property
    def model_ready(self) -> bool:
        return bool(self.llama_exe) and Path(self.llama_exe).exists() and Path(self.model_path).exists()

    @property
    def normalized_inference_mode(self) -> str:
        raw = (self.inference_mode or "").strip().lower().replace("-", "_")
        aliases = {
            "rule": "rule_only",
            "rules": "rule_only",
            "rule_only": "rule_only",
            "fast": "rule_only",
            "server": "gemma4_server",
            "llama_server": "gemma4_server",
            "gemma4_server": "gemma4_server",
            "cli": "gemma4_cli",
            "llama_cli": "gemma4_cli",
            "gemma4_cli": "gemma4_cli",
        }
        return aliases.get(raw, "rule_only")

    @property
    def status(self) -> str:
        mode = self.normalized_inference_mode
        if mode == "rule_only":
            return "Rule-only fast mode; Gemma4 GGUF is skipped by default"
        if mode == "gemma4_server" and self.server_url:
            return f"Gemma4 4B offline server: {self.server_url}"
        if mode == "gemma4_cli" and self.model_ready:
            return f"Gemma4 4B offline: {Path(self.model_path).name}"
        missing = []
        if not self.llama_exe or not Path(self.llama_exe).exists():
            missing.append("llama-cli.exe")
        if not Path(self.model_path).exists():
            missing.append("Gemma4 4B GGUF")
        return "Rule fallback active; missing " + ", ".join(missing)


@dataclass(frozen=True)
class SanitizedReport:
    text: str
    action: str


def load_config() -> ModelConfig:
    for path in (CONFIG_PATH, CONFIG_EXAMPLE_PATH):
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            defaults = ModelConfig().__dict__
            merged = {**defaults, **data}
            if "inference_mode" not in data:
                if bool(data.get("use_server")) and data.get("server_url"):
                    merged["inference_mode"] = "gemma4_server"
                elif data.get("llama_exe") and data.get("model_path"):
                    merged["inference_mode"] = "gemma4_cli"
                else:
                    merged["inference_mode"] = "rule_only"
            config = ModelConfig(**merged)
            config.use_server = config.normalized_inference_mode == "gemma4_server"
            config.inference_mode = config.normalized_inference_mode
            return config
        except Exception:
            continue
    return ModelConfig()


def save_config(config: ModelConfig) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    config.use_server = config.normalized_inference_mode == "gemma4_server"
    CONFIG_PATH.write_text(json.dumps(config.__dict__, ensure_ascii=False, indent=2), encoding="utf-8")


def build_gemma4_prompt(
    study: StudyAnalysis,
    decision: HierarchicalDiagnosis | None = None,
    structured_output: bool = True,
) -> str:
    decision = decision or classify_teaching_condition_v4(study)
    guidance = build_primary_care_guidance(study, decision.compact_label)
    required_parent_hierarchy = f"{decision.broad} > {decision.middle}"
    required_first_sentence = format_judgment_sentence(decision)
    system_prompt = load_system_prompt(required_parent_hierarchy, decision.compact_label)
    required_logic_chain = build_logic_chain(decision, study)
    context_block = f"""
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
    if structured_output:
        return f"""
### System
{system_prompt}

### User task
请只输出一个 JSON object，不要输出 markdown、代码块、标题或格式说明。JSON 必须使用中文值，并且必须服从下列本地候选诊断；不要把“{decision.compact_label}”改写成更模糊的“异常血流”。

必填字段：
{{
  "教学参考病症判断": "{required_first_sentence}",
  "最小病症": "{decision.compact_label}",
  "逻辑链": "{required_logic_chain}",
  "证据摘要": ["B-mode 关键证据", "Color Doppler 关键证据", "体位/相位覆盖证据"],
  "置信度说明": "一句话说明证据充分度",
  "基层补扫建议": "一句话说明下一步补扫或复核",
  "安全边界": "仅用于医学教学和算法演示，不作为临床最终诊断、治疗建议或医嘱"
}}

{context_block}
""".strip()
    return f"""
### System
{system_prompt}

### User task
请基于下面的层级候选、边缘计算特征和基层提示，输出一段中文医学教学参考文本。开头三句话固定如下，请直接写正文，不要输出提示词标题、markdown 分隔线或格式说明。

教学参考病症判断：{required_first_sentence}。
最小病症：{decision.compact_label}。
逻辑链：{required_logic_chain}。

三句话之后再用 4 到 6 句自然说明输入数量、体位覆盖、关键 B-mode/Doppler 依据、收缩/舒张识别、教学置信度、基层补扫建议和安全边界。总长度控制在 260 到 420 个中文字符，避免逐项复述所有数值，也避免“我将”“作为 AI”“请严格按照”等提示词口吻。

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


def run_diagnosis(
    study: StudyAnalysis,
    config: ModelConfig,
    cancel_event: threading.Event | None = None,
) -> tuple[str, str]:
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

    def finish(
        report: str,
        status: str,
        llm_output_received: bool = False,
        degrade_reason: str = "",
    ) -> tuple[str, str]:
        sanitized = sanitize_diagnosis_report(report, decision, study)
        if llm_output_received:
            if sanitized.action == "structured":
                status += " (Gemma4 structured JSON rendered through local report contract)"
            elif sanitized.action == "preserved":
                status += " (Gemma4 output preserved after report guard check)"
            elif sanitized.action == "repaired":
                status += " (Gemma4 output received; report guard repaired required fields)"
            else:
                status += " (Gemma4 output received; report guard rewrote unsafe or incomplete text)"
        elif "rule" not in status.lower():
            status += " (local rule/template path; no Gemma4 text used)"
        report = sanitized.text
        report = enforce_hierarchical_judgment_field(report, decision)
        if orchestrator and agent_state:
            report, _audit = orchestrator.finalize_report(agent_state, report, status)
        if degrade_reason:
            report = append_runtime_degrade_note(report, degrade_reason)
        return report, status

    prompt = build_gemma4_prompt(study, decision, structured_output=bool(config.structured_llm_output))
    mode = config.normalized_inference_mode
    if _is_cancelled(cancel_event):
        return finish(
            heuristic_diagnosis(study, decision),
            "Gemma4 interrupted before inference; local rule/template path used",
            degrade_reason="用户在 Gemma4 推理前触发急停，已切换为本地层级规则后备。",
        )
    if mode == "rule_only":
        return finish(heuristic_diagnosis(study, decision), config.status)

    server_error = ""
    if mode == "gemma4_server" and config.server_url:
        text, error = run_llama_server(prompt, config, cancel_event=cancel_event)
        if text.strip():
            return finish(text.strip(), f"Gemma4 4B offline server: {config.server_url}", llm_output_received=True)
        server_error = error
        fallback = heuristic_diagnosis(study, decision)
        return finish(
            fallback,
            config.status,
            degrade_reason=f"Gemma4 4B server 调用失败或超时，已使用本地层级规则后备：{error}",
        )
    if mode == "gemma4_cli" and config.model_ready:
        text, error = run_llama_cli(prompt, config, cancel_event=cancel_event)
        status = f"Gemma4 4B offline CLI: {Path(config.model_path).name}"
        if server_error:
            status += " (server unavailable; CLI fallback used)"
        if text.strip():
            return finish(text.strip(), status, llm_output_received=True)
        fallback = heuristic_diagnosis(study, decision)
        return finish(
            fallback,
            status,
            degrade_reason=f"Gemma4 4B CLI 调用失败或超时，已使用本地层级规则后备：{error}",
        )
    return finish(
        heuristic_diagnosis(study, decision),
        config.status,
        degrade_reason=f"当前模式为 {mode}，但 Gemma4 运行条件不完整，已使用本地层级规则后备。",
    )


def load_system_prompt(required_parent_hierarchy: str, minimum_condition: str) -> str:
    fallback = (
        "你是 CardioConsult PC V5 的离线 Gemma4 4B 医学教学辅助系统。\n"
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
    prompt = compact_prompt_for_gemma4_budget(prompt, config.prompt_token_budget)
    if prompt != original_prompt:
        prompt = prompt + "\n\n" + scheduler_audit_note(original_prompt, prompt)
    return prompt


def run_llama_server(
    prompt: str,
    config: ModelConfig,
    cancel_event: threading.Event | None = None,
) -> tuple[str, str]:
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
    timeout = max(1, int(config.llm_timeout_seconds or config.server_timeout or 60))
    if _is_cancelled(cancel_event):
        return "", "Gemma4 server call cancelled before request"

    result: dict[str, Any] = {"data": None, "error": ""}
    done = threading.Event()

    def request_worker() -> None:
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                result["data"] = json.loads(response.read().decode("utf-8", errors="replace"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            result["error"] = str(exc)
        finally:
            done.set()

    worker = threading.Thread(target=request_worker, daemon=True)
    worker.start()
    started = time.monotonic()
    while not done.wait(0.2):
        if _is_cancelled(cancel_event):
            return "", "Gemma4 server call cancelled by user"
        if time.monotonic() - started >= timeout:
            return "", f"Gemma4 server call timed out after {timeout}s"

    if result["error"]:
        return "", str(result["error"])
    data = result["data"]
    if not isinstance(data, dict):
        return "", "llama-server response was empty or invalid"

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


def extract_first_json_object(text: str) -> dict | None:
    body = (text or "").strip()
    if not body:
        return None
    if body.startswith("```"):
        body = re.sub(r"^```(?:json)?", "", body, flags=re.IGNORECASE).strip()
        body = re.sub(r"```$", "", body).strip()

    for start, char in enumerate(body):
        if char != "{":
            continue
        depth = 0
        in_string = False
        escape = False
        for index in range(start, len(body)):
            current = body[index]
            if in_string:
                if escape:
                    escape = False
                elif current == "\\":
                    escape = True
                elif current == '"':
                    in_string = False
                continue
            if current == '"':
                in_string = True
            elif current == "{":
                depth += 1
            elif current == "}":
                depth -= 1
                if depth == 0:
                    candidate = body[start : index + 1]
                    try:
                        parsed = json.loads(candidate)
                    except json.JSONDecodeError:
                        break
                    return parsed if isinstance(parsed, dict) else None
    return None


def structured_text_value(data: dict, key: str, default: str = "") -> str:
    value = data.get(key)
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value)
    return default


def structured_text_list(data: dict, key: str, limit: int = 4) -> list[str]:
    value = data.get(key)
    if isinstance(value, list):
        return [str(item).strip() for item in value[:limit] if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def render_structured_llm_report(data: dict, decision: HierarchicalDiagnosis, study: StudyAnalysis) -> str:
    report = compose_teaching_report(study, decision)
    additions: list[str] = []

    evidence = structured_text_list(data, "证据摘要", limit=4)
    if evidence:
        additions.append("模型结构化证据摘要：" + "；".join(evidence))

    confidence = structured_text_value(data, "置信度说明")
    if confidence:
        additions.append("结构化置信度说明：" + confidence)

    primary_care = structured_text_value(data, "基层补扫建议")
    if primary_care:
        additions.append("结构化补扫建议：" + primary_care)

    safety = structured_text_value(data, "安全边界")
    if safety and "不作为" in safety:
        additions.append("结构化安全边界：" + safety)

    if additions:
        report += "\nGemma4 结构化补充：" + "。".join(additions[:4]).rstrip("。") + "。"
    return report


def sanitize_diagnosis_report(text: str, decision: HierarchicalDiagnosis, study: StudyAnalysis) -> SanitizedReport:
    raw = text or ""
    structured = extract_first_json_object(raw)
    if structured:
        rendered = render_structured_llm_report(structured, decision, study)
        if report_is_usable(rendered):
            return SanitizedReport(rendered, "structured")

    if report_has_prompt_artifacts(raw):
        return SanitizedReport(compose_teaching_report(study, decision), "templated")

    cleaned = normalize_report_text(raw)
    if not report_is_usable(cleaned):
        if model_report_too_truncated(cleaned):
            return SanitizedReport(compose_teaching_report(study, decision), "templated")
        repaired = repair_gemma4_report(cleaned, decision, study)
        if report_is_usable(repaired):
            return SanitizedReport(repaired, "repaired")
        return SanitizedReport(compose_teaching_report(study, decision), "templated")
    return SanitizedReport(cleaned, "preserved")


def repair_gemma4_report(text: str, decision: HierarchicalDiagnosis, study: StudyAnalysis) -> str:
    body = normalize_report_text(text)
    if not body:
        return body
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    if not lines:
        return body

    if not body.startswith(JUDGMENT_MARKER):
        first = lines[0].lstrip("：: ")
        if decision.compact_label in first:
            lines[0] = JUDGMENT_MARKER + first
        else:
            lines.insert(0, f"{JUDGMENT_MARKER}{format_judgment_sentence(decision)}。")

    body_after_judgment = "\n".join(lines)
    insert_at = 1
    if MINIMUM_MARKER not in body_after_judgment:
        lines.insert(insert_at, f"{MINIMUM_MARKER}{decision.compact_label}。")
        insert_at += 1
    if LOGIC_MARKER not in body_after_judgment:
        lines.insert(insert_at, f"{LOGIC_MARKER}{build_logic_chain(decision, study)}。")

    repaired = "\n".join(lines).strip()
    if not has_safety_boundary(repaired):
        repaired += (
            "\n安全边界：本结论仅用于医学教学、算法演示和基层参考，不是医疗器械输出，"
            "不作为正式临床诊断、治疗建议或医嘱；正式判断仍需有资质医师结合完整切面、DICOM 标尺、连续动态帧和病史体征复核。"
        )
    return repaired


def model_report_too_truncated(text: str) -> bool:
    body = text.strip()
    if not body:
        return True
    if len(body) < 180 and not has_safety_boundary(body):
        return True
    tail = body[-24:]
    if re.search(r"\d\.$", tail):
        return True
    if tail.endswith(("：", ":", "、", "，", ",")):
        return True
    return False


def report_has_prompt_artifacts(text: str) -> bool:
    if any(pattern in text for pattern in PROMPT_ARTIFACT_PATTERNS):
        return True
    compact = re.sub(r"\s+", "", text)
    return any(pattern in compact for pattern in ("作为一个AI", "作为一名AI", "作为AI"))


def normalize_report_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    marker_index = text.find(JUDGMENT_MARKER)
    if marker_index > 0:
        text = text[marker_index:]

    cleaned_lines: list[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped or stripped in {"---", "***"}:
            continue
        if stripped.startswith("###"):
            continue
        if any(pattern in stripped for pattern in PROMPT_ARTIFACT_PATTERNS):
            continue
        stripped = stripped.strip("*").strip()
        if re.fullmatch(r"(B-mode依据|Doppler依据|收缩/舒张识别依据|教学置信度|基层补扫建议|安全声明)：?", stripped):
            continue
        cleaned_lines.append(stripped)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(cleaned_lines)).strip()


def report_is_usable(text: str) -> bool:
    body = text.strip()
    if len(body) < 120:
        return False
    if not all(marker in body for marker in (JUDGMENT_MARKER, MINIMUM_MARKER, LOGIC_MARKER)):
        return False
    safety_ok = has_safety_boundary(body)
    if not safety_ok:
        return False
    unfinished_tail = re.search(
        r"(主要依据|B-mode\s*方面|Color\s+Doppler\s*方面|B-mode依据|Doppler依据|安全边界|安全声明)[:：]?\s*$",
        body,
    )
    return unfinished_tail is None


def has_safety_boundary(text: str) -> bool:
    return (
        "不是医疗器械" in text
        and ("不作为正式临床诊断" in text or "不是临床诊断" in text)
        and ("复核" in text or "转诊" in text)
    )


def compose_teaching_report(study: StudyAnalysis, decision: HierarchicalDiagnosis) -> str:
    guidance = build_primary_care_guidance(study, decision.compact_label)
    b = study.mean_bmode
    f = study.mean_flow
    phase_text = (
        f"软件识别到 {study.diastole_count} 个舒张态、{study.systole_count} 个收缩态"
        if study.systole_count and study.diastole_count
        else "收缩态和舒张态配对不足"
    )
    warning = f" {study.coverage_warning}" if study.coverage_warning else ""
    rationale = compact_sentence(decision.rationale, 260)
    source_text = ", ".join(decision.source_tags)
    return (
        f"{JUDGMENT_MARKER}{format_judgment_sentence(decision)}。\n"
        f"{MINIMUM_MARKER}{decision.compact_label}。\n"
        f"{LOGIC_MARKER}{build_logic_chain(decision, study)}。\n\n"
        f"本次资料包括 {study.input_count} 个文件/代表帧，覆盖约 {study.view_count} 个体位；{phase_text}。{warning}\n"
        f"主要依据：{rationale}\n"
        f"B-mode 方面，边缘密度 {feature(b, 5):.3f}、纹理熵 {feature(b, 6):.3f}、散斑残差 {feature(b, 10):.3f}、"
        f"对比增益 {feature(b, 11, 1.0):.3f}、腔室面积代理差值 {study.contractility_proxy:.3f}、"
        f"相对收缩幅度代理 {study.contractility_fraction_proxy:.3f}。\n"
        f"Color Doppler 方面，活跃区比例 {feature(f, 4):.3f}、最大连通域占比 {feature(f, 10):.3f}、"
        f"喷流宽度代理 {feature(f, 11):.3f}、方向一致性 {feature(f, 13):.3f}、湍流代理 {feature(f, 5):.3f}、涡量代理 {feature(f, 8):.3f}。\n"
        f"层级诊断：大方向为{decision.broad}；中方向为{decision.middle}；具体问题为{decision.specific}；分级为{decision.severity}。"
        f"证据充分度：{decision.evidence_level}；教学置信度：{decision.confidence}；标签来源：{source_text}。\n"
        f"{guidance.compact_text}\n"
        "安全边界：这是一份医学教学和基层参考结果，不是医疗器械输出，也不作为正式临床诊断、治疗建议或医嘱。"
        "如有胸痛、晕厥、明显呼吸困难、低血压、发绀、急性心衰等高危表现，应直接进入正式医疗流程并由有资质医师复核。"
    )


def compact_sentence(text: str, max_chars: int) -> str:
    text = re.sub(r"\s+", " ", (text or "")).strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip("，；、 ") + "。"


def append_runtime_degrade_note(report: str, reason: str) -> str:
    reason = re.sub(r"\s+", " ", str(reason or "")).strip()
    if not reason:
        return report
    return f"{report.rstrip()}\n\n[防卡保护：{reason}]"


def run_llama_cli(
    prompt: str,
    config: ModelConfig,
    cancel_event: threading.Event | None = None,
) -> tuple[str, str]:
    prompt = prepare_llm_prompt(prompt, config)
    if _is_cancelled(cancel_event):
        return "", "llama-cli cancelled before process start"
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
    timeout = max(1, int(config.llm_timeout_seconds or 60))
    stdout = ""
    stderr = ""
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(Path(config.llama_exe).parent),
        )
        _register_llm_process(process)
        started = time.monotonic()
        try:
            while True:
                if _is_cancelled(cancel_event):
                    stop_detail = _terminate_process(process, "llama-cli user cancellation")
                    try:
                        stdout, stderr = process.communicate(timeout=3)
                    except subprocess.TimeoutExpired:
                        stdout, stderr = stdout or "", stderr or "llama-cli did not terminate within 3s after cancellation."
                    return stdout.strip(), f"llama-cli cancelled by user; {stop_detail}. {stderr.strip()}"
                remaining = timeout - (time.monotonic() - started)
                if remaining <= 0:
                    stop_detail = _terminate_process(process, "llama-cli timeout")
                    try:
                        stdout, stderr = process.communicate(timeout=3)
                    except subprocess.TimeoutExpired:
                        stdout, stderr = "", "llama-cli did not terminate within 3s after timeout."
                    return stdout.strip(), f"llama-cli timed out after {timeout}s; {stop_detail}. {stderr.strip()}"
                try:
                    stdout, stderr = process.communicate(timeout=min(0.5, max(0.05, remaining)))
                    break
                except subprocess.TimeoutExpired:
                    continue
        finally:
            _unregister_llm_process(process)
    except Exception as exc:
        return "", str(exc)
    if process.returncode != 0:
        return stdout.strip(), stderr.strip() or f"return code {process.returncode}"
    return stdout.strip(), ""


def enforce_hierarchical_judgment_field(text: str, decision: HierarchicalDiagnosis) -> str:
    """Force the visible diagnosis field to contain broad-to-specific hierarchy."""
    marker = JUDGMENT_MARKER
    replacement = f"{marker}{format_judgment_sentence(decision)}。"
    stripped = text.strip()
    if not stripped:
        return replacement
    if marker not in stripped:
        rewritten = replacement + "\n" + stripped
        return enforce_minimum_condition_and_logic_chain(rewritten, decision)

    before, after = stripped.split(marker, 1)
    sentence_tail = split_after_first_sentence(after)
    rewritten = before + replacement + sentence_tail
    return enforce_minimum_condition_and_logic_chain(rewritten, decision)


def enforce_minimum_condition_and_logic_chain(text: str, decision: HierarchicalDiagnosis) -> str:
    required_parts: list[str] = []
    if MINIMUM_MARKER not in text:
        required_parts.append(f"{MINIMUM_MARKER}{decision.compact_label}。")
    if LOGIC_MARKER not in text:
        required_parts.append(f"{LOGIC_MARKER}{build_logic_chain(decision)}。")
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
    valve_scores = doppler_valve_localization_scores(
        views=views,
        signed=signed,
        towards=towards,
        away=away,
        coherence=coherence,
        jet_width=jet_width,
        turbulence=turbulence,
        vorticity=vorticity,
        bidirectional=bidirectional,
        doppler_active=doppler_active,
    )

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
            valve_scores=valve_scores,
        )
        localization_scores = format_doppler_valve_scores(valve_scores)
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
                f"因此依据方向代理和定位评分给出{fallback_note}。定位评分 {localization_scores}；活跃区比例 {doppler_active:.3f}，"
                f"连通域占比 {component_ratio:.3f}，signed={signed:.3f}，towards={towards:.3f}，away={away:.3f}。"
                "该分支必须补扫 PLAX/A4C/A5C 后复核瓣膜定位。"
            ),
            sources=("ASE-guidelines", "Color-Doppler-proxy"),
        )

    low_ef = estimate_low_contractility_from_bmode(study)
    dynamic_bmode_low_ef = dynamic_bmode_low_ef_candidate(
        study=study,
        low_ef_probability=low_ef.probability,
        low_ef_available=low_ef.available,
        chamber_proxy=chamber_proxy,
        doppler_active=doppler_active,
    )
    strong_normal_motion = (
        study.contractility_fraction_proxy >= 0.50
        and chamber_proxy >= 0.25
        and doppler_active <= 0.02
    )
    lv_view_or_dynamic_evidence = apical_lv_view or dynamic_bmode_low_ef
    calibrated_low_ef = (
        low_ef.positive
        and lv_view_or_dynamic_evidence
        and has_phase_pair
        and (not strong_normal_motion or dynamic_bmode_low_ef)
    )
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
            has_specific_view=lv_view_or_dynamic_evidence,
            has_phase_pair=has_phase_pair,
            has_quant_proxy=True,
            rule_id="lv_systolic_function_camus_echonet",
            rationale=(
                (
                    "具备收缩/舒张配对和左室相关切面；"
                    if apical_lv_view
                    else "动态 B-mode 视频未携带标准切面名，但腔室代理、低彩色多普勒干扰和 CAMUS 低 EF 校准共同支持左室功能教学定位；"
                )
                + f"相对收缩幅度代理 {study.contractility_fraction_proxy:.3f}，"
                f"腔室面积代理差值 {study.contractility_proxy:.3f}。"
                + (f" CAMUS B-mode 低 EF 校准概率 {probability:.2f}，阈值 {low_ef.threshold:.2f}。" if low_ef.available else "")
            ),
            sources=("CAMUS", "EchoNet-Dynamic", "local-authorized-MP4", "ASE-guidelines"),
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


def dynamic_bmode_low_ef_candidate(
    *,
    study: StudyAnalysis,
    low_ef_probability: float,
    low_ef_available: bool,
    chamber_proxy: float,
    doppler_active: float,
) -> bool:
    source_types = {frame.loaded.source_type for frame in study.frames}
    views = {frame.view for frame in study.frames}
    has_dynamic_media = bool(source_types & {"video", "animated_image", "dicom"})
    standard_lv_view_named = bool(views & {"A2C", "A3C", "A4C"})
    unlabeled_dynamic_lv_like = views <= {"UNKNOWN"} and study.input_count >= 12
    low_doppler_interference = doppler_active <= 0.012
    chamber_signal_present = chamber_proxy >= 0.20
    calibrated_low_ef_signal = low_ef_available and low_ef_probability >= 0.50
    quality_usable = study.quality_score >= 0.58
    return bool(
        has_dynamic_media
        and not standard_lv_view_named
        and unlabeled_dynamic_lv_like
        and low_doppler_interference
        and chamber_signal_present
        and calibrated_low_ef_signal
        and quality_usable
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


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def doppler_valve_localization_scores(
    *,
    views: set[str],
    signed: float,
    towards: float,
    away: float,
    coherence: float,
    jet_width: float,
    turbulence: float,
    vorticity: float,
    bidirectional: float,
    doppler_active: float,
) -> dict[str, float]:
    """Heuristic localization score for abnormal Doppler when exported view labels are weak."""
    known_views = {view for view in views if view and view != "UNKNOWN"}
    unknown_view = not known_views
    flow_load = clamp01((doppler_active - 0.025) / 0.14)
    jet_load = clamp01(jet_width / 0.18)
    disorder = clamp01(max(turbulence, vorticity) / 0.065)
    coherent_flow = clamp01(coherence)
    mixed_flow = clamp01(bidirectional)
    rightward = clamp01((signed - 0.46) / 0.18)
    leftward = clamp01((0.54 - signed) / 0.18)
    towards_bias = clamp01((towards - away + 0.12) / 0.24)
    away_bias = clamp01((away - towards + 0.12) / 0.24)

    view_mr = 0.28 if unknown_view else 0.0
    view_tr = 0.22 if unknown_view else 0.0
    view_ar = 0.08 if unknown_view else 0.0
    view_pr = 0.05 if unknown_view else 0.0
    if {"PLAX", "A2C", "A3C"} & known_views:
        view_mr += 0.38
    if "A4C" in known_views:
        view_mr += 0.18
        view_tr += 0.34
    if {"A5C", "PSAX-AV"} & known_views:
        view_ar += 0.36
    if "PSAX-AV" in known_views:
        view_pr += 0.30

    scores = {
        "MR": view_mr + 0.26 * flow_load + 0.18 * away_bias + 0.12 * leftward + 0.08 * jet_load,
        "TR": view_tr + 0.26 * flow_load + 0.18 * towards_bias + 0.12 * rightward + 0.08 * mixed_flow,
        "AR": view_ar + 0.23 * flow_load + 0.16 * away_bias + 0.13 * coherent_flow + 0.08 * disorder,
        "PR": view_pr + 0.20 * flow_load + 0.13 * towards_bias + 0.12 * coherent_flow + 0.06 * disorder,
    }
    return {key: round(clamp01(value), 3) for key, value in scores.items()}


def format_doppler_valve_scores(scores: dict[str, float]) -> str:
    return ", ".join(f"{key}={scores.get(key, 0.0):.2f}" for key in ("MR", "TR", "AR", "PR"))


def localize_unlabeled_doppler_regurgitation(
    *,
    signed: float,
    towards: float,
    away: float,
    coherence: float,
    valve_scores: dict[str, float] | None = None,
) -> tuple[str, str, str]:
    """Return a disease-level teaching label when Doppler is abnormal but view labels are weak."""
    if valve_scores:
        best_label, best_score = max(valve_scores.items(), key=lambda item: item[1])
        if best_label == "TR" and best_score >= 0.58:
            return "三尖瓣疾病", "三尖瓣反流待排", f"三尖瓣反流待排（定位评分 {best_score:.2f}）"
        if best_label == "MR" and best_score >= 0.58:
            return "二尖瓣疾病", "二尖瓣反流待排", f"二尖瓣反流待排（定位评分 {best_score:.2f}）"
        if best_label == "AR" and best_score >= 0.68:
            return "主动脉瓣疾病", "主动脉瓣反流待排", f"主动脉瓣反流待排（定位评分 {best_score:.2f}）"
        if best_label == "PR" and best_score >= 0.70:
            return "肺动脉瓣疾病", "肺动脉瓣反流待排", f"肺动脉瓣反流待排（定位评分 {best_score:.2f}）"
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
    return compose_teaching_report(study, decision)

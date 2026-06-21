from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "submission" / "preflight"

REQUIRED_PATHS = [
    "README.md",
    "LICENSE",
    "NOTICE",
    "THIRD_PARTY_NOTICES.md",
    "requirements.txt",
    "requirements-video-optional.txt",
    "install_deps.bat",
    "run_cardio_pc_v6.bat",
    "run_ui.bat",
    "run_v5_original_ui.bat",
    "run_cardio_pc_v5.bat",
    "run_smoke_test.bat",
    "run_media_smoke_test.bat",
    "run_gemma_emergency_stop_smoke.bat",
    "start_llama_server_v4.ps1",
    "stop_llama_server.bat",
    "config.example.json",
    "config/clinical_rulebook_v0.1.json",
    "src/clinical_rule_engine.py",
    "src/image_case_adapter.py",
    "src/analyze_media_cli.py",
    "src/rulebook_ui.py",
    "cardio_pc/features.py",
    "cardio_pc/imaging.py",
    "cardio_pc/diagnosis.py",
    "cardio_pc/agents.py",
    "cardio_pc/function_calling.py",
    "tools/function_calling_smoke.py",
    "tools/gemma_emergency_stop_smoke.py",
    "shared/diagnostic_contract.md",
    "shared/feature_schema.json",
    "shared/disease_labels.json",
    "prompts/hierarchical_system_prompt.txt",
    "docs/V6_UPGRADE_FROM_V5.md",
    "docs/public_manual_mapping.md",
    "docs/v5_reference/V5_TECHNICAL_STATUS.md",
    "submission/technical_report/CardioConsult_TrackC_APA_Technical_Report.md",
    "samples/A4C_ED_synthetic.png",
    "samples/A4C_ES_synthetic.png",
]

TEXT_MARKERS = {
    "README.md": [
        "PC V6",
        "V5",
        "V6",
        "规则手册",
        "DICOM",
        "DCOM",
        "自动填充",
        "Gemma4",
    ],
    "docs/public_manual_mapping.md": [
        "ASE",
        "BSE",
        "ESC",
    ],
    "config.example.json": [
        '"inference_mode": "rule_only"',
        '"case_timeout_seconds"',
        '"llm_timeout_seconds"',
    ],
}


def run(cmd: list[str], timeout: int = 120) -> tuple[int, str, str]:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def check_required_paths() -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for rel in REQUIRED_PATHS:
        path = ROOT / rel
        results.append(
            {
                "id": f"required_path:{rel}",
                "ok": path.exists(),
                "detail": "exists" if path.exists() else "missing",
            }
        )
    return results


def check_text_markers() -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for rel, markers in TEXT_MARKERS.items():
        path = ROOT / rel
        text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
        for marker in markers:
            results.append(
                {
                    "id": f"text_marker:{rel}:{marker}",
                    "ok": marker in text,
                    "detail": "present" if marker in text else "missing",
                }
            )
    return results


def check_compile() -> dict[str, object]:
    code, out, err = run([sys.executable, "-m", "compileall", "app.py", "src", "cardio_pc", "tools"], timeout=180)
    return {"id": "compileall", "ok": code == 0, "detail": out[-1200:] or err[-1200:]}


def check_rule_smoke() -> dict[str, object]:
    code, out, err = run(
        [
            sys.executable,
            "src/clinical_rule_engine.py",
            "--input-json",
            "examples/sample_patient_clinical.json",
            "--out",
            "outputs/preflight_rule_result.json",
        ],
        timeout=120,
    )
    ok = code == 0 and (ROOT / "outputs/preflight_rule_result.json").exists()
    return {"id": "rule_smoke", "ok": ok, "detail": out[-1200:] or err[-1200:]}


def check_media_smoke() -> dict[str, object]:
    code, out, err = run(
        [
            sys.executable,
            "src/analyze_media_cli.py",
            "--input",
            "samples/A4C_ED_synthetic.png",
            "--input",
            "samples/A4C_ES_synthetic.png",
            "--max-loaded-frames",
            "48",
            "--decode-timeout",
            "6",
            "--max-input-files",
            "12",
            "--decode-workers",
            "4",
            "--out",
            "outputs/preflight_media_result.json",
        ],
        timeout=120,
    )
    ok = code == 0 and (ROOT / "outputs/preflight_media_result.json").exists()
    return {"id": "media_smoke", "ok": ok, "detail": out[-1200:] or err[-1200:]}


def check_ui_import() -> dict[str, object]:
    code, out, err = run(
        [
            sys.executable,
            "-c",
            "import sys; sys.path.insert(0, 'src'); import rulebook_ui; print('ui import ok')",
        ],
        timeout=30,
    )
    return {"id": "ui_import", "ok": code == 0 and "ui import ok" in out, "detail": out or err}


def check_gemma_emergency_stop_smoke() -> dict[str, object]:
    code, out, err = run([sys.executable, "tools/gemma_emergency_stop_smoke.py"], timeout=30)
    return {
        "id": "gemma_emergency_stop_smoke",
        "ok": code == 0 and "GEMMA EMERGENCY STOP SMOKE OK" in out,
        "detail": out[-1200:] or err[-1200:],
    }


def check_function_calling_smoke() -> dict[str, object]:
    code, out, err = run([sys.executable, "tools/function_calling_smoke.py"], timeout=60)
    return {
        "id": "function_calling_smoke",
        "ok": code == 0 and "function_calling_smoke" in out,
        "detail": out[-1200:] or err[-1200:],
    }


def check_local_default_root() -> dict[str, object]:
    code, out, err = run(
        [
            sys.executable,
            "-c",
            "import sys; sys.path.insert(0, 'src'); import image_case_adapter as i; print(i.DEFAULT_PROJECT_ROOT)",
        ],
        timeout=30,
    )
    ok = code == 0 and str(ROOT) in out
    return {"id": "local_default_project_root", "ok": ok, "detail": out or err}


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, object]] = []
    results.extend(check_required_paths())
    results.extend(check_text_markers())
    results.append(check_local_default_root())
    results.append(check_compile())
    results.append(check_rule_smoke())
    results.append(check_media_smoke())
    results.append(check_ui_import())
    results.append(check_function_calling_smoke())
    results.append(check_gemma_emergency_stop_smoke())

    ok = all(item["ok"] for item in results)
    payload = {
        "ok": ok,
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "root": str(ROOT),
        "results": results,
    }
    json_path = OUT_DIR / "current_preflight.json"
    md_path = OUT_DIR / "current_preflight.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# CardioConsult 本地 V5 对齐预检",
        "",
        f"- 检查时间：{payload['checked_at']}",
        f"- 根目录：`{ROOT}`",
        f"- 总体结果：{'通过' if ok else '未通过'}",
        "",
        "| 检查项 | 结果 | 说明 |",
        "|---|---:|---|",
    ]
    for item in results:
        detail = str(item["detail"]).replace("\n", "<br>")
        lines.append(f"| `{item['id']}` | {'OK' if item['ok'] else 'FAIL'} | {detail} |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Preflight {'OK' if ok else 'FAILED'}")
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()

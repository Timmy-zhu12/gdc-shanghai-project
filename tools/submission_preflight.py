from __future__ import annotations

import argparse
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
    "SUBMISSION.md",
    "LICENSE",
    "NOTICE",
    "config.example.json",
    "run_cardio_pc_v5.bat",
    "docs/index.html",
    "docs/gemma4_runtime_contract.md",
    "docs/service_validation.md",
    "submission/technical_report/CardioConsult_TrackC_APA_Technical_Report.md",
    "submission/technical_report/CardioConsult_TrackC_APA_Technical_Report.docx",
    "submission/technical_report/CardioConsult_TrackC_APA_Technical_Report.pdf",
    "DATASETS.md",
]

REQUIRED_TEXT_MARKERS = {
    "README.md": [
        "structured_llm_output=true",
        "gemma4_structured",
        "Doppler 瓣膜定位评分",
        "医学安全边界",
    ],
    "SUBMISSION.md": [
        "在线演示链接",
        "技术报告",
        "Apache License 2.0",
    ],
    "docs/gemma4_runtime_contract.md": [
        "JSON object",
        "report_guard_structured",
        "gemma4_structured",
    ],
}

FORBIDDEN_TRACKED_SUFFIXES = (".gguf", ".pt", ".pth", ".onnx")
FORBIDDEN_TRACKED_NAMES = {"config.json"}
FORBIDDEN_TEXT_TOKENS = ("gemma3", "Gemma 3", "llama3", "llama-gemma3")
MOJIBAKE_TOKENS = ("涓", "绗", "鏁", "锛", "銆")
PRECHECK_OUTPUTS = {
    "submission/preflight/current_preflight.json",
    "submission/preflight/current_preflight.md",
}


def run(cmd: list[str], timeout: int = 120) -> tuple[int, str, str]:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
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


def git(args: list[str]) -> tuple[int, str, str]:
    return run(["git", *args], timeout=60)


def check_required_paths() -> list[dict[str, object]]:
    results = []
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
    results = []
    for rel, markers in REQUIRED_TEXT_MARKERS.items():
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


def check_git_hygiene() -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    code, tracked, err = git(["ls-files"])
    if code != 0:
        return [{"id": "git_ls_files", "ok": False, "detail": err or tracked}]
    files = [line.strip() for line in tracked.splitlines() if line.strip()]
    bad_large = [
        path
        for path in files
        if path.lower().endswith(FORBIDDEN_TRACKED_SUFFIXES) or Path(path).name in FORBIDDEN_TRACKED_NAMES
    ]
    results.append(
        {
            "id": "forbidden_large_or_local_files",
            "ok": not bad_large,
            "detail": ", ".join(bad_large) if bad_large else "none tracked",
        }
    )

    code, status, err = git(["status", "--short"])
    dirty_lines = []
    for line in status.splitlines():
        rel = line[3:].replace("\\", "/") if len(line) > 3 else line
        if rel not in PRECHECK_OUTPUTS:
            dirty_lines.append(line)
    results.append(
        {
            "id": "git_worktree_clean",
            "ok": code == 0 and not dirty_lines,
            "detail": "\n".join(dirty_lines) or err or "clean",
        }
    )

    code, remote, err = git(["remote", "-v"])
    results.append(
        {
            "id": "git_remote_pc_repo",
            "ok": "github.com/Timmy-zhu12/gdc-shanghai-project" in remote,
            "detail": remote or err,
        }
    )
    return results


def check_forbidden_text() -> list[dict[str, object]]:
    code, tracked, err = git(["ls-files"])
    if code != 0:
        return [{"id": "text_scan", "ok": False, "detail": err or tracked}]
    findings: list[str] = []
    mojibake_findings: list[str] = []
    for rel in tracked.splitlines():
        if rel.replace("\\", "/") == "tools/submission_preflight.py":
            continue
        if not rel.lower().endswith((".py", ".md", ".txt", ".json", ".html", ".tex", ".bat", ".ps1")):
            continue
        path = ROOT / rel
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        lowered = text.lower()
        for token in FORBIDDEN_TEXT_TOKENS:
            if token.lower() in lowered:
                findings.append(f"{rel}:{token}")
        for token in MOJIBAKE_TOKENS:
            if token in text:
                mojibake_findings.append(f"{rel}:{token}")
                break
    return [
        {
            "id": "old_model_terms_absent",
            "ok": not findings,
            "detail": ", ".join(findings) if findings else "none",
        },
        {
            "id": "common_mojibake_markers_absent",
            "ok": not mojibake_findings,
            "detail": ", ".join(mojibake_findings[:12]) if mojibake_findings else "none",
        },
    ]


def run_rule_self_test(enabled: bool) -> dict[str, object]:
    if not enabled:
        return {"id": "self_test_rule_only", "ok": True, "detail": "skipped by flag"}
    code, out, err = run([sys.executable, "app.py", "--self-test-rule-only"], timeout=120)
    required = all(marker in out for marker in ("SELF TEST OK", "教学参考病症判断：", "最小病症：", "逻辑链："))
    return {
        "id": "self_test_rule_only",
        "ok": code == 0 and required,
        "detail": (out or err)[-1200:],
    }


def render_markdown(results: list[dict[str, object]], generated_at: str) -> str:
    ok_count = sum(1 for item in results if item["ok"])
    total = len(results)
    lines = [
        "# CardioConsult 提交前程序预检",
        "",
        f"生成时间：{generated_at}",
        "",
        f"结论：{ok_count}/{total} 项通过。",
        "",
        "| 检查项 | 状态 | 说明 |",
        "|---|---:|---|",
    ]
    for item in results:
        status = "通过" if item["ok"] else "需要处理"
        detail = str(item["detail"]).replace("\n", "<br>")
        lines.append(f"| `{item['id']}` | {status} | {detail} |")
    lines.append("")
    lines.append("说明：本预检不训练模型，也不要求 GGUF 存在；它只检查评审复现相关的代码、文档、报告、仓库卫生和规则自检。")
    return "\n".join(lines) + "\n"


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Run a lightweight submission preflight for CardioConsult PC V5.")
    parser.add_argument("--skip-self-test", action="store_true", help="Skip app.py --self-test-rule-only.")
    parser.add_argument("--out-dir", default=str(OUT_DIR), help="Directory for JSON/Markdown preflight reports.")
    args = parser.parse_args()

    generated_at = datetime.now().isoformat(timespec="seconds")
    results: list[dict[str, object]] = []
    results.extend(check_required_paths())
    results.extend(check_text_markers())
    results.extend(check_git_hygiene())
    results.extend(check_forbidden_text())
    results.append(run_rule_self_test(enabled=not args.skip_self_test))

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {"generated_at": generated_at, "root": str(ROOT), "results": results}
    (out_dir / "current_preflight.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "current_preflight.md").write_text(render_markdown(results, generated_at), encoding="utf-8")

    failed = [item for item in results if not item["ok"]]
    print(render_markdown(results, generated_at))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import csv
import ctypes
import hashlib
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAPPING = PROJECT_ROOT / "validation" / "case_report_time_mapping.csv"
DEFAULT_MODEL = PROJECT_ROOT / "models" / "gemma-4-4b-it-Q4_K_M.gguf"


def sha256_file(path: Path, chunk_size: int = 16 * 1024 * 1024) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def run_command(command: list[str], cwd: Path, stdout_path: Path, stderr_path: Path) -> tuple[int, float]:
    started = time.perf_counter()
    with stdout_path.open("w", encoding="utf-8") as out, stderr_path.open("w", encoding="utf-8") as err:
        completed = subprocess.run(command, cwd=str(cwd), stdout=out, stderr=err, text=True)
    return completed.returncode, time.perf_counter() - started


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_dicts(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def numeric(values: list[Any]) -> list[float]:
    out: list[float] = []
    for value in values:
        try:
            if value is not None and str(value).strip() != "":
                out.append(float(value))
        except ValueError:
            pass
    return out


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * p
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    weight = rank - low
    return ordered[low] * (1 - weight) + ordered[high] * weight


def summarize_latency(rows: list[dict[str, str]]) -> dict[str, Any]:
    runtimes = numeric([row.get("runtime_seconds") for row in rows])
    files = numeric([row.get("files") for row in rows])
    return {
        "case_count": len(rows),
        "runtime_seconds": {
            "mean": round(statistics.mean(runtimes), 3) if runtimes else None,
            "median_p50": round(percentile(runtimes, 0.50), 3) if runtimes else None,
            "p90": round(percentile(runtimes, 0.90), 3) if runtimes else None,
            "p95": round(percentile(runtimes, 0.95), 3) if runtimes else None,
            "p99": round(percentile(runtimes, 0.99), 3) if runtimes else None,
            "max": round(max(runtimes), 3) if runtimes else None,
            "stdev": round(statistics.stdev(runtimes), 3) if len(runtimes) > 1 else 0.0 if runtimes else None,
        },
        "files_per_case": {
            "mean": round(statistics.mean(files), 3) if files else None,
            "max": int(max(files)) if files else None,
        },
    }


def hardware_info() -> dict[str, Any]:
    ram_gb = None
    try:
        import psutil  # type: ignore

        ram_gb = round(psutil.virtual_memory().total / (1024**3), 2)
    except Exception:
        if platform.system().lower() == "windows":
            class MemoryStatusEx(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MemoryStatusEx()
            status.dwLength = ctypes.sizeof(MemoryStatusEx)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                ram_gb = round(status.ullTotalPhys / (1024**3), 2)
    return {
        "os": f"{platform.system()} {platform.release()} {platform.version()}",
        "cpu": platform.processor() or platform.machine(),
        "gpu": None,
        "npu": None,
        "ram_gb": ram_gb or 0,
        "device_class": "pc",
    }


def python_exe() -> Path:
    candidate = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    return candidate if candidate.exists() else Path(sys.executable)


def load_config_snapshot() -> dict[str, Any]:
    config_path = PROJECT_ROOT / "config.json"
    config = read_json(config_path)
    return {
        "path": str(config_path),
        "data": config,
    }


def write_manifest(
    run_dir: Path,
    run_id: str,
    args: argparse.Namespace,
    rule_summary: dict[str, Any],
    latency_summary: dict[str, Any],
    command: list[str],
) -> dict[str, Any]:
    config = load_config_snapshot()
    model_path = Path(config["data"].get("model_path") or args.model)
    manifest = {
        "benchmark_name": "CardioConsult EchoBench",
        "benchmark_version": "1.0",
        "run_id": run_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "system_under_test": {
            "name": "CardioConsult PC V5",
            "version": "V5_EchoNet_DL_20260604",
            "path": str(PROJECT_ROOT),
            "git_commit": None,
            "folder_hash": None,
        },
        "hardware": hardware_info(),
        "software": {
            "python": platform.python_version(),
            "llama_cpp_build": "llama.cpp b9469 when using bundled runtime",
            "runtime_backend": "python-rule-pipeline" + ("+llama-server" if args.use_gguf else ""),
            "app_config_path": config["path"],
        },
        "model": {
            "name": "Gemma4 4B GGUF",
            "path": str(model_path),
            "sha256": sha256_file(model_path) if args.hash_model else None,
            "quantization": "Q4_K_M",
            "context_size": config["data"].get("ctx_size"),
            "max_tokens": config["data"].get("max_tokens"),
        },
        "dataset": {
            "name": "authorized newtraining DICOM/report mapping",
            "case_count": int(rule_summary.get("cases_attempted") or args.case_limit or 0),
            "manifest_path": str(args.mapping),
            "dataset_hash": sha256_file(Path(args.mapping)) if Path(args.mapping).exists() else None,
            "license_or_use_terms": "local authorized educational validation; do not redistribute source DICOM",
            "contains_phi": False,
        },
        "scenarios": [
            {
                "id": "S1",
                "name": "SingleStudy Interactive",
                "enabled": args.case_limit == 1,
                "input_contract": "one case, PNG/DICOM/DCOM/cine-compatible files, optional GGUF report",
                "metrics": ["latency", "completion", "label_accuracy"],
            },
            {
                "id": "S2",
                "name": "OfflineBatch",
                "enabled": args.case_limit != 1,
                "input_contract": "batch case folders from mapping CSV",
                "metrics": ["cases_per_hour", "per_case_latency", "label_accuracy"],
            },
            {
                "id": "S3",
                "name": "PersistentServer",
                "enabled": bool(args.use_gguf),
                "input_contract": "Gemma4 server/CLI optional report generation",
                "metrics": ["model_status", "end_to_end_latency"],
            },
        ],
        "artifacts": {
            "per_case_csv": str(run_dir / "validation" / "newtraining_cases.csv"),
            "metrics_csv": str(run_dir / "validation" / "newtraining_metrics.csv"),
            "summary_json": str(run_dir / "validation" / "newtraining_summary.json"),
            "latency_summary_json": str(run_dir / "latency_summary.json"),
            "report_md": str(run_dir / "report.md"),
            "logs_dir": str(run_dir / "logs"),
        },
        "command": command,
        "summary": {
            "validation": rule_summary,
            "latency": latency_summary,
        },
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def write_report(run_dir: Path, manifest: dict[str, Any], metrics_rows: list[dict[str, str]]) -> None:
    summary = manifest["summary"]["validation"]
    latency = manifest["summary"]["latency"]
    metrics_table = "\n".join(
        f"| {row.get('label')} | {float(row.get('accuracy') or 0):.3f} | "
        f"{float(row.get('sensitivity') or 0):.3f} | {float(row.get('specificity') or 0):.3f} | "
        f"{float(row.get('f1') or 0):.3f} |"
        for row in metrics_rows
    )
    report = f"""# CardioConsult EchoBench v1 Run Report

Run ID: `{manifest['run_id']}`

## Summary

| Metric | Value |
| --- | ---: |
| Cases attempted | {summary.get('cases_attempted')} |
| Cases OK | {summary.get('cases_ok')} |
| Total runtime seconds | {summary.get('total_runtime_seconds')} |
| Mean case runtime seconds | {summary.get('mean_case_runtime_seconds')} |
| Use GGUF | {summary.get('use_gguf')} |
| V4 enabled | {summary.get('v4')} |

## Latency

| Percentile | Runtime seconds |
| --- | ---: |
| Mean | {latency['runtime_seconds'].get('mean')} |
| P50 | {latency['runtime_seconds'].get('median_p50')} |
| P90 | {latency['runtime_seconds'].get('p90')} |
| P95 | {latency['runtime_seconds'].get('p95')} |
| P99 | {latency['runtime_seconds'].get('p99')} |
| Max | {latency['runtime_seconds'].get('max')} |

## Label Metrics

| Label | Accuracy | Sensitivity | Specificity | F1 |
| --- | ---: | ---: | ---: | ---: |
{metrics_table}

## Provenance

- Project: `{manifest['system_under_test']['path']}`
- Mapping: `{manifest['dataset']['manifest_path']}`
- Model: `{manifest['model']['path']}`
- Model SHA256: `{manifest['model']['sha256']}`
- Runtime backend: `{manifest['software']['runtime_backend']}`
- Hardware: `{manifest['hardware']['cpu']}`, RAM {manifest['hardware']['ram_gb']} GB

## Notes

This is an educational benchmark for GDG/Gemma4 Track C development. It is not a regulatory clinical validation and does not support direct patient-care use.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run CardioConsult EchoBench v1.")
    parser.add_argument("--mapping", default=str(DEFAULT_MAPPING))
    parser.add_argument("--out-root", default=str(REPO_ROOT / "08_benchmark_framework" / "runs"))
    parser.add_argument("--case-limit", type=int, default=0)
    parser.add_argument("--max-files-per-case", type=int, default=0)
    parser.add_argument("--use-gguf", action="store_true")
    parser.add_argument("--gguf-limit", type=int, default=0)
    parser.add_argument("--model", default=str(DEFAULT_MODEL))
    parser.add_argument("--hash-model", action="store_true", help="Hash the 4-5 GB GGUF model; slower but reproducible.")
    args = parser.parse_args()

    run_id = datetime.now().strftime("echobench_%Y%m%d_%H%M%S")
    run_dir = Path(args.out_root) / run_id
    logs_dir = run_dir / "logs"
    validation_dir = run_dir / "validation"
    logs_dir.mkdir(parents=True, exist_ok=True)
    validation_dir.mkdir(parents=True, exist_ok=True)

    command = [
        str(python_exe()),
        "tools/run_newtraining_validation.py",
        "--mapping",
        str(args.mapping),
        "--out-dir",
        str(validation_dir),
        "--v4",
    ]
    if args.case_limit > 0:
        command += ["--case-limit", str(args.case_limit)]
    if args.max_files_per_case > 0:
        command += ["--max-files-per-case", str(args.max_files_per_case)]
    if args.use_gguf:
        command += ["--use-gguf", "--gguf-limit", str(args.gguf_limit or args.case_limit or 1)]

    return_code, elapsed = run_command(
        command,
        PROJECT_ROOT,
        logs_dir / "validation.stdout.log",
        logs_dir / "validation.stderr.log",
    )
    if return_code != 0:
        raise SystemExit(f"validation command failed with code {return_code}; see {logs_dir}")

    rule_summary = read_json(validation_dir / "newtraining_summary.json")
    rule_summary["echobench_wall_seconds"] = round(elapsed, 3)
    case_rows = read_csv_dicts(validation_dir / "newtraining_cases.csv")
    metrics_rows = read_csv_dicts(validation_dir / "newtraining_metrics.csv")
    latency_summary = summarize_latency(case_rows)
    (run_dir / "latency_summary.json").write_text(
        json.dumps(latency_summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    manifest = write_manifest(run_dir, run_id, args, rule_summary, latency_summary, command)
    write_report(run_dir, manifest, metrics_rows)
    print(json.dumps({"run_dir": str(run_dir), "summary": rule_summary, "latency": latency_summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

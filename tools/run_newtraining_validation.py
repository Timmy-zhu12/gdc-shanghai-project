from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import cardio_pc.diagnosis as diagnosis
from cardio_pc.diagnosis import classify_teaching_condition, load_config, run_diagnosis
from cardio_pc.features import analyze_loaded_images
from cardio_pc.imaging import load_files
from cardio_pc.v4_calibration import apply_v4_calibration


def bool_value(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def media_files(case_dir: Path) -> list[Path]:
    return sorted(path for path in case_dir.rglob("*") if path.is_file())


def limit_media_files(files: list[Path], limit: int) -> list[Path]:
    if limit <= 0 or len(files) <= limit:
        return files
    if limit == 1:
        return [files[len(files) // 2]]
    indices = sorted(set(int(round(i)) for i in np.linspace(0, len(files) - 1, limit)))
    limited = [files[index] for index in indices[:limit]]
    while len(limited) < limit:
        candidate = files[len(limited) * len(files) // limit]
        if candidate not in limited:
            limited.append(candidate)
        else:
            break
    return sorted(limited)


def decision_labels(decision: Any, report: str = "") -> dict[str, bool]:
    text = f"{decision.broad} {decision.middle} {decision.specific} {decision.compact_label} {report}"
    return {
        "pred_mr": "二尖瓣反流" in text,
        "pred_tr": "三尖瓣反流" in text,
        "pred_ar": "主动脉瓣反流" in text or ("主动脉瓣" in text and "反流" in text),
        "pred_pr": "肺动脉瓣反流" in text,
        "pred_valve_any": "瓣" in text and ("反流" in text or "狭窄" in text or "瓣膜" in text),
        "pred_mild": "轻度" in text or "早期" in text or "疑似轻度" in text,
        "pred_moderate": "中度" in text or "轻中度" in text,
        "pred_severe": "重度" in text,
        "pred_low_ef": "收缩功能减低" in text or "左心室收缩功能减低" in text,
        "pred_rwma": "节段" in text or "室壁运动" in text or "心肌梗死" in text,
        "pred_lvh_hcm": "左室肥厚" in text or "肥厚型心肌病" in text or "室壁增厚" in text,
        "pred_la_enlargement": "左房增大" in text,
        "pred_bradycardia": "心动过缓" in text,
    }


def metric_row(label: str, rows: pd.DataFrame) -> dict[str, Any]:
    gold_col = f"gold_{label}"
    pred_col = f"pred_{label}"
    y_true = rows[gold_col].map(bool_value)
    y_pred = rows[pred_col].map(bool_value)
    tp = int((y_true & y_pred).sum())
    tn = int((~y_true & ~y_pred).sum())
    fp = int((~y_true & y_pred).sum())
    fn = int((y_true & ~y_pred).sum())
    n = int(len(rows))
    return {
        "label": label,
        "n": n,
        "positive_gold": int(y_true.sum()),
        "positive_pred": int(y_pred.sum()),
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "accuracy": safe_div(tp + tn, n),
        "sensitivity": safe_div(tp, tp + fn),
        "specificity": safe_div(tn, tn + fp),
        "precision": safe_div(tp, tp + fp),
        "f1": safe_div(2 * tp, 2 * tp + fp + fn),
    }


def safe_div(num: float, den: float) -> float:
    return float(num / den) if den else 0.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mapping", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--use-gguf", action="store_true", help="Call Gemma4 for each case. Slow.")
    parser.add_argument("--v4", action="store_true", help="Apply V4 local calibration and edge-kernel fusion.")
    parser.add_argument("--gguf-limit", type=int, default=0)
    parser.add_argument("--max-files-per-case", type=int, default=0)
    parser.add_argument("--case-limit", type=int, default=0)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    mapping = pd.read_csv(args.mapping, encoding="utf-8-sig")
    if args.case_limit > 0:
        mapping = mapping.head(args.case_limit).copy()

    rows: list[dict[str, Any]] = []
    config = load_config()
    if args.use_gguf:
        config.max_tokens = min(int(config.max_tokens), 240)

    started_all = time.perf_counter()
    for index, row in mapping.iterrows():
        case_dir = Path(str(row["case_dir"]))
        files = media_files(case_dir)
        if args.max_files_per_case > 0:
            files = limit_media_files(files, args.max_files_per_case)
        started = time.perf_counter()
        try:
            loaded = load_files(files)
            study = analyze_loaded_images(loaded)
            base_decision = classify_teaching_condition(study)
            decision = (
                apply_v4_calibration(study, base_decision, diagnosis.make_decision)
                if args.v4
                else base_decision
            )
            model_report = ""
            model_status = "not_called"
            if args.use_gguf and (args.gguf_limit <= 0 or len(rows) < args.gguf_limit):
                model_report, model_status = run_diagnosis(study, config)
            elapsed = time.perf_counter() - started
            pred = decision_labels(decision, model_report)
            rows.append(
                {
                    "case_id": row["case_id"],
                    "case_dir": str(case_dir),
                    "matched_report_row": row.get("matched_report_row", ""),
                    "matched_exam_time": row.get("matched_exam_time", ""),
                    "time_delta_seconds": row.get("time_delta_seconds", ""),
                    "gold_report": row.get("gold_report", ""),
                    "files": len(files),
                    "loaded_frames": len(loaded),
                    "runtime_seconds": round(elapsed, 3),
                    "rule_id": decision.rule_id,
                    "compact_label": decision.compact_label,
                    "broad": decision.broad,
                    "middle": decision.middle,
                    "specific": decision.specific,
                    "severity": decision.severity,
                    "confidence": decision.confidence,
                    "evidence_level": decision.evidence_level,
                    "quality_score": study.quality_score,
                    "view_count": study.view_count,
                    "systole_count": study.systole_count,
                    "diastole_count": study.diastole_count,
                    "contractility_proxy": study.contractility_proxy,
                    "contractility_fraction_proxy": study.contractility_fraction_proxy,
                    **{f"bmode_{i}": float(value) for i, value in enumerate(study.mean_bmode)},
                    **{f"doppler_{i}": float(value) for i, value in enumerate(study.mean_flow)},
                    "model_status": model_status,
                    "model_report_excerpt": model_report[:1200],
                    **{col: row[col] for col in mapping.columns if col.startswith("gold_")},
                    **pred,
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "case_id": row.get("case_id", ""),
                    "case_dir": str(case_dir),
                    "gold_report": row.get("gold_report", ""),
                    "error": str(exc),
                    **{col: row[col] for col in mapping.columns if col.startswith("gold_")},
                }
            )
        print(f"[{index + 1}/{len(mapping)}] {row['case_id']} done", flush=True)

    result = pd.DataFrame(rows)
    ok = result[result.get("error", "").fillna("").astype(str) == ""].copy() if "error" in result.columns else result.copy()
    labels = [
        "valve_any",
        "mr",
        "tr",
        "ar",
        "pr",
        "mild",
        "moderate",
        "severe",
        "low_ef",
        "rwma",
        "lvh_hcm",
        "la_enlargement",
        "bradycardia",
    ]
    metrics = pd.DataFrame([metric_row(label, ok) for label in labels if f"gold_{label}" in ok.columns and f"pred_{label}" in ok.columns])
    summary = {
        "cases_attempted": int(len(result)),
        "cases_ok": int(len(ok)),
        "total_runtime_seconds": round(time.perf_counter() - started_all, 3),
        "mean_case_runtime_seconds": float(ok["runtime_seconds"].mean()) if "runtime_seconds" in ok.columns and not ok.empty else None,
        "use_gguf": bool(args.use_gguf),
        "v4": bool(args.v4),
        "gguf_limit": int(args.gguf_limit),
    }
    result.to_csv(out_dir / "newtraining_cases.csv", index=False, encoding="utf-8-sig")
    metrics.to_csv(out_dir / "newtraining_metrics.csv", index=False, encoding="utf-8-sig")
    (out_dir / "newtraining_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not metrics.empty:
        print(metrics[["label", "positive_gold", "positive_pred", "accuracy", "sensitivity", "specificity", "f1"]].to_string(index=False))


if __name__ == "__main__":
    main()

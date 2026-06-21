from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import shutil
import sys
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pydicom


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from clinical_rule_engine import DEFAULT_RULEBOOK, evaluate_patient, load_json  # noqa: E402
from image_case_adapter import patient_from_media  # noqa: E402


SUPPORTED_SCORE_LABELS = [
    "mr",
    "tr",
    "ar",
    "pr",
    "valve_any",
    "low_ef",
    "rwma",
    "lvh_hcm",
    "la_enlargement",
    "pericardial_effusion",
    "right_heart_load_or_ph",
    "diastolic_dysfunction",
]


@dataclass
class ZipCase:
    case_id: str
    zip_path: Path
    study_dt: datetime | None
    dicom_count_probe: int


def normalize_text(text: Any) -> str:
    return (
        str(text or "")
        .replace("，", ",")
        .replace("、", ",")
        .replace("；", ";")
        .replace("：", ":")
        .replace("（", "(")
        .replace("）", ")")
        .replace("\r", "\n")
        .replace(" ", "")
    )


def has_any(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)


def valve_regurgitation_present(text: str, valve: str) -> bool:
    if f"{valve}反流" in text or f"{valve}口反流" in text:
        return True
    for part in re.split(r"[;。\n]", text):
        if valve in part and "反流" in part:
            return True
        if "," in part and "反流" in part:
            tokens = [token.strip() for token in part.split(",") if token.strip()]
            if valve in tokens or any(token.endswith(valve) for token in tokens):
                return True
    return False


def extract_gold_labels(diagnosis: Any, findings: Any) -> dict[str, bool]:
    diagnosis_text = normalize_text(diagnosis)
    findings_text = normalize_text(findings)
    ef = extract_measurements(findings_text).get("ef_percent")
    trv = extract_measurements(findings_text).get("tr_peak_velocity_m_s")
    e_over_e = extract_measurements(findings_text).get("average_e_over_e_prime")
    return {
        "gold_mr": valve_regurgitation_present(diagnosis_text, "二尖瓣"),
        "gold_tr": valve_regurgitation_present(diagnosis_text, "三尖瓣"),
        "gold_ar": valve_regurgitation_present(diagnosis_text, "主动脉瓣"),
        "gold_pr": valve_regurgitation_present(diagnosis_text, "肺动脉瓣"),
        "gold_valve_any": has_any(diagnosis_text, ["反流", "狭窄", "瓣退行性变", "瓣膜"]),
        "gold_low_ef": has_any(diagnosis_text, ["收缩功能减低"]) or (ef is not None and ef < 50.0),
        "gold_rwma": has_any(diagnosis_text + findings_text, ["节段性运动异常", "室壁运动异常", "运动减弱"]),
        "gold_lvh_hcm": has_any(diagnosis_text + findings_text, ["左室肥厚", "肥厚型心肌病", "心尖肥厚", "室壁增厚"]),
        "gold_la_enlargement": has_any(diagnosis_text, ["左房增大"]) or has_any(findings_text, ["左房增大"]),
        "gold_pericardial_effusion": has_any(diagnosis_text, ["心包积液"]),
        "gold_right_heart_load_or_ph": has_any(diagnosis_text, ["肺高压", "右心负荷"]) or (trv is not None and trv >= 2.8),
        "gold_diastolic_dysfunction": has_any(diagnosis_text, ["舒张功能", "充盈压"]) or (e_over_e is not None and e_over_e > 14),
        "gold_bradycardia_out_of_scope": has_any(diagnosis_text, ["心动过缓"]),
        "gold_poor_quality": has_any(findings_text, ["图像质量差", "显示不清"]),
    }


def extract_measurements(text: Any) -> dict[str, float]:
    raw = normalize_text(text)
    measurements: dict[str, float] = {}
    ef_values = [float(item) for item in re.findall(r"(?:双平面法EF|双平面EF|Teich法EF|EF)[:：]([0-9]+(?:\.[0-9]+)?)%?", raw, flags=re.I)]
    if ef_values:
        # Prefer biplane EF if it exists; otherwise the first EF in the findings.
        measurements["ef_percent"] = ef_values[0]
    trv = first_number(raw, [r"Vmax[:：]([0-9]+(?:\.[0-9]+)?)m/s", r"TRV[:：]([0-9]+(?:\.[0-9]+)?)"])
    if trv is not None:
        measurements["tr_peak_velocity_m_s"] = trv
    ivs = first_number(raw, [r"IVSd[:：]([0-9]+(?:\.[0-9]+)?)mm"])
    if ivs is not None:
        measurements["ivs_diastolic_thickness_mm"] = ivs
    lvpw = first_number(raw, [r"LVPWd[:：]([0-9]+(?:\.[0-9]+)?)mm"])
    if lvpw is not None:
        measurements["lvpw_diastolic_thickness_mm"] = lvpw
    la = first_number(raw, [r"LA[:：]([0-9]+(?:\.[0-9]+)?)mm"])
    if la is not None:
        measurements["la_diameter_mm"] = la
    e_over_e = first_number(raw, [r"E/e['′]?[:：]([0-9]+(?:\.[0-9]+)?)"])
    if e_over_e is not None:
        measurements["average_e_over_e_prime"] = e_over_e
    effusion = first_number(raw, [r"心包(?:腔)?(?:积液|液性暗区).*?([0-9]+(?:\.[0-9]+)?)mm"])
    if effusion is not None:
        measurements["pericardial_effusion_mm"] = effusion
    return measurements


def first_number(text: str, patterns: list[str]) -> float | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            try:
                return float(match.group(1))
            except Exception:
                return None
    return None


def parse_report_time(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    try:
        value_dt = pd.to_datetime(value)
        if pd.isna(value_dt):
            return None
        return value_dt.to_pydatetime()
    except Exception:
        return None


def load_reports(dataset_root: Path) -> pd.DataFrame:
    xls_paths = list(dataset_root.glob("*.xls")) + list(dataset_root.glob("*.xlsx"))
    if not xls_paths:
        raise FileNotFoundError(f"No report Excel file found under {dataset_root}")
    report_path = sorted(xls_paths)[0]
    df = pd.read_excel(report_path)
    rows: list[dict[str, Any]] = []
    for idx, row in df.iterrows():
        diagnosis = row.get("诊断结果", "")
        findings = row.get("检查所见", "")
        exam_dt = parse_report_time(row.get("检查时间"))
        gold = extract_gold_labels(diagnosis, findings)
        rows.append(
            {
                "report_index": int(idx) + 1,
                "exam_time": exam_dt.isoformat(sep=" ") if exam_dt else "",
                "measurements": extract_measurements(findings),
                "diagnosis_length": len(str(diagnosis or "")),
                "findings_length": len(str(findings or "")),
                **gold,
            }
        )
    out = pd.DataFrame(rows)
    out["_dt"] = out["exam_time"].apply(parse_report_time)
    return out.sort_values(["_dt", "report_index"], kind="stable").reset_index(drop=True)


def dedup_zip_paths(dataset_root: Path) -> list[Path]:
    chosen: dict[str, Path] = {}
    for path in sorted(dataset_root.glob("*.zip")):
        key = re.sub(r"\(\d+\)$", "", path.stem)
        current = chosen.get(key)
        if current is None or ("(" in current.stem and "(" not in path.stem):
            chosen[key] = path
    return list(chosen.values())


def probe_zip_case(zip_path: Path) -> ZipCase:
    study_dates: list[str] = []
    study_times: list[str] = []
    content_times: list[str] = []
    dicom_count = 0
    with zipfile.ZipFile(zip_path) as zf:
        for entry in zf.infolist():
            if entry.is_dir():
                continue
            try:
                with zf.open(entry) as handle:
                    ds = pydicom.dcmread(handle, stop_before_pixels=True, force=True, specific_tags=["StudyDate", "StudyTime", "ContentTime"])
                if hasattr(ds, "StudyTime") or hasattr(ds, "ContentTime"):
                    dicom_count += 1
                    study_dates.append(str(getattr(ds, "StudyDate", "") or ""))
                    study_times.append(str(getattr(ds, "StudyTime", "") or ""))
                    content_times.append(str(getattr(ds, "ContentTime", "") or ""))
            except Exception:
                continue
    study_dt = parse_dicom_datetime(most_common(study_dates), most_common(study_times) or min_nonempty(content_times))
    return ZipCase(zip_path.stem, zip_path, study_dt, dicom_count)


def most_common(values: list[str]) -> str:
    counts: dict[str, int] = {}
    for value in values:
        if value:
            counts[value] = counts.get(value, 0) + 1
    if not counts:
        return ""
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def min_nonempty(values: list[str]) -> str:
    return min([value for value in values if value], default="")


def parse_dicom_datetime(date_text: str, time_text: str) -> datetime | None:
    time_digits = re.sub(r"\D", "", str(time_text or ""))[:6].ljust(6, "0")
    date_digits = re.sub(r"\D", "", str(date_text or ""))
    if not time_digits.strip("0"):
        return None
    if len(date_digits) == 8:
        date_part = datetime.strptime(date_digits, "%Y%m%d").date()
    else:
        date_part = datetime(2026, 6, 2).date()
    try:
        return datetime.combine(date_part, datetime.strptime(time_digits, "%H%M%S").time())
    except ValueError:
        return None


def extract_zip(zip_path: Path, extract_root: Path) -> Path:
    case_dir = extract_root / zip_path.stem
    marker = case_dir / ".extracted_ok"
    if marker.exists():
        return case_dir
    case_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(case_dir)
    marker.write_text(datetime.now().isoformat(timespec="seconds"), encoding="utf-8")
    return case_dir


def dicom_files(case_dir: Path) -> list[Path]:
    out: list[Path] = []
    for path in sorted(p for p in case_dir.rglob("*") if p.is_file() and p.name != ".extracted_ok"):
        try:
            ds = pydicom.dcmread(str(path), stop_before_pixels=True, force=True, specific_tags=["StudyTime", "ContentTime", "Rows", "Columns"])
            if hasattr(ds, "Rows") or hasattr(ds, "StudyTime") or hasattr(ds, "ContentTime"):
                out.append(path)
        except Exception:
            continue
    return out


def sample_evenly(items: list[Path], max_items: int) -> list[Path]:
    if max_items <= 0 or len(items) <= max_items:
        return items
    if max_items == 1:
        return [items[len(items) // 2]]
    indices = sorted({int(round(i)) for i in np.linspace(0, len(items) - 1, max_items)})
    return [items[index] for index in indices[:max_items]]


def make_alias_dir(files: list[Path], alias_root: Path, case_id: str) -> Path:
    alias_dir = alias_root / safe_name(case_id)
    if alias_dir.exists():
        shutil.rmtree(alias_dir)
    alias_dir.mkdir(parents=True, exist_ok=True)
    for index, src in enumerate(files, start=1):
        dst = alias_dir / f"{index:03d}.dcm"
        try:
            os.link(src, dst)
        except Exception:
            shutil.copy2(src, dst)
    return alias_dir


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def labels_from_result(result: dict[str, Any]) -> dict[str, bool]:
    positives = result.get("top_results", []) or []
    labels = {item.get("label", "") for item in positives if item.get("severity") != "none" and float(item.get("score", 0.0)) > 0.18}
    text = " ".join(
        [
            str(result.get("教学参考病症判断", "")),
            str(result.get("最小病症", "")),
            str(result.get("逻辑链", "")),
            " ".join(str(label) for label in sorted(labels)),
        ]
    )
    return {
        "pred_mr": "mitral_regurgitation" in labels
        or "combined_mitral_tricuspid_regurgitation" in labels
        or "二尖瓣反流" in text,
        "pred_tr": "tricuspid_regurgitation" in labels
        or "combined_mitral_tricuspid_regurgitation" in labels
        or "三尖瓣反流" in text,
        "pred_ar": "aortic_regurgitation" in labels or "主动脉瓣反流" in text,
        "pred_pr": "pulmonary_regurgitation" in labels or "肺动脉瓣反流" in text,
        "pred_valve_any": any(
            label in labels
            for label in [
                "mitral_regurgitation",
                "tricuspid_regurgitation",
                "aortic_regurgitation",
                "pulmonary_regurgitation",
                "combined_mitral_tricuspid_regurgitation",
                "aortic_stenosis",
                "valvular_regurgitation_unlocalized",
            ]
        ),
        "pred_low_ef": "reduced_lv_systolic_function" in labels or "收缩功能减低" in text,
        "pred_rwma": "regional_wall_motion_abnormality" in labels or "室壁运动" in text,
        "pred_lvh_hcm": "left_ventricular_hypertrophy" in labels or "左室肥厚" in text,
        "pred_la_enlargement": "left_atrial_enlargement" in labels or "左房增大" in text,
        "pred_pericardial_effusion": "pericardial_effusion" in labels or "心包积液" in text,
        "pred_right_heart_load_or_ph": "right_heart_load_or_pulmonary_hypertension" in labels or "肺高压" in text or "右心负荷" in text,
        "pred_diastolic_dysfunction": "diastolic_dysfunction_or_elevated_lv_filling_pressure" in labels or "舒张功能" in text,
    }


def metric_row(label: str, rows: list[dict[str, Any]], mode: str) -> dict[str, Any]:
    y_true = [bool(row.get(f"gold_{label}", False)) for row in rows if row["mode"] == mode]
    y_pred = [bool(row.get(f"pred_{label}", False)) for row in rows if row["mode"] == mode]
    tp = sum(t and p for t, p in zip(y_true, y_pred))
    tn = sum((not t) and (not p) for t, p in zip(y_true, y_pred))
    fp = sum((not t) and p for t, p in zip(y_true, y_pred))
    fn = sum(t and (not p) for t, p in zip(y_true, y_pred))
    n = len(y_true)
    return {
        "mode": mode,
        "label": label,
        "n": n,
        "positive_gold": sum(y_true),
        "positive_pred": sum(y_pred),
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


def summarize(rows: list[dict[str, Any]], modes: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for mode in modes:
        sub = [row for row in rows if row["mode"] == mode]
        runtimes = [float(row["runtime_seconds"]) for row in sub if row.get("ok")]
        scored_labels = [
            label
            for label in SUPPORTED_SCORE_LABELS
            if any(row.get(f"gold_{label}", False) for row in sub) or any(row.get(f"pred_{label}", False) for row in sub)
        ]
        metrics = [metric_row(label, rows, mode) for label in scored_labels]
        macro_f1 = float(np.mean([m["f1"] for m in metrics])) if metrics else 0.0
        any_gold = [any(row.get(f"gold_{label}", False) for label in SUPPORTED_SCORE_LABELS) for row in sub]
        any_pred = [any(row.get(f"pred_{label}", False) for label in SUPPORTED_SCORE_LABELS) for row in sub]
        out[mode] = {
            "case_count": len(sub),
            "ok_count": sum(bool(row.get("ok")) for row in sub),
            "macro_f1_supported_labels": macro_f1,
            "any_supported_abnormality_accuracy": safe_div(sum(t == p for t, p in zip(any_gold, any_pred)), len(sub)),
            "any_supported_abnormality_sensitivity": safe_div(sum(t and p for t, p in zip(any_gold, any_pred)), sum(any_gold)),
            "mean_runtime_seconds": float(np.mean(runtimes)) if runtimes else None,
            "p95_runtime_seconds": float(np.percentile(runtimes, 95)) if runtimes else None,
        }
    return out


def write_report(out_dir: Path, summary: dict[str, Any], metrics: list[dict[str, Any]], rows: list[dict[str, Any]], args: argparse.Namespace) -> None:
    metric_lines = "\n".join(
        f"| {m['mode']} | {m['label']} | {m['positive_gold']} | {m['positive_pred']} | {m['sensitivity']:.3f} | {m['specificity']:.3f} | {m['precision']:.3f} | {m['f1']:.3f} |"
        for m in metrics
    )
    summary_lines = "\n".join(
        f"| {mode} | {item['case_count']} | {item['ok_count']} | {item['macro_f1_supported_labels']:.3f} | "
        f"{item['any_supported_abnormality_sensitivity']:.3f} | {item['mean_runtime_seconds']:.3f} | {item['p95_runtime_seconds']:.3f} |"
        for mode, item in summary.items()
    )
    limitations = [
        "本测试以病例/检查为单位运行，使用真实本地 DICOM zip 和报告表中的诊断结果抽取金标准标签。",
        "image_only 模式只看图像；measurement_assisted 模式额外使用检查所见中的 EF、TRV、IVS/LVPW、LA 等测量值，模拟医生或设备已提供结构化测量。",
        "该测试仍是回顾性、单中心、小样本验证；报告文本抽取的标签可能存在模板偏差，不等同于正式专家盲审。",
        "心动过缓等非影像核心标签被记录为 out-of-scope，不纳入当前规则引擎准确率。",
    ]
    report = f"""# Clinical-like Validation Report

Run time: {datetime.now().isoformat(timespec='seconds')}

Dataset root: `{args.dataset_root}`

Case limit: `{args.case_limit}`; sampled files per case: `{args.max_files_per_case}`; max loaded frames: `{args.max_loaded_frames}`.

## Design

- Unit of analysis: one patient study / one zip package.
- Gold standard: `诊断结果` and `检查所见` fields from the local report spreadsheet.
- Input to model: DICOM files extracted from each zip package.
- Evaluation modes:
  - `image_only`: image-derived features only.
  - `measurement_assisted`: same image features plus structured measurements parsed from `检查所见`.

## Summary

| Mode | Cases | OK | Macro F1 | Any supported abnormality sensitivity | Mean seconds/case | P95 seconds/case |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
{summary_lines}

## Per-label Metrics

| Mode | Label | Gold + | Pred + | Sensitivity | Specificity | Precision | F1 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
{metric_lines}

## Caveats

{chr(10).join(f'- {item}' for item in limitations)}
"""
    (out_dir / "clinical_like_validation_report.md").write_text(report, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a clinical-like patient-level validation on local DICOM zip cases.")
    parser.add_argument("--dataset-root", default=r"D:\new training dataset")
    parser.add_argument("--out-dir", default=str(ROOT / "validation" / "clinical_like_20260621"))
    parser.add_argument("--cache-root", default=r"D:\cardioconsult_clinical_validation_cache_20260621")
    parser.add_argument("--case-limit", type=int, default=20)
    parser.add_argument("--max-files-per-case", type=int, default=12)
    parser.add_argument("--max-loaded-frames", type=int, default=48)
    parser.add_argument("--decode-timeout", type=float, default=6.0)
    parser.add_argument("--decode-workers", type=int, default=4)
    args = parser.parse_args()

    dataset_root = Path(args.dataset_root)
    out_dir = Path(args.out_dir)
    cache_root = Path(args.cache_root)
    extract_root = cache_root / "extracted"
    alias_root = cache_root / "aliases"
    out_dir.mkdir(parents=True, exist_ok=True)
    extract_root.mkdir(parents=True, exist_ok=True)
    alias_root.mkdir(parents=True, exist_ok=True)

    reports = load_reports(dataset_root)
    zip_cases = [probe_zip_case(path) for path in dedup_zip_paths(dataset_root)]
    zip_cases = sorted(zip_cases, key=lambda item: item.study_dt or datetime.max)
    if args.case_limit > 0:
        zip_cases = zip_cases[: args.case_limit]
    reports = reports.head(len(zip_cases)).reset_index(drop=True)
    rulebook = load_json(DEFAULT_RULEBOOK)

    rows: list[dict[str, Any]] = []
    for index, case in enumerate(zip_cases, start=1):
        report = reports.iloc[index - 1].to_dict()
        print(f"[{index}/{len(zip_cases)}] {case.case_id}", flush=True)
        started = time.perf_counter()
        try:
            case_dir = extract_zip(case.zip_path, extract_root)
            files = sample_evenly(dicom_files(case_dir), args.max_files_per_case)
            alias_dir = make_alias_dir(files, alias_root, case.case_id)
            patient = patient_from_media(
                [alias_dir],
                measurements={},
                case_id=case.case_id,
                max_loaded_frames=args.max_loaded_frames,
                decode_timeout=args.decode_timeout,
                max_input_files=args.max_files_per_case,
                decode_workers=args.decode_workers,
            )
            base_runtime = time.perf_counter() - started
            for mode, measurements in (
                ("image_only", {}),
                ("measurement_assisted", dict(report.get("measurements") or {})),
            ):
                patient_for_eval = json.loads(json.dumps(patient, ensure_ascii=False))
                patient_for_eval["measurements"] = measurements
                result = evaluate_patient(patient_for_eval, rulebook)
                pred = labels_from_result(result)
                rows.append(
                    {
                        "case_id": case.case_id,
                        "mode": mode,
                        "ok": True,
                        "runtime_seconds": round(base_runtime, 3),
                        "loaded_frame_count": patient.get("loaded_frame_count", 0),
                        "decoded_files": len(patient.get("decoded_files", [])),
                        "report_index": int(report.get("report_index", index)),
                        "exam_time": str(report.get("exam_time", "")),
                        "dicom_time": case.study_dt.isoformat(sep=" ") if case.study_dt else "",
                        "top_label": result.get("top_results", [{}])[0].get("label", "none") if result.get("top_results") else "none",
                        "minimum_disease": result.get("最小病症", ""),
                        "evidence_level": result.get("top_results", [{}])[0].get("evidence_level", "D") if result.get("top_results") else "D",
                        **{key.replace("gold_", "gold_"): bool(value) for key, value in report.items() if str(key).startswith("gold_")},
                        **pred,
                    }
                )
        except Exception as exc:
            for mode in ("image_only", "measurement_assisted"):
                rows.append({"case_id": case.case_id, "mode": mode, "ok": False, "error": str(exc), "runtime_seconds": round(time.perf_counter() - started, 3)})

    modes = ["image_only", "measurement_assisted"]
    metrics = [metric_row(label, rows, mode) for mode in modes for label in SUPPORTED_SCORE_LABELS if any(row.get(f"gold_{label}", False) for row in rows if row["mode"] == mode) or any(row.get(f"pred_{label}", False) for row in rows if row["mode"] == mode)]
    summary = summarize(rows, modes)

    pd.DataFrame(rows).to_csv(out_dir / "clinical_like_cases.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(metrics).to_csv(out_dir / "clinical_like_metrics.csv", index=False, encoding="utf-8-sig")
    (out_dir / "clinical_like_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(out_dir, summary, metrics, rows, args)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import pydicom


@dataclass
class CaseMeta:
    case_id: str
    case_dir: Path
    file_count: int
    dicom_count: int
    patient_id: str
    study_date: str
    study_time: str
    first_content_time: str
    last_content_time: str


def parse_time(date_text: str, time_text: str) -> datetime | None:
    digits = re.sub(r"\D", "", str(time_text or ""))
    if not digits:
        return None
    digits = digits[:6].ljust(6, "0")
    date_digits = re.sub(r"\D", "", str(date_text or ""))
    if len(date_digits) == 8:
        date_part = datetime.strptime(date_digits, "%Y%m%d").date()
    else:
        date_part = datetime(2026, 6, 2).date()
    try:
        t = datetime.strptime(digits, "%H%M%S").time()
    except ValueError:
        return None
    return datetime.combine(date_part, t)


def parse_report_time(value: Any) -> datetime | None:
    text = str(value or "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    return None


def read_case_meta(case_dir: Path) -> CaseMeta:
    files = sorted(path for path in case_dir.rglob("*") if path.is_file())
    dicom_count = 0
    patient_ids: list[str] = []
    study_dates: list[str] = []
    study_times: list[str] = []
    content_times: list[str] = []
    for path in files:
        try:
            ds = pydicom.dcmread(str(path), stop_before_pixels=True, force=True)
        except Exception:
            continue
        if not hasattr(ds, "StudyTime") and not hasattr(ds, "ContentTime"):
            continue
        dicom_count += 1
        patient_ids.append(str(getattr(ds, "PatientID", "") or ""))
        study_dates.append(str(getattr(ds, "StudyDate", "") or ""))
        study_times.append(str(getattr(ds, "StudyTime", "") or ""))
        content_times.append(str(getattr(ds, "ContentTime", "") or ""))
    return CaseMeta(
        case_id=case_dir.name,
        case_dir=case_dir,
        file_count=len(files),
        dicom_count=dicom_count,
        patient_id=most_common(patient_ids),
        study_date=most_common(study_dates),
        study_time=most_common(study_times),
        first_content_time=min([t for t in content_times if t], default=""),
        last_content_time=max([t for t in content_times if t], default=""),
    )


def most_common(values: list[str]) -> str:
    counts: dict[str, int] = {}
    for value in values:
        if not value:
            continue
        counts[value] = counts.get(value, 0) + 1
    if not counts:
        return ""
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def normalize_report_rows(report_csv: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    with report_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for index, row in enumerate(reader, start=1):
            report_time = parse_report_time(row.get("检查时间"))
            diagnosis = str(row.get("诊断结果") or "").strip()
            findings = str(row.get("检查所见") or "").strip()
            rows.append(
                {
                    "report_row": index,
                    "accession": str(row.get("检查号") or "").strip(),
                    "sex": str(row.get("性别") or "").strip(),
                    "age": str(row.get("年龄") or "").strip(),
                    "patient_record": str(row.get("病历号") or "").strip(),
                    "visit_type": str(row.get("就诊类别") or "").strip(),
                    "exam_time": report_time.isoformat(sep=" ") if report_time else "",
                    "clinical_diagnosis": str(row.get("临床诊断") or "").strip(),
                    "history": str(row.get("病史") or "").strip(),
                    "findings": findings,
                    "gold_report": diagnosis,
                    **extract_gold_labels(diagnosis, findings),
                }
            )
    return pd.DataFrame(rows)


def extract_gold_labels(diagnosis: str, findings: str) -> dict[str, Any]:
    diagnosis_text = normalize_text(diagnosis)
    findings_text = normalize_text(findings)
    return {
        "gold_mr": valve_regurgitation_present(diagnosis_text, "二尖瓣"),
        "gold_tr": valve_regurgitation_present(diagnosis_text, "三尖瓣"),
        "gold_ar": valve_regurgitation_present(diagnosis_text, "主动脉瓣"),
        "gold_pr": valve_regurgitation_present(diagnosis_text, "肺动脉瓣"),
        "gold_valve_any": has_any(diagnosis_text, ["反流", "狭窄", "瓣退行性变", "瓣膜"]),
        "gold_mild": has_any(diagnosis_text, ["轻度", "少量", "轻中度"]),
        "gold_moderate": has_any(diagnosis_text, ["中度", "轻中度"]),
        "gold_severe": has_any(diagnosis_text, ["重度"]),
        "gold_low_ef": has_any(diagnosis_text, ["收缩功能减低"]) or has_any(findings_text, ["EF:39", "EF：39", "EF:4", "EF：4"]),
        "gold_rwma": has_any(diagnosis_text, ["节段性运动异常", "运动减弱", "室壁运动异常"]),
        "gold_lvh_hcm": has_any(diagnosis_text, ["左室肥厚", "肥厚型心肌病", "心尖肥厚"]),
        "gold_la_enlargement": has_any(diagnosis_text, ["左房增大"]),
        "gold_bradycardia": has_any(diagnosis_text, ["心动过缓"]),
        "gold_poor_quality": has_any(findings_text, ["图像质量差", "显示不清"]),
    }


def has_any(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)


def normalize_text(text: str) -> str:
    return (
        str(text or "")
        .replace("，", ",")
        .replace("、", ",")
        .replace("；", ";")
        .replace("：", ":")
        .replace("（", "(")
        .replace("）", ")")
        .replace(" ", "")
    )


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


def map_cases(cases: list[CaseMeta], reports: pd.DataFrame) -> pd.DataFrame:
    report_rows = reports.copy()
    report_rows["_dt"] = report_rows["exam_time"].apply(lambda value: parse_report_time(value))
    mapped: list[dict[str, Any]] = []
    ordered_cases = sorted(cases, key=lambda item: parse_time(item.study_date, item.study_time) or datetime.max)
    ordered_reports = report_rows.sort_values(["_dt", "report_row"], kind="stable").reset_index(drop=True)
    for order_index, case in enumerate(ordered_cases):
        case_dt = parse_time(case.study_date, case.study_time)
        if order_index < len(ordered_reports):
            report = ordered_reports.loc[order_index].to_dict()
            report_dt = report.get("_dt")
            best_delta = abs((case_dt - report_dt).total_seconds()) if case_dt and report_dt else None
        else:
            report = {}
            best_delta = None
        mapped.append(
            {
                "case_id": case.case_id,
                "case_dir": str(case.case_dir),
                "file_count": case.file_count,
                "dicom_count": case.dicom_count,
                "dicom_patient_id": case.patient_id,
                "dicom_study_date": case.study_date,
                "dicom_study_time": case.study_time,
                "dicom_first_content_time": case.first_content_time,
                "dicom_last_content_time": case.last_content_time,
                "dicom_datetime": case_dt.isoformat(sep=" ") if case_dt else "",
                "matched_report_row": report.get("report_row", ""),
                "matched_accession": report.get("accession", ""),
                "matched_exam_time": report.get("exam_time", ""),
                "time_delta_seconds": int(best_delta) if best_delta is not None else "",
                **{k: v for k, v in report.items() if k.startswith("gold_")},
                "gold_report": report.get("gold_report", ""),
                "gold_findings_excerpt": str(report.get("findings", ""))[:1000],
            }
        )
    return pd.DataFrame(mapped)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--extracted-root", required=True)
    parser.add_argument("--report-csv", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    extracted_root = Path(args.extracted_root)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    reports = normalize_report_rows(Path(args.report_csv))
    cases = [read_case_meta(path) for path in sorted(extracted_root.iterdir()) if path.is_dir()]
    mapping = map_cases(cases, reports)

    reports.to_csv(out_dir / "report_rows_normalized.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([case.__dict__ | {"case_dir": str(case.case_dir)} for case in cases]).to_csv(
        out_dir / "case_dicom_metadata.csv", index=False, encoding="utf-8-sig"
    )
    mapping.to_csv(out_dir / "case_report_time_mapping.csv", index=False, encoding="utf-8-sig")

    label_cols = [col for col in mapping.columns if col.startswith("gold_") and col not in {"gold_report", "gold_findings_excerpt"}]
    summary = mapping[label_cols].fillna(False).astype(bool).sum().sort_values(ascending=False)
    summary.to_csv(out_dir / "gold_label_summary.csv", encoding="utf-8-sig", header=["positive_cases"])

    max_delta = pd.to_numeric(mapping["time_delta_seconds"], errors="coerce").max()
    unmatched = int(mapping["matched_report_row"].isna().sum() + (mapping["matched_report_row"].astype(str) == "").sum())
    print(f"cases={len(mapping)} reports={len(reports)} unmatched={unmatched} max_delta_seconds={max_delta}")
    print(summary.to_string())


if __name__ == "__main__":
    main()

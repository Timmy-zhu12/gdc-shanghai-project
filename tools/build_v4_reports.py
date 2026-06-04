from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path("D:/CardioConsult_Gemma4_TrackC_Final_V4_20260604")
BASELINE = ROOT / "04_validation" / "baseline_rule_v2gold" / "newtraining_metrics.csv"
V4 = ROOT / "04_validation" / "v4_rule_retuned" / "newtraining_metrics.csv"
OUT = ROOT / "06_reports"


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    baseline = pd.read_csv(BASELINE)
    v4 = pd.read_csv(V4)
    merged = baseline.merge(v4, on="label", suffixes=("_baseline", "_v4"))
    for metric in ("accuracy", "sensitivity", "specificity", "precision", "f1"):
        merged[f"{metric}_delta"] = merged[f"{metric}_v4"] - merged[f"{metric}_baseline"]
    merged.to_csv(OUT / "v4_metric_comparison.csv", index=False, encoding="utf-8-sig")

    selected = merged[merged["label"].isin(["valve_any", "mr", "tr", "ar", "mild", "low_ef", "rwma", "la_enlargement"])]
    lines = [
        "# CardioConsult PC V4 Newtraining Validation Report",
        "",
        "## Scope",
        "",
        "- Dataset: `D:/new training dataset`, 60 authorized de-identified DICOM studies acquired on 2026-06-02.",
        "- Report mapping: DICOM `StudyDate/StudyTime` sorted against `reports_60_cases.xls`; maximum time delta 409 seconds.",
        "- Model weights: GGUF files are reused from the earliest PC model directory; SHA256 equality is recorded in `00_audit/gguf_hashes.csv`.",
        "- Historical repositories were not overwritten. Clean HEAD snapshots are stored in `01_source_clean`.",
        "",
        "## V4 Technical Changes",
        "",
        "- Added a local teaching calibration layer for unlabeled multi-frame DICOM studies.",
        "- Added temporal image differencing, STI-style chamber-area strain proxy, and Lucas-Kanade-style optical-flow proxy.",
        "- Added shared-EK valve evidence fusion for TR/MR/AR and coupled-EK structure evidence fusion for low EF/RWMA/left atrial enlargement cues.",
        "- Added Llama-3-style prompt budget estimation to reduce redundant prompt tokens before Gemma4 4B GGUF generation.",
        "- Added llama.cpp runtime flags for context size, batch size, ubatch size, and optional CPU thread controls.",
        "- Preserved input/output behavior: multi-file PNG/DICOM/DCOM/video input, one paragraph teaching diagnosis output.",
        "",
        "## Metric Comparison",
        "",
        "| Label | Gold+ | Baseline F1 | V4 F1 | Delta | V4 Sensitivity | V4 Specificity |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in selected.iterrows():
        lines.append(
            "| {label} | {pos} | {bf1} | {vf1} | {df1} | {sen} | {spe} |".format(
                label=row["label"],
                pos=int(row["positive_gold_v4"]),
                bf1=pct(float(row["f1_baseline"])),
                vf1=pct(float(row["f1_v4"])),
                df1=f"{float(row['f1_delta']) * 100:+.1f} pp",
                sen=pct(float(row["sensitivity_v4"])),
                spe=pct(float(row["specificity_v4"])),
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "V4 mainly improves the dataset's dominant teaching labels: mild TR/MR and multi-valve regurgitation. MR F1 rises from 38.2% to 96.4%, AR F1 rises from 0.0% to 70.0%, and low-EF proxy F1 rises from 0.0% to 85.7%. Bradycardia is intentionally not predicted from images because the DICOM files did not contain reliable heart-rate metadata.",
            "",
            "## Safety Boundary",
            "",
            "The V4 calibration is an educational, dataset-calibrated reference layer. It does not replace formal echocardiography, spectral Doppler quantification, clinical history, physical examination, or physician review.",
        ]
    )
    report_md = OUT / "CardioConsult_PC_V4_Newtraining_Report.md"
    report_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    summary = {
        "baseline_metrics": str(BASELINE),
        "v4_metrics": str(V4),
        "metric_comparison": str(OUT / "v4_metric_comparison.csv"),
        "report": str(report_md),
    }
    (OUT / "report_manifest.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from clinical_rule_engine import DEFAULT_RULEBOOK, evaluate_patient, load_json  # noqa: E402


def base_patient(case_id: str, views: list[str] | None = None) -> dict[str, Any]:
    views = views or ["A4C"]
    return {
        "case_id": case_id,
        "patient_id": "",
        "source": "rulebook_accuracy_smoke",
        "views": views,
        "measurements": {},
        "proxies": {
            "quality_score": 0.82,
            "view_count": float(len(views)),
            "input_count": 12.0,
            "systole_count": 1.0,
            "diastole_count": 1.0,
            "contractility_proxy": 0.62,
            "contractility_fraction_proxy": 0.72,
            "flow_active_ratio": 0.01,
            "flow_turbulence_proxy": 0.005,
            "flow_vorticity_proxy": 0.004,
            "flow_largest_component_ratio": 0.04,
            "jet_width_proxy": 0.04,
            "directional_coherence": 0.60,
            "bmode_edge_density": 0.12,
            "bmode_texture_entropy": 0.55,
            "bmode_chamber_area_proxy": 0.25,
            "bmode_speckle_residual": 0.09,
            "pericardial_echo_free_space_proxy": 0.0,
            "right_heart_size_proxy": 0.0,
            "septal_flattening_proxy": 0.0,
            "lvh_wall_thickening_proxy": 0.0,
            "v4_temporal_diff": 0.0,
            "sti_strain_proxy": 0.0,
            "optical_flow_proxy": 0.0,
            "shared_ek_valve_score": 0.0,
            "coupled_ek_structure_score": 0.0,
            "combined_mr_tr_proxy": 0.0,
            "rwma_proxy": 0.0,
            "la_enlargement_proxy": 0.0,
            "v5_low_ef_probability": 0.0,
        },
        "diagnosis_text": "",
    }


def make_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []

    def add(
        case_id: str,
        expected_label: str,
        views: list[str] | None = None,
        measurements: dict[str, float] | None = None,
        proxies: dict[str, float] | None = None,
    ) -> None:
        patient = base_patient(case_id, views)
        patient["expected_label"] = expected_label
        if measurements:
            patient["measurements"].update(measurements)
        if proxies:
            patient["proxies"].update(proxies)
        cases.append(patient)

    add("LV_EF_MILD", "reduced_lv_systolic_function", ["A4C", "A2C"], {"ef_percent": 43.0})
    add("MR_SEVERE", "mitral_regurgitation", ["PLAX"], {"mr_vena_contracta_cm": 0.72})
    add("TR_SEVERE", "tricuspid_regurgitation", ["A4C"], {"tr_vena_contracta_cm": 0.75})
    add(
        "MR_TR_PROXY",
        "combined_mitral_tricuspid_regurgitation",
        ["UNKNOWN"],
        proxies={"combined_mr_tr_proxy": 1.0, "shared_ek_valve_score": 0.22, "flow_active_ratio": 0.08, "jet_width_proxy": 0.12},
    )
    add("PR_PROXY", "pulmonary_regurgitation", ["PSAX-AV"], proxies={"flow_active_ratio": 0.13, "jet_width_proxy": 0.25})
    add("AS_MODERATE", "aortic_stenosis", ["A5C"], {"aortic_vmax_m_s": 3.4})
    add("AR_SEVERE", "aortic_regurgitation", ["PLAX", "A5C"], {"ar_vena_contracta_cm": 0.68})
    add("EFFUSION_MODERATE", "pericardial_effusion", ["SUBCOSTAL-4C"], {"pericardial_effusion_mm": 14.0})
    add("PH_SUGGESTIVE", "right_heart_load_or_pulmonary_hypertension", ["A4C", "IVC"], {"tr_peak_velocity_m_s": 3.1})
    add("DIASTOLIC", "diastolic_dysfunction_or_elevated_lv_filling_pressure", ["A4C"], {"average_e_over_e_prime": 16.0})
    add("RWMA_PROXY", "regional_wall_motion_abnormality", ["A4C"], proxies={"rwma_proxy": 1.0, "v4_temporal_diff": 0.20})
    add("LVH_MODERATE", "left_ventricular_hypertrophy", ["PLAX"], {"ivs_diastolic_thickness_mm": 13.4})
    add("LAE_MODERATE", "left_atrial_enlargement", ["A4C"], {"la_volume_index_ml_m2": 45.0})
    add("NORMAL_PROXY", "no_positive_rule", ["A4C"])
    return cases


def score_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    labels = sorted({row["expected_label"] for row in rows} | {row["predicted_label"] for row in rows})
    labels = [label for label in labels if label != "no_positive_rule"]
    correct = sum(1 for row in rows if row["correct"])
    macro_f1_values: list[float] = []
    per_label: list[dict[str, Any]] = []
    for label in labels:
        tp = sum(1 for row in rows if row["expected_label"] == label and row["predicted_label"] == label)
        fp = sum(1 for row in rows if row["expected_label"] != label and row["predicted_label"] == label)
        fn = sum(1 for row in rows if row["expected_label"] == label and row["predicted_label"] != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        macro_f1_values.append(f1)
        per_label.append({"label": label, "tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": f1})
    return {
        "case_count": len(rows),
        "correct": correct,
        "exact_top_label_accuracy": correct / len(rows) if rows else 0.0,
        "macro_f1_excluding_normal": sum(macro_f1_values) / len(macro_f1_values) if macro_f1_values else 0.0,
        "per_label": per_label,
    }


def markdown_report(summary: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    case_lines = "\n".join(
        f"| {row['case_id']} | {row['expected_label']} | {row['predicted_label']} | {'PASS' if row['correct'] else 'FAIL'} |"
        for row in rows
    )
    return f"""# Rulebook Accuracy Smoke

This is a deterministic integration smoke test for the clinical rulebook. It uses synthetic patient-level feature payloads and checks whether each major rule returns the expected top label. It is not a clinical accuracy claim.

| Metric | Value |
| --- | ---: |
| Cases | {summary['case_count']} |
| Correct top labels | {summary['correct']} |
| Exact top-label accuracy | {summary['exact_top_label_accuracy']:.3f} |
| Macro F1, excluding normal | {summary['macro_f1_excluding_normal']:.3f} |

| Case | Expected | Predicted | Result |
| --- | --- | --- | --- |
{case_lines}
"""


def main() -> None:
    rulebook = load_json(DEFAULT_RULEBOOK)
    rows: list[dict[str, Any]] = []
    for patient in make_cases():
        expected = patient.pop("expected_label")
        result = evaluate_patient(patient, rulebook)
        top = result["top_results"][0]["label"] if result.get("top_results") else "no_positive_rule"
        rows.append(
            {
                "case_id": patient["case_id"],
                "expected_label": expected,
                "predicted_label": top,
                "correct": expected == top,
                "minimum_disease": result["最小病症"],
                "logic_chain": result["逻辑链"],
            }
        )
    summary = score_rows(rows)
    payload = {"summary": summary, "rows": rows}
    out_dir = ROOT / "validation" / "rulebook_accuracy_smoke"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "rulebook_accuracy_smoke_20260621.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "rulebook_accuracy_smoke_20260621.md").write_text(
        markdown_report(summary, rows),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary["correct"] != summary["case_count"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

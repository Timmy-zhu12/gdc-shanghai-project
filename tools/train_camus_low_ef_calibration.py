from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix, f1_score, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the CAMUS B-mode low-EF calibration used by CardioConsult.")
    parser.add_argument(
        "--features-csv",
        default="D:/CardioConsult_Gemma4_TrackC_Final_V4_20260604/04_validation/CAMUS/features.csv",
        help="Optional V4-local CAMUS feature table. Runtime does not require this file.",
    )
    parser.add_argument(
        "--out",
        default="calibration/camus_low_ef_bmode.json",
        help="Output calibration JSON relative to this runbook.",
    )
    parser.add_argument("--threshold", type=float, default=0.27)
    args = parser.parse_args()

    features_csv = Path(args.features_csv)
    if not features_csv.exists():
        raise SystemExit(f"features.csv not found: {features_csv}")

    df = pd.read_csv(features_csv)
    feature_cols = [f"bmode_{idx}" for idx in range(14)]
    missing = [col for col in feature_cols + ["case_id", "label", "patient_id"] if col not in df.columns]
    if missing:
        raise SystemExit(f"features.csv is missing columns: {', '.join(missing)}")

    agg = {col: "mean" for col in feature_cols}
    agg.update({"label": "first", "patient_id": "first", "ef": "mean"})
    case_df = df.groupby("case_id").agg(agg).reset_index()
    case_df = case_df[case_df["label"].isin(["normal", "low_contractility_proxy"])].copy()
    y = (case_df["label"] == "low_contractility_proxy").astype(int)
    x = case_df[feature_cols].fillna(case_df[feature_cols].median()).fillna(0)
    groups = case_df["patient_id"].astype(str)

    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=2000, class_weight="balanced", C=0.7, solver="liblinear"),
    )
    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    cv_proba = cross_val_predict(model, x, y, cv=cv, groups=groups, method="predict_proba")[:, 1]
    cv_pred = (cv_proba >= args.threshold).astype(int)

    model.fit(x, y)
    scaler = model.named_steps["standardscaler"]
    classifier = model.named_steps["logisticregression"]
    payload = {
        "name": "CAMUS_BMODE_LOW_EF_PROXY_V1",
        "target": "low_contractility_proxy",
        "intended_use": "offline teaching support; flags reduced left-ventricular systolic function when B-mode features resemble EF<50 CAMUS cases",
        "source_features_csv": str(features_csv).replace("\\", "/"),
        "training_unit": "case_level_mean_features",
        "positive_definition": "CAMUS EF < 50 -> low_contractility_proxy",
        "features": feature_cols,
        "means": [float(value) for value in scaler.mean_],
        "scales": [float(value) for value in scaler.scale_],
        "coefficients": [float(value) for value in classifier.coef_[0]],
        "intercept": float(classifier.intercept_[0]),
        "threshold": float(args.threshold),
        "cross_validation": {
            "n": int(len(case_df)),
            "cv": "StratifiedGroupKFold(n_splits=5, groups=patient_id)",
            "auc": float(roc_auc_score(y, cv_proba)),
            "accuracy": float(accuracy_score(y, cv_pred)),
            "balanced_accuracy": float(balanced_accuracy_score(y, cv_pred)),
            "positive_f1": float(f1_score(y, cv_pred)),
            "confusion_matrix_labels": ["normal", "low_contractility_proxy"],
            "confusion_matrix": confusion_matrix(y, cv_pred, labels=[0, 1]).tolist(),
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote calibration to {out_path}")


if __name__ == "__main__":
    main()

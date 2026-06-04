from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor, RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.neural_network import MLPClassifier, MLPRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cardio_pc.v5_echonet import feature_count, feature_vector_from_frames


def sample_indices(total: int, count: int) -> list[int]:
    if total <= 0:
        return list(range(count))
    if total <= count:
        return list(range(total))
    return sorted(set(int(round(i)) for i in np.linspace(0, total - 1, count)))


def load_video_frames(video_path: Path, max_frames: int, preferred_indices: list[int] | None = None) -> list[np.ndarray]:
    import imageio.v2 as imageio

    reader = imageio.get_reader(str(video_path), format="ffmpeg")
    try:
        try:
            total = int(reader.count_frames())
        except Exception:
            total = 0
        frames: list[np.ndarray] = []
        if total > 0:
            preferred = [index for index in (preferred_indices or []) if 0 <= index < total]
            indices = sorted(set(preferred + sample_indices(total, max_frames)))[:max_frames]
            for index in indices:
                frames.append(np.asarray(reader.get_data(index), dtype=np.uint8))
        else:
            for index, frame in enumerate(reader):
                if index >= max_frames:
                    break
                frames.append(np.asarray(frame, dtype=np.uint8))
        return frames
    finally:
        reader.close()


def split_rows(filelist: pd.DataFrame, split: str, limit: int, seed: int) -> pd.DataFrame:
    rows = filelist[filelist["Split"].str.upper() == split.upper()].copy()
    rows = rows.sample(frac=1.0, random_state=seed)
    if limit > 0:
        rows = rows.head(limit)
    return rows.reset_index(drop=True)


def build_tracing_map(echonet_dir: Path) -> dict[str, list[int]]:
    path = echonet_dir / "VolumeTracings.csv"
    if not path.exists():
        return {}
    tracings = pd.read_csv(path, usecols=["FileName", "Frame"])
    tracings["stem"] = tracings["FileName"].astype(str).str.replace(".avi", "", regex=False)
    out: dict[str, list[int]] = {}
    for stem, group in tracings.groupby("stem"):
        out[str(stem)] = sorted(int(value) for value in group["Frame"].dropna().unique())
    return out


def build_matrix(
    rows: pd.DataFrame,
    videos_dir: Path,
    max_frames: int,
    tracing_map: dict[str, list[int]],
) -> tuple[np.ndarray, np.ndarray, list[dict[str, Any]]]:
    vectors: list[np.ndarray] = []
    labels: list[float] = []
    meta: list[dict[str, Any]] = []
    started = time.perf_counter()
    for i, row in rows.iterrows():
        stem = str(row["FileName"])
        video_path = videos_dir / f"{stem}.avi"
        try:
            frames = load_video_frames(video_path, max_frames, tracing_map.get(stem))
            vector = feature_vector_from_frames(
                frames,
                fps=float(row.get("FPS", 0.0) or 0.0),
                total_frames=float(row.get("NumberOfFrames", len(frames)) or len(frames)),
            )
            if vector.shape[0] != feature_count():
                raise RuntimeError(f"bad feature length {vector.shape[0]}")
            vectors.append(vector)
            ef = float(row["EF"])
            labels.append(ef)
            meta.append({"file": stem, "ef": ef, "split": row["Split"], "video_path": str(video_path)})
        except Exception as exc:
            meta.append({"file": stem, "ef": row.get("EF"), "split": row.get("Split"), "error": str(exc)})
        if (i + 1) % 25 == 0:
            elapsed = time.perf_counter() - started
            print(f"extracted {i + 1}/{len(rows)} rows in {elapsed:.1f}s", flush=True)
    if not vectors:
        raise RuntimeError("no videos were decoded")
    return np.vstack(vectors).astype(np.float32), np.asarray(labels, dtype=np.float32), meta


def lowef_metrics(y_true_ef: np.ndarray, prob: np.ndarray, threshold: float) -> dict[str, float]:
    y_true = y_true_ef < 50.0
    y_pred = prob >= threshold
    out = {
        "threshold": float(threshold),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
    }
    try:
        out["auc"] = float(roc_auc_score(y_true, prob))
    except Exception:
        out["auc"] = 0.0
    return out


def choose_threshold(y_true_ef: np.ndarray, prob: np.ndarray) -> tuple[float, dict[str, float]]:
    best_threshold = 0.5
    best = lowef_metrics(y_true_ef, prob, best_threshold)
    for threshold in np.linspace(0.25, 0.75, 51):
        metrics = lowef_metrics(y_true_ef, prob, float(threshold))
        if (metrics["f1"], metrics["recall"], metrics["accuracy"]) > (best["f1"], best["recall"], best["accuracy"]):
            best = metrics
            best_threshold = float(threshold)
    return best_threshold, best


def regression_metrics(y_true: np.ndarray, pred: np.ndarray) -> dict[str, float]:
    return {
        "mae": float(mean_absolute_error(y_true, pred)),
        "rmse": float(mean_squared_error(y_true, pred) ** 0.5),
        "corr": float(np.corrcoef(y_true, pred)[0, 1]) if len(y_true) > 1 else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--echonet-dir", default="D:/new training dataset/EchoNet-Dynamic")
    parser.add_argument("--out-dir", default=str(PROJECT_ROOT / "training" / "echonet_v5"))
    parser.add_argument("--model-out", default=str(PROJECT_ROOT / "models" / "echonet_v5_lowef_mlp.joblib"))
    parser.add_argument("--train-limit", type=int, default=600)
    parser.add_argument("--val-limit", type=int, default=160)
    parser.add_argument("--test-limit", type=int, default=160)
    parser.add_argument("--max-frames", type=int, default=16)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    echonet_dir = Path(args.echonet_dir)
    videos_dir = echonet_dir / "Videos"
    filelist = pd.read_csv(echonet_dir / "FileList.csv")
    tracing_map = build_tracing_map(echonet_dir)
    print(f"loaded tracing keyframe map for {len(tracing_map)} videos", flush=True)

    splits = {
        "train": split_rows(filelist, "TRAIN", args.train_limit, args.seed),
        "val": split_rows(filelist, "VAL", args.val_limit, args.seed),
        "test": split_rows(filelist, "TEST", args.test_limit, args.seed),
    }

    matrices: dict[str, tuple[np.ndarray, np.ndarray, list[dict[str, Any]]]] = {}
    for name, rows in splits.items():
        print(f"building {name}: {len(rows)} videos", flush=True)
        matrices[name] = build_matrix(rows, videos_dir, args.max_frames, tracing_map)
        pd.DataFrame(matrices[name][2]).to_csv(out_dir / f"{name}_extraction_log.csv", index=False, encoding="utf-8-sig")
        np.savez_compressed(out_dir / f"{name}_features.npz", X=matrices[name][0], y=matrices[name][1])

    X_train, y_train, _ = matrices["train"]
    X_val, y_val, _ = matrices["val"]
    X_test, y_test, _ = matrices["test"]
    y_train_low = y_train < 50.0

    ef_candidates = {
        "ridge": make_pipeline(StandardScaler(), Ridge(alpha=5.0)),
        "hist_gradient_boosting": HistGradientBoostingRegressor(
            max_iter=220,
            learning_rate=0.045,
            l2_regularization=0.08,
            random_state=args.seed,
        ),
        "mlp": make_pipeline(
            StandardScaler(),
            MLPRegressor(
                hidden_layer_sizes=(96, 32),
                activation="relu",
                alpha=1e-3,
                learning_rate_init=1e-3,
                max_iter=180,
                early_stopping=True,
                n_iter_no_change=12,
                random_state=args.seed,
            ),
        ),
    }
    low_candidates = {
        "logistic": make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, class_weight="balanced")),
        "hist_gradient_boosting": HistGradientBoostingClassifier(
            max_iter=220,
            learning_rate=0.045,
            l2_regularization=0.08,
            random_state=args.seed,
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=240,
            max_depth=10,
            min_samples_leaf=3,
            class_weight="balanced_subsample",
            random_state=args.seed,
            n_jobs=-1,
        ),
        "mlp": make_pipeline(
            StandardScaler(),
            MLPClassifier(
                hidden_layer_sizes=(64, 24),
                activation="relu",
                alpha=1e-3,
                learning_rate_init=1e-3,
                max_iter=180,
                early_stopping=True,
                n_iter_no_change=12,
                random_state=args.seed,
            ),
        ),
    }

    ef_results: dict[str, dict[str, float]] = {}
    for name, model in ef_candidates.items():
        print(f"training EF {name}", flush=True)
        model.fit(X_train, y_train)
        ef_results[name] = regression_metrics(y_val, model.predict(X_val))
    best_ef_name = min(ef_results, key=lambda name: ef_results[name]["mae"])
    ef_model = ef_candidates[best_ef_name]

    low_results: dict[str, dict[str, float]] = {}
    thresholds: dict[str, float] = {}
    for name, model in low_candidates.items():
        print(f"training low-EF {name}", flush=True)
        model.fit(X_train, y_train_low)
        prob = model.predict_proba(X_val)[:, 1]
        threshold, metrics = choose_threshold(y_val, prob)
        thresholds[name] = threshold
        low_results[name] = metrics
    best_low_name = max(low_results, key=lambda name: (low_results[name]["f1"], low_results[name]["recall"], low_results[name]["accuracy"]))
    low_model = low_candidates[best_low_name]
    low_threshold = thresholds[best_low_name]

    test_ef_pred = ef_model.predict(X_test)
    test_low_prob = low_model.predict_proba(X_test)[:, 1]
    test_metrics = {
        "ef": regression_metrics(y_test, test_ef_pred),
        "low_ef": lowef_metrics(y_test, test_low_prob, low_threshold),
    }
    artifact = {
        "version": "v5_echonet_dynamic_mlp",
        "feature_count": int(feature_count()),
        "ef_model_name": best_ef_name,
        "lowef_model_name": best_low_name,
        "ef_model": ef_model,
        "lowef_model": low_model,
        "lowef_threshold": float(low_threshold),
        "ef_positive_cutoff": 50.0,
        "train_limit": int(args.train_limit),
        "val_limit": int(args.val_limit),
        "test_limit": int(args.test_limit),
        "max_frames": int(args.max_frames),
        "validation": {"ef_candidates": ef_results, "low_candidates": low_results},
        "test": test_metrics,
    }
    import joblib

    model_out = Path(args.model_out)
    model_out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, model_out)
    report = {
        "model_out": str(model_out),
        "feature_count": int(feature_count()),
        "selected": {"ef": best_ef_name, "low_ef": best_low_name, "threshold": float(low_threshold)},
        "validation": {"ef_candidates": ef_results, "low_candidates": low_results},
        "test": test_metrics,
        "limits": {"train": len(y_train), "val": len(y_val), "test": len(y_test), "max_frames": args.max_frames},
    }
    (out_dir / "training_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()

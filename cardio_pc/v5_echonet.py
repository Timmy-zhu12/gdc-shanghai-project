from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable, Iterable

import numpy as np
from PIL import Image

from .features import StudyAnalysis, bmode_features, chamber_area_proxy, resize_rgb, rgb_to_gray
from .label_hierarchy import HierarchicalDiagnosis, severity_from_strength


PROJECT_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = PROJECT_DIR / "models" / "echonet_v5_lowef_mlp.joblib"
MAX_V5_FRAMES = 16
THUMB_SIZE = 16


@dataclass(frozen=True)
class V5EchoNetPrediction:
    available: bool
    ef_pred: float
    low_ef_probability: float
    threshold: float
    positive: bool
    model_path: str
    note: str

    @property
    def audit_text(self) -> str:
        if not self.available:
            return f"V5 EchoNet-Dynamic 校准不可用: {self.note}"
        return (
            f"V5 EchoNet-Dynamic 轻量深度校准: EF预测={self.ef_pred:.1f}%, "
            f"低EF概率={self.low_ef_probability:.2f}, 阈值={self.threshold:.2f}"
        )


def apply_v5_echonet_calibration(
    study: StudyAnalysis,
    base_decision: HierarchicalDiagnosis,
    make_decision: Callable[..., HierarchicalDiagnosis],
) -> HierarchicalDiagnosis:
    prediction = predict_echonet_low_ef(study)
    if not prediction.available or not prediction.positive:
        return base_decision

    has_dynamic_input = study.input_count >= 6 or any(
        frame.loaded.source_type in {"video", "animated_image", "dicom"} for frame in study.frames
    )
    if not has_dynamic_input:
        return base_decision

    if base_decision.broad == "瓣膜性心脏病" and prediction.low_ef_probability < 0.85:
        return base_decision

    severity = severity_from_strength(
        max(prediction.low_ef_probability, max(0.0, (50.0 - prediction.ef_pred) / 30.0)),
        mild=0.45,
        moderate=0.68,
        severe=0.88,
    )
    if base_decision.broad == "瓣膜性心脏病":
        specific = f"{base_decision.compact_label}，并左心室收缩功能减低"
        broad = "复合心脏超声异常"
        middle = "瓣膜异常伴左心室收缩功能异常"
    else:
        specific = "左心室收缩功能减低"
        broad = "心肌与心功能异常"
        middle = "左心室收缩功能异常"

    return make_decision(
        broad=broad,
        middle=middle,
        specific=specific,
        severity=severity,
        study=study,
        has_specific_view=study.view_count >= 1,
        has_phase_pair=study.systole_count >= 1 and study.diastole_count >= 1,
        has_quant_proxy=True,
        rule_id="v5_echonet_dynamic_mlp_lowef",
        rationale=(
            "V5 使用 EchoNet-Dynamic A4C 动态心超数据训练轻量 MLP 校准器，"
            "将多帧 B-mode 纹理、腔室面积变化、帧间差分和低维缩略图特征融合，"
            "用于低 EF/左心室收缩功能减低教学标签。"
            + prediction.audit_text
        ),
        sources=("EchoNet-Dynamic", "V5-MLP-calibrator", "ASE-guidelines"),
    )


def predict_echonet_low_ef(study: StudyAnalysis) -> V5EchoNetPrediction:
    model = load_v5_model()
    if not model:
        return V5EchoNetPrediction(False, 0.0, 0.0, 0.5, False, str(MODEL_PATH), "model file missing")
    try:
        vector = feature_vector_from_study(study).reshape(1, -1)
        if vector.shape[1] != int(model.get("feature_count", vector.shape[1])):
            return V5EchoNetPrediction(False, 0.0, 0.0, 0.5, False, str(MODEL_PATH), "feature size mismatch")
        ef_pred = float(model["ef_model"].predict(vector)[0])
        if hasattr(model["lowef_model"], "predict_proba"):
            low_prob = float(model["lowef_model"].predict_proba(vector)[0, 1])
        else:
            raw = float(model["lowef_model"].predict(vector)[0])
            low_prob = float(np.clip(raw, 0.0, 1.0))
        threshold = float(model.get("lowef_threshold", 0.5))
        positive = bool(low_prob >= threshold or ef_pred < float(model.get("ef_positive_cutoff", 50.0)))
        return V5EchoNetPrediction(True, ef_pred, low_prob, threshold, positive, str(MODEL_PATH), "ok")
    except Exception as exc:
        return V5EchoNetPrediction(False, 0.0, 0.0, 0.5, False, str(MODEL_PATH), str(exc))


@lru_cache(maxsize=1)
def load_v5_model() -> dict | None:
    if not MODEL_PATH.exists():
        return None
    try:
        import joblib

        return joblib.load(MODEL_PATH)
    except Exception:
        return None


def feature_vector_from_study(study: StudyAnalysis) -> np.ndarray:
    frames = [frame.loaded.image for frame in study.frames[:MAX_V5_FRAMES]]
    fps = metadata_float((frame.loaded.metadata for frame in study.frames), "fps", 0.0)
    total_frames = metadata_float((frame.loaded.metadata for frame in study.frames), "n_frames", float(study.input_count))
    return feature_vector_from_frames(frames, fps=fps, total_frames=total_frames)


def feature_vector_from_frames(frames: Iterable[np.ndarray], fps: float = 0.0, total_frames: float = 0.0) -> np.ndarray:
    sampled = list(frames)[:MAX_V5_FRAMES]
    if not sampled:
        return np.zeros(feature_count(), dtype=np.float32)

    bmode_rows: list[np.ndarray] = []
    focus_rows: list[np.ndarray] = []
    areas: list[float] = []
    grays: list[np.ndarray] = []
    thumbs: list[np.ndarray] = []

    for frame in sampled:
        rgb = resize_rgb(frame, size=128)
        gray = rgb_to_gray(rgb)
        grays.append(gray)
        bmode_rows.append(bmode_features(gray))
        focus_rows.append(lv_focus_features(gray))
        areas.append(float(chamber_area_proxy(gray)))
        thumbs.append(gray_thumbnail(gray, THUMB_SIZE))

    bmode = np.vstack(bmode_rows).astype(np.float32)
    focus = np.vstack(focus_rows).astype(np.float32)
    area_arr = np.asarray(areas, dtype=np.float32)
    diffs = np.asarray(
        [float(np.mean(np.abs(b - a))) for a, b in zip(grays, grays[1:])],
        dtype=np.float32,
    )
    if diffs.size == 0:
        diffs = np.asarray([0.0], dtype=np.float32)

    min_idx = int(np.argmin(area_arr))
    max_idx = int(np.argmax(area_arr))
    mean_thumb = np.mean(np.vstack([thumb.reshape(1, -1) for thumb in thumbs]), axis=0)
    deep_part = np.concatenate([thumbs[min_idx].ravel(), thumbs[max_idx].ravel(), mean_thumb]).astype(np.float32)

    base = np.asarray(
        [
            len(sampled) / MAX_V5_FRAMES,
            np.log1p(max(total_frames, len(sampled))) / 8.0,
            min(max(fps, 0.0), 120.0) / 120.0,
            float(np.mean(area_arr)),
            float(np.std(area_arr)),
            float(np.min(area_arr)),
            float(np.max(area_arr)),
            float((np.max(area_arr) - np.min(area_arr)) / max(np.max(area_arr), 1e-6)),
            float(np.mean(diffs)),
            float(np.std(diffs)),
            float(np.max(diffs)),
            float(min_idx / max(len(sampled) - 1, 1)),
            float(max_idx / max(len(sampled) - 1, 1)),
        ],
        dtype=np.float32,
    )
    vector = np.concatenate(
        [base, bmode.mean(axis=0), bmode.std(axis=0), focus.mean(axis=0), focus.std(axis=0), deep_part]
    ).astype(np.float32)
    expected = feature_count()
    if vector.size < expected:
        vector = np.pad(vector, (0, expected - vector.size)).astype(np.float32)
    return vector[:expected]


def feature_count() -> int:
    return 13 + 14 + 14 + 8 + 8 + THUMB_SIZE * THUMB_SIZE * 3


def lv_focus_features(gray: np.ndarray) -> np.ndarray:
    h, w = gray.shape
    crop = gray[int(h * 0.18) : int(h * 0.92), int(w * 0.18) : int(w * 0.82)]
    if crop.size == 0:
        return np.zeros(8, dtype=np.float32)
    q20 = float(np.quantile(crop, 0.20))
    q35 = float(np.quantile(crop, 0.35))
    dark = crop <= q35
    very_dark = crop <= q20
    yy, xx = np.mgrid[0 : crop.shape[0], 0 : crop.shape[1]]
    if np.any(dark):
        weights = dark.astype(np.float32)
        total = float(np.sum(weights))
        cy = float(np.sum(yy * weights) / max(total, 1e-6) / max(crop.shape[0] - 1, 1))
        cx = float(np.sum(xx * weights) / max(total, 1e-6) / max(crop.shape[1] - 1, 1))
        y_any = np.any(dark, axis=1)
        x_any = np.any(dark, axis=0)
        height = float(np.sum(y_any) / max(crop.shape[0], 1))
        width = float(np.sum(x_any) / max(crop.shape[1], 1))
    else:
        cy = cx = height = width = 0.0
    return np.asarray(
        [
            float(np.mean(crop)),
            float(np.std(crop)),
            float(np.mean(dark)),
            float(np.mean(very_dark)),
            cy,
            cx,
            height,
            width,
        ],
        dtype=np.float32,
    )


def gray_thumbnail(gray: np.ndarray, size: int) -> np.ndarray:
    arr = np.clip(gray, 0.0, 1.0)
    image = Image.fromarray((arr * 255).astype(np.uint8), mode="L").resize((size, size), Image.Resampling.BILINEAR)
    return np.asarray(image, dtype=np.float32) / 255.0


def metadata_float(metadata_iter: Iterable[dict], key: str, default: float) -> float:
    for metadata in metadata_iter:
        raw = metadata.get(key)
        if raw is None and key == "fps":
            raw = metadata.get("FPS")
        try:
            value = float(raw)
            if np.isfinite(value):
                return value
        except Exception:
            continue
    return default

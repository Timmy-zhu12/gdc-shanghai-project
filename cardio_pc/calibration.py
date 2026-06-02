from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import json
import math

from .features import StudyAnalysis


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_LOW_EF_CALIBRATION = PROJECT_DIR / "calibration" / "camus_low_ef_bmode.json"


@dataclass(frozen=True)
class CalibrationEstimate:
    available: bool
    probability: float = 0.0
    threshold: float = 1.0
    name: str = ""
    evidence: str = ""

    @property
    def positive(self) -> bool:
        return self.available and self.probability >= self.threshold


@lru_cache(maxsize=4)
def load_calibration(path: str = str(DEFAULT_LOW_EF_CALIBRATION)) -> dict:
    calibration_path = Path(path)
    if not calibration_path.exists():
        return {}
    try:
        return json.loads(calibration_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def estimate_low_contractility_from_bmode(study: StudyAnalysis) -> CalibrationEstimate:
    spec = load_calibration()
    features = spec.get("features") or []
    means = spec.get("means") or []
    scales = spec.get("scales") or []
    coefs = spec.get("coefficients") or []
    threshold = float(spec.get("threshold", 1.0))
    if not (features and len(features) == len(means) == len(scales) == len(coefs)):
        return CalibrationEstimate(False, evidence="未找到可用的 CAMUS B-mode 低 EF 校准文件。")

    logit = float(spec.get("intercept", 0.0))
    used: list[str] = []
    for name, mean, scale, coef in zip(features, means, scales, coefs):
        if not name.startswith("bmode_"):
            continue
        try:
            idx = int(name.split("_", 1)[1])
        except ValueError:
            continue
        if idx >= len(study.mean_bmode):
            continue
        value = float(study.mean_bmode[idx])
        z = (value - float(mean)) / max(float(scale), 1e-6)
        logit += float(coef) * z
        used.append(name)

    probability = stable_sigmoid(logit)
    cv = spec.get("cross_validation", {})
    evidence = (
        f"CAMUS B-mode 低 EF 校准概率 {probability:.2f}，阈值 {threshold:.2f}，"
        f"校准集 case-level CV 准确率 {float(cv.get('accuracy', 0.0)):.3f}，"
        f"AUC {float(cv.get('auc', 0.0)):.3f}。"
    )
    return CalibrationEstimate(
        available=bool(used),
        probability=probability,
        threshold=threshold,
        name=str(spec.get("name", "")),
        evidence=evidence,
    )


def stable_sigmoid(value: float) -> float:
    if value >= 0:
        return 1.0 / (1.0 + math.exp(-value))
    exp_value = math.exp(value)
    return exp_value / (1.0 + exp_value)

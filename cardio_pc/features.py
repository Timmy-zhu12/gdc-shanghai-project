from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image, ImageFilter

from .imaging import LoadedImage


STANDARD_VIEWS: list[tuple[str, tuple[str, ...]]] = [
    ("PLAX", ("plax", "parasternal_long", "long_axis", "左室长轴", "胸骨旁长轴")),
    ("PSAX-AV", ("psax_av", "aortic_valve", "short_axis_av", "主动脉瓣短轴")),
    ("PSAX-MV", ("psax_mv", "mitral", "二尖瓣短轴")),
    ("PSAX-PM", ("psax_pm", "papillary", "乳头肌短轴")),
    ("PSAX-APEX", ("psax_apex", "apex_short", "心尖短轴")),
    ("A4C", ("a4c", "apical_4", "four_chamber", "心尖四腔")),
    ("A5C", ("a5c", "apical_5", "five_chamber", "心尖五腔")),
    ("A2C", ("a2c", "apical_2", "two_chamber", "心尖二腔")),
    ("A3C", ("a3c", "apical_3", "three_chamber", "心尖三腔")),
    ("SUBCOSTAL-4C", ("subcostal", "subxiphoid", "剑突下", "肋下")),
    ("IVC", ("ivc", "下腔静脉")),
    ("SUPRASTERNAL", ("suprasternal", "arch", "胸骨上窝", "主动脉弓")),
]


@dataclass
class FrameAnalysis:
    loaded: LoadedImage
    view: str
    phase: str
    chamber_area_proxy: float
    has_color_doppler: bool
    bmode_features: np.ndarray
    flow_features: np.ndarray
    notes: str


@dataclass
class StudyAnalysis:
    frames: list[FrameAnalysis]
    view_count: int
    input_count: int
    systole_count: int
    diastole_count: int
    mean_bmode: np.ndarray
    mean_flow: np.ndarray
    contractility_proxy: float
    coverage_warning: str
    feature_summary: str

    def compact_feature_text(self) -> str:
        b = ", ".join(f"{value:.4f}" for value in self.mean_bmode)
        f = ", ".join(f"{value:.4f}" for value in self.mean_flow)
        return (
            f"views={self.view_count}, files_or_frames={self.input_count}, "
            f"systole={self.systole_count}, diastole={self.diastole_count}, "
            f"contractility_proxy={self.contractility_proxy:.4f}\n"
            f"B-mode mean features=[{b}]\n"
            f"Doppler mean features=[{f}]"
        )


def analyze_loaded_images(images: list[LoadedImage]) -> StudyAnalysis:
    if not images:
        raise ValueError("No input images were loaded")

    provisional: list[FrameAnalysis] = []
    for image in images:
        arr = resize_rgb(image.image)
        gray = rgb_to_gray(arr)
        bmode = bmode_features(gray)
        flow = flow_features(arr)
        provisional.append(
            FrameAnalysis(
                loaded=image,
                view=detect_view(image.path),
                phase=phase_from_name(image.path),
                chamber_area_proxy=chamber_area_proxy(gray),
                has_color_doppler=bool(flow[4] > 0.015),
                bmode_features=bmode,
                flow_features=flow,
                notes="",
            )
        )

    frames = assign_phases(provisional)
    views = {frame.view for frame in frames}
    systole = sum(1 for frame in frames if frame.phase == "systole")
    diastole = sum(1 for frame in frames if frame.phase == "diastole")
    mean_b = np.mean([frame.bmode_features for frame in frames], axis=0)
    mean_f = np.mean([frame.flow_features for frame in frames], axis=0)
    contractility = compute_contractility_proxy(frames)
    warning = ""
    if len(views) > 12:
        warning = "输入超过 12 个体位标签，已按全部文件聚合；建议按标准 12 体位整理。"
    elif len(views) < 2:
        warning = "体位覆盖较少，输出只能作为极低置信度的疑似描述。"

    summary = build_feature_summary(frames, mean_b, mean_f, contractility, warning)
    return StudyAnalysis(
        frames=frames,
        view_count=len(views),
        input_count=len(images),
        systole_count=systole,
        diastole_count=diastole,
        mean_bmode=mean_b,
        mean_flow=mean_f,
        contractility_proxy=contractility,
        coverage_warning=warning,
        feature_summary=summary,
    )


def resize_rgb(arr: np.ndarray, size: int = 256) -> np.ndarray:
    image = Image.fromarray(ensure_rgb(arr), mode="RGB").resize((size, size), Image.Resampling.BILINEAR)
    return np.asarray(image, dtype=np.uint8)


def ensure_rgb(arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr)
    if arr.ndim == 2:
        return np.stack([arr, arr, arr], axis=-1).astype(np.uint8)
    if arr.ndim == 3 and arr.shape[-1] >= 3:
        return arr[..., :3].astype(np.uint8)
    raise ValueError(f"Unsupported image shape: {arr.shape}")


def rgb_to_gray(rgb: np.ndarray) -> np.ndarray:
    rgb_f = rgb.astype(np.float32) / 255.0
    return 0.299 * rgb_f[..., 0] + 0.587 * rgb_f[..., 1] + 0.114 * rgb_f[..., 2]


def bmode_features(gray: np.ndarray) -> np.ndarray:
    normalized = robust_normalize(gray)
    dog = dog_enhance(normalized)
    dx = np.diff(normalized, axis=1)
    dy = np.diff(normalized, axis=0)
    grad = np.sqrt(dx[:-1, :] ** 2 + dy[:, :-1] ** 2)
    hist, _ = np.histogram(normalized, bins=32, range=(0.0, 1.0), density=False)
    entropy = normalized_entropy(hist)
    return np.array(
        [
            float(np.mean(normalized)),
            float(np.var(normalized)),
            float(np.mean(np.abs(dx))),
            float(np.mean(np.abs(dy))),
            float(np.mean(grad)),
            float(np.mean(grad > 0.12)),
            entropy,
            float(np.mean(dog)),
            float(np.mean(dog > 0.65)),
            float(chamber_area_proxy(normalized)),
        ],
        dtype=np.float32,
    )


def flow_features(rgb: np.ndarray) -> np.ndarray:
    hsv = rgb_to_hsv(rgb)
    hue = hsv[..., 0]
    saturation = hsv[..., 1]
    value = hsv[..., 2]
    speed = saturation * value
    active = speed > 0.12
    theta = hue_to_theta(hue)
    vx = np.where(active, speed * np.cos(theta), 0.0)
    vy = np.where(active, speed * np.sin(theta), 0.0)
    active_count = max(int(np.sum(active)), 1)
    towards = float(np.sum((vx >= 0) & active) / active_count)
    away = float(np.sum((vx < 0) & active) / active_count)
    mean_speed = float(np.sum(speed[active]) / active_count)
    active_ratio = float(np.mean(active))
    grad_x = np.diff(vx, axis=1)
    grad_y = np.diff(vy, axis=0)
    turbulence = float(np.var(speed[active])) if np.any(active) else 0.0
    gradient_energy = float((np.mean(np.abs(grad_x)) + np.mean(np.abs(grad_y))) / 2.0)
    divergence = float(np.mean(np.abs(np.diff(vx, axis=1)[:-1, :] + np.diff(vy, axis=0)[:, :-1])))
    vorticity = float(np.mean(np.abs(np.diff(vy, axis=1)[:-1, :] - np.diff(vx, axis=0)[:, :-1])))
    confidence = float(np.mean(speed[active])) if np.any(active) else 0.0
    return np.array(
        [
            towards,
            away,
            mean_speed,
            float(np.mean(vx) * 0.5 + 0.5),
            active_ratio,
            turbulence,
            gradient_energy,
            divergence,
            vorticity,
            confidence,
        ],
        dtype=np.float32,
    )


def dog_enhance(gray: np.ndarray) -> np.ndarray:
    image = Image.fromarray((gray * 255).astype(np.uint8), mode="L")
    g1 = np.asarray(image.filter(ImageFilter.GaussianBlur(radius=1.0)), dtype=np.float32) / 255.0
    g2 = np.asarray(image.filter(ImageFilter.GaussianBlur(radius=2.0)), dtype=np.float32) / 255.0
    dog = g1 - g2
    return robust_normalize(dog)


def robust_normalize(values: np.ndarray) -> np.ndarray:
    low = float(np.percentile(values, 2))
    high = float(np.percentile(values, 98))
    return np.clip((values - low) / max(high - low, 1e-6), 0.0, 1.0)


def chamber_area_proxy(gray: np.ndarray) -> float:
    h, w = gray.shape
    crop = gray[int(h * 0.18) : int(h * 0.86), int(w * 0.12) : int(w * 0.88)]
    threshold = otsu_threshold(crop)
    dark = crop < threshold
    yy, xx = np.mgrid[0 : crop.shape[0], 0 : crop.shape[1]]
    cy = (crop.shape[0] - 1) / 2.0
    cx = (crop.shape[1] - 1) / 2.0
    radius = np.sqrt(((yy - cy) / max(crop.shape[0], 1)) ** 2 + ((xx - cx) / max(crop.shape[1], 1)) ** 2)
    weights = np.clip(1.0 - radius * 2.2, 0.15, 1.0)
    return float(np.sum(dark * weights) / np.sum(weights))


def otsu_threshold(values: np.ndarray) -> float:
    clipped = np.clip(values, 0.0, 1.0)
    hist, edges = np.histogram(clipped, bins=96, range=(0.0, 1.0))
    total = hist.sum()
    if total <= 0:
        return 0.25
    centers = (edges[:-1] + edges[1:]) / 2.0
    sum_total = float(np.sum(hist * centers))
    weight_bg = 0.0
    sum_bg = 0.0
    best_var = -1.0
    best = 0.25
    for count, center in zip(hist, centers):
        weight_bg += float(count)
        if weight_bg <= 0:
            continue
        weight_fg = float(total) - weight_bg
        if weight_fg <= 0:
            break
        sum_bg += float(count) * float(center)
        mean_bg = sum_bg / weight_bg
        mean_fg = (sum_total - sum_bg) / weight_fg
        between = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
        if between > best_var:
            best_var = between
            best = float(center)
    return float(np.clip(best, 0.08, 0.55))


def rgb_to_hsv(rgb: np.ndarray) -> np.ndarray:
    arr = rgb.astype(np.float32) / 255.0
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    maxc = np.max(arr, axis=-1)
    minc = np.min(arr, axis=-1)
    delta = maxc - minc
    hue = np.zeros_like(maxc)
    mask = delta > 1e-6
    rmask = mask & (maxc == r)
    gmask = mask & (maxc == g)
    bmask = mask & (maxc == b)
    hue[rmask] = ((g[rmask] - b[rmask]) / delta[rmask]) % 6.0
    hue[gmask] = ((b[gmask] - r[gmask]) / delta[gmask]) + 2.0
    hue[bmask] = ((r[bmask] - g[bmask]) / delta[bmask]) + 4.0
    hue *= 60.0
    saturation = np.where(maxc <= 1e-6, 0.0, delta / np.maximum(maxc, 1e-6))
    return np.stack([hue, saturation, maxc], axis=-1)


def hue_to_theta(hue: np.ndarray) -> np.ndarray:
    theta = np.zeros_like(hue, dtype=np.float32)
    theta = np.where(hue <= 240.0, (hue / 240.0) * np.pi, theta)
    theta = np.where((hue > 240.0) & (hue < 330.0), np.pi + ((hue - 240.0) / 90.0) * np.pi, theta)
    theta = np.where(hue >= 330.0, 0.0, theta)
    return theta


def detect_view(path: Path) -> str:
    name = path.stem.lower()
    for view, keywords in STANDARD_VIEWS:
        if any(keyword.lower() in name for keyword in keywords):
            return view
    return "UNKNOWN"


def phase_from_name(path: Path) -> str:
    name = path.stem.lower()
    systole_keys = ("systole", "systolic", "_es", "-es", "endsystole", "end_systole", "收缩")
    diastole_keys = ("diastole", "diastolic", "_ed", "-ed", "enddiastole", "end_diastole", "舒张")
    if any(key in name for key in systole_keys):
        return "systole"
    if any(key in name for key in diastole_keys):
        return "diastole"
    return "unknown"


def assign_phases(frames: list[FrameAnalysis]) -> list[FrameAnalysis]:
    by_view: dict[str, list[FrameAnalysis]] = {}
    for frame in frames:
        by_view.setdefault(frame.view, []).append(frame)

    for group in by_view.values():
        unknown = [frame for frame in group if frame.phase == "unknown"]
        if len(group) >= 2 and unknown:
            ordered = sorted(group, key=lambda item: item.chamber_area_proxy)
            ordered[0].phase = "systole"
            ordered[-1].phase = "diastole"
            for middle in ordered[1:-1]:
                if middle.phase == "unknown":
                    middle.phase = "intermediate"
        elif len(group) == 1 and group[0].phase == "unknown":
            group[0].phase = "unknown_single_frame"
    return frames


def compute_contractility_proxy(frames: Iterable[FrameAnalysis]) -> float:
    by_view: dict[str, list[FrameAnalysis]] = {}
    for frame in frames:
        by_view.setdefault(frame.view, []).append(frame)

    deltas: list[float] = []
    for group in by_view.values():
        systolic = [frame.chamber_area_proxy for frame in group if frame.phase == "systole"]
        diastolic = [frame.chamber_area_proxy for frame in group if frame.phase == "diastole"]
        if systolic and diastolic:
            deltas.append(max(diastolic) - min(systolic))
    return float(np.mean(deltas)) if deltas else 0.0


def normalized_entropy(hist: np.ndarray) -> float:
    total = np.sum(hist)
    if total <= 0:
        return 0.0
    p = hist.astype(np.float32) / float(total)
    p = p[p > 0]
    entropy = -np.sum(p * np.log2(p))
    return float(np.clip(entropy / 5.0, 0.0, 1.0))


def build_feature_summary(
    frames: list[FrameAnalysis],
    mean_b: np.ndarray,
    mean_f: np.ndarray,
    contractility: float,
    warning: str,
) -> str:
    view_names = ", ".join(sorted({frame.view for frame in frames}))
    phase_text = ", ".join(f"{frame.loaded.display_name}:{frame.phase}/{frame.view}" for frame in frames[:24])
    return (
        f"输入 {len(frames)} 个文件/帧，覆盖体位: {view_names}. "
        f"相位识别: {phase_text}. "
        f"收缩-舒张腔室面积代理差值: {contractility:.3f}. "
        f"B-mode 边缘密度={mean_b[5]:.3f}, 纹理熵={mean_b[6]:.3f}; "
        f"Doppler 活跃区比例={mean_f[4]:.3f}, 湍流代理={mean_f[5]:.3f}, 涡量代理={mean_f[8]:.3f}. "
        f"{warning}"
    ).strip()

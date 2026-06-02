from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image, ImageFilter

from .imaging import LoadedImage


STANDARD_VIEWS: list[tuple[str, tuple[str, ...]]] = [
    ("PLAX", ("plax", "parasternal_long", "long_axis", "parasternal long", "left_ventricle_long_axis", "左室长轴", "胸骨旁长轴")),
    ("PSAX-AV", ("psax_av", "aortic_valve", "short_axis_av", "aortic valve short", "主动脉瓣短轴")),
    ("PSAX-MV", ("psax_mv", "mitral_short", "mitral valve short", "二尖瓣短轴")),
    ("PSAX-PM", ("psax_pm", "papillary", "papillary_muscle", "乳头肌短轴")),
    ("PSAX-APEX", ("psax_apex", "apex_short", "apical_short", "心尖短轴")),
    ("A4C", ("a4c", "4ch", "apical_4", "four_chamber", "apical four", "心尖四腔")),
    ("A5C", ("a5c", "apical_5", "five_chamber", "apical five", "心尖五腔")),
    ("A2C", ("a2c", "2ch", "apical_2", "two_chamber", "apical two", "心尖二腔")),
    ("A3C", ("a3c", "3ch", "apical_3", "three_chamber", "apical long", "心尖三腔")),
    ("SUBCOSTAL-4C", ("subcostal", "subxiphoid", "subcostal_4c", "剑突下", "肋下")),
    ("IVC", ("ivc", "inferior_vena_cava", "下腔静脉")),
    ("SUPRASTERNAL", ("suprasternal", "arch", "aortic_arch", "胸骨上窝", "主动脉弓")),
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
    contractility_fraction_proxy: float
    coverage_warning: str
    feature_summary: str
    quality_score: float
    method_notes: str

    def compact_feature_text(self) -> str:
        b = ", ".join(f"{value:.4f}" for value in self.mean_bmode)
        f = ", ".join(f"{value:.4f}" for value in self.mean_flow)
        return (
            f"views={self.view_count}, files_or_frames={self.input_count}, "
            f"systole={self.systole_count}, diastole={self.diastole_count}, "
            f"contractility_proxy={self.contractility_proxy:.4f}, "
            f"contractility_fraction_proxy={self.contractility_fraction_proxy:.4f}, "
            f"quality_score={self.quality_score:.3f}\n"
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
        enhanced = preprocess_bmode(gray)
        provisional.append(
            FrameAnalysis(
                loaded=image,
                view=detect_view(image.path),
                phase=phase_from_name(image.path),
                chamber_area_proxy=chamber_area_proxy(enhanced),
                has_color_doppler=bool(flow[4] > 0.018 and flow[10] > 0.10),
                bmode_features=bmode,
                flow_features=flow,
                notes="SRAD/CLAHE enhanced B-mode; connected-component filtered Doppler",
            )
        )

    frames = assign_phases(provisional)
    views = {frame.view for frame in frames}
    systole = sum(1 for frame in frames if frame.phase == "systole")
    diastole = sum(1 for frame in frames if frame.phase == "diastole")
    mean_b = np.mean([frame.bmode_features for frame in frames], axis=0)
    mean_f = np.mean([frame.flow_features for frame in frames], axis=0)
    contractility = compute_contractility_proxy(frames)
    contractility_fraction = compute_contractility_fraction_proxy(frames)
    quality = compute_quality_score(frames, len(views), systole, diastole)

    warning = ""
    if len(views) > 12:
        warning = "输入超过 12 个体位标签，已按全部文件聚合；建议按标准 12 体位整理。"
    elif len(views) < 2:
        warning = "体位覆盖较少，输出只能作为低置信度的疑似教学判断。"
    if systole == 0 or diastole == 0:
        warning = (warning + " " if warning else "") + "收缩态/舒张态配对不足，已降低置信度。"

    method_notes = (
        "改进版使用 SRAD-inspired 散斑抑制、CLAHE 局部对比度增强、"
        "ED/ES 腔室面积代理相位识别、Doppler 连通域过滤、喷流宽度代理、"
        "方向一致性、散度与涡量代理，并加入 CAMUS B-mode 低 EF 校准和层级标签体系。"
    )
    summary = build_feature_summary(frames, mean_b, mean_f, contractility, contractility_fraction, quality, warning)
    return StudyAnalysis(
        frames=frames,
        view_count=len(views),
        input_count=len(images),
        systole_count=systole,
        diastole_count=diastole,
        mean_bmode=mean_b,
        mean_flow=mean_f,
        contractility_proxy=contractility,
        contractility_fraction_proxy=contractility_fraction,
        coverage_warning=warning,
        feature_summary=summary,
        quality_score=quality,
        method_notes=method_notes,
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


def preprocess_bmode(gray: np.ndarray) -> np.ndarray:
    normalized = robust_normalize(gray)
    log_compressed = np.log1p(8.0 * normalized) / np.log1p(8.0)
    despeckled = srad_inspired_filter(log_compressed, iterations=8, step=0.16)
    return clahe_like(despeckled, tile_grid=8, bins=128, clip_fraction=0.015)


def bmode_features(gray: np.ndarray) -> np.ndarray:
    normalized = robust_normalize(gray)
    enhanced = preprocess_bmode(gray)
    dog = dog_enhance(enhanced)
    dx = np.diff(enhanced, axis=1)
    dy = np.diff(enhanced, axis=0)
    grad = np.sqrt(dx[:-1, :] ** 2 + dy[:, :-1] ** 2)
    hist, _ = np.histogram(enhanced, bins=32, range=(0.0, 1.0), density=False)
    entropy = normalized_entropy(hist)
    gx = float(np.mean(np.abs(dx)))
    gy = float(np.mean(np.abs(dy)))
    directional_anisotropy = abs(gx - gy) / max(gx + gy, 1e-6)
    left = float(np.mean(enhanced[:, : enhanced.shape[1] // 2]))
    right = float(np.mean(enhanced[:, enhanced.shape[1] // 2 :]))
    symmetry_proxy = 1.0 - min(abs(left - right), 1.0)
    speckle_residual = float(np.mean(np.abs(normalized - enhanced)))
    contrast_gain = float(np.var(enhanced) / max(np.var(normalized), 1e-6))
    return np.array(
        [
            float(np.mean(enhanced)),
            float(np.var(enhanced)),
            gx,
            gy,
            float(np.mean(grad)),
            float(np.mean(grad > 0.12)),
            entropy,
            float(np.mean(dog)),
            float(np.mean(dog > 0.65)),
            float(chamber_area_proxy(enhanced)),
            speckle_residual,
            float(np.clip(contrast_gain, 0.0, 5.0)),
            directional_anisotropy,
            symmetry_proxy,
        ],
        dtype=np.float32,
    )


def flow_features(rgb: np.ndarray) -> np.ndarray:
    hsv = rgb_to_hsv(rgb)
    hue = hsv[..., 0]
    saturation = hsv[..., 1]
    value = hsv[..., 2]
    speed = saturation * value

    red_like = (hue <= 55.0) | (hue >= 315.0)
    blue_like = (hue >= 170.0) & (hue <= 270.0)
    alias_like = (saturation > 0.35) & (value > 0.18) & ~(red_like | blue_like)
    active = (saturation > 0.25) & (value > 0.18) & (red_like | blue_like | alias_like)
    active = denoise_binary_mask(active, min_neighbors=3)

    theta = hue_to_theta(hue)
    signed_direction = np.where(red_like, 1.0, np.where(blue_like, -1.0, np.cos(theta)))
    vx = np.where(active, speed * signed_direction, 0.0)
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
    confidence = mean_speed if np.any(active) else 0.0
    component_ratio, jet_width_proxy = largest_component_metrics(active)
    bidirectional_ratio = float(min(towards, away) / max(max(towards, away), 1e-6))
    vector_norm = float(np.sqrt(np.sum(vx) ** 2 + np.sum(vy) ** 2))
    directional_coherence = vector_norm / max(float(np.sum(speed[active])), 1e-6)
    signed_proxy = float(np.mean(vx[active]) * 0.5 + 0.5) if np.any(active) else 0.5

    return np.array(
        [
            towards,
            away,
            mean_speed,
            signed_proxy,
            active_ratio,
            turbulence,
            gradient_energy,
            divergence,
            vorticity,
            confidence,
            component_ratio,
            jet_width_proxy,
            bidirectional_ratio,
            float(np.clip(directional_coherence, 0.0, 1.0)),
        ],
        dtype=np.float32,
    )


def srad_inspired_filter(image: np.ndarray, iterations: int = 8, step: float = 0.16) -> np.ndarray:
    img = np.asarray(image, dtype=np.float32).copy()
    eps = 1e-6
    for _ in range(iterations):
        mean = float(np.mean(img))
        q0_sq = float(np.var(img) / max(mean * mean, eps))
        padded = np.pad(img, 1, mode="edge")
        north = padded[:-2, 1:-1] - img
        south = padded[2:, 1:-1] - img
        west = padded[1:-1, :-2] - img
        east = padded[1:-1, 2:] - img
        grad_sq = (north**2 + south**2 + west**2 + east**2) / np.maximum(img**2, eps)
        lap = (north + south + west + east) / np.maximum(img, eps)
        q_sq = (0.5 * grad_sq - 0.0625 * lap**2) / np.maximum((1.0 + 0.25 * lap) ** 2, eps)
        ratio = (q_sq - q0_sq) / max(q0_sq * (1.0 + q0_sq), eps)
        denom = 1.0 + ratio
        denom = np.where(np.abs(denom) < eps, eps, denom)
        diffusion = 1.0 / denom
        diffusion = np.clip(diffusion, 0.0, 1.0)
        update = diffusion * (north + south + west + east) / 4.0
        img = np.clip(img + step * update, 0.0, 1.0)
    return img


def clahe_like(image: np.ndarray, tile_grid: int = 8, bins: int = 128, clip_fraction: float = 0.015) -> np.ndarray:
    img = np.clip(image, 0.0, 1.0)
    h, w = img.shape
    out = np.zeros_like(img, dtype=np.float32)
    tile_h = int(np.ceil(h / tile_grid))
    tile_w = int(np.ceil(w / tile_grid))
    for ty in range(tile_grid):
        for tx in range(tile_grid):
            y0, y1 = ty * tile_h, min((ty + 1) * tile_h, h)
            x0, x1 = tx * tile_w, min((tx + 1) * tile_w, w)
            if y0 >= y1 or x0 >= x1:
                continue
            tile = img[y0:y1, x0:x1]
            hist, _ = np.histogram(tile, bins=bins, range=(0.0, 1.0))
            clip_limit = max(2, int(clip_fraction * tile.size))
            excess = np.maximum(hist - clip_limit, 0)
            hist = np.minimum(hist, clip_limit)
            redistribute = int(np.sum(excess))
            hist += redistribute // bins
            hist[: redistribute % bins] += 1
            cdf = np.cumsum(hist).astype(np.float32)
            cdf /= max(float(cdf[-1]), 1.0)
            idx = np.clip((tile * (bins - 1)).astype(np.int32), 0, bins - 1)
            out[y0:y1, x0:x1] = cdf[idx]
    return robust_normalize(out)


def dog_enhance(gray: np.ndarray) -> np.ndarray:
    image = Image.fromarray((gray * 255).astype(np.uint8), mode="L")
    g1 = np.asarray(image.filter(ImageFilter.GaussianBlur(radius=1.0)), dtype=np.float32) / 255.0
    g2 = np.asarray(image.filter(ImageFilter.GaussianBlur(radius=2.4)), dtype=np.float32) / 255.0
    dog = g1 - g2
    return robust_normalize(dog)


def robust_normalize(values: np.ndarray) -> np.ndarray:
    low = float(np.percentile(values, 2))
    high = float(np.percentile(values, 98))
    return np.clip((values - low) / max(high - low, 1e-6), 0.0, 1.0).astype(np.float32)


def chamber_area_proxy(gray: np.ndarray) -> float:
    h, w = gray.shape
    crop = gray[int(h * 0.18) : int(h * 0.86), int(w * 0.12) : int(w * 0.88)]
    threshold = otsu_threshold(crop)
    dark = crop < threshold
    component_area = central_dark_component_area(dark)
    if component_area > 0:
        return component_area
    yy, xx = np.mgrid[0 : crop.shape[0], 0 : crop.shape[1]]
    cy = (crop.shape[0] - 1) / 2.0
    cx = (crop.shape[1] - 1) / 2.0
    radius = np.sqrt(((yy - cy) / max(crop.shape[0], 1)) ** 2 + ((xx - cx) / max(crop.shape[1], 1)) ** 2)
    weights = np.clip(1.0 - radius * 2.2, 0.15, 1.0)
    return float(np.sum(dark * weights) / np.sum(weights))


def central_dark_component_area(mask: np.ndarray) -> float:
    h, w = mask.shape
    if h <= 0 or w <= 0 or not np.any(mask):
        return 0.0
    visited = np.zeros(mask.shape, dtype=bool)
    cy = (h - 1) / 2.0
    cx = (w - 1) / 2.0
    best_score = -1.0
    best_count = 0
    starts = np.argwhere(mask)
    for sy, sx in starts:
        if visited[sy, sx]:
            continue
        q: deque[tuple[int, int]] = deque([(int(sy), int(sx))])
        visited[sy, sx] = True
        count = 0
        sum_y = 0.0
        sum_x = 0.0
        touches_border = False
        while q:
            y, x = q.popleft()
            count += 1
            sum_y += y
            sum_x += x
            touches_border = touches_border or y <= 1 or x <= 1 or y >= h - 2 or x >= w - 2
            for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not visited[ny, nx]:
                    visited[ny, nx] = True
                    q.append((ny, nx))
        if count < max(24, int(0.0015 * h * w)):
            continue
        centroid_y = sum_y / count
        centroid_x = sum_x / count
        dist = np.sqrt(((centroid_y - cy) / max(h, 1)) ** 2 + ((centroid_x - cx) / max(w, 1)) ** 2)
        border_penalty = 0.25 if touches_border else 1.0
        score = count * border_penalty * max(0.15, 1.0 - 2.0 * dist)
        if score > best_score:
            best_score = score
            best_count = count
    return float(np.clip(best_count / max(h * w, 1), 0.0, 1.0))


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


def denoise_binary_mask(mask: np.ndarray, min_neighbors: int = 3) -> np.ndarray:
    padded = np.pad(mask.astype(np.uint8), 1, mode="constant")
    count = np.zeros(mask.shape, dtype=np.uint8)
    for dy in range(3):
        for dx in range(3):
            count += padded[dy : dy + mask.shape[0], dx : dx + mask.shape[1]]
    return mask & (count >= min_neighbors)


def largest_component_metrics(mask: np.ndarray) -> tuple[float, float]:
    h, w = mask.shape
    total = int(np.sum(mask))
    if total <= 0:
        return 0.0, 0.0
    visited = np.zeros(mask.shape, dtype=bool)
    best_count = 0
    best_bbox = (0, 0, 0, 0)
    starts = np.argwhere(mask)
    for sy, sx in starts:
        if visited[sy, sx]:
            continue
        q: deque[tuple[int, int]] = deque([(int(sy), int(sx))])
        visited[sy, sx] = True
        count = 0
        min_y = max_y = int(sy)
        min_x = max_x = int(sx)
        while q:
            y, x = q.popleft()
            count += 1
            min_y, max_y = min(min_y, y), max(max_y, y)
            min_x, max_x = min(min_x, x), max(max_x, x)
            for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not visited[ny, nx]:
                    visited[ny, nx] = True
                    q.append((ny, nx))
        if count > best_count:
            best_count = count
            best_bbox = (min_y, max_y, min_x, max_x)
    min_y, max_y, min_x, max_x = best_bbox
    bbox_h = max_y - min_y + 1
    bbox_w = max_x - min_x + 1
    jet_width_proxy = min(bbox_h / max(h, 1), bbox_w / max(w, 1))
    return float(best_count / max(total, 1)), float(np.clip(jet_width_proxy, 0.0, 1.0))


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
        has_systole = any(frame.phase == "systole" for frame in group)
        has_diastole = any(frame.phase == "diastole" for frame in group)
        if len(group) >= 2 and unknown:
            ordered_unknown = sorted(unknown, key=lambda item: item.chamber_area_proxy)
            if not has_systole and ordered_unknown:
                ordered_unknown[0].phase = "systole"
            if not has_diastole and ordered_unknown:
                ordered_unknown[-1].phase = "diastole"
            for middle in ordered_unknown:
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
            deltas.append(max(max(diastolic) - min(systolic), 0.0))
    return float(np.mean(deltas)) if deltas else 0.0


def compute_contractility_fraction_proxy(frames: Iterable[FrameAnalysis]) -> float:
    by_view: dict[str, list[FrameAnalysis]] = {}
    for frame in frames:
        by_view.setdefault(frame.view, []).append(frame)

    fractions: list[float] = []
    for group in by_view.values():
        systolic = [frame.chamber_area_proxy for frame in group if frame.phase == "systole"]
        diastolic = [frame.chamber_area_proxy for frame in group if frame.phase == "diastole"]
        if systolic and diastolic:
            ed_area = max(diastolic)
            es_area = min(systolic)
            fractions.append(max(ed_area - es_area, 0.0) / max(ed_area, 1e-6))
    return float(np.mean(fractions)) if fractions else 0.0


def compute_quality_score(frames: list[FrameAnalysis], view_count: int, systole: int, diastole: int) -> float:
    has_phase_pair = systole > 0 and diastole > 0
    coverage_score = min(view_count / 6.0, 1.0)
    if has_phase_pair and view_count >= 1:
        coverage_score = max(coverage_score, 0.55)
    phase_score = 1.0 if has_phase_pair else 0.35
    doppler_components = [float(frame.flow_features[10]) for frame in frames]
    bmode_contrast = [float(frame.bmode_features[11]) for frame in frames]
    doppler_score = min(float(np.mean(doppler_components)) * 1.3, 1.0) if doppler_components else 0.0
    contrast_score = min(float(np.mean(bmode_contrast)) / 1.6, 1.0) if bmode_contrast else 0.5
    return float(np.clip(0.30 * coverage_score + 0.35 * phase_score + 0.20 * contrast_score + 0.15 * doppler_score, 0.0, 1.0))


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
    contractility_fraction: float,
    quality: float,
    warning: str,
) -> str:
    view_names = ", ".join(sorted({frame.view for frame in frames}))
    phase_text = ", ".join(f"{frame.loaded.display_name}:{frame.phase}/{frame.view}" for frame in frames[:24])
    return (
        f"输入 {len(frames)} 个文件/帧，覆盖体位: {view_names}. "
        f"相位识别: {phase_text}. "
        f"收缩-舒张腔室面积代理差值 {contractility:.3f}, "
        f"相对收缩幅度代理 {contractility_fraction:.3f}. "
        f"B-mode 边缘密度={mean_b[5]:.3f}, 纹理熵={mean_b[6]:.3f}, "
        f"散斑残差={mean_b[10]:.3f}, 对比增益={mean_b[11]:.3f}; "
        f"Doppler 活跃区比例={mean_f[4]:.3f}, 连通域比例={mean_f[10]:.3f}, "
        f"喷流宽度代理={mean_f[11]:.3f}, 方向一致性={mean_f[13]:.3f}, "
        f"湍流代理={mean_f[5]:.3f}, 涡量代理={mean_f[8]:.3f}. "
        f"综合质量分={quality:.2f}. {warning}"
    ).strip()

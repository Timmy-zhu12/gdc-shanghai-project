from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT_ROOT = ROOT


def add_project_root(project_root: str | Path = DEFAULT_PROJECT_ROOT) -> Path:
    root = Path(project_root).resolve()
    if not root.exists():
        raise FileNotFoundError(f"CardioConsult PC project root not found: {root}")
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root


def supported_media_extensions(project_root: str | Path = DEFAULT_PROJECT_ROOT) -> set[str]:
    add_project_root(project_root)
    from cardio_pc.imaging import SUPPORTED_EXTENSIONS

    return set(SUPPORTED_EXTENSIONS)


def collect_media_paths(paths: list[str | Path], project_root: str | Path = DEFAULT_PROJECT_ROOT) -> list[Path]:
    extensions = supported_media_extensions(project_root)
    out: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            for item in path.rglob("*"):
                if item.is_file() and item.suffix.lower() in extensions:
                    out.append(item.resolve())
        elif path.is_file() and path.suffix.lower() in extensions:
            out.append(path.resolve())
    return sorted(dict.fromkeys(out), key=natural_sort_key)


def natural_sort_key(path: Path) -> list[Any]:
    text = str(path).lower()
    parts = re.split(r"(\d+)", text)
    return [int(part) if part.isdigit() else part for part in parts]


def sample_evenly(items: list[Path], max_items: int) -> list[Path]:
    if max_items <= 0 or len(items) <= max_items:
        return items
    if max_items == 1:
        return [items[0]]
    indices = sorted({int(round(i)) for i in np.linspace(0, len(items) - 1, max_items)})
    return [items[index] for index in indices[:max_items]]


def parse_measurement_pairs(pairs: list[str]) -> dict[str, float]:
    measurements: dict[str, float] = {}
    for pair in pairs:
        if "=" not in pair:
            continue
        key, value = pair.split("=", 1)
        key = key.strip()
        try:
            number = float(value.strip())
        except ValueError:
            continue
        if key:
            measurements[key] = number
    return measurements


def patient_from_media(
    paths: list[str | Path],
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    measurements: dict[str, float] | None = None,
    case_id: str = "",
    patient_id: str = "",
    max_loaded_frames: int = 48,
    decode_timeout: float = 6.0,
    max_input_files: int = 12,
    decode_workers: int = 4,
) -> dict[str, Any]:
    root = add_project_root(project_root)
    from cardio_pc.features import analyze_loaded_images

    media_paths = collect_media_paths(paths, root)
    if not media_paths:
        raise RuntimeError("No supported ultrasound media files were selected.")

    warnings: list[str] = []
    started = time.perf_counter()
    loaded, decode_stats = load_files_fast(
        media_paths,
        project_root=root,
        file_decode_timeout_seconds=decode_timeout,
        max_loaded_frames=max_loaded_frames,
        max_input_files=max_input_files,
        workers=decode_workers,
        warnings=warnings,
    )
    if not loaded:
        raise RuntimeError("No frames could be decoded from selected files.")

    study = analyze_loaded_images(loaded)
    mean_bmode = np.asarray(study.mean_bmode, dtype=float)
    mean_flow = np.asarray(study.mean_flow, dtype=float)
    views = sorted({frame.view for frame in study.frames if str(frame.view).strip()})
    proxies = {
        "view_count": float(study.view_count),
        "input_count": float(study.input_count),
        "systole_count": float(study.systole_count),
        "diastole_count": float(study.diastole_count),
        "contractility_proxy": float(study.contractility_proxy),
        "contractility_fraction_proxy": float(study.contractility_fraction_proxy),
        "quality_score": float(study.quality_score),
        "flow_active_ratio": float(mean_flow[4]) if mean_flow.size > 4 else 0.0,
        "flow_turbulence_proxy": float(mean_flow[5]) if mean_flow.size > 5 else 0.0,
        "flow_vorticity_proxy": float(mean_flow[8]) if mean_flow.size > 8 else 0.0,
        "flow_largest_component_ratio": float(mean_flow[10]) if mean_flow.size > 10 else 0.0,
        "jet_width_proxy": float(mean_flow[11]) if mean_flow.size > 11 else 0.0,
        "directional_coherence": float(mean_flow[13]) if mean_flow.size > 13 else 0.0,
        "bmode_edge_density": float(mean_bmode[5]) if mean_bmode.size > 5 else 0.0,
        "bmode_texture_entropy": float(mean_bmode[6]) if mean_bmode.size > 6 else 0.0,
        "bmode_chamber_area_proxy": float(mean_bmode[9]) if mean_bmode.size > 9 else 0.0,
        "bmode_speckle_residual": float(mean_bmode[10]) if mean_bmode.size > 10 else 0.0,
    }
    proxies.update(build_v5_aligned_proxy_features(study, warnings))
    frame_rows = [
        {
            "file": str(frame.loaded.path),
            "frame_index": int(frame.loaded.frame_index),
            "view": frame.view,
            "phase": frame.phase,
            "has_color_doppler": bool(frame.has_color_doppler),
            "chamber_area_proxy": float(frame.chamber_area_proxy),
        }
        for frame in study.frames
    ]
    return {
        "case_id": case_id or infer_case_id(media_paths),
        "patient_id": patient_id or "",
        "source": "media_adapter",
        "source_files": [str(path) for path in media_paths],
        "decoded_files": list(decode_stats["decoded_paths"]),
        "skipped_files_by_sampling": list(decode_stats["skipped_paths"]),
        "loaded_frame_count": len(loaded),
        "decode_warnings": warnings,
        "decode_mode": decode_stats,
        "elapsed_seconds_feature_extraction": round(time.perf_counter() - started, 4),
        "measurements": measurements or {},
        "proxies": proxies,
        "views": views,
        "frame_summary": frame_rows,
        "feature_summary": study.feature_summary,
        "diagnosis_text": "",
    }


def build_v5_aligned_proxy_features(study: Any, warnings: list[str] | None = None) -> dict[str, float]:
    proxies: dict[str, float] = {}
    warnings = warnings if warnings is not None else []
    proxies.update(estimate_morphology_proxy_features(study))

    try:
        from cardio_pc.v4_calibration import build_v4_evidence

        evidence = build_v4_evidence(study)
        low_turbulence = float(get_feature(study.mean_flow, 5)) <= 0.035 and float(get_feature(study.mean_flow, 8)) <= 0.030
        proxies.update(
            {
                "v4_temporal_diff": float(evidence.temporal_diff),
                "sti_strain_proxy": float(evidence.sti_strain_proxy),
                "optical_flow_proxy": float(evidence.optical_flow_proxy),
                "shared_ek_valve_score": float(evidence.shared_ek_valve),
                "coupled_ek_structure_score": float(evidence.coupled_ek_structure),
                "v4_mr_flag": 1.0 if evidence.mr else 0.0,
                "v4_tr_flag": 1.0 if evidence.tr else 0.0,
                "v4_ar_flag": 1.0 if evidence.ar else 0.0,
                "v4_low_ef_flag": 1.0 if evidence.low_ef else 0.0,
                "v4_rwma_flag": 1.0 if evidence.rwma else 0.0,
                "v4_la_enlargement_flag": 1.0 if evidence.la_enlargement else 0.0,
                "combined_mr_tr_proxy": 1.0 if evidence.mr and evidence.tr and low_turbulence else 0.0,
                "rwma_proxy": 1.0 if evidence.rwma else 0.0,
                "la_enlargement_proxy": 1.0 if evidence.la_enlargement else 0.0,
            }
        )
    except Exception as exc:
        warnings.append(f"V4 经验特征未能计算：{exc}")
        proxies.update(
            {
                "v4_temporal_diff": 0.0,
                "sti_strain_proxy": 0.0,
                "optical_flow_proxy": 0.0,
                "shared_ek_valve_score": 0.0,
                "coupled_ek_structure_score": 0.0,
                "v4_mr_flag": 0.0,
                "v4_tr_flag": 0.0,
                "v4_ar_flag": 0.0,
                "v4_low_ef_flag": 0.0,
                "v4_rwma_flag": 0.0,
                "v4_la_enlargement_flag": 0.0,
                "combined_mr_tr_proxy": 0.0,
                "rwma_proxy": 0.0,
                "la_enlargement_proxy": 0.0,
            }
        )

    try:
        from cardio_pc.v5_echonet import predict_echonet_low_ef

        prediction = predict_echonet_low_ef(study)
        proxies.update(
            {
                "v5_low_ef_available": 1.0 if prediction.available else 0.0,
                "v5_low_ef_probability": float(prediction.low_ef_probability if prediction.available else 0.0),
                "v5_ef_pred_percent": float(prediction.ef_pred if prediction.available else 0.0),
                "v5_low_ef_positive": 1.0 if prediction.available and prediction.positive else 0.0,
            }
        )
    except Exception as exc:
        warnings.append(f"V5 EchoNet 轻量校准未能计算：{exc}")
        proxies.update(
            {
                "v5_low_ef_available": 0.0,
                "v5_low_ef_probability": 0.0,
                "v5_ef_pred_percent": 0.0,
                "v5_low_ef_positive": 0.0,
            }
        )

    return proxies


def estimate_morphology_proxy_features(study: Any) -> dict[str, float]:
    pericardial_values: list[float] = []
    right_heart_values: list[float] = []
    septal_values: list[float] = []
    lvh_values: list[float] = []
    frames = list(getattr(study, "frames", []) or [])[:32]
    if not frames:
        return {
            "pericardial_echo_free_space_proxy": 0.0,
            "right_heart_size_proxy": 0.0,
            "septal_flattening_proxy": 0.0,
            "lvh_wall_thickening_proxy": 0.0,
        }

    from cardio_pc.features import resize_rgb, robust_normalize, rgb_to_gray

    for frame in frames:
        rgb = resize_rgb(frame.loaded.image, size=128)
        gray = robust_normalize(rgb_to_gray(rgb))
        bmode = getattr(frame, "bmode_features", np.zeros(14, dtype=np.float32))
        pericardial_values.append(estimate_pericardial_dark_rim(gray))
        right_heart_values.append(estimate_right_heart_size_proxy(gray, str(getattr(frame, "view", ""))))
        septal_values.append(estimate_septal_flattening_proxy(gray))
        edge_density = get_feature(bmode, 5)
        anisotropy = get_feature(bmode, 12)
        symmetry = get_feature(bmode, 13, 1.0)
        lvh_values.append(float(np.clip(0.55 * edge_density + 0.35 * anisotropy + 0.10 * (1.0 - symmetry), 0.0, 1.0)))

    return {
        "pericardial_echo_free_space_proxy": percentile95(pericardial_values),
        "right_heart_size_proxy": percentile95(right_heart_values),
        "septal_flattening_proxy": percentile95(septal_values),
        "lvh_wall_thickening_proxy": percentile95(lvh_values),
    }


def estimate_pericardial_dark_rim(gray: np.ndarray) -> float:
    h, w = gray.shape
    crop = gray[int(h * 0.14) : int(h * 0.92), int(w * 0.08) : int(w * 0.92)]
    if crop.size == 0:
        return 0.0
    threshold = float(np.quantile(crop, 0.22))
    dark = crop <= threshold
    ch, cw = crop.shape
    yy, xx = np.mgrid[0:ch, 0:cw]
    y = yy / max(ch - 1, 1)
    x = xx / max(cw - 1, 1)
    ring = (y > 0.10) & (y < 0.96) & (x > 0.05) & (x < 0.95) & ~((y > 0.28) & (y < 0.76) & (x > 0.24) & (x < 0.76))
    central = (y > 0.30) & (y < 0.72) & (x > 0.26) & (x < 0.74)
    ring_dark = float(np.mean(dark[ring])) if np.any(ring) else 0.0
    central_dark = float(np.mean(dark[central])) if np.any(central) else 0.0
    return float(np.clip((ring_dark - 0.65 * central_dark) * 1.35, 0.0, 1.0))


def estimate_right_heart_size_proxy(gray: np.ndarray, view: str) -> float:
    h, w = gray.shape
    crop = gray[int(h * 0.18) : int(h * 0.88), int(w * 0.10) : int(w * 0.90)]
    if crop.size == 0:
        return 0.0
    threshold = float(np.quantile(crop, 0.34))
    dark = crop <= threshold
    left = float(np.mean(dark[:, : crop.shape[1] // 2]))
    right = float(np.mean(dark[:, crop.shape[1] // 2 :]))
    dominant = max(left, right)
    asymmetry = abs(left - right)
    view_weight = 1.0 if view in {"A4C", "RV-focused A4C", "SUBCOSTAL-4C", "UNKNOWN"} else 0.55
    return float(np.clip(view_weight * (0.65 * max(0.0, dominant - 0.18) + 0.35 * asymmetry), 0.0, 1.0))


def estimate_septal_flattening_proxy(gray: np.ndarray) -> float:
    h, w = gray.shape
    crop = gray[int(h * 0.18) : int(h * 0.88), int(w * 0.14) : int(w * 0.86)]
    if crop.size == 0:
        return 0.0
    threshold = float(np.quantile(crop, 0.30))
    dark = crop <= threshold
    coords = np.argwhere(dark)
    if coords.shape[0] < max(24, int(0.01 * crop.size)):
        return 0.0
    y0, x0 = coords.min(axis=0)
    y1, x1 = coords.max(axis=0)
    height = max(float(y1 - y0 + 1), 1.0)
    width = max(float(x1 - x0 + 1), 1.0)
    width_height = width / height
    return float(np.clip((width_height - 0.70) * 0.45, 0.0, 1.0))


def percentile95(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(np.clip(np.percentile(np.asarray(values, dtype=float), 95), 0.0, 1.0))


def get_feature(values: Any, index: int, default: float = 0.0) -> float:
    try:
        if index < len(values):
            value = float(values[index])
            if math.isfinite(value):
                return value
    except Exception:
        pass
    return default


def load_files_fast(
    media_paths: list[Path],
    project_root: Path,
    file_decode_timeout_seconds: float,
    max_loaded_frames: int,
    max_input_files: int,
    workers: int,
    warnings: list[str],
) -> tuple[list[Any], dict[str, Any]]:
    add_project_root(project_root)
    from cardio_pc.imaging import load_one_path_safe, sample_loaded_frames

    selected_paths = sample_evenly(media_paths, max_input_files)
    skipped_paths = [path for path in media_paths if path not in set(selected_paths)]
    if skipped_paths:
        warnings.append(
            f"输入 {len(media_paths)} 个文件，极速模式采样 {len(selected_paths)} 个代表文件；"
            f"如需全量分析，可把最大文件数设为 0。"
        )

    if not selected_paths:
        return [], {"selected_paths": [], "decoded_paths": [], "skipped_paths": skipped_paths, "workers": workers}

    per_file_limit = max(1, int(math.ceil(max(1, max_loaded_frames) / max(1, len(selected_paths)))))
    loaded: list[Any] = []
    decoded_paths: list[Path] = []
    workers = max(1, min(int(workers or 1), len(selected_paths), 8))

    def decode_one(path: Path) -> tuple[Path, list[Any], str, float]:
        started = time.perf_counter()
        frames, error = load_one_path_safe(path, file_decode_timeout_seconds)
        sampled = sample_loaded_frames(frames, per_file_limit) if frames else []
        return path, sampled, error, time.perf_counter() - started

    if workers == 1:
        iterator = [decode_one(path) for path in selected_paths]
    else:
        iterator = []
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(decode_one, path) for path in selected_paths]
            for future in as_completed(futures):
                iterator.append(future.result())

    order = {path: index for index, path in enumerate(selected_paths)}
    for path, frames, error, elapsed in sorted(iterator, key=lambda item: order[item[0]]):
        if frames:
            decoded_paths.append(path)
            loaded.extend(frames)
        if error:
            warnings.append(error)
        warnings.append(f"{path.name}: 解码 {len(frames)} 帧，用时 {elapsed:.2f}s")

    loaded = sample_loaded_frames(loaded, max_loaded_frames)
    return loaded, {
        "strategy": "parallel_fair_sampling",
        "input_file_count": len(media_paths),
        "selected_file_count": len(selected_paths),
        "decoded_file_count": len(decoded_paths),
        "max_input_files": max_input_files,
        "max_loaded_frames": max_loaded_frames,
        "per_file_frame_limit": per_file_limit,
        "file_decode_timeout_seconds": file_decode_timeout_seconds,
        "workers": workers,
        "selected_paths": [str(path) for path in selected_paths],
        "decoded_paths": [str(path) for path in decoded_paths],
        "skipped_paths": [str(path) for path in skipped_paths],
    }


def infer_case_id(paths: list[Path]) -> str:
    if not paths:
        return "CASE_UNKNOWN"
    parents = [path.parent for path in paths]
    common = parents[0]
    if all(parent == common for parent in parents):
        return common.name or paths[0].stem
    return paths[0].stem


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert ultrasound media files into a patient-level rule-engine input JSON.")
    parser.add_argument("--input", action="append", required=True, help="File or folder. Can be repeated.")
    parser.add_argument("--project-root", default=str(DEFAULT_PROJECT_ROOT))
    parser.add_argument("--measurement", action="append", default=[], help="Optional measurement pair, e.g. ef_percent=43")
    parser.add_argument("--case-id", default="")
    parser.add_argument("--patient-id", default="")
    parser.add_argument("--max-loaded-frames", type=int, default=48)
    parser.add_argument("--decode-timeout", type=float, default=6.0)
    parser.add_argument("--max-input-files", type=int, default=12, help="0 means decode all selected files.")
    parser.add_argument("--decode-workers", type=int, default=4)
    parser.add_argument("--out", default=str(ROOT / "outputs" / "patient_from_media.json"))
    args = parser.parse_args()

    patient = patient_from_media(
        args.input,
        project_root=args.project_root,
        measurements=parse_measurement_pairs(args.measurement),
        case_id=args.case_id,
        patient_id=args.patient_id,
        max_loaded_frames=args.max_loaded_frames,
        decode_timeout=args.decode_timeout,
        max_input_files=args.max_input_files,
        decode_workers=args.decode_workers,
    )
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(patient, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote patient JSON: {out_path}")
    print(f"Loaded frames: {patient['loaded_frame_count']}, views: {patient['views']}")


if __name__ == "__main__":
    main()

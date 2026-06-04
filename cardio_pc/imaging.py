from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageSequence


STATIC_IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".tif",
    ".tiff",
    ".webp",
    ".heic",
    ".heif",
}

ANIMATED_IMAGE_EXTENSIONS = {
    ".gif",
    ".apng",
}

DICOM_EXTENSIONS = {".dcm", ".dicom", ".dcom"}

VIDEO_EXTENSIONS = {
    ".mp4",
    ".m4v",
    ".mov",
    ".avi",
    ".mkv",
    ".webm",
    ".wmv",
    ".mpg",
    ".mpeg",
    ".ts",
    ".mts",
    ".m2ts",
    ".3gp",
    ".cine",
}

SUPPORTED_EXTENSIONS = STATIC_IMAGE_EXTENSIONS | ANIMATED_IMAGE_EXTENSIONS | DICOM_EXTENSIONS | VIDEO_EXTENSIONS

MAX_FRAMES_PER_CINE = 48
DEFAULT_VIDEO_STRIDE = 0
MIN_PARALLEL_LOAD_FILES = 4
MAX_LOAD_WORKERS = max(1, min(8, (os.cpu_count() or 4) - 1))
FAST_CINE_MODE_ENV = "CARDIO_FAST_CINE_MODE"
FAST_CINE_AUTO_MAX_FRAMES = 24


@dataclass(frozen=True)
class LoadedImage:
    path: Path
    frame_index: int
    image: np.ndarray
    source_type: str
    metadata: dict[str, Any]

    @property
    def display_name(self) -> str:
        suffix = f"#{self.frame_index}" if self.frame_index else ""
        return f"{self.path.name}{suffix}"


def is_supported(path: str | Path) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS


def load_files(paths: list[str | Path]) -> list[LoadedImage]:
    loaded: list[LoadedImage] = []
    errors: list[str] = []

    raw_paths = [Path(raw_path) for raw_path in paths]
    if len(raw_paths) >= MIN_PARALLEL_LOAD_FILES and MAX_LOAD_WORKERS > 1:
        workers = min(MAX_LOAD_WORKERS, len(raw_paths))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            results = list(executor.map(load_one_path, raw_paths))
    else:
        results = [load_one_path(path) for path in raw_paths]

    for frames, error in results:
        if frames:
            loaded.extend(frames)
        if error:
            errors.append(error)

    if errors and not loaded:
        raise RuntimeError("\n".join(errors))
    return loaded


def load_one_path(path: Path) -> tuple[list[LoadedImage], str]:
    if not path.exists():
        return [], f"{path}: file not found"
    try:
        suffix = path.suffix.lower()
        if suffix in DICOM_EXTENSIONS:
            return load_dicom(path), ""
        if suffix in VIDEO_EXTENSIONS:
            return load_video(path), ""
        if suffix in SUPPORTED_EXTENSIONS:
            return load_pillow_image_or_animation(path), ""
        return load_unknown_by_probe(path), ""
    except Exception as exc:  # noqa: BLE001 - UI needs concrete messages.
        return [], f"{path.name}: load failed: {exc}"


def load_pillow_image_or_animation(path: Path) -> list[LoadedImage]:
    register_optional_pillow_plugins()
    with Image.open(path) as image:
        n_frames = int(getattr(image, "n_frames", 1) or 1)
        if n_frames <= 1:
            return [loaded_from_pil(path, 0, image.convert("RGB"), "raster", {"n_frames": "1"})]

        out: list[LoadedImage] = []
        for output_index, frame_index in enumerate(sample_indices(n_frames, MAX_FRAMES_PER_CINE)):
            image.seek(frame_index)
            frame = image.convert("RGB")
            out.append(
                loaded_from_pil(
                    path,
                    output_index,
                    frame,
                    "animated_image",
                    {"n_frames": str(n_frames), "source_frame_index": str(frame_index)},
                )
            )
        return out


def load_unknown_by_probe(path: Path) -> list[LoadedImage]:
    errors: list[str] = []
    for loader_name, loader in (
        ("DICOM", load_dicom),
        ("Pillow", load_pillow_image_or_animation),
        ("video", load_video),
    ):
        try:
            return loader(path)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{loader_name}: {exc}")
    raise RuntimeError("unsupported or undecodable file; " + " | ".join(errors))


def register_optional_pillow_plugins() -> None:
    try:
        from pillow_heif import register_heif_opener

        register_heif_opener()
    except Exception:
        pass


def loaded_from_pil(path: Path, frame_index: int, image: Image.Image, source_type: str, metadata: dict[str, Any]) -> LoadedImage:
    arr = np.asarray(image, dtype=np.uint8).copy()
    return LoadedImage(
        path=path,
        frame_index=frame_index,
        image=arr,
        source_type=source_type,
        metadata=metadata,
    )


def load_video(path: Path) -> list[LoadedImage]:
    errors: list[str] = []
    try:
        return load_video_with_imageio(path)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"imageio: {exc}")
    try:
        return load_video_with_cv2(path)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"opencv: {exc}")
    raise RuntimeError("video decoder unavailable or failed; " + " | ".join(errors))


def load_video_with_imageio(path: Path) -> list[LoadedImage]:
    try:
        import imageio.v2 as imageio
    except ModuleNotFoundError as exc:
        raise RuntimeError("imageio is not installed") from exc

    reader = imageio.get_reader(str(path), format="ffmpeg")
    try:
        try:
            total_raw = reader.count_frames()
            total = int(total_raw) if np.isfinite(total_raw) and total_raw > 0 else 0
        except Exception:
            total = 0

        out: list[LoadedImage] = []
        if total > 0:
            indices = sample_indices(total, MAX_FRAMES_PER_CINE)
            for output_index, frame_index in enumerate(indices):
                frame = reader.get_data(frame_index)
                out.append(
                    LoadedImage(
                        path=path,
                        frame_index=output_index,
                        image=ensure_rgb(frame),
                        source_type="video",
                        metadata={"decoder": "imageio-ffmpeg", "n_frames": str(total), "source_frame_index": str(frame_index)},
                    )
                )
        else:
            for output_index, frame in enumerate(reader):
                if output_index >= MAX_FRAMES_PER_CINE:
                    break
                out.append(
                    LoadedImage(
                        path=path,
                        frame_index=output_index,
                        image=ensure_rgb(frame),
                        source_type="video",
                        metadata={"decoder": "imageio-ffmpeg", "n_frames": "unknown", "source_frame_index": str(output_index)},
                    )
                )

        if not out:
            raise RuntimeError("no frames decoded by imageio")
        return out
    finally:
        reader.close()


def load_video_with_cv2(path: Path) -> list[LoadedImage]:
    try:
        import cv2
    except ModuleNotFoundError as exc:
        raise RuntimeError("opencv-python is not installed") from exc

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise RuntimeError("OpenCV could not open video")
    try:
        total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if total <= 0:
            total = MAX_FRAMES_PER_CINE
        indices = sample_indices(total, MAX_FRAMES_PER_CINE)
        out: list[LoadedImage] = []
        for output_index, frame_index in enumerate(indices):
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ok, frame = capture.read()
            if not ok or frame is None:
                continue
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            out.append(
                LoadedImage(
                    path=path,
                    frame_index=output_index,
                    image=ensure_rgb(rgb),
                    source_type="video",
                    metadata={"decoder": "opencv", "n_frames": str(total), "source_frame_index": str(frame_index)},
                )
            )
        if not out:
            raise RuntimeError("no frames decoded by OpenCV")
        return out
    finally:
        capture.release()


def load_dicom(path: Path) -> list[LoadedImage]:
    try:
        import pydicom
    except ModuleNotFoundError as exc:
        raise RuntimeError("pydicom is not installed. Run install_deps.bat first.") from exc

    dataset = pydicom.dcmread(str(path), force=True)
    if not hasattr(dataset, "pixel_array"):
        raise RuntimeError("DICOM has no pixel data")

    pixel = dataset.pixel_array
    frames = _split_dicom_frames(pixel, getattr(dataset, "SamplesPerPixel", 1))
    indices = sample_indices(len(frames), MAX_FRAMES_PER_CINE)
    metadata = {
        "PatientID": str(getattr(dataset, "PatientID", "")),
        "StudyDate": str(getattr(dataset, "StudyDate", "")),
        "StudyDescription": str(getattr(dataset, "StudyDescription", "")),
        "SeriesDescription": str(getattr(dataset, "SeriesDescription", "")),
        "PhotometricInterpretation": str(getattr(dataset, "PhotometricInterpretation", "")),
        "Modality": str(getattr(dataset, "Modality", "")),
        "NumberOfFrames": str(getattr(dataset, "NumberOfFrames", len(frames))),
        "FrameTime": str(getattr(dataset, "FrameTime", "")),
    }

    out: list[LoadedImage] = []
    for output_index, source_index in enumerate(indices):
        rgb = _dicom_frame_to_rgb(frames[source_index], dataset)
        merged_metadata = {**metadata, "source_frame_index": str(source_index)}
        out.append(
            LoadedImage(
                path=path,
                frame_index=output_index,
                image=rgb,
                source_type="dicom",
                metadata=merged_metadata,
            )
        )
    return out


def _split_dicom_frames(pixel: np.ndarray, samples_per_pixel: int) -> list[np.ndarray]:
    arr = np.asarray(pixel)
    if arr.ndim == 2:
        return [arr]
    if arr.ndim == 3 and samples_per_pixel == 3:
        return [arr]
    if arr.ndim == 3:
        return [arr[index] for index in range(arr.shape[0])]
    if arr.ndim == 4:
        return [arr[index] for index in range(arr.shape[0])]
    raise RuntimeError(f"Unsupported DICOM pixel shape: {arr.shape}")


def _dicom_frame_to_rgb(frame: np.ndarray, dataset: Any) -> np.ndarray:
    arr = np.asarray(frame)
    if arr.ndim == 3 and arr.shape[-1] >= 3:
        rgb = arr[..., :3].astype(np.float32)
        rgb = _normalize_to_uint8(rgb)
        return rgb

    image = arr.astype(np.float32)
    slope = float(getattr(dataset, "RescaleSlope", 1.0) or 1.0)
    intercept = float(getattr(dataset, "RescaleIntercept", 0.0) or 0.0)
    image = image * slope + intercept

    center = _first_number(getattr(dataset, "WindowCenter", None))
    width = _first_number(getattr(dataset, "WindowWidth", None))
    if center is not None and width and width > 1:
        low = center - width / 2.0
        high = center + width / 2.0
        image = np.clip((image - low) / max(high - low, 1e-6), 0.0, 1.0) * 255.0

    if str(getattr(dataset, "PhotometricInterpretation", "")).upper() == "MONOCHROME1":
        image = image.max() - image

    gray = _normalize_to_uint8(image)
    return np.stack([gray, gray, gray], axis=-1)


def ensure_rgb(arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr)
    if arr.ndim == 2:
        return np.stack([_normalize_to_uint8(arr)] * 3, axis=-1)
    if arr.ndim == 3 and arr.shape[-1] >= 3:
        return _normalize_to_uint8(arr[..., :3])
    raise ValueError(f"Unsupported frame shape: {arr.shape}")


def _normalize_to_uint8(arr: np.ndarray) -> np.ndarray:
    if arr.dtype == np.uint8:
        return arr.copy()
    arr = arr.astype(np.float32)
    low = float(np.percentile(arr, 1))
    high = float(np.percentile(arr, 99))
    denom = max(high - low, 1e-6)
    scaled = np.clip((arr - low) / denom, 0.0, 1.0)
    return (scaled * 255.0).astype(np.uint8)


def sample_indices(total_frames: int, max_frames: int = MAX_FRAMES_PER_CINE) -> list[int]:
    total_frames = max(1, int(total_frames))
    max_frames = max(1, int(max_frames))
    if should_use_fast_cine_auto(total_frames, max_frames):
        max_frames = FAST_CINE_AUTO_MAX_FRAMES
    if total_frames <= max_frames:
        return list(range(total_frames))
    return sorted({int(round(value)) for value in np.linspace(0, total_frames - 1, max_frames)})


def should_use_fast_cine_auto(total_frames: int, max_frames: int) -> bool:
    mode = os.environ.get(FAST_CINE_MODE_ENV, "off").strip().lower()
    return mode == "auto" and max_frames == MAX_FRAMES_PER_CINE and total_frames > FAST_CINE_AUTO_MAX_FRAMES


def _first_number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        value = value[0] if value else None
    try:
        if hasattr(value, "__iter__") and not isinstance(value, str):
            value = list(value)[0]
        return float(value)
    except Exception:
        return None

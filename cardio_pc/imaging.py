from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


SUPPORTED_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".tif",
    ".tiff",
    ".dcm",
    ".dicom",
    ".dcom",
}

DICOM_EXTENSIONS = {".dcm", ".dicom", ".dcom"}


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

    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists():
            errors.append(f"{path}: file not found")
            continue
        if path.suffix.lower() in DICOM_EXTENSIONS:
            try:
                loaded.extend(load_dicom(path))
            except Exception as exc:  # noqa: BLE001 - UI needs the concrete message.
                errors.append(f"{path.name}: DICOM load failed: {exc}")
        elif is_supported(path):
            try:
                loaded.append(load_raster(path))
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{path.name}: image load failed: {exc}")
        else:
            errors.append(f"{path.name}: unsupported extension")

    if errors and not loaded:
        raise RuntimeError("\n".join(errors))
    return loaded


def load_raster(path: Path) -> LoadedImage:
    with Image.open(path) as image:
        rgb = image.convert("RGB")
        arr = np.asarray(rgb, dtype=np.uint8).copy()
    return LoadedImage(
        path=path,
        frame_index=0,
        image=arr,
        source_type="raster",
        metadata={},
    )


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
    metadata = {
        "PatientID": str(getattr(dataset, "PatientID", "")),
        "StudyDate": str(getattr(dataset, "StudyDate", "")),
        "StudyDescription": str(getattr(dataset, "StudyDescription", "")),
        "SeriesDescription": str(getattr(dataset, "SeriesDescription", "")),
        "PhotometricInterpretation": str(getattr(dataset, "PhotometricInterpretation", "")),
        "Modality": str(getattr(dataset, "Modality", "")),
    }

    out: list[LoadedImage] = []
    for index, frame in enumerate(frames):
        rgb = _dicom_frame_to_rgb(frame, dataset)
        out.append(
            LoadedImage(
                path=path,
                frame_index=index,
                image=rgb,
                source_type="dicom",
                metadata=metadata,
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


def _normalize_to_uint8(arr: np.ndarray) -> np.ndarray:
    arr = arr.astype(np.float32)
    low = float(np.percentile(arr, 1))
    high = float(np.percentile(arr, 99))
    denom = max(high - low, 1e-6)
    scaled = np.clip((arr - low) / denom, 0.0, 1.0)
    return (scaled * 255.0).astype(np.uint8)


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

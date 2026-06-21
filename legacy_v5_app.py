from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image

from cardio_pc.diagnosis import ModelConfig, load_config, run_diagnosis
from cardio_pc.features import analyze_loaded_images
from cardio_pc.imaging import LoadedImage
from cardio_pc.ui import CardioConsultPCApp


def main() -> None:
    parser = argparse.ArgumentParser(description="CardioConsult PC")
    parser.add_argument("--self-test", action="store_true", help="Run a non-GUI processing self-test.")
    parser.add_argument(
        "--self-test-rule-only",
        action="store_true",
        help="Run the self-test with the auditable rule backend only, without invoking GGUF.",
    )
    args = parser.parse_args()
    if args.self_test or args.self_test_rule_only:
        self_test(rule_only=args.self_test_rule_only)
    else:
        CardioConsultPCApp().mainloop()


def self_test(rule_only: bool = False) -> None:
    sample_dir = Path(__file__).resolve().parent / "samples"
    sample_dir.mkdir(parents=True, exist_ok=True)
    diastole = synthetic_echo(chamber_radius=62, doppler=False)
    systole = synthetic_echo(chamber_radius=38, doppler=True)
    dia_path = sample_dir / "A4C_ED_synthetic.png"
    sys_path = sample_dir / "A4C_ES_synthetic.png"
    Image.fromarray(diastole).save(dia_path)
    Image.fromarray(systole).save(sys_path)

    loaded = [
        LoadedImage(dia_path, 0, diastole, "synthetic", {}),
        LoadedImage(sys_path, 0, systole, "synthetic", {}),
    ]
    study = analyze_loaded_images(loaded)
    config = ModelConfig(llama_exe="", model_path="", use_server=False) if rule_only else load_config()
    report, status = run_diagnosis(study, config)
    if "教学参考病症判断：" not in report or "最小病症：" not in report or "逻辑链：" not in report:
        raise RuntimeError("Self-test failed: required diagnosis fields are missing.")
    print("SELF TEST OK")
    print(study.compact_feature_text())
    print(status)
    print(report)


def synthetic_echo(chamber_radius: int, doppler: bool) -> np.ndarray:
    size = 256
    yy, xx = np.mgrid[0:size, 0:size]
    center = np.array([132, 126])
    dist = np.sqrt((xx - center[0]) ** 2 + ((yy - center[1]) * 1.25) ** 2)
    img = np.full((size, size), 34, dtype=np.float32)
    myocardium = (dist > chamber_radius) & (dist < chamber_radius + 24)
    chamber = dist <= chamber_radius
    img[myocardium] = 172
    img[chamber] = 12
    img += np.clip((xx + yy) / 8, 0, 45)
    rgb = np.stack([img, img, img], axis=-1)
    if doppler:
        jet = (np.abs(xx - yy + 18) < 10) & (dist < chamber_radius + 40)
        rgb[jet, 0] = 240
        rgb[jet, 1] = 36
        rgb[jet, 2] = 42
        blue = (np.abs(xx + yy - 255) < 8) & (dist < chamber_radius + 36)
        rgb[blue, 0] = 30
        rgb[blue, 1] = 70
        rgb[blue, 2] = 235
    noise = np.random.default_rng(12).normal(0, 6, rgb.shape)
    return np.clip(rgb + noise, 0, 255).astype(np.uint8)


if __name__ == "__main__":
    main()

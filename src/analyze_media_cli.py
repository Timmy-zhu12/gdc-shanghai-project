from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from clinical_rule_engine import DEFAULT_RULEBOOK, evaluate_patient, load_json
from image_case_adapter import DEFAULT_PROJECT_ROOT, parse_measurement_pairs, patient_from_media


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze real ultrasound media files with the clinical rulebook engine.")
    parser.add_argument("--input", action="append", required=True, help="Ultrasound file or patient folder. Can be repeated.")
    parser.add_argument("--project-root", default=str(DEFAULT_PROJECT_ROOT))
    parser.add_argument("--rulebook", default=str(DEFAULT_RULEBOOK))
    parser.add_argument("--measurement", action="append", default=[], help="Optional measurement, e.g. ef_percent=43")
    parser.add_argument("--case-id", default="")
    parser.add_argument("--patient-id", default="")
    parser.add_argument("--max-loaded-frames", type=int, default=48)
    parser.add_argument("--decode-timeout", type=float, default=6.0)
    parser.add_argument("--max-input-files", type=int, default=12)
    parser.add_argument("--decode-workers", type=int, default=4)
    parser.add_argument("--out", default="")
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
    rulebook = load_json(args.rulebook)
    result = evaluate_patient(patient, rulebook)
    payload = {"patient": patient, "result": result}
    out_path = Path(args.out) if args.out else ROOT / "outputs" / f"media_rule_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(result["教学参考病症判断"])
    print("最小病症：" + result["最小病症"])
    print("逻辑链：" + result["逻辑链"])
    print(f"Wrote: {out_path}")


if __name__ == "__main__":
    main()

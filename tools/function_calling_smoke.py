from __future__ import annotations

import json
from pathlib import Path
import sys


PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from app import synthetic_echo  # noqa: E402
from cardio_pc.diagnosis import classify_teaching_condition_v4, heuristic_diagnosis  # noqa: E402
from cardio_pc.features import analyze_loaded_images  # noqa: E402
from cardio_pc.function_calling import execute_tool_call, gemma4_tool_manifest  # noqa: E402
from cardio_pc.imaging import LoadedImage  # noqa: E402


def main() -> None:
    diastole = synthetic_echo(chamber_radius=62, doppler=False)
    systole = synthetic_echo(chamber_radius=38, doppler=True)
    loaded = [
        LoadedImage(PROJECT_DIR / "samples" / "toolcall_ED.png", 0, diastole, "synthetic", {}),
        LoadedImage(PROJECT_DIR / "samples" / "toolcall_ES.png", 1, systole, "synthetic", {}),
    ]
    study = analyze_loaded_images(loaded)
    decision = classify_teaching_condition_v4(study)

    def rule_report() -> str:
        return heuristic_diagnosis(study, decision)

    feature_result = execute_tool_call(
        {"function_call": {"name": "summarize_ultrasound_features", "arguments": {}}},
        study,
        rule_report,
    )
    report_result = execute_tool_call(
        {"function_call": {"name": "run_rule_diagnosis", "arguments": {}}},
        study,
        rule_report,
    )
    rejected = execute_tool_call(
        {"function_call": {"name": "read_local_file", "arguments": {"path": "config.json"}}},
        study,
        rule_report,
    )

    if not feature_result.ok or not report_result.ok or rejected.ok:
        raise RuntimeError("function calling smoke failed")
    if "教学参考病症判断" not in str(report_result.payload.get("report", "")):
        raise RuntimeError("rule report was not returned by function call")

    print(
        json.dumps(
            {
                "function_calling_smoke": "ok",
                "tools": [tool["name"] for tool in gemma4_tool_manifest()],
                "feature_view_count": feature_result.payload["view_count"],
                "rejected_tool": rejected.name,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

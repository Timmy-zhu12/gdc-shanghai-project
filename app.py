from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
SRC = Path(__file__).resolve().parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def self_test_rule_only() -> int:
    from clinical_rule_engine import DEFAULT_RULEBOOK, evaluate_patient, load_json

    rulebook = load_json(DEFAULT_RULEBOOK)
    patient = load_json(ROOT / "examples" / "sample_patient_clinical.json")
    result = evaluate_patient(patient, rulebook)
    print("SELF TEST OK")
    print("教学参考病症判断：" + result.get("教学参考病症判断", ""))
    print("最小病症：" + result.get("最小病症", ""))
    print("逻辑链：" + result.get("逻辑链", ""))
    return 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        from legacy_v5_app import self_test

        self_test(rule_only=False)
        raise SystemExit(0)
    if "--self-test-rule-only" in sys.argv:
        raise SystemExit(self_test_rule_only())
    from rulebook_ui import main

    main()

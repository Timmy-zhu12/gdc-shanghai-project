from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RULEBOOK = ROOT / "config" / "clinical_rulebook_v0.1.json"
SEVERITY_RANK = {"none": 0, "trace": 1, "mild": 2, "suggestive": 2, "abnormal_component": 2, "supportive": 2, "moderate": 3, "high_probability_component": 3, "severe": 4}
SEVERITY_ZH = {
    "none": "未见明确异常",
    "trace": "微量",
    "mild": "轻度",
    "suggestive": "提示",
    "abnormal_component": "异常指标",
    "supportive": "支持证据",
    "moderate": "中度",
    "high_probability_component": "高概率组成证据",
    "severe": "重度",
    "unknown": "程度未定"
}


def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def dump_json(path: str | Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        out = float(value)
    except Exception:
        return None
    if not math.isfinite(out):
        return None
    return out


def check_condition(value: float, condition: dict[str, Any]) -> bool:
    op = condition["op"]
    if op == "<":
        return value < float(condition["value"])
    if op == "<=":
        return value <= float(condition["value"])
    if op == ">":
        return value > float(condition["value"])
    if op == ">=":
        return value >= float(condition["value"])
    if op == "range_closed_open":
        return float(condition["low"]) <= value < float(condition["high"])
    if op == "range_closed":
        return float(condition["low"]) <= value <= float(condition["high"])
    if op == "range_open_open":
        return float(condition["low"]) < value < float(condition["high"])
    if op == "range_open_closed":
        return float(condition["low"]) < value <= float(condition["high"])
    raise ValueError(f"Unsupported condition op: {op}")


def proxy_severity(value: float, threshold: dict[str, Any]) -> str | None:
    direction = threshold.get("direction")
    mild = to_float(threshold.get("mild"))
    moderate = to_float(threshold.get("moderate"))
    severe = to_float(threshold.get("severe"))
    if direction == "higher_is_worse":
        if severe is not None and value >= severe:
            return "severe"
        if moderate is not None and value >= moderate:
            return "moderate"
        if mild is not None and value >= mild:
            return "mild"
    if direction == "lower_is_worse":
        if severe is not None and value <= severe:
            return "severe"
        if moderate is not None and value <= moderate:
            return "moderate"
        if mild is not None and value <= mild:
            return "mild"
    return None


def severity_max(values: list[str]) -> str:
    if not values:
        return "unknown"
    return max(values, key=lambda item: SEVERITY_RANK.get(item, 0))


def severity_score(severity: str) -> float:
    return min(1.0, SEVERITY_RANK.get(severity, 0) / 4.0)


def patient_from_current_feature_row(row: dict[str, Any], rulebook: dict[str, Any]) -> dict[str, Any]:
    mapping = rulebook["feature_mapping"]["current_cardioconsult_csv"]
    proxies: dict[str, float] = {}
    for logical_name, column in mapping.items():
        value = to_float(row.get(column))
        if value is not None:
            proxies[logical_name] = value
    measurements: dict[str, float] = {}
    ef = to_float(row.get("ef_numeric") or row.get("ef"))
    if ef is not None:
        measurements["ef_percent"] = ef
    return {
        "case_id": row.get("case_id", ""),
        "patient_id": row.get("patient_id", ""),
        "diagnosis_text": row.get("diagnosis_text", ""),
        "measurements": measurements,
        "proxies": proxies,
        "views": [],
        "source": "current_cardioconsult_features_csv"
    }


def requirement_notes(rule: dict[str, Any], patient: dict[str, Any]) -> tuple[bool, list[str], list[str]]:
    req = rule.get("requirements", {})
    proxies = patient.get("proxies", {})
    measurements = patient.get("measurements", {})
    views = set(patient.get("views", []) or [])
    missing: list[str] = []
    warnings: list[str] = []
    ok = True
    quality = to_float(proxies.get("quality_score"))
    quality_min = to_float(req.get("quality_score_gte"))
    if quality_min is not None and quality is not None and quality < quality_min:
        ok = False
        missing.append(f"quality_score {quality:.3f} < {quality_min:.3f}")
    if req.get("dynamic_pair_required"):
        systole = to_float(proxies.get("systole_count")) or 0.0
        diastole = to_float(proxies.get("diastole_count")) or 0.0
        if systole < 1 or diastole < 1:
            ok = False
            missing.append("缺少收缩态/舒张态配对")
    if req.get("color_doppler_required"):
        if to_float(proxies.get("flow_active_ratio")) is None and not any(key.startswith(("mr_", "tr_", "ar_")) for key in measurements):
            ok = False
            missing.append("缺少彩色多普勒或反流定量指标")
    if req.get("spectral_doppler_required_for_grading"):
        needed = {"aortic_vmax_m_s", "aortic_mean_gradient_mmhg", "aortic_valve_area_cm2"}
        if not (needed & set(measurements)):
            warnings.append("缺少频谱多普勒定量指标，主动脉瓣狭窄只能作为代理筛查提示")
    if req.get("tissue_doppler_required"):
        needed = {"average_e_over_e_prime", "septal_e_prime_cm_s", "lateral_e_prime_cm_s", "la_volume_index_ml_m2", "tr_peak_velocity_m_s"}
        if not (needed & set(measurements)):
            ok = False
            missing.append("缺少组织多普勒/LA/TRV 舒张功能指标")
    preferred = set(req.get("preferred_views", []))
    if preferred and views and not (preferred & views):
        warnings.append("当前显式体位未覆盖该规则推荐切面")
    return ok, missing, warnings


def evaluate_rule(rule: dict[str, Any], patient: dict[str, Any]) -> dict[str, Any]:
    measurements = patient.get("measurements", {})
    proxies = patient.get("proxies", {})
    ok, missing, warnings = requirement_notes(rule, patient)
    clinical_hits: list[dict[str, Any]] = []
    proxy_hits: list[dict[str, Any]] = []
    clinical_severities: list[str] = []
    proxy_severities: list[str] = []
    relevant_clinical_present = any(
        to_float(measurements.get(threshold["measurement"])) is not None
        for threshold in rule.get("clinical_thresholds", [])
    )

    for threshold in rule.get("clinical_thresholds", []):
        measurement = threshold["measurement"]
        value = to_float(measurements.get(measurement))
        if value is None:
            continue
        if check_condition(value, threshold):
            severity = threshold["severity"]
            clinical_severities.append(severity)
            clinical_hits.append(
                {
                    "measurement": measurement,
                    "value": value,
                    "unit": threshold.get("unit", ""),
                    "severity": severity,
                    "condition": {key: value for key, value in threshold.items() if key not in {"measurement", "unit"}}
                }
            )

    if not (relevant_clinical_present and not clinical_hits):
        for threshold in rule.get("proxy_thresholds", []):
            feature = threshold["feature"]
            value = to_float(proxies.get(feature))
            if value is None:
                continue
            severity = proxy_severity(value, threshold)
            if severity:
                proxy_severities.append(severity)
                proxy_hits.append(
                    {
                        "feature": feature,
                        "value": value,
                        "severity": severity,
                        "calibration": threshold.get("calibration", "")
                    }
                )
    elif rule.get("proxy_thresholds"):
        warnings.append("存在相关临床量化指标且未命中异常阈值，代理异常不覆盖临床量化结果")

    if proxy_hits and not clinical_hits and rule.get("requirements", {}).get("proxy_localization_required"):
        preferred = set(rule.get("requirements", {}).get("preferred_views", []))
        views = set(patient.get("views", []) or [])
        if not views or not (preferred & views):
            warnings.append("缺少明确瓣膜定位/推荐切面，取消具体瓣膜 proxy-only 诊断")
            proxy_hits = []
            proxy_severities = []

    has_clinical = bool(clinical_hits)
    has_proxy = bool(proxy_hits)
    severity = severity_max(clinical_severities or proxy_severities)
    score = 0.0
    if has_clinical:
        score += 0.72 * severity_score(severity)
    if has_proxy:
        score += 0.35 * max(severity_score(item) for item in proxy_severities)
    if ok:
        score += 0.10
    else:
        score -= 0.18
    quality = to_float(proxies.get("quality_score"))
    if quality is not None:
        score += 0.10 * max(0.0, min(1.0, quality))
    if has_clinical or has_proxy:
        score += max(0.0, min(0.15, to_float(rule.get("score_bonus")) or 0.0))
    score = max(0.0, min(1.0, score))

    if has_clinical and ok:
        evidence_level = "A"
    elif has_clinical:
        evidence_level = "B"
    elif has_proxy and ok:
        evidence_level = "B" if (to_float(proxies.get("view_count")) or 0) >= 2 else "C"
    elif has_proxy:
        evidence_level = "C"
    else:
        evidence_level = "D"

    return {
        "rule_id": rule["id"],
        "label": rule["label"],
        "zh": rule["zh"],
        "category": rule["category"],
        "severity": severity if (has_clinical or has_proxy) else "none",
        "score": round(score, 4),
        "evidence_level": evidence_level,
        "proxy_only": bool(has_proxy and not has_clinical),
        "clinical_hits": clinical_hits,
        "proxy_hits": proxy_hits,
        "missing_or_blocking": missing,
        "warnings": warnings,
        "logic": rule.get("logic", ""),
        "references": rule.get("references", [])
    }


def evaluate_patient(patient: dict[str, Any], rulebook: dict[str, Any]) -> dict[str, Any]:
    results = [evaluate_rule(rule, patient) for rule in rulebook["rules"]]
    positive = [item for item in results if item["severity"] != "none" and item["score"] > 0.18]
    positive.sort(key=lambda item: (item["score"], SEVERITY_RANK.get(item["severity"], 0)), reverse=True)
    if positive:
        top = positive[0]
        disease = f"{SEVERITY_ZH.get(top['severity'], top['severity'])}{top['zh']}" if top["severity"] in {"mild", "moderate", "severe"} else top["zh"]
        judgment = f"{top['category']} > {top['zh']} > {disease}"
        minimum = disease
        logic_chain = build_logic_chain(top, patient)
    else:
        judgment = "证据不足 > 未见明确可量化心超异常"
        minimum = "未见明确可量化心超异常"
        logic_chain = "未达到临床量化阈值或代理阈值；建议补充标准切面与必要频谱/测量。"
    return {
        "case_id": patient.get("case_id", ""),
        "patient_id": patient.get("patient_id", ""),
        "教学参考病症判断": judgment,
        "最小病症": minimum,
        "逻辑链": logic_chain,
        "top_results": positive[:5],
        "all_results": results,
        "manual_version": rulebook["version"],
        "safety_boundary": "本输出仅用于医学教学、质量控制和算法测试；不作为临床最终诊断、治疗建议或医嘱。"
    }


def build_logic_chain(result: dict[str, Any], patient: dict[str, Any]) -> str:
    clinical = "; ".join(
        f"{hit['measurement']}={hit['value']}{hit.get('unit','')} 命中 {hit['severity']}"
        for hit in result["clinical_hits"]
    )
    proxy = "; ".join(
        f"{hit['feature']}={hit['value']:.3f} 命中 {hit['severity']}"
        for hit in result["proxy_hits"]
    )
    quality = patient.get("proxies", {}).get("quality_score", "NA")
    view_count = patient.get("proxies", {}).get("view_count", "NA")
    parts = [f"规则 {result['rule_id']}", f"证据等级 {result['evidence_level']}", f"质量分 {quality}", f"体位数 {view_count}"]
    if clinical:
        parts.append("临床量化: " + clinical)
    if proxy:
        parts.append("代理特征: " + proxy)
    if result["missing_or_blocking"]:
        parts.append("缺失/限制: " + "; ".join(result["missing_or_blocking"]))
    if result["proxy_only"]:
        parts.append("仅代理证据，需用 1000 例数据校准并由医生复核")
    return " → ".join(parts)


def read_feature_csv(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def run_json(input_path: Path, rulebook: dict[str, Any]) -> list[dict[str, Any]]:
    payload = load_json(input_path)
    patients = payload if isinstance(payload, list) else [payload]
    return [evaluate_patient(patient, rulebook) for patient in patients]


def run_features_csv(path: Path, rulebook: dict[str, Any], limit: int = 0) -> list[dict[str, Any]]:
    rows = read_feature_csv(path)
    if limit > 0:
        rows = rows[:limit]
    patients = [patient_from_current_feature_row(row, rulebook) for row in rows]
    return [evaluate_patient(patient, rulebook) for patient in patients]


def main() -> None:
    parser = argparse.ArgumentParser(description="CardioConsult clinical rulebook test engine.")
    parser.add_argument("--rulebook", default=str(DEFAULT_RULEBOOK))
    parser.add_argument("--input-json", default="")
    parser.add_argument("--features-csv", default="")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--out", default="outputs/rulebook_results.json")
    args = parser.parse_args()

    rulebook = load_json(args.rulebook)
    if args.input_json:
        results = run_json(Path(args.input_json), rulebook)
    elif args.features_csv:
        results = run_features_csv(Path(args.features_csv), rulebook, args.limit)
    else:
        raise SystemExit("Provide --input-json or --features-csv.")
    dump_json(args.out, results)
    for item in results[:10]:
        print(f"{item['case_id']}: {item['教学参考病症判断']} | {item['最小病症']}")
        print(f"  {item['逻辑链']}")
    print(f"Wrote {len(results)} result(s) to {args.out}")


if __name__ == "__main__":
    main()

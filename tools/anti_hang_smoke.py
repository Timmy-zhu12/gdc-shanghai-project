from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app import synthetic_echo
from cardio_pc.diagnosis import ModelConfig, run_diagnosis
from cardio_pc.features import analyze_loaded_images
from cardio_pc.imaging import LoadedImage, load_files


REQUIRED_REPORT_MARKERS = ("教学参考病症判断：", "最小病症：", "逻辑链：")


def make_synthetic_study():
    dia = synthetic_echo(chamber_radius=62, doppler=False)
    sys = synthetic_echo(chamber_radius=38, doppler=True)
    loaded = [
        LoadedImage(Path("anti_hang_A4C_ED.png"), 0, dia, "synthetic", {}),
        LoadedImage(Path("anti_hang_A4C_ES.png"), 0, sys, "synthetic", {}),
    ]
    return analyze_loaded_images(loaded)


def assert_report_contract(report: str) -> None:
    missing = [marker for marker in REQUIRED_REPORT_MARKERS if marker not in report]
    if missing:
        raise AssertionError(f"report missing required markers: {missing}")


def smoke_rule_mode() -> dict[str, object]:
    study = make_synthetic_study()
    config = ModelConfig(inference_mode="rule_only", llama_exe="", model_path="", use_server=False)
    started = time.perf_counter()
    report, status = run_diagnosis(study, config)
    elapsed = time.perf_counter() - started
    assert_report_contract(report)
    if elapsed > 5:
        raise AssertionError(f"rule-only mode took too long: {elapsed:.3f}s")
    if "Gemma4" in status and "skipped" not in status:
        raise AssertionError(f"rule-only mode unexpectedly waited for Gemma4: {status}")
    return {"name": "rule_only_fast", "elapsed_seconds": round(elapsed, 3), "status": status}


class SlowCompletionHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API.
        time.sleep(5)
        body = json.dumps({"content": "too late"}, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *_args) -> None:
        return


def smoke_slow_server_timeout() -> dict[str, object]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), SlowCompletionHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        study = make_synthetic_study()
        config = ModelConfig(
            inference_mode="gemma4_server",
            use_server=True,
            server_url=f"http://127.0.0.1:{server.server_port}",
            llm_timeout_seconds=2,
            llama_exe="",
            model_path="",
        )
        started = time.perf_counter()
        report, status = run_diagnosis(study, config)
        elapsed = time.perf_counter() - started
        assert_report_contract(report)
        if elapsed > 4.5:
            raise AssertionError(f"slow server fallback took too long: {elapsed:.3f}s")
        if "防卡保护" not in report:
            raise AssertionError("slow server fallback did not record anti-hang degrade note")
        return {"name": "slow_server_timeout", "elapsed_seconds": round(elapsed, 3), "status": status}
    finally:
        server.shutdown()
        server.server_close()


def smoke_slow_decode_timeout() -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "anti_hang_sleep.dcm"
        path.write_bytes(b"not a real dicom; test hook should sleep before decoding")
        old_value = os.environ.get("CARDIO_TEST_DECODE_SLEEP_SECONDS")
        os.environ["CARDIO_TEST_DECODE_SLEEP_SECONDS"] = "5"
        errors: list[str] = []
        started = time.perf_counter()
        try:
            try:
                load_files(
                    [path],
                    file_decode_timeout_seconds=2,
                    max_loaded_frames=96,
                    error_callback=errors.append,
                )
            except RuntimeError as exc:
                message = str(exc)
            else:
                raise AssertionError("slow decode unexpectedly returned frames")
        finally:
            if old_value is None:
                os.environ.pop("CARDIO_TEST_DECODE_SLEEP_SECONDS", None)
            else:
                os.environ["CARDIO_TEST_DECODE_SLEEP_SECONDS"] = old_value
        elapsed = time.perf_counter() - started
        if elapsed > 4.5:
            raise AssertionError(f"slow decode timeout took too long: {elapsed:.3f}s")
        detail = " | ".join(errors) or message
        if "timed out" not in detail:
            raise AssertionError(f"slow decode did not report timeout: {detail}")
        return {"name": "slow_decode_timeout", "elapsed_seconds": round(elapsed, 3), "detail": detail}


def main() -> int:
    results = [
        smoke_rule_mode(),
        smoke_slow_server_timeout(),
        smoke_slow_decode_timeout(),
    ]
    print(json.dumps({"anti_hang_smoke": "ok", "results": results}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

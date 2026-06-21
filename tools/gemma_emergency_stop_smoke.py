from __future__ import annotations

import threading
import time
from pathlib import Path
import sys



ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cardio_pc.diagnosis import ModelConfig, run_llama_cli


def main() -> None:
    fake_cli = ROOT / "outputs" / "fake_slow_llama_cli.bat"
    fake_cli.parent.mkdir(parents=True, exist_ok=True)
    fake_cli.write_text(
        "@echo off\r\n"
        "echo fake llama started\r\n"
        "ping -n 30 127.0.0.1 >nul\r\n"
        "echo fake llama finished\r\n",
        encoding="ascii",
    )
    cancel_event = threading.Event()
    config = ModelConfig(
        llama_exe=str(fake_cli),
        model_path=str(ROOT / "requirements.txt"),
        llm_timeout_seconds=60,
        max_tokens=8,
    )
    threading.Timer(1.0, cancel_event.set).start()
    started = time.monotonic()
    stdout, stderr = run_llama_cli("hello", config, cancel_event=cancel_event)
    elapsed = time.monotonic() - started
    print(f"elapsed_seconds={elapsed:.2f}")
    print(f"stdout={stdout[:120]}")
    print(f"stderr={stderr[:240]}")
    if elapsed > 4.0:
        raise SystemExit("Gemma CLI emergency stop took too long.")
    if "cancelled" not in stderr.lower():
        raise SystemExit("Gemma CLI emergency stop did not report cancellation.")
    print("GEMMA EMERGENCY STOP SMOKE OK")


if __name__ == "__main__":
    main()

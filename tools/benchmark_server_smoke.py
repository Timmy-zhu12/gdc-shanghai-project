from __future__ import annotations

import argparse
import json
import socket
import time
import urllib.error
import urllib.request
from pathlib import Path


def wait_port(host: str, port: int, timeout: float) -> float:
    started = time.perf_counter()
    while time.perf_counter() - started < timeout:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            try:
                sock.connect((host, port))
                return time.perf_counter() - started
            except OSError:
                time.sleep(0.5)
    raise TimeoutError(f"{host}:{port} did not become ready within {timeout:.1f}s")


def completion(base_url: str, prompt: str, n_predict: int, timeout: float) -> dict:
    payload = {
        "prompt": prompt,
        "n_predict": n_predict,
        "temperature": 0.0,
        "stream": False,
        "cache_prompt": True,
    }
    request = urllib.request.Request(
        base_url.rstrip("/") + "/completion",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    deadline = time.perf_counter() + timeout
    while True:
        try:
            with urllib.request.urlopen(request, timeout=min(30.0, timeout)) as response:
                data = json.loads(response.read().decode("utf-8", errors="replace"))
            break
        except urllib.error.HTTPError as exc:
            if exc.code != 503 or time.perf_counter() >= deadline:
                raise
            time.sleep(1.0)
    elapsed = time.perf_counter() - started
    content = str(data.get("content") or data.get("response") or data.get("text") or "")
    return {
        "elapsed_seconds": round(elapsed, 3),
        "content_excerpt": content[:120],
        "predicted_n": data.get("predicted_n"),
        "tokens_cached": data.get("tokens_cached"),
        "timings": data.get("timings", {}),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8088")
    parser.add_argument("--out", required=True)
    parser.add_argument("--wait-timeout", type=float, default=600.0)
    parser.add_argument("--request-timeout", type=float, default=600.0)
    parser.add_argument("--n-predict", type=int, default=8)
    args = parser.parse_args()

    host = args.url.split("//", 1)[-1].split("/", 1)[0].split(":", 1)[0]
    port = int(args.url.rsplit(":", 1)[-1].split("/", 1)[0])
    ready_seconds = wait_port(host, port, args.wait_timeout)
    prompt = "Output exactly: OK"
    first = completion(args.url, prompt, args.n_predict, args.request_timeout)
    second = completion(args.url, prompt, args.n_predict, args.request_timeout)
    result = {
        "server_url": args.url,
        "ready_wait_seconds": round(ready_seconds, 3),
        "n_predict": args.n_predict,
        "first_completion": first,
        "second_completion": second,
    }
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

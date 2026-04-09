from __future__ import annotations

import argparse
import json
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import requests
from requests import exceptions as requests_exceptions


DEFAULT_PROMPTS = [
    "扫地机器人吸力变弱怎么排查？",
    "拖布多久清洗一次比较合适？",
    "家里有宠物毛发，选购时更适合看哪些参数？",
    "机器人提示主刷异常，一般是什么原因？",
    "如果地图总是丢失，应该怎么处理？",
]


@dataclass
class BenchmarkResult:
    mode: str
    prompt: str
    status_code: int
    ok: bool
    total_ms: float
    first_chunk_ms: float | None = None
    session_id: str | None = None
    reply_length: int = 0
    error: str | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark AgentProject chat API and report latency metrics.",
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="FastAPI base URL")
    parser.add_argument("--username", default="benchmark_user", help="Login username")
    parser.add_argument("--password", default="benchmark-pass-123", help="Login password")
    parser.add_argument(
        "--mode",
        choices=["chat", "stream", "both"],
        default="both",
        help="Benchmark non-stream, stream, or both endpoints",
    )
    parser.add_argument("--rounds", type=int, default=100, help="How many rounds to run")
    parser.add_argument(
        "--prompts-file",
        type=Path,
        help="Optional text file containing one prompt per line",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path to save raw benchmark results as JSON",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="Per request timeout in seconds",
    )
    parser.add_argument(
        "--register-if-needed",
        action="store_true",
        help="Register automatically when the benchmark user does not exist",
    )
    return parser.parse_args()


def load_prompts(prompts_file: Path | None) -> list[str]:
    if prompts_file is None:
        return DEFAULT_PROMPTS

    lines = [line.strip() for line in prompts_file.read_text(encoding="utf-8").splitlines()]
    prompts = [line for line in lines if line]
    if not prompts:
        raise ValueError("prompts file is empty")
    return prompts


def ensure_login(session: requests.Session, args: argparse.Namespace) -> None:
    payload = {"username": args.username, "password": args.password}
    login_url = f"{args.base_url.rstrip('/')}/api/auth/login"
    try:
        response = session.post(login_url, json=payload, timeout=args.timeout)
    except requests_exceptions.ConnectionError as exc:
        raise RuntimeError(build_server_unavailable_message(args.base_url)) from exc

    if response.ok:
        return

    if response.status_code == 401 and args.register_if_needed:
        register_url = f"{args.base_url.rstrip('/')}/api/auth/register"
        register_response = session.post(register_url, json=payload, timeout=args.timeout)
        if register_response.ok:
            return
        if register_response.status_code == 400 and "已存在" in register_response.text:
            retry_response = session.post(login_url, json=payload, timeout=args.timeout)
            retry_response.raise_for_status()
            return

        register_response.raise_for_status()

    response.raise_for_status()


def ensure_server_available(session: requests.Session, base_url: str, timeout: float) -> None:
    health_url = f"{base_url.rstrip('/')}/health"
    try:
        response = session.get(health_url, timeout=timeout)
    except requests_exceptions.ConnectionError as exc:
        raise RuntimeError(build_server_unavailable_message(base_url)) from exc
    except requests_exceptions.RequestException as exc:
        raise RuntimeError(f"无法访问服务健康检查接口: {health_url}\n{exc}") from exc

    if not response.ok:
        raise RuntimeError(
            f"服务已启动，但健康检查失败: {health_url} -> HTTP {response.status_code}\n"
            f"响应内容: {response.text[:300]}"
        )


def build_server_unavailable_message(base_url: str) -> str:
    return (
        f"无法连接到后端服务: {base_url}\n"
        "请先启动 FastAPI 服务，再执行压测脚本。\n\n"
        "推荐命令:\n"
        "uvicorn main:app --reload --host 0.0.0.0 --port 8000\n\n"
        "如果你使用的是虚拟环境，先激活 .venv；如果端口不是 8000，请同步修改 --base-url。"
    )


def benchmark_chat(
    session: requests.Session,
    base_url: str,
    prompt: str,
    timeout: float,
) -> BenchmarkResult:
    url = f"{base_url.rstrip('/')}/api/chat"
    started_at = time.perf_counter()
    response = session.post(url, json={"message": prompt}, timeout=timeout)
    total_ms = (time.perf_counter() - started_at) * 1000

    if not response.ok:
        return BenchmarkResult(
            mode="chat",
            prompt=prompt,
            status_code=response.status_code,
            ok=False,
            total_ms=total_ms,
            error=response.text[:300],
        )

    payload = response.json()
    reply = str(payload.get("reply", ""))
    return BenchmarkResult(
        mode="chat",
        prompt=prompt,
        status_code=response.status_code,
        ok=True,
        total_ms=total_ms,
        session_id=payload.get("session_id"),
        reply_length=len(reply),
    )


def benchmark_stream(
    session: requests.Session,
    base_url: str,
    prompt: str,
    timeout: float,
) -> BenchmarkResult:
    url = f"{base_url.rstrip('/')}/api/chat/stream"
    started_at = time.perf_counter()
    response = session.get(
        url,
        params={"message": prompt},
        stream=True,
        timeout=timeout,
    )

    if not response.ok:
        total_ms = (time.perf_counter() - started_at) * 1000
        return BenchmarkResult(
            mode="stream",
            prompt=prompt,
            status_code=response.status_code,
            ok=False,
            total_ms=total_ms,
            error=response.text[:300],
        )

    first_chunk_ms: float | None = None
    session_id: str | None = None
    reply_parts: list[str] = []

    try:
        for raw_line in response.iter_lines(decode_unicode=True):
            if not raw_line or not raw_line.startswith("data: "):
                continue

            payload = json.loads(raw_line[6:])
            if first_chunk_ms is None and isinstance(payload.get("chunk"), str):
                first_chunk_ms = (time.perf_counter() - started_at) * 1000

            chunk = payload.get("chunk")
            if isinstance(chunk, str):
                reply_parts.append(chunk)

            if payload.get("done"):
                session_id = payload.get("session_id")
                break
    finally:
        response.close()

    total_ms = (time.perf_counter() - started_at) * 1000
    return BenchmarkResult(
        mode="stream",
        prompt=prompt,
        status_code=response.status_code,
        ok=True,
        total_ms=total_ms,
        first_chunk_ms=first_chunk_ms,
        session_id=session_id,
        reply_length=len("".join(reply_parts)),
    )


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]

    sorted_values = sorted(values)
    index = (len(sorted_values) - 1) * ratio
    lower = int(index)
    upper = min(lower + 1, len(sorted_values) - 1)
    if lower == upper:
        return sorted_values[lower]
    weight = index - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def format_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m {sec}s"
    if minutes:
        return f"{minutes}m {sec}s"
    return f"{sec}s"


def print_summary(results: list[BenchmarkResult]) -> None:
    grouped: dict[str, list[BenchmarkResult]] = {}
    for item in results:
        grouped.setdefault(item.mode, []).append(item)

    print("=" * 72)
    print("Benchmark Summary")
    print("=" * 72)

    for mode, items in grouped.items():
        total_values = [item.total_ms for item in items if item.ok]
        first_chunk_values = [item.first_chunk_ms for item in items if item.ok and item.first_chunk_ms is not None]
        success_count = sum(1 for item in items if item.ok)

        print(f"\n[{mode}] success={success_count}/{len(items)}")
        if total_values:
            print(f"avg total   : {statistics.mean(total_values):.2f} ms")
            print(f"p95 total   : {percentile(total_values, 0.95):.2f} ms")
            print(f"min total   : {min(total_values):.2f} ms")
            print(f"max total   : {max(total_values):.2f} ms")
        if first_chunk_values:
            print(f"avg first   : {statistics.mean(first_chunk_values):.2f} ms")
            print(f"p95 first   : {percentile(first_chunk_values, 0.95):.2f} ms")
            print(f"min first   : {min(first_chunk_values):.2f} ms")
            print(f"max first   : {max(first_chunk_values):.2f} ms")

        failures = [item for item in items if not item.ok]
        if failures:
            print("failures:")
            for failure in failures:
                print(f"- status={failure.status_code}, prompt={failure.prompt}, error={failure.error}")


def save_results(output_path: Path, results: list[BenchmarkResult]) -> None:
    payload: dict[str, Any] = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "results": [asdict(item) for item in results],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()
    prompts = load_prompts(args.prompts_file)
    session = requests.Session()
    session.headers.update({"Accept": "application/json"})

    ensure_server_available(session, args.base_url, args.timeout)
    ensure_login(session, args)

    results: list[BenchmarkResult] = []
    run_started_at = time.perf_counter()
    for index in range(args.rounds):
        prompt = prompts[index % len(prompts)]
        current_round = index + 1
        progress = current_round / args.rounds

        if args.mode in {"chat", "both"}:
            result = benchmark_chat(session, args.base_url, prompt, args.timeout)
            results.append(result)
            elapsed = time.perf_counter() - run_started_at
            eta_seconds = (elapsed / current_round) * (args.rounds - current_round)
            print(
                f"[chat]   round={current_round}/{args.rounds} "
                f"progress={progress:.0%} total={result.total_ms:.2f} ms ok={result.ok} "
                f"elapsed={format_duration(elapsed)} eta={format_duration(eta_seconds)}"
            )

        if args.mode in {"stream", "both"}:
            result = benchmark_stream(session, args.base_url, prompt, args.timeout)
            first_ms = "-" if result.first_chunk_ms is None else f"{result.first_chunk_ms:.2f}"
            results.append(result)
            elapsed = time.perf_counter() - run_started_at
            eta_seconds = (elapsed / current_round) * (args.rounds - current_round)
            print(
                f"[stream] round={current_round}/{args.rounds} "
                f"progress={progress:.0%} first={first_ms} ms total={result.total_ms:.2f} ms ok={result.ok} "
                f"elapsed={format_duration(elapsed)} eta={format_duration(eta_seconds)}"
            )

    print_summary(results)

    if args.output:
        save_results(args.output, results)
        print(f"\nRaw results saved to: {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
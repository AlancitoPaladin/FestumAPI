#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request
import socket


def percentile(sorted_values: list[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (len(sorted_values) - 1) * pct
    lower = int(rank)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = rank - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark /api/v1/client/bootstrap")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="API base URL")
    parser.add_argument("--token", required=True, help="JWT bearer token")
    parser.add_argument("--calls", type=int, default=20, help="Number of sequential calls")
    parser.add_argument("--images", choices=["lite", "full"], default="lite", help="Bootstrap images mode")
    parser.add_argument("--timeout", type=float, default=15.0, help="HTTP timeout seconds")
    args = parser.parse_args()

    endpoint = f"{args.base_url.rstrip('/')}/api/v1/client/bootstrap?{urllib.parse.urlencode({'images': args.images})}"
    latencies_ms: list[float] = []
    payload_bytes: list[int] = []
    statuses: list[int] = []
    failures: list[dict] = []

    print(f"Benchmarking: {endpoint}")
    for idx in range(args.calls):
        req = urllib.request.Request(
            endpoint,
            method="GET",
            headers={
                "Authorization": f"Bearer {args.token}",
                "Accept": "application/json",
                "X-Request-ID": f"bench-bootstrap-{idx + 1}",
            },
        )
        start = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=args.timeout) as resp:
                body = resp.read()
                status_code = resp.getcode()
        except urllib.error.HTTPError as exc:
            body = exc.read()
            status_code = exc.code
        except urllib.error.URLError as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies_ms.append(elapsed_ms)
            payload_bytes.append(0)
            statuses.append(0)
            failures.append(
                {
                    "index": idx + 1,
                    "error": type(exc.reason).__name__ if getattr(exc, "reason", None) else type(exc).__name__,
                    "detail": str(exc.reason or exc),
                    "latency_ms": round(elapsed_ms, 2),
                }
            )
            print(f"{idx + 1:02d}. status=ERR latency_ms={elapsed_ms:.2f} error={exc.reason or exc}")
            continue
        except TimeoutError as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies_ms.append(elapsed_ms)
            payload_bytes.append(0)
            statuses.append(0)
            failures.append(
                {
                    "index": idx + 1,
                    "error": type(exc).__name__,
                    "detail": str(exc),
                    "latency_ms": round(elapsed_ms, 2),
                }
            )
            print(f"{idx + 1:02d}. status=ERR latency_ms={elapsed_ms:.2f} error={exc}")
            continue
        except socket.timeout as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies_ms.append(elapsed_ms)
            payload_bytes.append(0)
            statuses.append(0)
            failures.append(
                {
                    "index": idx + 1,
                    "error": type(exc).__name__,
                    "detail": str(exc),
                    "latency_ms": round(elapsed_ms, 2),
                }
            )
            print(f"{idx + 1:02d}. status=ERR latency_ms={elapsed_ms:.2f} error={exc}")
            continue
        elapsed_ms = (time.perf_counter() - start) * 1000

        latencies_ms.append(elapsed_ms)
        payload_bytes.append(len(body or b""))
        statuses.append(status_code)
        print(f"{idx + 1:02d}. status={status_code} latency_ms={elapsed_ms:.2f} payload_bytes={len(body or b'')}")

    sorted_lat = sorted(latencies_ms)
    p50 = percentile(sorted_lat, 0.50)
    p95 = percentile(sorted_lat, 0.95)
    p99 = percentile(sorted_lat, 0.99)
    avg = statistics.mean(latencies_ms) if latencies_ms else 0.0
    avg_payload = statistics.mean(payload_bytes) if payload_bytes else 0.0

    warm_latencies = latencies_ms[1:] if len(latencies_ms) > 1 else []
    warm_sorted = sorted(warm_latencies)
    warm_p50 = percentile(warm_sorted, 0.50)
    warm_p95 = percentile(warm_sorted, 0.95)
    warm_p99 = percentile(warm_sorted, 0.99)
    warm_avg = statistics.mean(warm_latencies) if warm_latencies else 0.0

    print("\nSummary")
    print(json.dumps(
        {
            "calls": args.calls,
            "images_mode": args.images,
            "status_codes": sorted(set(statuses)),
            "success_count": sum(1 for s in statuses if s > 0),
            "failure_count": len(failures),
            "latency_ms": {
                "p50": round(p50, 2),
                "p95": round(p95, 2),
                "p99": round(p99, 2),
                "avg": round(avg, 2),
            },
            "latency_ms_warm_excluding_first": {
                "p50": round(warm_p50, 2),
                "p95": round(warm_p95, 2),
                "p99": round(warm_p99, 2),
                "avg": round(warm_avg, 2),
            },
            "payload_bytes": {
                "avg": round(avg_payload, 2),
                "min": min(payload_bytes) if payload_bytes else 0,
                "max": max(payload_bytes) if payload_bytes else 0,
            },
            "failures": failures,
        },
        indent=2,
        ensure_ascii=False,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

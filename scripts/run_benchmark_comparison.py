#!/usr/bin/env python3
"""
$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
RealMathUniverse v0.2C Benchmark Comparison Runner

Purpose:
    Run multiple profiles through main.py and generate one comparison JSON report.

Default:
    preview + desktop

Example:
    python3 scripts/run_benchmark_comparison.py

Custom:
    python3 scripts/run_benchmark_comparison.py --profiles preview desktop --warmup-frames 30 --frames 240
$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.output.benchmark_comparison import BenchmarkComparisonWriter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run RealMathUniverse benchmark comparisons.")
    parser.add_argument(
        "--profiles",
        nargs="+",
        default=None,
        help="Profiles to run. Default comes from config/benchmark_config.json, usually preview desktop.",
    )
    parser.add_argument(
        "--warmup-frames",
        type=int,
        default=None,
        help="Warmup frames per profile. Default comes from benchmark_config.json.",
    )
    parser.add_argument(
        "--frames",
        type=int,
        default=None,
        help="Measured frames per profile. Default comes from benchmark_config.json.",
    )
    parser.add_argument(
        "--comparison-name",
        default="preview_vs_desktop",
        help="Name token used in the comparison report filename.",
    )
    return parser.parse_args()


def load_benchmark_config() -> dict:
    path = PROJECT_ROOT / "config" / "benchmark_config.json"
    if not path.exists():
        return {
            "benchmark": {
                "comparison_profiles": ["preview", "desktop"],
                "default_warmup_frames": 30,
                "default_measured_frames": 240,
            }
        }
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def newest_summary_before() -> set[Path]:
    summary_dir = PROJECT_ROOT / "output" / "run_summaries"
    summary_dir.mkdir(parents=True, exist_ok=True)
    return set(summary_dir.glob("RealMathUniverse_v0_2B_*_run_summary.json")) | set(summary_dir.glob("RealMathUniverse_v0_2C_*_run_summary.json"))


def find_new_summary(before: set[Path]) -> Path | None:
    summary_dir = PROJECT_ROOT / "output" / "run_summaries"
    candidates = list(summary_dir.glob("RealMathUniverse_v0_2B_*_run_summary.json")) + list(summary_dir.glob("RealMathUniverse_v0_2C_*_run_summary.json"))
    new_files = [p for p in candidates if p not in before]
    if not new_files:
        latest = summary_dir / "LATEST_RUN_SUMMARY.json"
        return latest if latest.exists() else None
    return max(new_files, key=lambda p: p.stat().st_mtime)


def main() -> int:
    args = parse_args()
    cfg = load_benchmark_config().get("benchmark", {})

    profiles = args.profiles or cfg.get("comparison_profiles", ["preview", "desktop"])
    warmup_frames = int(args.warmup_frames if args.warmup_frames is not None else cfg.get("default_warmup_frames", 30))
    frames = int(args.frames if args.frames is not None else cfg.get("default_measured_frames", 240))

    logs_dir = PROJECT_ROOT / "output" / "logs" / "benchmark_comparisons"
    logs_dir.mkdir(parents=True, exist_ok=True)

    writer = BenchmarkComparisonWriter(PROJECT_ROOT)
    records = []

    print("RealMathUniverse v0.2C benchmark comparison")
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Profiles: {profiles}")
    print(f"Warmup frames: {warmup_frames}")
    print(f"Measured frames: {frames}")

    for profile in profiles:
        stamp = time.strftime("%Y%m%d_%H%M%S_UTC", time.gmtime())
        stdout_path = logs_dir / f"RealMathUniverse_v0_2C_{profile}_{stamp}_stdout.log"
        stderr_path = logs_dir / f"RealMathUniverse_v0_2C_{profile}_{stamp}_stderr.log"

        command = [
            sys.executable,
            str(PROJECT_ROOT / "main.py"),
            "--profile", profile,
            "--headless",
            "--warmup-frames", str(warmup_frames),
            "--frames", str(frames),
        ]

        print(f"\nRunning profile: {profile}")
        print(" ".join(command))

        before = newest_summary_before()
        proc = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
        )

        stdout_path.write_text(proc.stdout, encoding="utf-8")
        stderr_path.write_text(proc.stderr, encoding="utf-8")

        summary_path = find_new_summary(before) if proc.returncode == 0 else None

        record = writer.build_record_from_summary(
            profile=profile,
            command=command,
            return_code=proc.returncode,
            summary_path=summary_path,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
        )
        records.append(record)

        if proc.returncode == 0:
            print(f"Profile passed: {profile}")
            print(f"Summary: {summary_path}")
        else:
            print(f"Profile failed: {profile}")
            print(f"stderr log: {stderr_path}")

    comparison_path = writer.write(args.comparison_name, records)
    print(f"\nComparison report written:")
    print(comparison_path)
    print("\nLatest alias:")
    print(PROJECT_ROOT / "output" / "run_summaries" / "LATEST_BENCHMARK_COMPARISON.json")

    failed = [r for r in records if r.get("status") != "passed"]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

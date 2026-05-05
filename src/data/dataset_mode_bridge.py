#!/usr/bin/env python3
"""
RealMathUniverse v1.1B Dataset Mode Bridge

Sidecar process started by scripts/run_metal_session.sh after v1.1B install.
It writes output/dataset_state.json continuously and falls back safely when no
CSV is present or when data mode is disabled.
"""

from __future__ import annotations

from pathlib import Path
import argparse
import json
import signal
import sys
import time

from src.data.calibrated_dataset_driver import CalibratedDatasetDriver
from src.data.dataset_mode_manager import DatasetModeManager


_RUNNING = True


def _handle_stop(signum, frame):  # noqa: ANN001
    global _RUNNING
    _RUNNING = False


def main() -> int:
    parser = argparse.ArgumentParser(description="RealMathUniverse v1.1B dataset mode bridge")
    parser.add_argument("--project-root", default=str(Path.cwd()))
    parser.add_argument("--once", action="store_true", help="write one dataset state and exit")
    parser.add_argument("--report", action="store_true", help="write calibration report after load")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    manager = DatasetModeManager(project_root)
    driver = CalibratedDatasetDriver(project_root)

    signal.signal(signal.SIGTERM, _handle_stop)
    signal.signal(signal.SIGINT, _handle_stop)

    poll_seconds = float(driver.config.get("poll_seconds", 0.5))
    write_interval_seconds = float(driver.config.get("write_interval_seconds", 1.0))
    last_write = 0.0
    report_written = False

    while _RUNNING:
        runtime = manager.read_state()
        enabled = bool(runtime.get("enabled", True))
        now = time.time()
        if now - last_write >= write_interval_seconds or args.once:
            state = driver.build_state(enabled=enabled)
            state["runtime_control"] = runtime
            driver.write_state(state)
            if args.report and driver.loaded and not report_written:
                report_path = driver.write_report()
                if report_path:
                    state["calibration_report"] = str(report_path)
                    driver.write_state(state)
                report_written = True
            last_write = now
        if args.once:
            break
        time.sleep(poll_seconds)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

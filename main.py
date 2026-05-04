#!/usr/bin/env python3
"""
$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
RealMathUniverse v0.5A Collapse Behavior Controls
Author: Joe Stem / RedGloveProductions
Version: 0.5A

Purpose:
    main.py is the session orchestrator. It does not perform physics directly.
    v0.5A adds particle collapse behavior controls while preserving continuous
    Metal renderer sessions.

Usage:
    python3 main.py --profile preview --headless --warmup-frames 30 --frames 0

Stop:
    Ctrl-C
$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from src.core.config_loader import ConfigLoader
from src.core.execution_profiles import ExecutionProfiles
from src.core.diagnostics import Diagnostics
from src.compute.backend_manager import ComputeBackendManager
from src.compute.gpu_preflight import GPUPreflight
from src.compute.buffer_registry import BufferRegistry
from src.core.solver_registry import SolverRegistry
from src.core.module_registry import ModuleRegistry
from src.core.engine import RealMathUniverseEngine
from src.output.run_summary import RunSummaryWriter


PROJECT_ROOT = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="RealMathUniverse v0.5A collapse behavior controls."
    )
    parser.add_argument("--profile", default="preview")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--frames", type=int, default=0, help="Use 0 to run continuously until Ctrl-C.")
    parser.add_argument("--warmup-frames", type=int, default=30)
    parser.add_argument("--status-every", type=int, default=300)
    parser.add_argument("--config-dir", default=str(PROJECT_ROOT / "config"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    start_time = time.time()

    diagnostics = Diagnostics(project_root=PROJECT_ROOT)
    diagnostics.info("RealMathUniverse v0.5A booting...")
    diagnostics.info(f"Project root: {PROJECT_ROOT}")

    preflight_report = None
    engine = None
    compute = None
    buffer_registry = None
    solver_registry = None
    module_registry = None
    configs = None
    profile = None

    try:
        config_loader = ConfigLoader(config_dir=Path(args.config_dir))
        configs = config_loader.load_all_json()

        profiles = ExecutionProfiles(configs["execution_profiles"])
        profile = profiles.resolve(args.profile)

        diagnostics.info(f"Selected profile: {profile.name}")
        diagnostics.info(f"Strict physics mode: {profile.strict_physics_mode}")
        diagnostics.info(f"Strict GPU mode: {profile.strict_gpu}")
        diagnostics.info(f"Headless mode: {args.headless}")
        diagnostics.info("Run mode: continuous until Ctrl-C" if args.frames == 0 else f"Run mode: {args.frames} measured frames")

        compute = ComputeBackendManager(profile=profile, gpu_config=configs["gpu_config"], diagnostics=diagnostics)
        compute.initialize()

        preflight = GPUPreflight(profile=profile, compute=compute, gpu_config=configs["gpu_config"], diagnostics=diagnostics)
        preflight_report = preflight.run()
        preflight.enforce(preflight_report)

        buffer_registry = BufferRegistry(xp=compute.xp, backend_report=compute.backend_report, diagnostics=diagnostics)

        solver_registry = SolverRegistry(solver_config=configs["solver_config"], profile=profile, diagnostics=diagnostics)
        solver_registry.load_solvers()

        module_registry = ModuleRegistry(
            module_config=configs["module_config"],
            configs=configs,
            profile=profile,
            compute=compute,
            buffer_registry=buffer_registry,
            solver_registry=solver_registry,
            diagnostics=diagnostics,
        )
        module_registry.load_modules()

        engine = RealMathUniverseEngine(
            configs=configs,
            profile=profile,
            compute=compute,
            buffer_registry=buffer_registry,
            module_registry=module_registry,
            diagnostics=diagnostics,
            headless=args.headless,
        )
        engine.initialize()

        diagnostics.info(f"Running {args.warmup_frames} warmup frames...")
        for frame_index in range(args.warmup_frames):
            frame_ms = engine.update(record_timing=False)
            if frame_index == 0 or (frame_index + 1) == args.warmup_frames:
                diagnostics.info(
                    f"Warmup frame {frame_index + 1}/{args.warmup_frames} complete | "
                    f"frame_ms={frame_ms:.3f} | sim_time={engine.sim_time:.4f}"
                )

        engine.reset_measured_timing()

        if args.frames == 0:
            diagnostics.info("Running continuous v0.5A update frames. Press Ctrl-C to stop and write summary.")
            frame_index = 0
            try:
                while True:
                    engine.update(record_timing=True)
                    frame_index += 1
                    if frame_index == 1 or frame_index % max(1, args.status_every) == 0:
                        diagnostics.info(f"Measured frame {frame_index} complete | sim_time={engine.sim_time:.4f}")
            except KeyboardInterrupt:
                diagnostics.warn("Ctrl-C received. Shutting down continuous run cleanly.")
        else:
            diagnostics.info(f"Running {args.frames} measured v0.5A update frames...")
            for frame_index in range(args.frames):
                engine.update(record_timing=True)
                if frame_index == 0 or (frame_index + 1) % max(1, args.status_every) == 0 or (frame_index + 1) == args.frames:
                    diagnostics.info(f"Measured frame {frame_index + 1}/{args.frames} complete | sim_time={engine.sim_time:.4f}")

        engine.shutdown()

        elapsed = time.time() - start_time
        summary_writer = RunSummaryWriter(project_root=PROJECT_ROOT, diagnostics=diagnostics)
        summary_path = summary_writer.write_summary(
            args=args,
            configs=configs,
            profile=profile,
            compute_report=compute.backend_report,
            preflight_report=preflight_report,
            buffers=buffer_registry.describe_buffers(),
            solvers=solver_registry.describe(),
            modules=module_registry.describe(),
            elapsed_seconds=elapsed,
            engine_diagnostics=engine.diagnostics_payload() if engine else {},
        )

        diagnostics.info(f"Run summary written: {summary_path}")
        diagnostics.info("RealMathUniverse v0.5A shutdown complete.")
        return 0

    except KeyboardInterrupt:
        diagnostics.warn("Ctrl-C received during boot or setup.")
        if engine is not None:
            engine.shutdown()
        return 130

    except Exception as exc:
        diagnostics.error(f"Fatal boot failure: {exc}")
        diagnostics.write_crash_report(exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())

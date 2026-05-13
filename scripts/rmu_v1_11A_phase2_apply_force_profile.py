from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from datetime import datetime, timezone


ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
CFG = ROOT / "config/volumetric_force_profile_v1_11A.json"

OPERATOR = ROOT / "output/operator_authority_state.json"
DATASET_COUPLING = ROOT / "output/dataset_coupling_state.json"
OUT = ROOT / "output/volumetric_force_state.json"


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def read_json(path, default):
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text())
    except Exception:
        return default


def atomic_write(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent), text=True)
    tmp_path = Path(tmp)
    try:
        with os.fdopen(fd, "w") as h:
            json.dump(payload, h, indent=2)
            h.write("\n")
            h.flush()
            os.fsync(h.fileno())
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def main():
    cfg = read_json(CFG, {})
    weights = cfg.get("field_weights", {})

    op = read_json(OPERATOR, {})
    if not isinstance(op, dict):
        op = {}

    op["manual_field_weights"] = {
        "radial": float(weights.get("radial", 0.42)),
        "orbital": float(weights.get("orbital", 0.65)),
        "vertical": float(weights.get("vertical", 1.35)),
        "turbulence": float(weights.get("turbulence", 1.85)),
        "shell": float(weights.get("shell", 0.03))
    }
    op["auto_fields_enabled"] = False
    op["dataset_coupling_mode"] = cfg.get("dataset_coupling", {}).get("recommended_mode", "observe")
    op["selected_field_layer"] = "vertical"
    op["last_hotkey_reason"] = "v1_11A_large_volumetric_force_profile"
    op["updated_by"] = "rmu_v1_11A_phase2_apply_force_profile.py"
    op["updated_utc"] = now_iso()
    op["updated_unix"] = time.time()

    dc = read_json(DATASET_COUPLING, {})
    if not isinstance(dc, dict):
        dc = {}

    dc["mode"] = op["dataset_coupling_mode"]
    dc["enabled"] = op["dataset_coupling_mode"] in {"observe", "propose", "apply"}
    dc["field_weights"] = op["manual_field_weights"]
    dc["field_targets"] = op["manual_field_weights"]
    dc["boundary_mode"] = cfg.get("boundary", {})
    dc["updated_by"] = "rmu_v1_11A_phase2_apply_force_profile.py"
    dc["updated_utc"] = now_iso()
    dc["updated_unix"] = time.time()

    force_state = {
        "schema": "rmu.volumetric_force_state.v1_11A",
        "version": "v1.11A",
        "updated_utc": now_iso(),
        "field_weights": op["manual_field_weights"],
        "motion": cfg.get("motion", {}),
        "boundary": cfg.get("boundary", {}),
        "dataset_coupling_mode": op["dataset_coupling_mode"],
        "status": "applied"
    }

    atomic_write(OPERATOR, op)
    atomic_write(DATASET_COUPLING, dc)
    atomic_write(OUT, force_state)

    print("RMU v1.11A phase 2 complete")
    print("field_weights:", op["manual_field_weights"])
    print("dataset_coupling_mode:", op["dataset_coupling_mode"])
    print("wrote:", OUT)


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from datetime import datetime, timezone


ROOT = Path("/Users/Joe/Documents/RealMathUniverse")

FILES = {
    "operator": ROOT / "output/operator_authority_state.json",
    "effective": ROOT / "output/effective_control_state.json",
    "manual": ROOT / "output/manual_authority_mode.json",
    "dataset_coupling": ROOT / "output/dataset_coupling_state.json",
    "volumetric": ROOT / "output/volumetric_force_state.json",
}


VOLUMETRIC_FIELD_WEIGHTS = {
    "radial": 0.03,
    "orbital": 0.02,
    "vertical": 1.65,
    "turbulence": 2.25,
    "shell": 0.0,
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def read_json(path: Path, default):
    try:
        if not path.exists():
            return default
        data = json.loads(path.read_text())
        return data if isinstance(data, type(default)) else default
    except Exception:
        return default


def atomic_write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
        text=True,
    )
    tmp_path = Path(tmp)

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(str(tmp_path), str(path))

    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def patch_operator() -> dict:
    op = read_json(FILES["operator"], {})

    op.update({
        "schema": op.get("schema", "rmu.operator_authority_state.v1_11A"),
        "version": "v1.11A_phase3B_volumetric_authority_lock",

        "auto_fields_enabled": False,
        "auto_behavior_enabled": False,
        "auto_camera_enabled": False,

        "no_behavior_enabled": False,
        "manual_behavior_code": 4,
        "last_manual_behavior_code": 4,

        "dataset_coupling_mode": "off",
        "selected_field_layer": "vertical",
        "manual_scene_index": 0,
        "manual_field_weights": dict(VOLUMETRIC_FIELD_WEIGHTS),

        "queues_paused": True,
        "behavior_queue_paused": True,
        "field_queue_paused": True,

        "volumetric_domain_enabled": True,
        "boundary_mode": "open_soft_far_field",
        "shell_as_wall_enabled": False,
        "visible_boundary_enabled": False,

        "last_hotkey_reason": "v1_11A_phase3B_stop_disc_snap",
        "updated_by": "rmu_v1_11A_phase3B_volumetric_authority_lock.py",
        "updated_utc": now_iso(),
        "updated_unix": time.time(),
    })

    atomic_write(FILES["operator"], op)
    return op


def patch_manual(op: dict) -> dict:
    manual = read_json(FILES["manual"], {})

    manual.update({
        "schema": "rmu.manual_authority_mode.v1_11A_phase3B",
        "version": "v1.11A_phase3B_volumetric_authority_lock",

        "auto_fields_enabled": False,
        "auto_behavior_enabled": False,
        "no_behavior_enabled": False,

        "manual_behavior_code": 4,
        "manual_scene_index": 0,
        "manual_field_weights": dict(VOLUMETRIC_FIELD_WEIGHTS),

        "dataset_coupling_mode": "off",
        "volumetric_domain_enabled": True,
        "boundary_mode": "open_soft_far_field",
        "updated_by": "rmu_v1_11A_phase3B_volumetric_authority_lock.py",
        "updated_utc": now_iso(),
        "updated_unix": time.time(),
    })

    atomic_write(FILES["manual"], manual)
    return manual


def patch_dataset_coupling() -> dict:
    dc = read_json(FILES["dataset_coupling"], {})

    dc.update({
        "schema": dc.get("schema", "rmu.dataset_coupling_state.v1_11A_phase3B"),
        "version": "v1.11A_phase3B_volumetric_authority_lock",

        "mode": "off",
        "enabled": False,
        "fallback": False,

        "field_weights": dict(VOLUMETRIC_FIELD_WEIGHTS),
        "field_targets": dict(VOLUMETRIC_FIELD_WEIGHTS),

        "boundary_mode": "open_soft_far_field",
        "shell_as_wall_enabled": False,
        "visible_boundary_enabled": False,

        "updated_by": "rmu_v1_11A_phase3B_volumetric_authority_lock.py",
        "updated_utc": now_iso(),
        "updated_unix": time.time(),
    })

    atomic_write(FILES["dataset_coupling"], dc)
    return dc


def patch_effective() -> dict:
    eff = read_json(FILES["effective"], {})

    eff.update({
        "schema": "rmu.effective_control_state.v1_11A_phase3B",
        "version": "v1.11A_phase3B_volumetric_authority_lock",

        "authority": {
            "behavior": "manual_volumetric",
            "field_weights": "manual_volumetric_open_world",
            "field_recipe": "manual_volumetric_open_world",
            "camera": "hotkey_manual",
            "dataset_coupling": "off",
            "color": eff.get("authority", {}).get("color", "unchanged"),
            "vcv": "pure_vcv_signal_truth"
        },

        "modes": {
            **eff.get("modes", {}),
            "auto_fields_enabled": False,
            "auto_behavior_enabled": False,
            "auto_camera_enabled": False,
            "queues_paused": True,
            "behavior_queue_paused": True,
            "field_queue_paused": True,
            "volumetric_domain_enabled": True
        },

        "effective": {
            **eff.get("effective", {}),
            "scene_index": 0.0,
            "behavior_code": 4.0,
            "behavior_authority_gate": 0.0,
            "field_weights": dict(VOLUMETRIC_FIELD_WEIGHTS)
        },

        "dataset_coupling_mode": "off",
        "dataset_loaded": eff.get("dataset_loaded", True),
        "fallback": False,
        "field_weights": dict(VOLUMETRIC_FIELD_WEIGHTS),
        "field_targets": dict(VOLUMETRIC_FIELD_WEIGHTS),

        "volumetric_domain_enabled": True,
        "boundary_mode": "open_soft_far_field",
        "shell_as_wall_enabled": False,
        "visible_boundary_enabled": False,

        "updated_by": "rmu_v1_11A_phase3B_volumetric_authority_lock.py",
        "updated_utc": now_iso(),
        "updated_unix": time.time(),
    })

    atomic_write(FILES["effective"], eff)
    return eff


def patch_volumetric_state() -> dict:
    state = {
        "schema": "rmu.volumetric_runtime_authority.v1_11A_phase3B",
        "version": "v1.11A_phase3B_volumetric_authority_lock",
        "updated_utc": now_iso(),
        "updated_unix": time.time(),
        "status": "locked",

        "purpose": "prevent old shell/orbit/scene/coupling authority from snapping the large spawn cloud back into a disk",

        "field_weights": dict(VOLUMETRIC_FIELD_WEIGHTS),

        "disabled_authorities": [
            "dataset_coupling_apply",
            "auto_field_queue",
            "auto_behavior_queue",
            "shell_wall",
            "visible_boundary",
            "scene_field_recipe_snap"
        ],

        "active_behavior": {
            "manual_behavior_code": 4,
            "reason": "use turbulence/vertical behavior rather than stable_orbit_cloud"
        },

        "boundary": {
            "mode": "open_soft_far_field",
            "hard_clamp_enabled": False,
            "visible_ring_boundary_enabled": False,
            "shell_as_wall_enabled": False,
            "shell_as_weak_field_influence": True,
            "soft_return_strength": 0.00001
        }
    }

    atomic_write(FILES["volumetric"], state)
    return state


def main():
    op = patch_operator()
    patch_manual(op)
    patch_dataset_coupling()
    patch_effective()
    state = patch_volumetric_state()

    print("RMU v1.11A Phase 3B applied.")
    print("Field weights:", state["field_weights"])
    print("Dataset coupling:", "off")
    print("Behavior:", "manual code 4")
    print("Queues:", "paused")
    print("Boundary:", state["boundary"])


if __name__ == "__main__":
    main()

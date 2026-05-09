#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output"
VCV_STATE = OUTPUT_DIR / "vcv_state.json"
CONTROL_STATE = OUTPUT_DIR / "control_state.json"

POLL_SECONDS = 0.05


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def bipolar_5v(value: float) -> float:
    return clamp(float(value), -5.0, 5.0)


def particle_turbulence_from_bipolar(value: float) -> float:
    # /ch/11: -5V..+5V -> 0.00..2.50
    n = (bipolar_5v(value) + 5.0) / 10.0
    return clamp(n * 2.50, 0.0, 2.50)


def particle_cohesion_from_bipolar(value: float) -> float:
    # /ch/12: -5V..+5V -> 0.00..3.00
    n = (bipolar_5v(value) + 5.0) / 10.0
    return clamp(n * 3.00, 0.0, 3.00)


def load_json(path: Path) -> dict[str, Any]:
    try:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def recursive_find_channel(obj: Any, channel_number: int) -> Any:
    """
    Finds channel values in common bridge layouts:
      native_channels["/ch/11"]
      aux_channels["/ch/11"]
      channels["/ch/11"]
      values["/ch/11"]
      raw_channels[10]
      channel_values[10]
      "11"
      "ch11"
      "ch_11"
      "channel_11"
    """
    channel_address = f"/ch/{channel_number}"
    possible_keys = {
        channel_address,
        str(channel_number),
        f"ch{channel_number}",
        f"ch_{channel_number}",
        f"channel_{channel_number}",
        f"channel{channel_number}",
        f"aux_{channel_number}",
    }

    if isinstance(obj, dict):
        for key in possible_keys:
            if key in obj:
                return obj[key]

        for preferred_parent in (
            "native_channels",
            "aux_channels",
            "channels",
            "channel_values",
            "raw_channels",
            "values",
            "mapped",
            "vcv",
        ):
            if preferred_parent in obj:
                found = recursive_find_channel(obj[preferred_parent], channel_number)
                if found is not None:
                    return found

        for value in obj.values():
            found = recursive_find_channel(value, channel_number)
            if found is not None:
                return found

    if isinstance(obj, list):
        index = channel_number - 1
        if 0 <= index < len(obj):
            candidate = obj[index]
            if isinstance(candidate, (int, float)):
                return candidate

        for value in obj:
            found = recursive_find_channel(value, channel_number)
            if found is not None:
                return found

    return None


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def inject_mapped_values(data: dict[str, Any], raw_11: float, raw_12: float) -> dict[str, Any]:
    turbulence = particle_turbulence_from_bipolar(raw_11)
    cohesion = particle_cohesion_from_bipolar(raw_12)

    data["particle_turbulence_raw"] = raw_11
    data["particle_turbulence"] = turbulence
    data["particle_cohesion_raw"] = raw_12
    data["particle_cohesion"] = cohesion

    mapped = data.setdefault("mapped", {})
    if isinstance(mapped, dict):
        mapped["particle_turbulence_raw"] = raw_11
        mapped["particle_turbulence"] = turbulence
        mapped["particle_cohesion_raw"] = raw_12
        mapped["particle_cohesion"] = cohesion

    vcv = data.setdefault("vcv", {})
    if isinstance(vcv, dict):
        vcv["particle_turbulence_raw"] = raw_11
        vcv["particle_turbulence"] = turbulence
        vcv["particle_cohesion_raw"] = raw_12
        vcv["particle_cohesion"] = cohesion

    return data


def main() -> None:
    print("RMU v1.3F7C mapper running: /ch/11 -> particle_turbulence, /ch/12 -> particle_cohesion")
    print(f"Watching: {VCV_STATE}")
    print(f"Writing:  {VCV_STATE}")
    print(f"Writing:  {CONTROL_STATE}")

    last_print = 0.0

    while True:
        vcv_state = load_json(VCV_STATE)
        control_state = load_json(CONTROL_STATE)

        raw_11_candidate = recursive_find_channel(vcv_state, 11)
        raw_12_candidate = recursive_find_channel(vcv_state, 12)

        if raw_11_candidate is None:
            raw_11_candidate = recursive_find_channel(control_state, 11)
        if raw_12_candidate is None:
            raw_12_candidate = recursive_find_channel(control_state, 12)

        raw_11 = as_float(raw_11_candidate, 0.0)
        raw_12 = as_float(raw_12_candidate, 0.0)

        vcv_state = inject_mapped_values(vcv_state, raw_11, raw_12)
        control_state = inject_mapped_values(control_state, raw_11, raw_12)

        atomic_write_json(VCV_STATE, vcv_state)
        atomic_write_json(CONTROL_STATE, control_state)

        now = time.time()
        if now - last_print > 2.0:
            print(
                f"/ch/11 raw={raw_11:+.3f} turbulence={particle_turbulence_from_bipolar(raw_11):.3f} | "
                f"/ch/12 raw={raw_12:+.3f} cohesion={particle_cohesion_from_bipolar(raw_12):.3f}",
                flush=True,
            )
            last_print = now

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()

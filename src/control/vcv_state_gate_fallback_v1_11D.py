from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any


ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
VCV_STATE = ROOT / "output/vcv_state.json"

FALLBACKS = {
    "/ch/8": {
        "label": "behavior_gate",
        "fallback_value": 10.0,
        "requires": "/ch/18",
        "reason": "behavior gate missing while behavior_code is present",
    },
    "/ch/19": {
        "label": "color_gate",
        "fallback_value": 10.0,
        "requires": "/ch/7",
        "reason": "color gate missing while color_index is present",
    },
}


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
        text=True,
    )

    with os.fdopen(fd, "w") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")

    os.replace(tmp, path)


def make_channel(label: str, value: float, reason: str) -> dict[str, Any]:
    now = time.time()
    return {
        "label": label,
        "raw": value,
        "value": value,
        "mapped": value,
        "voices": [value],
        "voice_count": 1,
        "source": "v1_11D_gate_fallback",
        "reason": reason,
        "updated_unix": now,
    }


def normalize_once() -> tuple[bool, str]:
    if not VCV_STATE.exists():
        return False, "FAIL missing output/vcv_state.json"

    try:
        data = json.loads(VCV_STATE.read_text())
    except Exception as exc:
        return False, f"FAIL unreadable vcv_state.json: {exc}"

    channels = data.setdefault("channels", {})
    labels = data.setdefault("labels", {})

    changed = False
    parts = []

    for address, rule in FALLBACKS.items():
        required = rule["requires"]

        if address in channels:
            labels[address] = rule["label"]
            parts.append(f"PASS {address} present")
            continue

        if required in channels:
            channels[address] = make_channel(
                label=rule["label"],
                value=float(rule["fallback_value"]),
                reason=rule["reason"],
            )
            labels[address] = rule["label"]
            changed = True
            parts.append(f"PASS {address} fallback=10.0 requires={required}")
            continue

        parts.append(f"FAIL {address} missing requires={required}")

    if changed:
        data["gate_fallback_v1_11D"] = {
            "active": True,
            "updated_unix": time.time(),
            "rules": FALLBACKS,
        }
        atomic_write_json(VCV_STATE, data)

    return changed, " | ".join(parts)


def main() -> None:
    print("RMU v1.11D gate fallback running. Ctrl+C to stop.")

    last = None

    while True:
        changed, line = normalize_once()

        if changed or line != last:
            print(line)
            last = line

        time.sleep(0.20)


if __name__ == "__main__":
    main()

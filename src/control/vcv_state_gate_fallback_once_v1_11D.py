from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any


ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
VCV_STATE = ROOT / "output/vcv_state.json"


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
        "source": "v1_11D_gate_fallback_once",
        "reason": reason,
        "updated_unix": now,
    }


def main() -> int:
    if not VCV_STATE.exists():
        print("FAIL missing output/vcv_state.json")
        return 1

    data = json.loads(VCV_STATE.read_text())
    channels = data.setdefault("channels", {})
    labels = data.setdefault("labels", {})

    changed = False

    if "/ch/18" in channels and "/ch/8" not in channels:
        channels["/ch/8"] = make_channel(
            "behavior_gate",
            10.0,
            "behavior gate fallback high because /ch/18 behavior_code is present",
        )
        labels["/ch/8"] = "behavior_gate"
        changed = True

    if "/ch/7" in channels and "/ch/19" not in channels:
        channels["/ch/19"] = make_channel(
            "color_gate",
            10.0,
            "color gate fallback high because /ch/7 color_index is present",
        )
        labels["/ch/19"] = "color_gate"
        changed = True

    data["gate_fallback_once_v1_11D"] = {
        "active": True,
        "updated_unix": time.time(),
        "ch8_present": "/ch/8" in channels,
        "ch19_present": "/ch/19" in channels,
    }

    if changed:
        atomic_write_json(VCV_STATE, data)

    print(
        f"/ch/7={'YES' if '/ch/7' in channels else 'NO'} "
        f"/ch/8={'YES' if '/ch/8' in channels else 'NO'} "
        f"/ch/18={'YES' if '/ch/18' in channels else 'NO'} "
        f"/ch/19={'YES' if '/ch/19' in channels else 'NO'}"
    )

    return 0 if "/ch/8" in channels and "/ch/19" in channels else 1


if __name__ == "__main__":
    raise SystemExit(main())

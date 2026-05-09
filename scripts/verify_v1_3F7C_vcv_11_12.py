#!/usr/bin/env python3
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PATHS = [
    PROJECT_ROOT / "output" / "vcv_state.json",
    PROJECT_ROOT / "output" / "control_state.json",
]


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def find_key(obj: Any, target: str) -> Any:
    if isinstance(obj, dict):
        if target in obj:
            return obj[target]
        for value in obj.values():
            found = find_key(value, target)
            if found is not None:
                return found
    if isinstance(obj, list):
        for value in obj:
            found = find_key(value, target)
            if found is not None:
                return found
    return None


print("Move the VCV controls feeding /ch/11 and /ch/12.")
print("Sampling mapped state 10 times.\n")

for i in range(10):
    print(f"Sample {i + 1}")
    for path in PATHS:
        data = load_json(path)
        print(f"  {path.name}")
        for key in [
            "particle_turbulence_raw",
            "particle_turbulence",
            "particle_cohesion_raw",
            "particle_cohesion",
            "/ch/11",
            "/ch/12",
        ]:
            print(f"    {key}: {find_key(data, key)}")
    print()
    time.sleep(0.75)

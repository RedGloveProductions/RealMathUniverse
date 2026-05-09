#!/usr/bin/env python3
from __future__ import annotations
import json, time
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
PATHS=[ROOT/"output"/"vcv_state.json", ROOT/"output"/"control_state.json", ROOT/"output"/"runtime_state.json"]
KEYS=["particle_speed","particle_mass","particle_turbulence_raw","particle_turbulence","particle_cohesion_raw","particle_cohesion","/ch/9","/ch/10","/ch/11","/ch/12"]
def load(path: Path) -> Any:
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc: return {"_error":str(exc)}
def find_key(obj: Any, key: str) -> Any:
    if isinstance(obj, dict):
        if key in obj: return obj[key]
        for value in obj.values():
            found=find_key(value,key)
            if found is not None: return found
    elif isinstance(obj, list):
        for value in obj:
            found=find_key(value,key)
            if found is not None: return found
    return None
print("RealMathUniverse v1.3F8 OSC channel verifier")
print("Move VCV /ch/9, /ch/10, /ch/11, and /ch/12 while this runs.\n")
for sample in range(10):
    print(f"sample {sample+1}")
    for path in PATHS:
        data=load(path); print(f"  {path.name}")
        for key in KEYS: print(f"    {key}: {find_key(data,key)}")
    print(); time.sleep(0.75)

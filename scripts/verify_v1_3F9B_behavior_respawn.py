#!/usr/bin/env python3
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PATHS = [ROOT / 'output' / 'runtime_state.json', ROOT / 'output' / 'control_state.json', ROOT / 'output' / 'vcv_state.json']
KEYS = ['behavior_enabled', 'respawn_on_capture', 'behavior_mode', 'particle_speed', 'particle_mass', 'particle_turbulence', 'particle_cohesion']

def load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception as exc:
        return {'_error': str(exc)}

def find_key(obj: Any, key: str) -> Any:
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for value in obj.values():
            found = find_key(value, key)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = find_key(value, key)
            if found is not None:
                return found
    return None

print('RealMathUniverse v1.3F9B behavior/respawn verifier')
print('Test SHIFT+E for behavior ON/OFF and R for respawn ON/OFF.\n')
for i in range(12):
    print(f'sample {i + 1}')
    for path in PATHS:
        data = load(path)
        print(f'  {path.name}')
        for key in KEYS:
            print(f'    {key}: {find_key(data, key)}')
    print()
    time.sleep(0.75)

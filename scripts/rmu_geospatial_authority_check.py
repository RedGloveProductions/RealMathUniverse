#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path('/Users/Joe/Documents/RealMathUniverse')
paths = {
    'particle_source_authority': ROOT/'output/particle_source_authority.json',
    'runtime_state': ROOT/'output/runtime_state.json',
    'behavior_state': ROOT/'output/behavior_state.json',
    'latest_run_summary': ROOT/'output/run_summaries/LATEST_RUN_SUMMARY.json',
    'metadata': ROOT/'output/metal_live/metadata.json',
}
for label, path in paths.items():
    print('='*72)
    print(label, path)
    if not path.exists():
        print('missing')
        continue
    try:
        data = json.loads(path.read_text())
    except Exception as e:
        print('read error', e)
        continue
    if label == 'latest_run_summary':
        buffers = data.get('buffers', {}).get('buffers', {})
        for k in ['particle_positions','particle_velocities','particle_forces','particle_mass','particle_species']:
            if k in buffers:
                print(k, buffers[k].get('shape'), buffers[k].get('backend'))
        live = data.get('engine_diagnostics', {}).get('module_diagnostics', {}).get('particle_solver', {}).get('live_control_state', {})
        print('live behavior:', live.get('behavior_mode'))
        print('live runtime:', live.get('runtime'))
        print('live particle_source_authority:', live.get('particle_source_authority'))
    else:
        for k in ['version','authority','status','point_count','particle_count','runtime_mode','geospatial_enabled','simulation_paused','physics_armed','behavior_mode','behavior_lock','source_csv']:
            if k in data:
                print(f'{k}: {data[k]}')

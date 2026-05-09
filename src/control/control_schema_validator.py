from __future__ import annotations
import json, os, tempfile, time
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict

def utc_now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")

def atomic_write_json(path: Path, payload: Dict[str, Any]):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent), text=True)
    tmp_path=Path(tmp)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            json.dump(payload,f,indent=2,sort_keys=False); f.write('\n'); f.flush(); os.fsync(f.fileno())
        os.replace(str(tmp_path), str(path))
    finally:
        if tmp_path.exists():
            try: tmp_path.unlink()
            except OSError: pass

def read_json(path: Path, default=None):
    if default is None: default={}
    try:
        if not path.exists(): return default
        data=json.loads(path.read_text())
        return data if isinstance(data, dict) else default
    except Exception:
        return default

def clamp(v, lo, hi): return max(lo, min(hi, v))
def safe_float(x, d=0.0):
    try: return float(x)
    except Exception: return d
def safe_int(x, d=0):
    try: return int(float(x))
    except Exception: return d

import argparse, subprocess, sys
from pathlib import Path
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('root',nargs='?',default='/Users/Joe/Documents/RealMathUniverse'); args=ap.parse_args(); root=Path(args.root); ok=True
    required=['config/control_schema_v1_8.json','config/hotkey_schema_v1_8.json','src/control/vcv_osc_bridge.py','src/control/operator_authority_resolver.py','src/control/control_queue_db.py','scripts/run_metal_session_v1_8.sh']
    for rel in required:
        p=root/rel; print(('OK   ' if p.exists() else 'MISS ')+rel); ok=ok and p.exists()
    eff=read_json(root/'output/effective_control_state.json',{}); op=read_json(root/'output/operator_authority_state.json',{})
    print('effective_control_state:', eff.get('version'), eff.get('authority')); print('operator_authority_state:', op.get('version'), 'auto_behavior=',op.get('auto_behavior_enabled'), 'auto_fields=',op.get('auto_fields_enabled'))
    ps=subprocess.check_output(['bash','-lc','ps aux | egrep "behavior_state_bridge|dataset_coupling_bridge|vcv_state_stabilizer|manual_authority_lock|vcv_osc_bridge.py" | grep -v grep || true'], text=True)
    print('active control processes:'); print(ps.strip() or '(none)')
    sys.exit(0 if ok else 1)
if __name__=='__main__': main()

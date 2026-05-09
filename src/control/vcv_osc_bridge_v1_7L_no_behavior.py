#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, signal, sys, tempfile, time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

try:
    from pythonosc.dispatcher import Dispatcher
    from pythonosc.osc_server import ThreadingOSCUDPServer
except Exception as exc:
    print(f"ERROR: python-osc is required: {exc}", file=sys.stderr)
    print("Install inside venv with: pip install python-osc", file=sys.stderr)
    raise

VERSION = "v1.7L_no_behavior_control_schema_bridge"
STARTED = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

LABELS = {
    1:"probability",2:"radial",3:"orbital",4:"vertical",5:"turbulence",6:"shell",7:"color_mode",8:"scene_index",
    9:"particle_speed",10:"species_mass_bank_A",11:"species_mass_bank_B",12:"particle_turbulence_bank_A",13:"particle_cohesion_bank_A",
    14:"gravity_well_position",15:"gravity_well_strength",16:"species_color_hsl_bank_A",17:"species_color_hsl_bank_B",18:"behavior_code",19:"behavior_authority_gate",
    28:"probability_bank_B",29:"color_mode_bank_B",30:"particle_speed_bank_B",31:"particle_turbulence_bank_B",32:"particle_cohesion_bank_B"
}
DANGEROUS = {2,3,4,5,6,8,18,19}

def utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

def atomic_write(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent), text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2)
            f.write("\n")
            f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        try:
            if os.path.exists(tmp): os.unlink(tmp)
        except OSError:
            pass

def read_json(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            data=json.load(f)
        return data if isinstance(data, dict) else default
    except Exception:
        return default

def sf(x: Any, default: float=0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def voltage_to_step(v: float, lo: int=0, hi: int=7) -> int:
    if 0 <= v <= hi and abs(v-round(v)) < 0.001:
        return int(clamp(round(v), lo, hi))
    return int(round(lo + clamp(v/10.0, 0.0, 1.0)*(hi-lo)))

def mode_defaults() -> Dict[str, Any]:
    return {
        "schema":"rmu.manual_authority_mode.v1_7J",
        "version":"v1.7J-control-schema-consolidation",
        "auto_fields_enabled":False,
        "auto_behavior_enabled":False,
        "auto_camera_enabled":False,
        "linked_behavior_presets_enabled":False,
        "linked_scene_presets_enabled":False,
        "no_behavior_enabled":False,
        "dataset_coupling_mode":"observe",
        "manual_scene_index":0,
        "manual_behavior_code":0,
        "manual_field_weights":{"radial":1.0,"orbital":1.0,"vertical":1.0,"turbulence":1.0,"shell":1.0}
    }

class Bridge:
    def __init__(self, root: Path, host: str, port: int, heartbeat: float, active_timeout: float):
        self.root=root; self.host=host; self.port=port; self.heartbeat=heartbeat; self.active_timeout=active_timeout
        self.output=root/"output"/"vcv_state.json"
        self.effective=root/"output"/"effective_control_state.json"
        self.mode_path=root/"output"/"manual_authority_mode.json"
        self.lock=root/"output"/"session_locks"/"vcv_state_writer.lock"
        self.values: Dict[int, List[float]] = {}
        self.last_rx=0.0; self.rx_count=0; self.running=True
        signal.signal(signal.SIGTERM, self.stop); signal.signal(signal.SIGINT, self.stop)
    def stop(self, *_): self.running=False
    def handler(self, addr: str, *args: Any):
        if not addr.startswith("/ch/"): return
        try: ch=int(addr.split("/")[-1])
        except Exception: return
        vals=[]
        for a in args:
            if isinstance(a, (list, tuple)): vals.extend([sf(x) for x in a])
            else: vals.append(sf(a))
        if not vals: vals=[0.0]
        self.values[ch]=vals[:16]
        self.last_rx=time.time(); self.rx_count += 1
    def manual_mode(self) -> Dict[str, Any]:
        d=mode_defaults(); loaded=read_json(self.mode_path, {})
        d.update(loaded)
        if not isinstance(d.get("manual_field_weights"), dict): d["manual_field_weights"]=mode_defaults()["manual_field_weights"]
        return d
    def ch_entry(self, ch: int, vals: List[float], label: str, locked: bool, source: str, mapped: float|None=None) -> Dict[str, Any]:
        value = sf(mapped if mapped is not None else (vals[0] if vals else 0.0))
        return {"label":label,"raw":vals[0] if vals else value,"mapped":value,"value":value,"stable":value,"voices":vals,"voice_count":len(vals),"locked":locked,"source":source,"writer_version":VERSION}
    def build(self) -> Dict[str, Any]:
        mode=self.manual_mode()
        auto_fields=bool(mode.get("auto_fields_enabled", False)); auto_behavior=bool(mode.get("auto_behavior_enabled", False)); auto_camera=bool(mode.get("auto_camera_enabled", False)); no_behavior=bool(mode.get("no_behavior_enabled", False))
        weights=mode.get("manual_field_weights") if isinstance(mode.get("manual_field_weights"),dict) else {}
        manual = {2:sf(weights.get("radial"),1.0),3:sf(weights.get("orbital"),1.0),4:sf(weights.get("vertical"),1.0),5:sf(weights.get("turbulence"),1.0),6:sf(weights.get("shell"),1.0),8:sf(mode.get("manual_scene_index"),0.0),18:(0.0 if no_behavior else sf(mode.get("manual_behavior_code"),0.0)),19:0.0}
        channels: Dict[str, Any]={}; direct: Dict[str, Any]={}; mapped: Dict[str, Any]={}; labels: Dict[str,str]={}; counts: Dict[str,int]={}
        now=time.time(); fresh=(now-self.last_rx) <= self.active_timeout if self.last_rx else False
        for ch in range(1,33):
            label=LABELS.get(ch, f"aux_{ch}"); vals=list(self.values.get(ch,[0.0])); locked=False; source="vcv_live"; mapval=None
            if ch in {2,3,4,5,6,8} and not auto_fields:
                locked=True; source="manual_locked_fields" if ch in {2,3,4,5,6} else "manual_locked_scene"; vals=[manual[ch]]; mapval=manual[ch]
            elif ch in {18,19} and no_behavior:
                locked=True; source="no_behavior_mode" if ch==18 else "no_behavior_gate_forced_off"; vals=[0.0]; mapval=0.0
            elif ch in {18,19} and not auto_behavior:
                locked=True; source="manual_locked_behavior" if ch==18 else "manual_locked_behavior_gate"; vals=[manual[ch]]; mapval=manual[ch]
            elif ch == 8 and auto_fields:
                mapval=float(voltage_to_step(vals[0] if vals else 0.0,0,7)); source="slow_auto_fields_allowed"
            elif ch == 18 and auto_behavior:
                mapval=float(voltage_to_step(vals[0] if vals else 0.0,0,7)); source="slow_auto_behavior_allowed"
            elif ch == 19 and auto_behavior:
                mapval=10.0 if (vals and vals[0] >= 6.0) else 0.0; source="slow_auto_behavior_gate_allowed"
            entry=self.ch_entry(ch, vals, label, locked, source, mapval)
            key=f"/ch/{ch}"; channels[key]=entry; direct[key]=entry; mapped[label]=entry["mapped"]; labels[key]=label; counts[key]=entry["voice_count"]
        # compatibility top-level keys
        obj={
            "schema":"rmu.vcv_state.v1_7J", "version":VERSION, "status":"ACTIVE" if fresh else "WAITING", "fresh":fresh,
            "timestamp_unix":now, "updated_utc":utc(), "started_utc":STARTED,
            "writer":{"name":"vcv_osc_bridge", "version":VERSION, "pid":os.getpid(), "owns":["output/vcv_state.json"], "lock":str(self.lock)},
            "host":self.host, "port":self.port, "rx_count":self.rx_count, "last_rx_unix":self.last_rx,
            "auto_fields_enabled":auto_fields, "auto_behavior_enabled":(False if no_behavior else auto_behavior), "auto_camera_enabled":auto_camera, "no_behavior_enabled":no_behavior,
            "linked_behavior_presets_enabled":bool(mode.get("linked_behavior_presets_enabled",False)),
            "linked_scene_presets_enabled":bool(mode.get("linked_scene_presets_enabled",False)),
            "dataset_coupling_mode":str(mode.get("dataset_coupling_mode","observe")),
            "camera_locked_manual":not auto_camera, "scene_may_not_switch_camera":False, "behavior_may_not_switch_camera":False,
            "channels":channels, "direct_channels":direct, "mapped_values":mapped, "labels":labels, "channel_voice_counts":counts,
            "field_layer_weights":[mapped["radial"],mapped["orbital"],mapped["vertical"],mapped["turbulence"],mapped["shell"]],
            "scene_index":mapped["scene_index"], "behavior_code":mapped["behavior_code"], "behavior_authority_gate":mapped["behavior_authority_gate"],
            "effective":{"scene_index":mapped["scene_index"],"behavior_code":mapped["behavior_code"],"behavior_authority_gate":mapped["behavior_authority_gate"],"no_behavior_enabled":no_behavior,"field_weights":{"radial":mapped["radial"],"orbital":mapped["orbital"],"vertical":mapped["vertical"],"turbulence":mapped["turbulence"],"shell":mapped["shell"]}}
        }
        return obj
    def write_lock(self):
        atomic_write(self.lock,{"schema":"rmu.session_lock.v1","writer":"vcv_state.json","version":VERSION,"pid":os.getpid(),"started_utc":STARTED,"updated_utc":utc()})
    def run(self):
        self.write_lock()
        disp=Dispatcher(); disp.set_default_handler(self.handler)
        server=ThreadingOSCUDPServer((self.host,self.port), disp)
        server.timeout=self.heartbeat
        print(f"{VERSION} listening on {self.host}:{self.port} root={self.root}")
        while self.running:
            server.handle_request()
            obj=self.build(); atomic_write(self.output,obj)
            atomic_write(self.effective,{"schema":"rmu.effective_control_state.v1_7J","version":VERSION,"updated_utc":utc(),"authority":{"field_weights":"auto" if obj["auto_fields_enabled"] else "manual","field_recipe":"auto" if obj["auto_fields_enabled"] else "manual","behavior":"disabled_no_behavior" if obj.get("no_behavior_enabled") else ("auto" if obj["auto_behavior_enabled"] else "manual"),"camera":"auto" if obj["auto_camera_enabled"] else "manual","dataset_coupling":obj["dataset_coupling_mode"]},"effective":obj["effective"],"writer":obj["writer"]})
        server.server_close()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--project-root", default=os.getcwd()); ap.add_argument("--host", default="127.0.0.1"); ap.add_argument("--port", type=int, default=9000); ap.add_argument("--heartbeat", type=float, default=0.25); ap.add_argument("--active-timeout", type=float, default=30.0)
    a=ap.parse_args(); Bridge(Path(a.project_root).resolve(), a.host, a.port, a.heartbeat, a.active_timeout).run()
if __name__ == "__main__": main()
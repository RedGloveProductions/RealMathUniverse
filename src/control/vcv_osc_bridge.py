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

import argparse, os, time
from pathlib import Path
from control_queue_db import connect, insert_event
try:
    from pythonosc.dispatcher import Dispatcher
    from pythonosc.osc_server import BlockingOSCUDPServer
except Exception:
    print('ERROR: python-osc is required. Install in venv: python3 -m pip install python-osc')
    raise
VERSION='v1.8A_vcv_event_queue_bridge'
LABELS={i:f'aux_{i}' for i in range(1,33)}
LABELS.update({1:'probability',2:'radial',3:'orbital',4:'vertical',5:'turbulence',6:'shell',7:'color',8:'scene_index',9:'particle_speed_bank_a',10:'species_mass_bank_a',11:'species_mass_bank_b',12:'particle_turbulence_bank_a',13:'particle_cohesion_bank_a',14:'gravity_well_position',15:'gravity_well_strength',16:'species_color_hsl_bank_a',17:'species_color_hsl_bank_b',18:'behavior_code',19:'behavior_gate_deprecated_event',28:'probability_bank_b',29:'color_mode_bank_b',30:'particle_speed_bank_b',31:'particle_turbulence_bank_b',32:'particle_cohesion_bank_b'})
STEPPED={8:'field',18:'behavior',19:'behavior_gate_deprecated'}
class Bridge:
    def __init__(self,root,host,port,heartbeat,timeout):
        self.root=root; self.host=host; self.port=port; self.heartbeat=heartbeat; self.timeout=timeout; self.channels={}; self.last_rx=0.0; self.rx_count=0; self.last_step={}; self.conn=connect(root/'output/control_events.sqlite'); self.writer_lock=root/'output/session_locks/vcv_state_writer.lock'; self.writer_lock.parent.mkdir(parents=True,exist_ok=True); self.running=True
    def voltage_to_step(self,v): return int(clamp(round(clamp(float(v),0,10)/10*7),0,7))
    def mode(self): return read_json(self.root/'output/operator_authority_state.json',{})
    def handle(self,address,*args):
        if not address.startswith('/ch/'): return
        try: n=int(address.split('/')[-1])
        except Exception: return
        vals=[]
        for a in args:
            if isinstance(a,(list,tuple)): vals += [safe_float(x,0) for x in a]
            else: vals.append(safe_float(a,0))
        if not vals: vals=[0.0]
        raw=vals[0]; self.rx_count+=1; self.last_rx=time.time(); label=LABELS.get(n,f'aux_{n}')
        self.channels[address]={'label':label,'raw':raw,'value':raw,'mapped':raw,'voices':vals,'voice_count':len(vals),'source':'vcv_raw','updated_unix':self.last_rx}
        if n in STEPPED and bool(self.mode().get('vcv_event_recording_enabled',True)):
            step=self.voltage_to_step(raw)
            if self.last_step.get(address)!=step: insert_event(self.conn,'vcv',address,STEPPED[n],raw,step,True,250); self.last_step[address]=step
        self.write_state()
    def write_state(self):
        mode=self.mode(); fresh=(time.time()-self.last_rx)<=self.timeout if self.last_rx else False; eff=read_json(self.root/'output/effective_control_state.json',{}).get('effective',{}); weights=eff.get('field_weights',{}) if isinstance(eff.get('field_weights'),dict) else {}
        out={'schema':'rmu.vcv_state.v1_8A','version':VERSION,'status':'ACTIVE' if fresh else 'STALE','fresh':fresh,'active':fresh,'rx_count':self.rx_count,'age_ms':int((time.time()-self.last_rx)*1000) if self.last_rx else None,'host':self.host,'port':self.port,'channels':dict(self.channels),'direct_channels':dict(self.channels),'mapped_values':{},'labels':{ch:e.get('label','') for ch,e in self.channels.items()},'operator_mode':{k:mode.get(k) for k in ['auto_fields_enabled','auto_behavior_enabled','auto_camera_enabled','no_behavior_enabled','vcv_event_recording_enabled','vcv_continuous_enabled']},'writer':{'name':'vcv_osc_bridge','version':VERSION,'pid':os.getpid(),'owns':['output/vcv_state.json'],'lock':str(self.writer_lock)},'updated_utc':utc_now_iso()}
        for ch,label,val in [('/ch/2','radial',weights.get('radial',1.0)),('/ch/3','orbital',weights.get('orbital',1.0)),('/ch/4','vertical',weights.get('vertical',1.0)),('/ch/5','turbulence',weights.get('turbulence',1.0)),('/ch/6','shell',weights.get('shell',1.0)),('/ch/8','scene_index',eff.get('scene_index',0.0)),('/ch/18','behavior_code',eff.get('behavior_code',0.0)),('/ch/19','behavior_authority_gate',eff.get('behavior_authority_gate',0.0))]:
            entry={'label':label,'raw':val,'mapped':val,'value':val,'stable':val,'locked':True,'source':'effective_control','operator_authority':True}; out['channels'][ch]=entry; out['direct_channels'][ch]=entry; out['mapped_values'][label]=val; out[label]=val
        out['effective']=eff; atomic_write_json(self.root/'output/vcv_state.json',out); atomic_write_json(self.writer_lock,out['writer'])
    def heartbeat_loop(self):
        while self.running: self.write_state(); time.sleep(self.heartbeat)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--project-root','--root',dest='root',default=os.getcwd()); ap.add_argument('--host',default='127.0.0.1'); ap.add_argument('--port',type=int,default=9000); ap.add_argument('--heartbeat',type=float,default=0.25); ap.add_argument('--active-timeout',type=float,default=30.0); args=ap.parse_args(); b=Bridge(Path(args.root).resolve(),args.host,args.port,args.heartbeat,args.active_timeout)
    import threading; threading.Thread(target=b.heartbeat_loop,daemon=True).start(); disp=Dispatcher(); disp.set_default_handler(b.handle); print(f'RealMathUniverse {VERSION} listening on {args.host}:{args.port}', flush=True); BlockingOSCUDPServer((args.host,args.port),disp).serve_forever()
if __name__=='__main__': main()

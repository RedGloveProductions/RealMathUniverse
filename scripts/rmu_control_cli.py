#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,time,sys
from pathlib import Path
def read(p):
    try: return json.loads(p.read_text())
    except Exception: return {}
def write(p,d): p.parent.mkdir(parents=True,exist_ok=True); d['updated_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()); p.write_text(json.dumps(d,indent=2)+'\n')
def state(root):
    p=Path(root)/'output/operator_authority_state.json'; d=read(p); d.setdefault('schema','rmu.operator_authority_state.v1_8A'); d.setdefault('version','v1.8A'); d.setdefault('manual_field_weights',{'radial':1,'orbital':1,'vertical':1,'turbulence':1,'shell':1}); d.setdefault('last_manual_behavior_code',1); d.setdefault('manual_behavior_code',0); d.setdefault('no_behavior_enabled',True); d.setdefault('active_auto_domain','behavior'); d.setdefault('behavior_step_seconds',30.0); d.setdefault('field_step_seconds',20.0); return p,d
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('action'); ap.add_argument('value',nargs='?'); ap.add_argument('--root',default='/Users/Joe/Documents/RealMathUniverse'); args=ap.parse_args(); p,d=state(args.root); a=args.action
    if a=='manual': d.update(auto_fields_enabled=False,auto_behavior_enabled=False,auto_camera_enabled=False,queues_paused=True,dataset_coupling_mode='observe')
    elif a=='auto': d.update(auto_fields_enabled=True,auto_behavior_enabled=True,no_behavior_enabled=False,queues_paused=False)
    elif a=='no_behavior': d['no_behavior_enabled']=not bool(d.get('no_behavior_enabled',False))
    elif a=='behavior': d['manual_behavior_code']=max(0,min(7,int(float(args.value or 0)))); d['last_manual_behavior_code']=d['manual_behavior_code'] or d.get('last_manual_behavior_code',1); d['no_behavior_enabled']=(d['manual_behavior_code']==0); d['auto_behavior_enabled']=False
    elif a=='field': d['manual_scene_index']=max(0,min(7,int(float(args.value or 0)))); d['auto_fields_enabled']=False
    elif a=='toggle_auto':
        on=not (d.get('auto_fields_enabled') or d.get('auto_behavior_enabled')); d['auto_fields_enabled']=on; d['auto_behavior_enabled']=on; d['no_behavior_enabled']=False if on else d.get('no_behavior_enabled',False)
    elif a=='status': print(json.dumps(d,indent=2)); return
    else: print('unknown action',a); sys.exit(1)
    write(p,d); print(json.dumps(d,indent=2))
if __name__=='__main__': main()

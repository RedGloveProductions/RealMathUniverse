#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, sys, termios, tty
from pathlib import Path
from typing import Any, Dict

VERSION='v1.7L-no-behavior-control-console'
DEFAULT_WEIGHTS={'radial':1.0,'orbital':1.0,'vertical':1.0,'turbulence':1.0,'shell':1.0}

def load_mode(path: Path) -> Dict[str, Any]:
    if path.exists():
        try: data=json.loads(path.read_text())
        except Exception: data={}
    else:
        data={}
    data.setdefault('schema','rmu.manual_authority_mode.v1_7L')
    data['version']=VERSION
    data.setdefault('auto_fields_enabled',False)
    data.setdefault('auto_behavior_enabled',False)
    data.setdefault('auto_camera_enabled',False)
    data.setdefault('no_behavior_enabled',False)
    data.setdefault('linked_behavior_presets_enabled',False)
    data.setdefault('linked_scene_presets_enabled',False)
    data.setdefault('dataset_coupling_mode','observe')
    data.setdefault('manual_scene_index',0)
    data.setdefault('manual_behavior_code',0)
    data.setdefault('manual_field_weights',dict(DEFAULT_WEIGHTS))
    return data

def save_mode(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(data, indent=2)+'\n')
    os.replace(tmp,path)

def status(data: Dict[str,Any]) -> str:
    return (f"auto_fields={data.get('auto_fields_enabled')} auto_behavior={data.get('auto_behavior_enabled')} "
            f"auto_camera={data.get('auto_camera_enabled')} no_behavior={data.get('no_behavior_enabled')} "
            f"scene={data.get('manual_scene_index')} behavior={data.get('manual_behavior_code')} "
            f"dataset={data.get('dataset_coupling_mode')}")

def print_help():
    print('''\nRMU v1.7L Control Console\n-------------------------\na = toggle slow auto fields/behavior ON/OFF\nn = toggle NO BEHAVIOR mode. Behavior off, VCV/fields/physics active\nm = force full manual lock\n0-7 = set manual behavior code, disables no-behavior, keeps behavior manual\n[ = previous manual scene index\n] = next manual scene index\ns = status\nq = quit\n\nRun this in a second terminal while the simulator runs.\n''')

def read_key() -> str:
    fd=sys.stdin.fileno()
    old=termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch=sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return ch

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--root', default=os.environ.get('RMU_ROOT','/Users/Joe/Documents/RealMathUniverse'))
    args=ap.parse_args()
    root=Path(args.root).expanduser().resolve()
    path=root/'output'/'manual_authority_mode.json'
    print_help()
    data=load_mode(path); save_mode(path,data); print('STATUS:', status(data))
    while True:
        ch=read_key()
        data=load_mode(path)
        if ch in ('q','Q','\x03'):
            print('\nquit')
            return 0
        if ch in ('s','S'):
            print('\nSTATUS:', status(data))
            continue
        if ch in ('a','A'):
            data['no_behavior_enabled']=False
            new=not (bool(data.get('auto_fields_enabled')) or bool(data.get('auto_behavior_enabled')))
            data['auto_fields_enabled']=new
            data['auto_behavior_enabled']=new
            data['auto_camera_enabled']=False
            data['dataset_coupling_mode']='observe'
            save_mode(path,data)
            print('\nAUTO ON' if new else '\nAUTO OFF', status(data))
            continue
        if ch in ('n','N'):
            new=not bool(data.get('no_behavior_enabled', False))
            data['no_behavior_enabled']=new
            if new:
                data['auto_fields_enabled']=True
                data['auto_behavior_enabled']=False
                data['manual_behavior_code']=0
                data['dataset_coupling_mode']='observe'
                print('\nNO BEHAVIOR ON: behavior forced off; fields/VCV/physics active')
            else:
                data['auto_fields_enabled']=False
                data['auto_behavior_enabled']=False
                data['dataset_coupling_mode']='observe'
                print('\nNO BEHAVIOR OFF: safe manual lock')
            data['auto_camera_enabled']=False
            save_mode(path,data)
            print('STATUS:', status(data))
            continue
        if ch in ('m','M'):
            data['no_behavior_enabled']=False
            data['auto_fields_enabled']=False
            data['auto_behavior_enabled']=False
            data['auto_camera_enabled']=False
            data['dataset_coupling_mode']='observe'
            save_mode(path,data)
            print('\nMANUAL LOCK', status(data))
            continue
        if ch in '01234567':
            data['no_behavior_enabled']=False
            data['auto_behavior_enabled']=False
            data['auto_camera_enabled']=False
            data['manual_behavior_code']=int(ch)
            save_mode(path,data)
            print(f"\nMANUAL BEHAVIOR {ch}", status(data))
            continue
        if ch == '[':
            data['auto_fields_enabled']=False
            scene=max(0, int(float(data.get('manual_scene_index',0)))-1)
            data['manual_scene_index']=scene
            save_mode(path,data)
            print(f"\nMANUAL SCENE {scene}", status(data))
            continue
        if ch == ']':
            data['auto_fields_enabled']=False
            scene=min(7, int(float(data.get('manual_scene_index',0)))+1)
            data['manual_scene_index']=scene
            save_mode(path,data)
            print(f"\nMANUAL SCENE {scene}", status(data))
            continue
        print(f"\nignored key {repr(ch)}")

if __name__=='__main__':
    raise SystemExit(main())

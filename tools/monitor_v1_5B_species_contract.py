#!/usr/bin/env python3
from pathlib import Path
import argparse,json,time
NAMES=['crab_default','electron','positron','electron_neutrino','up_quark','down_quark','photon_like','gluon_like','higgs_excitation','proton_like','neutron_like','muon','tau','muon_neutrino','tau_neutrino','strange_quark','charm_quark','top_quark','bottom_quark','W_like','Z_like','meson_like']
def fl(xs,n=6):
    if not isinstance(xs,list): return 'None'
    return '['+', '.join(f'{float(x):+.3f}' if isinstance(x,(int,float)) else str(x) for x in xs[:n])+(']' if len(xs)<=n else f' ... +{len(xs)-n}]')
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--project-root',default='/Users/Joe/Documents/RealMathUniverse'); ap.add_argument('--interval',type=float,default=.25); ap.add_argument('--no-clear',action='store_true'); a=ap.parse_args(); p=Path(a.project_root)/'output/vcv_state.json'
    try:
        while True:
            if not a.no_clear: print('\033[2J\033[H',end='')
            print('RealMathUniverse v1.5B LIVE VCV CONTRACT MONITOR'); print('='*86)
            if not p.exists(): print('No vcv_state.json yet.'); time.sleep(a.interval); continue
            try: d=json.loads(p.read_text())
            except Exception as e: print('read error',e); time.sleep(a.interval); continue
            now=time.time(); print('version:',d.get('version')); print('mtime age:',round(now-p.stat().st_mtime,3),'status:',d.get('status'),'active:',d.get('active'),'fresh:',d.get('fresh'))
            print('messages:',d.get('message_count'),'writes:',d.get('write_count'),'scene:',d.get('scene_index'),'color:',d.get('color_mode'))
            print('\nCHANNELS'); print('-'*86)
            for ch in range(1,16):
                addr=f'/ch/{ch}'; print(f'{addr:<6} {(d.get("native_channels") or {}).get(addr):<26} voices={(d.get("channel_voice_counts") or {}).get(addr)} mapped={(d.get("channels") or {}).get(addr)} raw={fl((d.get("raw_poly_channels") or {}).get(addr),6)}')
            print('\nSPECIES MASS BANK'); print('-'*86); raw=d.get('particle_species_mass_raw') or []; mass=d.get('particle_species_mass') or []
            for i,n in enumerate(NAMES): print(f'{i+1:02d} {n:<22} raw={(raw[i] if i<len(raw) else None)!s:<8} mass={mass[i] if i<len(mass) else None}')
            print('\n/ch12 turbulence:',d.get('particle_turbulence'),'/ch13 cohesion:',d.get('particle_cohesion'),'/ch14 gravity:',d.get('gravity_well_position_vec3'),'/ch15 strength:',d.get('gravity_well_strength'))
            time.sleep(a.interval)
    except KeyboardInterrupt: print('\nStopped.')
if __name__=='__main__': main()

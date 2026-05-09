#!/usr/bin/env python3
from pathlib import Path
import json,time,subprocess
ROOT=Path('/Users/Joe/Documents/RealMathUniverse'); B=ROOT/'src/control/vcv_osc_bridge.py'; S=ROOT/'config/vcv_adaptive_schema.json'; M=ROOT/'metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift'; ST=ROOT/'output/vcv_state.json'
print('RealMathUniverse v1.5B Species Mass + Scene Contract Validator'); print('='*78)
for name,p in [('bridge',B),('schema',S),('main.swift',M),('state',ST)]: print(name,'exists:',p.exists())
if B.exists():
 t=B.read_text(errors='replace'); print('bridge marker:', 'v1.5B_species_mass_scene_contract' in t); print('species fields:', all(x in t for x in ['species_mass_bank_A','species_mass_bank_B','particle_species_mass']))
if S.exists():
 d=json.loads(S.read_text()); print('schema version:',d.get('version')); print('/ch/10:',d.get('channels',{}).get('/ch/10',{}).get('label'),'/ch/11:',d.get('channels',{}).get('/ch/11',{}).get('label'))
if M.exists():
 t=M.read_text(errors='replace'); print('Swift species marker:', 'RMU_V1_5B_SPECIES_MASS_STATE' in t); print('Swift parser marker:', 'RMU_V1_5B_SPECIES_MASS_AND_SCENE_PARSE' in t)
try: print('\nProcesses:\n'+subprocess.check_output(['/bin/zsh','-lc',"pgrep -af 'vcv_osc_bridge.py|run_vcv_osc_bridge|RealMathUniverseMetalRenderer' || true"],text=True).strip())
except Exception as e: print('process check failed',e)
if ST.exists():
 d=json.loads(ST.read_text()); now=time.time(); print('\nstate version:',d.get('version')); print('mtime age:',round(now-ST.stat().st_mtime,3),'active:',d.get('active'),'status:',d.get('status')); print('scene:',d.get('scene_index'),'species voices:',d.get('particle_species_mass_voice_count'),'len:',len(d.get('particle_species_mass',[]))); print('/ch10 voices:',d.get('channel_voice_counts',{}).get('/ch/10'),'/ch11 voices:',d.get('channel_voice_counts',{}).get('/ch/11')); print('/ch12-15 labels:',[d.get('native_channels',{}).get(f'/ch/{i}') for i in range(12,16)])

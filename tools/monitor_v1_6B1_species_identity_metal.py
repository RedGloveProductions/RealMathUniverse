#!/usr/bin/env python3
from __future__ import annotations
import json, struct, time
from collections import Counter
from pathlib import Path
ROOT=Path("/Users/Joe/Documents/RealMathUniverse")
BIN=ROOT/"data/processed/species_identity_v1_6A.bin"
REPORT=ROOT/"output/v1_6B_renderer_species_identity_patch_report.json"
VCV=ROOT/"output/vcv_state.json"
def main():
    while True:
        print("\033[2J\033[H", end="")
        print("RealMathUniverse v1.6B1 SPECIES IDENTITY / METAL MONITOR")
        print("="*100)
        if BIN.exists():
            c=0
            with BIN.open("rb") as f:
                while len(f.read(8))==8: c+=1
            print("species_identity_v1_6A.bin records:", c)
        else: print("species_identity_v1_6A.bin: MISSING")
        if REPORT.exists():
            r=json.loads(REPORT.read_text()); print("patch report:", r.get("version"), "ok=", r.get("ok"), "build=", r.get("swift_build_ok"), "shader=", r.get("shader_species_consumption"))
        else: print("patch report: MISSING")
        if VCV.exists():
            v=json.loads(VCV.read_text()); print("vcv:", v.get("version"), "active=", v.get("active"), "fresh=", v.get("fresh"), "scene=", v.get("scene_index"), "color=", v.get("color_mode"))
        else: print("vcv_state: MISSING")
        print("\nCTRL+C to stop."); time.sleep(1)
if __name__=="__main__": main()

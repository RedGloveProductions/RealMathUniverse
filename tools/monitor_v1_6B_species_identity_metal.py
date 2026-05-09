#!/usr/bin/env python3
from __future__ import annotations
import json
import struct
import time
from pathlib import Path
from collections import Counter

ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
BIN = ROOT / "data" / "processed" / "species_identity_v1_6A.bin"
REPORT = ROOT / "output" / "v1_6B_renderer_species_identity_patch_report.json"
VCV = ROOT / "output" / "vcv_state.json"

SPECIES = [
    "crab_default","electron","positron","electron_neutrino","up_quark","down_quark",
    "photon_like","gluon_like","higgs_excitation","proton_like","neutron_like","muon",
    "tau","muon_neutrino","tau_neutrino","strange_quark","charm_quark","top_quark",
    "bottom_quark","W_like","Z_like","meson_like"
]

def read_bin_summary():
    if not BIN.exists():
        return None
    count = BIN.stat().st_size // 8
    species = Counter()
    families = Counter()
    weights = []
    with BIN.open("rb") as f:
        for _ in range(count):
            chunk = f.read(8)
            if len(chunk) != 8:
                break
            sid, fid, w = struct.unpack("<HHf", chunk)
            species[sid] += 1
            families[fid] += 1
            weights.append(w)
    return count, species, families, weights

def main():
    while True:
        print("\\033[2J\\033[H", end="")
        print("RealMathUniverse v1.6B SPECIES IDENTITY / METAL MONITOR")
        print("=" * 100)

        summary = read_bin_summary()
        if summary is None:
            print("species_identity_v1_6A.bin: MISSING")
        else:
            count, species, families, weights = summary
            print(f"species_identity_v1_6A.bin: records={count} weights={min(weights):.3f}..{max(weights):.3f}")
            print("top species:")
            for sid, c in species.most_common(8):
                name = SPECIES[sid] if sid < len(SPECIES) else f"sid_{sid}"
                print(f"  {sid:02d} {name:<22} {c}")

        print()
        if REPORT.exists():
            try:
                r = json.loads(REPORT.read_text())
                print("patch report:")
                print("  ok:", r.get("ok"), "build:", r.get("swift_build_ok"), "shader:", r.get("shader_species_consumption"))
                print("  records:", r.get("species_identity_records"))
            except Exception as e:
                print("patch report unreadable:", e)
        else:
            print("patch report: missing")

        print()
        if VCV.exists():
            try:
                v = json.loads(VCV.read_text())
                age = time.time() - VCV.stat().st_mtime
                print("vcv_state:")
                print("  version:", v.get("version"))
                print("  age:", round(age, 3), "active:", v.get("active"), "fresh:", v.get("fresh"), "status:", v.get("status"))
                for k in ["particle_species_probability","particle_species_speed","particle_species_mass","particle_species_turbulence","particle_species_cohesion","particle_species_color_hex"]:
                    val = v.get(k)
                    if isinstance(val, list):
                        print(f"  {k:<30} len={len(val):<2} first={val[:5]}")
                    else:
                        print(f"  {k:<30} {val}")
            except Exception as e:
                print("vcv_state unreadable:", e)
        else:
            print("vcv_state: missing")

        print()
        print("CTRL+C to stop.")
        time.sleep(1)

if __name__ == "__main__":
    main()

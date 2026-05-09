#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, json, struct
from pathlib import Path
from collections import Counter

def main():
    ap = argparse.ArgumentParser(description="Validate v1.6A species identity outputs.")
    ap.add_argument("--project-root", default="/Users/Joe/Documents/RealMathUniverse")
    ap.add_argument("--csv", default="data/processed/merged_navdata_species_v1_6A.csv")
    ap.add_argument("--bin", default="data/processed/species_identity_v1_6A.bin")
    ap.add_argument("--manifest", default="output/species_identity_state.json")
    args = ap.parse_args()
    root = Path(args.project_root).expanduser().resolve()
    csv_path, bin_path, manifest_path = root/args.csv, root/args.bin, root/args.manifest
    print("RealMathUniverse v1.6A species identity validator")
    print("="*88)
    print("csv exists:", csv_path.exists(), csv_path)
    print("bin exists:", bin_path.exists(), bin_path)
    print("manifest exists:", manifest_path.exists(), manifest_path)
    if not csv_path.exists() or not bin_path.exists() or not manifest_path.exists():
        raise SystemExit("VALIDATION FAILED: missing output file")
    manifest = json.loads(manifest_path.read_text())
    count = int(manifest.get("record_count", 0))
    print("version:", manifest.get("version"))
    print("record_count:", count)
    print("bin bytes:", bin_path.stat().st_size, "expected:", count*8)
    if bin_path.stat().st_size != count*8:
        raise SystemExit("VALIDATION FAILED: binary size mismatch")
    species, families, weights = Counter(), Counter(), []
    with bin_path.open("rb") as f:
        for i in range(count):
            sid, fid, w = struct.unpack("<HHf", f.read(8))
            if sid > 21 or fid > 6:
                raise SystemExit(f"VALIDATION FAILED: out of range at record {i}: sid={sid}, fid={fid}")
            species[sid] += 1
            families[fid] += 1
            weights.append(w)
    with csv_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"rmu_species_id","rmu_species_name","rmu_family_id","rmu_family_name","rmu_species_weight"}
        missing = required - set(reader.fieldnames or [])
        print("csv required columns present:", not missing)
        if missing:
            raise SystemExit(f"VALIDATION FAILED: missing columns {sorted(missing)}")
    print("species counts:", dict(sorted(species.items())))
    print("family counts:", dict(sorted(families.items())))
    print("weight range:", min(weights), max(weights))
    print("VALIDATION OK")

if __name__ == "__main__":
    main()

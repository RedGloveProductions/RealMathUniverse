#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, hashlib, json, math, struct, time
from collections import Counter
from pathlib import Path

VERSION = "v1.6A_species_identity_data_contract"

SPECIES = [
    ("crab_default",0), ("electron",1), ("positron",1), ("electron_neutrino",2),
    ("up_quark",3), ("down_quark",3), ("photon_like",4), ("gluon_like",4),
    ("higgs_excitation",6), ("proton_like",5), ("neutron_like",5), ("muon",1),
    ("tau",1), ("muon_neutrino",2), ("tau_neutrino",2), ("strange_quark",3),
    ("charm_quark",3), ("top_quark",3), ("bottom_quark",3), ("W_like",4),
    ("Z_like",4), ("meson_like",5),
]
FAMILY_NAMES = {0:"crab_data_origin",1:"lepton",2:"neutrino",3:"quark",4:"boson_field_carrier",5:"composite_hadron_like",6:"higgs_field_excitation"}
SURFACE_SPECIES = [1,2,6,11]
MID_SPECIES = [4,5,7,9,10,15,21]
DEEP_SPECIES = [8,12,16,17,18,19,20]
SPARSE_SPECIES = [3,13,14,6]
DENSE_SPECIES = [7,9,10,15,16,18,21]
ALL_PHYSICAL_SPECIES = list(range(1,22))

def stable_unit(seed: str) -> float:
    digest = hashlib.blake2b(seed.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "little") / float(2**64 - 1)

def stable_pick(pool: list[int], seed: str) -> int:
    if not pool:
        return 0
    idx = int(stable_unit(seed) * len(pool))
    return pool[min(idx, len(pool)-1)]

def as_float(value):
    try:
        x = float(str(value).strip())
        if math.isnan(x) or math.isinf(x):
            return None
        return x
    except Exception:
        return None

def pick_column(fieldnames: list[str], candidates: list[str]) -> str | None:
    lowered = {f.lower().strip(): f for f in fieldnames}
    for c in candidates:
        if c.lower() in lowered:
            return lowered[c.lower()]
    for f in fieldnames:
        lf = f.lower()
        for c in candidates:
            if c.lower() in lf:
                return f
    return None

def quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    pos = max(0.0, min(1.0, q)) * (len(xs)-1)
    lo, hi = int(math.floor(pos)), int(math.ceil(pos))
    if lo == hi:
        return xs[lo]
    t = pos - lo
    return xs[lo]*(1-t) + xs[hi]*t

def score(value, lo: float, hi: float, default: float=0.5) -> float:
    if value is None or hi == lo:
        return default
    return max(0.0, min(1.0, (value-lo)/(hi-lo)))

def assign_species(row_index, row, lat_col, lon_col, depth_col, density_col, stats):
    lat = as_float(row.get(lat_col)) if lat_col else None
    lon = as_float(row.get(lon_col)) if lon_col else None
    depth_raw = as_float(row.get(depth_col)) if depth_col else None
    density = as_float(row.get(density_col)) if density_col else None
    depth_mag = abs(depth_raw) if depth_raw is not None else None
    dscore = score(depth_mag, stats["depth_p05"], stats["depth_p95"], 0.5)
    dens_score = score(density, stats["density_p05"], stats["density_p95"], 0.5)
    seed_material = f"{row_index}|{lat}|{lon}|{depth_raw}|{density}"
    h = stable_unit(seed_material)
    if h < 0.035:
        species_id = 0
    else:
        if dens_score < 0.18:
            pool = SPARSE_SPECIES
        elif dens_score > 0.82:
            pool = DENSE_SPECIES
        elif dscore > 0.72:
            pool = DEEP_SPECIES
        elif dscore < 0.28:
            pool = SURFACE_SPECIES
        else:
            pool = MID_SPECIES
        if stable_unit(f"geo|{lat}|{lon}|{row_index//64}") > 0.94:
            pool = ALL_PHYSICAL_SPECIES
        species_id = stable_pick(pool, f"species|{seed_material}")
    species_name, family_id = SPECIES[species_id]
    family_name = FAMILY_NAMES[family_id]
    weight = max(0.0, min(1.0, 0.25 + 0.35*dscore + 0.30*dens_score + 0.10*h))
    return species_id, family_id, species_name, family_name, weight, dscore, dens_score, h

def main():
    ap = argparse.ArgumentParser(description="Build v1.6A species/family identity data for RealMathUniverse.")
    ap.add_argument("--project-root", default="/Users/Joe/Documents/RealMathUniverse")
    ap.add_argument("--input", default="data/raw/merged_navdata.csv")
    ap.add_argument("--output-csv", default="data/processed/merged_navdata_species_v1_6A.csv")
    ap.add_argument("--output-bin", default="data/processed/species_identity_v1_6A.bin")
    ap.add_argument("--manifest", default="output/species_identity_state.json")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    root = Path(args.project_root).expanduser().resolve()
    input_path = (root / args.input).resolve()
    output_csv = (root / args.output_csv).resolve()
    output_bin = (root / args.output_bin).resolve()
    manifest_path = (root / args.manifest).resolve()
    if not input_path.exists():
        raise SystemExit(f"INPUT CSV NOT FOUND: {input_path}")

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_bin.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    with input_path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        if not fieldnames:
            raise SystemExit("CSV has no header row.")
        lat_col = pick_column(fieldnames, ["Latitude","lat","decimal_latitude","Y"])
        lon_col = pick_column(fieldnames, ["Longitude","lon","lng","decimal_longitude","X"])
        depth_col = pick_column(fieldnames, ["depth","Depth","elevation","Elevation","z","Z","altitude"])
        density_col = pick_column(fieldnames, ["track_density","density","cluster_density","point_density"])
        rows, depths, densities = [], [], []
        for i, row in enumerate(reader):
            if args.limit and i >= args.limit:
                break
            rows.append(row)
            dv = as_float(row.get(depth_col)) if depth_col else None
            tv = as_float(row.get(density_col)) if density_col else None
            if dv is not None:
                depths.append(abs(dv))
            if tv is not None:
                densities.append(tv)

    stats = {
        "depth_p05": quantile(depths,0.05), "depth_p50": quantile(depths,0.50), "depth_p95": quantile(depths,0.95),
        "density_p05": quantile(densities,0.05), "density_p50": quantile(densities,0.50), "density_p95": quantile(densities,0.95),
    }
    species_counts, family_counts = Counter(), Counter()
    added = ["rmu_row_index","rmu_species_id","rmu_species_name","rmu_family_id","rmu_family_name","rmu_species_weight","rmu_depth_score","rmu_density_score","rmu_identity_seed"]
    output_fields = list(fieldnames) + [x for x in added if x not in fieldnames]

    with output_csv.open("w", newline="", encoding="utf-8") as csv_out, output_bin.open("wb") as bin_out:
        writer = csv.DictWriter(csv_out, fieldnames=output_fields)
        writer.writeheader()
        for row_index, row in enumerate(rows):
            sid, fid, sname, fname, weight, dscore, dens_score, h = assign_species(row_index, row, lat_col, lon_col, depth_col, density_col, stats)
            species_counts[sid] += 1
            family_counts[fid] += 1
            out = dict(row)
            out.update({
                "rmu_row_index": row_index,
                "rmu_species_id": sid,
                "rmu_species_name": sname,
                "rmu_family_id": fid,
                "rmu_family_name": fname,
                "rmu_species_weight": f"{weight:.8f}",
                "rmu_depth_score": f"{dscore:.8f}",
                "rmu_density_score": f"{dens_score:.8f}",
                "rmu_identity_seed": f"{h:.12f}",
            })
            writer.writerow(out)
            bin_out.write(struct.pack("<HHf", sid, fid, float(weight)))

    manifest = {
        "version": VERSION,
        "timestamp_unix": time.time(),
        "project_root": str(root),
        "input_csv": str(input_path),
        "output_csv": str(output_csv),
        "output_bin": str(output_bin),
        "schema": str(root / "config/species_families_v1_6A.json"),
        "record_count": len(rows),
        "bytes_per_record": 8,
        "binary_layout": ["uint16 species_id","uint16 family_id","float32 species_weight"],
        "columns": {"latitude":lat_col, "longitude":lon_col, "depth_or_elevation":depth_col, "density":density_col},
        "stats": stats,
        "species_counts": {SPECIES[i][0]: species_counts.get(i,0) for i in range(len(SPECIES))},
        "family_counts": {FAMILY_NAMES[i]: family_counts.get(i,0) for i in sorted(FAMILY_NAMES)},
        "species_id_order": [{"species_id":i,"species_name":SPECIES[i][0],"family_id":SPECIES[i][1],"family_name":FAMILY_NAMES[SPECIES[i][1]]} for i in range(len(SPECIES))]
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"RealMathUniverse {VERSION}")
    print(f"Rows: {len(rows)}")
    print(f"Wrote CSV: {output_csv}")
    print(f"Wrote BIN: {output_bin}")
    print(f"Wrote manifest: {manifest_path}")
    print("Species counts:")
    for i, (name, _) in enumerate(SPECIES):
        print(f"  {i:02d} {name:<22} {species_counts.get(i,0)}")
    print("Family counts:")
    for fid, name in FAMILY_NAMES.items():
        print(f"  {fid} {name:<24} {family_counts.get(fid,0)}")

if __name__ == "__main__":
    main()

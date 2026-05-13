from __future__ import annotations

import csv
import json
import math
import statistics
from pathlib import Path
from datetime import datetime, timezone


ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
CSV_CANDIDATES = [
    ROOT / "data/raw/merged_navdata.csv",
    ROOT / "merged_navdata.csv",
    Path("/Users/Joe/Documents/merged_navdata.csv"),
]
CONFIG_PATH = ROOT / "config/geospatial_domain_v1_11A.json"
OUT_PATH = ROOT / "output/geospatial_domain_state.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def percentile(values, p):
    if not values:
        return None
    vals = sorted(values)
    if len(vals) == 1:
        return vals[0]
    idx = (len(vals) - 1) * (p / 100.0)
    lo = int(math.floor(idx))
    hi = int(math.ceil(idx))
    if lo == hi:
        return vals[lo]
    return vals[lo] * (hi - idx) + vals[hi] * (idx - lo)


def find_csv() -> Path:
    for p in CSV_CANDIDATES:
        if p.exists():
            return p
    raise FileNotFoundError("Could not find merged_navdata.csv in expected locations.")


def get_field(row, names):
    lowered = {k.lower(): v for k, v in row.items()}
    for name in names:
        if name in row:
            return row[name]
        if name.lower() in lowered:
            return lowered[name.lower()]
    return None


def f(value):
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def main():
    csv_path = find_csv()
    cfg = json.loads(CONFIG_PATH.read_text())

    lats, lons, depths = [], [], []
    rows = 0

    with csv_path.open("r", newline="", errors="replace") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows += 1

            lat = f(get_field(row, ["Latitude", "latitude", "lat"]))
            lon = f(get_field(row, ["Longitude", "longitude", "lon", "lng"]))
            dep = f(get_field(row, ["Elevation", "elevation", "Depth", "depth", "z"]))

            if lat is not None:
                lats.append(lat)
            if lon is not None:
                lons.append(lon)
            if dep is not None:
                depths.append(dep)

    lat_p01, lat_p99 = percentile(lats, 1), percentile(lats, 99)
    lon_p01, lon_p99 = percentile(lons, 1), percentile(lons, 99)
    dep_p01, dep_p99 = percentile(depths, 1), percentile(depths, 99)

    lat_mid = (lat_p01 + lat_p99) / 2.0 if lat_p01 is not None else None
    lon_mid = (lon_p01 + lon_p99) / 2.0 if lon_p01 is not None else None

    lat_span_deg = abs(lat_p99 - lat_p01) if lat_p01 is not None else None
    lon_span_deg = abs(lon_p99 - lon_p01) if lon_p01 is not None else None

    lat_km = lat_span_deg * 111.0 if lat_span_deg is not None else None
    lon_km = lon_span_deg * 99.5 if lon_span_deg is not None else None

    payload = {
        "schema": "rmu.geospatial_domain_state.v1_11A",
        "version": "v1.11A",
        "updated_utc": now_iso(),
        "source_csv": str(csv_path),
        "row_count": rows,
        "coordinate_contract": {
            "x": "longitude",
            "y": "depth/elevation",
            "z": "latitude",
            "t": "row_order_or_time"
        },
        "source_stats": {
            "latitude": {
                "count": len(lats),
                "min": min(lats) if lats else None,
                "max": max(lats) if lats else None,
                "p01": lat_p01,
                "p99": lat_p99,
                "mean": statistics.fmean(lats) if lats else None
            },
            "longitude": {
                "count": len(lons),
                "min": min(lons) if lons else None,
                "max": max(lons) if lons else None,
                "p01": lon_p01,
                "p99": lon_p99,
                "mean": statistics.fmean(lons) if lons else None
            },
            "depth_or_elevation": {
                "count": len(depths),
                "min": min(depths) if depths else None,
                "max": max(depths) if depths else None,
                "p01": dep_p01,
                "p99": dep_p99,
                "mean": statistics.fmean(depths) if depths else None
            }
        },
        "derived_geographic_span": {
            "lat_mid": lat_mid,
            "lon_mid": lon_mid,
            "lat_span_deg_p01_p99": lat_span_deg,
            "lon_span_deg_p01_p99": lon_span_deg,
            "approx_north_south_km": lat_km,
            "approx_east_west_km": lon_km
        },
        "simulation_world": cfg["simulation_world"],
        "status": "ready"
    }

    OUT_PATH.write_text(json.dumps(payload, indent=2) + "\n")

    print("RMU v1.11A phase 1 complete")
    print("CSV:", csv_path)
    print("rows:", rows)
    print("approx east/west km:", lon_km)
    print("approx north/south km:", lat_km)
    print("wrote:", OUT_PATH)


if __name__ == "__main__":
    main()

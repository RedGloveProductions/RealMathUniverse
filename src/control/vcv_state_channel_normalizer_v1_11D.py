from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any


ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
VCV_STATE = ROOT / "output/vcv_state.json"

EXPECTED = {
    "/ch/7": "color_index",
    "/ch/8": "behavior_gate",
    "/ch/18": "behavior_code",
    "/ch/19": "color_gate",
}


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
        text=True,
    )

    with os.fdopen(fd, "w") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")

    os.replace(tmp, path)


def as_channel_obj(address: str, label: str, value: Any, source: str) -> dict[str, Any]:
    if isinstance(value, dict):
        raw = value.get("raw", value.get("value", value.get("mapped", 0.0)))
        mapped = value.get("mapped", value.get("value", raw))
        voices = value.get("voices", [])
        voice_count = value.get("voice_count", len(voices) if isinstance(voices, list) else 1)

        return {
            "label": value.get("label", label),
            "raw": raw,
            "value": value.get("value", mapped),
            "mapped": mapped,
            "voices": voices if isinstance(voices, list) else [raw],
            "voice_count": voice_count,
            "source": value.get("source", source),
            "updated_unix": value.get("updated_unix", time.time()),
        }

    try:
        number = float(value)
    except Exception:
        number = 0.0

    return {
        "label": label,
        "raw": number,
        "value": number,
        "mapped": number,
        "voices": [number],
        "voice_count": 1,
        "source": source,
        "updated_unix": time.time(),
    }


def possible_keys(address: str) -> list[str]:
    n = address.split("/")[-1]
    return [
        address,
        n,
        f"ch/{n}",
        f"ch{n}",
        f"channel_{n}",
        f"channel{n}",
        int(n),
    ]


def lookup_in_container(container: Any, address: str) -> tuple[Any, str] | None:
    if not isinstance(container, dict):
        return None

    for key in possible_keys(address):
        if key in container:
            return container[key], f"key:{key}"

    return None


def recursive_lookup(obj: Any, address: str, path: str = "root") -> tuple[Any, str] | None:
    if isinstance(obj, dict):
        direct = lookup_in_container(obj, address)
        if direct is not None:
            value, source = direct
            return value, f"{path}.{source}"

        for key, value in obj.items():
            found = recursive_lookup(value, address, f"{path}.{key}")
            if found is not None:
                return found

    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            found = recursive_lookup(value, address, f"{path}[{i}]")
            if found is not None:
                return found

    return None


def normalize_once() -> tuple[int, list[str]]:
    if not VCV_STATE.exists():
        return 0, ["FAIL missing output/vcv_state.json"]

    try:
        data = json.loads(VCV_STATE.read_text())
    except Exception as exc:
        return 0, [f"FAIL unreadable vcv_state.json {exc}"]

    data.setdefault("channels", {})
    data.setdefault("labels", {})

    changed = 0
    report: list[str] = []

    for address, label in EXPECTED.items():
        existing = data["channels"].get(address)

        if existing is not None:
            data["labels"][address] = label
            report.append(f"PASS {address} present")
            continue

        found = None

        # Prefer known bridge structures first.
        for top_key in [
            "channels",
            "raw_channels",
            "mapped_values",
            "direct_channels",
            "values",
            "raw",
            "mapped",
            "vcvRawChannelValues",
            "vcvChannelValues",
        ]:
            found = lookup_in_container(data.get(top_key), address)
            if found is not None:
                value, source = found
                data["channels"][address] = as_channel_obj(address, label, value, f"normalizer:{top_key}:{source}")
                data["labels"][address] = label
                changed += 1
                report.append(f"PASS {address} repaired_from {top_key}:{source}")
                break

        if found is not None:
            continue

        # Fallback recursive search.
        found = recursive_lookup(data, address)
        if found is not None:
            value, source = found
            data["channels"][address] = as_channel_obj(address, label, value, f"normalizer_recursive:{source}")
            data["labels"][address] = label
            changed += 1
            report.append(f"PASS {address} repaired_from {source}")
            continue

        # Do not fake voltage silently.
        report.append(f"FAIL {address} no_source_found")

    if changed:
        data["schema"] = data.get("schema", "rmu.vcv_state")
        data["normalizer_v1_11D"] = {
            "active": True,
            "updated_unix": time.time(),
            "expected": EXPECTED,
        }
        atomic_write_json(VCV_STATE, data)

    return changed, report


def main() -> None:
    print("RMU v1.11D VCV channel normalizer")
    print("Watching /ch/7 /ch/8 /ch/18 /ch/19. Ctrl+C to stop.")

    last = None

    while True:
        changed, report = normalize_once()
        line = " | ".join(report)

        if line != last or changed:
            print(line)
            last = line

        time.sleep(0.25)


if __name__ == "__main__":
    main()

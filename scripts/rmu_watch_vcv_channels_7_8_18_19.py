from __future__ import annotations

import json
import time
from pathlib import Path


ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
VCV = ROOT / "output/vcv_state.json"

WATCH = ["/ch/7", "/ch/8", "/ch/18", "/ch/19"]


def fmt_channel(ch: str, obj: dict) -> str:
    c = obj.get("channels", {}).get(ch)
    if not c:
        return f"{ch}=MISSING"

    raw = c.get("raw")
    value = c.get("value")
    mapped = c.get("mapped")
    voices = c.get("voice_count")
    label = c.get("label")

    return f"{ch} raw={raw} value={value} mapped={mapped} voices={voices} label={label}"


def main() -> None:
    print("Watching /ch/7 /ch/8 /ch/18 /ch/19. Ctrl+C to stop.")
    last = None

    while True:
        try:
            obj = json.loads(VCV.read_text())
            line = " | ".join(fmt_channel(ch, obj) for ch in WATCH)

            if line != last:
                print(line)
                last = line

        except Exception as exc:
            print(f"READ_FAIL {exc}")

        time.sleep(0.25)


if __name__ == "__main__":
    main()

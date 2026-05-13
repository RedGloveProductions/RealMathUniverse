from __future__ import annotations

from pathlib import Path
import json
import re

ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift"
RESOLVER = ROOT / "src/control/operator_authority_resolver.py"
BRIDGE = ROOT / "src/control/vcv_osc_bridge.py"
OUT = ROOT / "output/v1_11D_control_visual_audit.txt"


def read(path: Path) -> str:
    return path.read_text(errors="replace") if path.exists() else ""


def section(title: str) -> list[str]:
    return ["", "=" * 100, title, "=" * 100]


def grep_lines(text: str, patterns: list[str], radius: int = 3, limit: int = 80) -> list[str]:
    lines = text.splitlines()
    out = []
    hits = 0

    for i, line in enumerate(lines):
        if any(re.search(p, line, re.IGNORECASE) for p in patterns):
            hits += 1
            if hits > limit:
                out.append(f"... hit limit {limit}, more omitted ...")
                break

            out.append("")
            out.append(f"--- hit line {i + 1} ---")
            start = max(0, i - radius)
            end = min(len(lines), i + radius + 1)

            for j in range(start, end):
                mark = ">>" if j == i else "  "
                out.append(f"{mark} {j + 1:05d}: {lines[j]}")

    if hits == 0:
        out.append("no hits")

    return out


def slice_lines(text: str, start: int, end: int) -> list[str]:
    lines = text.splitlines()
    out = []
    for i in range(max(1, start), min(len(lines), end) + 1):
        out.append(f"{i:05d}: {lines[i - 1]}")
    return out


def dump_json(path: Path) -> list[str]:
    if not path.exists():
        return [f"{path} missing"]

    try:
        obj = json.loads(path.read_text())
        return json.dumps(obj, indent=2, sort_keys=True).splitlines()
    except Exception as exc:
        return [f"Could not parse {path}: {exc}", path.read_text(errors="replace")[:4000]]


def main() -> None:
    main_text = read(MAIN)
    resolver_text = read(RESOLVER)
    bridge_text = read(BRIDGE)

    out: list[str] = []

    out += section("RMU v1.11D CONTROL / VISUAL AUDIT")
    out.append(f"main.swift exists: {MAIN.exists()}")
    out.append(f"operator_authority_resolver.py exists: {RESOLVER.exists()}")
    out.append(f"vcv_osc_bridge.py exists: {BRIDGE.exists()}")

    out += section("1. Current v1.11 markers")
    out += grep_lines(main_text, [r"RMU_V1_11A", r"RMU_V1_11B", r"RMU_V1_11C"], radius=1, limit=120)

    out += section("2. Point rendering shader area, lines 1180-1450")
    out += slice_lines(main_text, 1180, 1450)

    out += section("3. Draw buffer and point-size area, lines 2260-2455")
    out += slice_lines(main_text, 2260, 2455)

    out += section("4. Camera and point-size functions, lines 2640-2740")
    out += slice_lines(main_text, 2640, 2740)

    out += section("5. Primary key handler area, lines 4060-4160")
    out += slice_lines(main_text, 4060, 4160)

    out += section("6. Late v1.8A key/control handler area, lines 5000-5120")
    out += slice_lines(main_text, 5000, 5120)

    out += section("7. Main.swift key/camera/point/coupling search")
    out += grep_lines(
        main_text,
        [
            r"keyDown",
            r"handleKey",
            r"zoomOut",
            r"zoomIn",
            r"panX",
            r"panY",
            r"increasePointSize",
            r"decreasePointSize",
            r"toggleSimulationPause",
            r"geospatialSimulationPaused",
            r"behaviorEffectCode",
            r"rmuV18A",
            r"dataset_coupling",
            r"coupling",
        ],
        radius=4,
        limit=140,
    )

    out += section("8. Resolver behavior/color/channel search")
    out += grep_lines(
        resolver_text,
        [
            r"/ch/7",
            r"/ch/8",
            r"/ch/18",
            r"/ch/19",
            r"behavior",
            r"color",
            r"gate",
            r"manual",
            r"auto",
            r"coupling",
            r"dataset",
        ],
        radius=4,
        limit=160,
    )

    out += section("9. Bridge VCV channel search")
    out += grep_lines(
        bridge_text,
        [
            r"/ch/7",
            r"/ch/8",
            r"/ch/18",
            r"/ch/19",
            r"channel",
            r"voices",
            r"raw",
            r"mapped",
            r"vcv_state",
        ],
        radius=4,
        limit=160,
    )

    out += section("10. Current vcv_state.json")
    out += dump_json(ROOT / "output/vcv_state.json")

    out += section("11. Current effective_control_state.json")
    out += dump_json(ROOT / "output/effective_control_state.json")

    out += section("12. Current operator_authority_state.json")
    out += dump_json(ROOT / "output/operator_authority_state.json")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(out) + "\n")

    print(f"Wrote audit: {OUT}")
    print("")
    print("Show the important sections with:")
    print("sed -n '1,220p' output/v1_11D_control_visual_audit.txt")
    print("sed -n '220,520p' output/v1_11D_control_visual_audit.txt")
    print("sed -n '520,900p' output/v1_11D_control_visual_audit.txt")


if __name__ == "__main__":
    main()

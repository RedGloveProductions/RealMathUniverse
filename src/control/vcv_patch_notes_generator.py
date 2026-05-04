#!/usr/bin/env python3
"""Generate VCV Rack patch notes from config/vcv_profiles.json."""

from __future__ import annotations

from pathlib import Path
import argparse
import datetime as dt
import json
import sys

THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT = THIS_FILE.parents[2]


def load_config(project_root: Path) -> dict:
    path = project_root / "config" / "vcv_profiles.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing profile config: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def generate_markdown(config: dict, profile_name: str) -> str:
    profiles = config.get("profiles", {})
    if profile_name not in profiles:
        available = ", ".join(sorted(profiles.keys()))
        raise KeyError(f"Unknown profile '{profile_name}'. Available: {available}")
    profile = profiles[profile_name]
    channels = profile.get("channels", {})
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = []
    lines.append(f"# RealMathUniverse VCV Patch Notes: {profile.get('title', profile_name)}")
    lines.append("")
    lines.append(f"**Profile:** `{profile_name}`")
    lines.append(f"**Generated:** {now}")
    lines.append(f"**Version:** {config.get('version', 'unknown')}")
    lines.append("")
    lines.append("## Intent")
    lines.append("")
    lines.append(profile.get("intent", "No profile intent provided."))
    lines.append("")
    lines.append("## Fixed OSC Contract")
    lines.append("")
    lines.append("The cvOSCcv channels must remain fixed as `/ch/1` through `/ch/8`. The profile changes the meaning of each channel, not the address.")
    lines.append("")
    lines.append("VCV cvOSCcv should use:")
    lines.append("")
    lines.append("```text")
    lines.append("OSC IP Address: 127.0.0.1")
    lines.append("Out Port:       9000")
    lines.append("In Port:        7001")
    lines.append("Namespace:      blank or /")
    lines.append("Channels:       /ch/1 ... /ch/8")
    lines.append("```")
    lines.append("")
    lines.append("## Channel Map")
    lines.append("")
    lines.append("| Address | Name | Field | Range | Smoothing | Role |")
    lines.append("|---|---|---|---:|---:|---|")
    for address in [f"/ch/{i}" for i in range(1, 9)]:
        cfg = channels.get(address, {})
        rng = f"{cfg.get('min', 0.0)} to {cfg.get('max', 1.0)}"
        lines.append(
            f"| `{address}` | `{cfg.get('name', '')}` | `{cfg.get('field', '')}` | {rng} | {cfg.get('smoothing', '')} | {cfg.get('role', '')} |"
        )
    lines.append("")
    lines.append("## Patch Build Notes")
    lines.append("")
    lines.append("Use VCV modules to produce useful voltages for the mapped field layers. Attenuate before cvOSCcv when needed. The bridge also clamps and smooths, but the cleanest patch is one that intentionally stays inside its profile range.")
    lines.append("")
    lines.append("## Performance Notes")
    lines.append("")
    lines.append("- Start the bridge before expecting VCV field control.")
    lines.append("- Keep `/ch/1` through `/ch/8` unchanged in cvOSCcv.")
    lines.append("- Use the renderer HUD to confirm `VCV: ACTIVE`, `FIELD CTRL: ON`, and the selected profile.")
    lines.append("- Use clean screenshots for documentation and HUD screenshots for diagnostics.")
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate RealMathUniverse VCV patch notes")
    parser.add_argument("profile", nargs="?", default="default_generic")
    parser.add_argument("--project-root", default=str(PROJECT_ROOT))
    parser.add_argument("--out", default=None)
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    project_root = Path(args.project_root).expanduser().resolve()
    config = load_config(project_root)
    profiles = config.get("profiles", {})

    if args.list:
        for name, profile in profiles.items():
            print(f"{name:<28} {profile.get('title', '')}")
        return 0

    markdown = generate_markdown(config, args.profile)
    if args.out:
        out_path = Path(args.out).expanduser().resolve()
    else:
        out_dir = project_root / config.get("global", {}).get("notes_output_dir", "docs/vcv_patch_notes")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{args.profile}_patch_notes.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(markdown, encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


ROOT = Path("/Users/Joe/Documents/RealMathUniverse")

FILES = {
    "operator": ROOT / "output/operator_authority_state.json",
    "effective": ROOT / "output/effective_control_state.json",
    "control": ROOT / "output/control_state.json",
    "runtime": ROOT / "output/runtime_state.json",
    "vcv": ROOT / "output/vcv_state.json",
}


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def get_nested(obj: dict[str, Any], *keys: str, default: Any = None) -> Any:
    cur: Any = obj
    for key in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
    return cur if cur is not None else default


def ch(vcv: dict[str, Any], addr: str) -> Any:
    channels = vcv.get("channels", {})
    if isinstance(channels, dict):
        c = channels.get(addr)
        if isinstance(c, dict):
            return c.get("raw", c.get("value", c.get("mapped")))
    return None


def summarize() -> str:
    op = read_json(FILES["operator"])
    eff = read_json(FILES["effective"])
    ctl = read_json(FILES["control"])
    rt = read_json(FILES["runtime"])
    vcv = read_json(FILES["vcv"])

    parts = []

    parts.append(
        "OP "
        f"autoB={op.get('auto_behavior_enabled')} "
        f"autoF={op.get('auto_fields_enabled')} "
        f"autoCam={op.get('auto_camera_enabled')} "
        f"domain={op.get('active_auto_domain')} "
        f"dataset={op.get('dataset_coupling_mode')} "
        f"selected={op.get('selected_field_layer')} "
        f"manualBeh={op.get('manual_behavior_code')} "
        f"noBeh={op.get('no_behavior_enabled')} "
        f"reason={op.get('last_hotkey_reason')}"
    )

    cmd = op.get("command")
    parts.append(f"CMD {cmd}")

    parts.append(
        "EFF "
        f"authority={get_nested(eff, 'authority', 'behavior', default=eff.get('behavior_authority'))} "
        f"behavior={get_nested(eff, 'effective', 'behavior_code', default=eff.get('behavior_code'))} "
        f"fieldWeights={get_nested(eff, 'effective', 'field_weights', default='?')}"
    )

    parts.append(
        "CONTROL "
        f"behavior_enabled={ctl.get('behavior_enabled')} "
        f"behavior_effect_code={ctl.get('behavior_effect_code')} "
        f"source={ctl.get('behavior_source')} "
        f"runtime={ctl.get('runtime_mode')}"
    )

    parts.append(
        "RUNTIME "
        f"paused={rt.get('simulation_paused', rt.get('paused'))} "
        f"mode={rt.get('runtime_mode')} "
        f"behavior={rt.get('behavior_effect_code')}"
    )

    parts.append(
        "VCV "
        f"/ch7={ch(vcv, '/ch/7')} "
        f"/ch8={ch(vcv, '/ch/8')} "
        f"/ch18={ch(vcv, '/ch/18')} "
        f"/ch19={ch(vcv, '/ch/19')}"
    )

    return "\n".join(parts)


def main() -> None:
    print("RMU v1.11F live control monitor")
    print("Press SHIFT+J, SHIFT+F, SHIFT+V, SHIFT+D, SHIFT+., SHIFT+,, CTRL+-, CTRL+= in the simulator.")
    print("This terminal will print when state changes.\n")

    last = None

    while True:
        current = summarize()
        if current != last:
            print("=" * 120)
            print(time.strftime("%H:%M:%S"))
            print(current)
            last = current

        time.sleep(0.15)


if __name__ == "__main__":
    main()

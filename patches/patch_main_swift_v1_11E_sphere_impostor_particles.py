from __future__ import annotations

import re
import shutil
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift"
MARKER = "RMU_V1_11E_SPHERE_IMPOSTOR_PARTICLES"


def fail(msg: str) -> None:
    print("ERROR:", msg)
    sys.exit(1)


def find_matching(text: str, start: int, open_ch: str, close_ch: str) -> int:
    depth = 0
    in_string = False
    escape = False

    for i in range(start, len(text)):
        ch = text[i]

        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
            continue

        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return i

    return -1


def find_fragment_function(text: str) -> tuple[int, int, str, str, str, str]:
    """
    Returns:
      func_start, func_end, return_type, func_name, param_text, stage_var
    """
    matches = list(re.finditer(r"fragment\s+(float4|half4)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", text))

    candidates = []

    for m in matches:
        paren_open = text.find("(", m.start())
        paren_close = find_matching(text, paren_open, "(", ")")
        if paren_close < 0:
            continue

        brace_open = text.find("{", paren_close)
        if brace_open < 0:
            continue

        brace_close = find_matching(text, brace_open, "{", "}")
        if brace_close < 0:
            continue

        params = text[paren_open + 1:paren_close]
        body = text[brace_open + 1:brace_close]

        if "[[stage_in]]" not in params:
            continue

        stage_match = re.search(r"([A-Za-z_][A-Za-z0-9_]*)\s*\[\[stage_in\]\]", params)
        if not stage_match:
            continue

        stage_var = stage_match.group(1)

        if f"{stage_var}.color" not in body and ".color" not in body:
            continue

        candidates.append((m.start(), brace_close + 1, m.group(1), m.group(2), params, stage_var))

    if not candidates:
        fail("Could not find a fragment function with [[stage_in]] and color output.")

    if len(candidates) > 1:
        print("Found multiple fragment candidates, using first:")
        for c in candidates:
            print(f" - {c[2]} {c[3]}(...)")

    return candidates[0]


def main() -> int:
    if not MAIN.exists():
        fail(f"Missing {MAIN}")

    original = MAIN.read_text()

    if MARKER in original:
        print("v1.11E sphere impostor patch already present.")
        return 0

    if "[[point_size]]" not in original:
        fail("Could not find Metal [[point_size]] path. This patch expects point primitives.")

    if ".point" not in original:
        fail("Could not find .point draw path. This patch expects point primitives.")

    backup = MAIN.with_name(
        f"main.swift.v1_11E_sphere_impostor_particles.backup.{time.strftime('%Y%m%d_%H%M%S')}.bak"
    )
    shutil.copy2(MAIN, backup)
    print("Backup:", backup)

    s = original

    func_start, func_end, ret_type, func_name, params, stage_var = find_fragment_function(s)

    if "[[point_coord]]" in s[func_start:func_end]:
        fail("Fragment function already has point_coord. Refusing to double patch.")

    new_params = params.rstrip()
    if new_params:
        new_params = new_params + ",\n            float2 pointCoord [[point_coord]]"
    else:
        new_params = "float2 pointCoord [[point_coord]]"

    return_ctor = "float4" if ret_type == "float4" else "half4"
    color_expr = f"{stage_var}.color"

    new_body = f'''fragment {ret_type} {func_name}(
            {new_params}
        ) {{
            // {MARKER}
            // Metal point primitives are square by default. This fragment path turns each
            // oversized point into a shaded sphere impostor.
            float2 uv = pointCoord * 2.0 - 1.0;
            float r2 = dot(uv, uv);

            if (r2 > 1.0) {{
                discard_fragment();
            }}

            float z = sqrt(max(1.0 - r2, 0.0));
            float3 normal = normalize(float3(uv.x, uv.y, z));

            float3 lightDir = normalize(float3(-0.45, 0.62, 0.78));
            float diffuse = max(dot(normal, lightDir), 0.0);

            float rim = pow(clamp(1.0 - z, 0.0, 1.0), 2.35);
            float core = 0.30 + 0.70 * diffuse;
            float edgeSoft = smoothstep(1.0, 0.72, r2);

            float3 baseColor = {color_expr}.rgb;
            float3 shaded = baseColor * core;
            shaded += baseColor * rim * 0.35;
            shaded += float3(1.0, 1.0, 1.0) * pow(diffuse, 16.0) * 0.18;

            float alpha = {color_expr}.a * edgeSoft;

            return {return_ctor}(shaded, alpha);
        }}'''

    s = s[:func_start] + new_body + s[func_end:]

    # Keep large particles, but reduce from giant square-block size if needed.
    # 22 is large enough to read as spheres without fully tiling into rectangles.
    s, n_default = re.subn(
        r"var\s+pointSize\s*:\s*Float\s*=\s*[0-9.]+",
        f"var pointSize: Float = 22.0 // {MARKER}: large shaded sphere impostors",
        s,
        count=1,
    )

    s, n_inc = re.subn(
        r"func\s+increasePointSize\(\)\s*\{\s*pointSize\s*=\s*min\(\s*pointSize\s*\+\s*[0-9.]+\s*,\s*[0-9.]+\s*\);\s*hud\?\.updateText\(\)\s*\}",
        f"func increasePointSize() {{ pointSize = min(pointSize + 3.0, 96.0); hud?.updateText() }} // {MARKER}",
        s,
        count=1,
    )

    s, n_dec = re.subn(
        r"func\s+decreasePointSize\(\)\s*\{\s*pointSize\s*=\s*max\(\s*pointSize\s*-\s*[0-9.]+\s*,\s*[0-9.]+\s*\);\s*hud\?\.updateText\(\)\s*\}",
        f"func decreasePointSize() {{ pointSize = max(pointSize - 3.0, 2.0); hud?.updateText() }} // {MARKER}",
        s,
        count=1,
    )

    s = f"// {MARKER}: shaded circular sphere impostors for large volumetric particles\n" + s

    MAIN.write_text(s)

    print(f"Patched fragment function: {ret_type} {func_name}(...)")
    print(f"pointSize default patched: {n_default}")
    print(f"increasePointSize patched: {n_inc}")
    print(f"decreasePointSize patched: {n_dec}")
    print("Running swift build -c release...")

    result = subprocess.run(
        ["swift", "build", "-c", "release"],
        cwd=str(ROOT / "metal_renderer"),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    print(result.stdout)

    if result.returncode != 0:
        print("Swift build failed. Restoring backup.")
        shutil.copy2(backup, MAIN)
        print("Restored:", backup)
        return result.returncode

    print("v1.11E sphere impostor patch passed Swift build.")
    print("NOTE: Swift build does not always prove embedded Metal compiles at runtime. Launch test is required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

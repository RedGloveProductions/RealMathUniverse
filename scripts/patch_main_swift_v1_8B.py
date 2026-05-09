#!/usr/bin/env python3
from __future__ import annotations

import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

PATCH = "v1.8B-effective-state-ownership-fix"
FUNC_NAME = "rmuV17JPublishEffectiveControlState"
CANONICAL_FILE = "effective_control_state.json"
DEBUG_FILE = "renderer_effective_debug_state.json"


def find_function_range(src: str, func_name: str):
    m = re.search(r"\bfunc\s+" + re.escape(func_name) + r"\b", src)
    if not m:
        return None
    brace = src.find("{", m.end())
    if brace < 0:
        raise RuntimeError(f"Found {func_name}, but could not find opening brace")
    depth = 0
    i = brace
    in_string = False
    escape = False
    while i < len(src):
        ch = src[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return (m.start(), i + 1)
        i += 1
    raise RuntimeError(f"Found {func_name}, but could not match closing brace")


def patch_source(src: str) -> tuple[str, list[str]]:
    notes: list[str] = []

    rng = find_function_range(src, FUNC_NAME)
    if rng is not None:
        start, end = rng
        block = src[start:end]
        original = block
        block = block.replace(CANONICAL_FILE, DEBUG_FILE)
        block = block.replace("rmu.effective_control_state.v1_7J", "rmu.renderer_effective_debug_state.v1_8B")
        block = block.replace("v1.7J-control-schema-consolidation", "v1.8B-renderer-debug-only")
        block = block.replace("MetalRenderer.rmuV17JPublishEffectiveControlState", "MetalRenderer.rmuV18BRendererDebugState")
        block = block.replace('"after_load_vcv"', '"renderer_debug_after_load_vcv"')
        block = block.replace('"after_dataset_coupling"', '"renderer_debug_after_dataset_coupling"')
        if "RMU_V1_8B_RENDERER_DEBUG_ONLY" not in block:
            insert = block.find("{") + 1
            block = block[:insert] + "\n        // RMU_V1_8B_RENDERER_DEBUG_ONLY: do not write canonical effective_control_state.json here." + block[insert:]
        if block != original:
            src = src[:start] + block + src[end:]
            notes.append(f"Patched {FUNC_NAME} to write {DEBUG_FILE}")
        else:
            notes.append(f"{FUNC_NAME} already appeared patched or did not require changes")
    else:
        notes.append(f"{FUNC_NAME} not found; checking for direct canonical writer strings")

    # Safety cleanup for common literal URL construction patterns outside the function.
    # We avoid replacing all uses because future renderer code may legitimately read the canonical file.
    suspicious_patterns = [
        'appendingPathComponent("effective_control_state.json")',
        'appendingPathComponent(\'effective_control_state.json\')',
        '"output/effective_control_state.json"',
        '\"output/effective_control_state.json\"',
    ]
    # Only replace these if they appear near v1.7J markers or the old updated_by marker.
    if "rmu.effective_control_state.v1_7J" in src or "MetalRenderer.rmuV17JPublishEffectiveControlState" in src:
        src = src.replace('appendingPathComponent("effective_control_state.json")', 'appendingPathComponent("renderer_effective_debug_state.json")')
        src = src.replace("appendingPathComponent('effective_control_state.json')", "appendingPathComponent('renderer_effective_debug_state.json')")
        src = src.replace('"output/effective_control_state.json"', '"output/renderer_effective_debug_state.json"')
        src = src.replace("'output/effective_control_state.json'", "'output/renderer_effective_debug_state.json'")
        src = src.replace("rmu.effective_control_state.v1_7J", "rmu.renderer_effective_debug_state.v1_8B")
        src = src.replace("v1.7J-control-schema-consolidation", "v1.8B-renderer-debug-only")
        src = src.replace("MetalRenderer.rmuV17JPublishEffectiveControlState", "MetalRenderer.rmuV18BRendererDebugState")
        notes.append("Applied fallback v1.7J debug-writer string replacements")

    return src, notes


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: patch_main_swift_v1_8B.py /path/to/main.swift", file=sys.stderr)
        return 2

    path = Path(sys.argv[1]).expanduser().resolve()
    if not path.exists():
        print(f"ERROR: main.swift not found: {path}", file=sys.stderr)
        return 1

    src = path.read_text(encoding="utf-8")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_name(f"{path.name}.v1_8B_effective_state_ownership.{stamp}.bak")
    shutil.copy2(path, backup)

    patched, notes = patch_source(src)
    path.write_text(patched, encoding="utf-8")

    print(f"Backed up main.swift to: {backup}")
    for note in notes:
        print(f"- {note}")

    if CANONICAL_FILE in patched and "rmu.effective_control_state.v1_7J" in patched:
        print("WARNING: main.swift still contains v1.7J canonical effective state markers.")
        print("The verifier will check this more strictly.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

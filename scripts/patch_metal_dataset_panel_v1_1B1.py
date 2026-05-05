#!/usr/bin/env python3
"""
RealMathUniverse v1.1B1 hotfix.

Reason:
SHIFT+P is already used by the renderer/trails path in the existing key map,
so the v1.1B dataset-panel toggle can be shadowed before it reaches the new
handler. This patch moves the dataset bottom-panel toggle to SHIFT+D.

SHIFT+N remains the dataset runtime on/off toggle.
"""
from __future__ import annotations
from pathlib import Path
import sys

PROJECT_ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path('/Users/Joe/Documents/RealMathUniverse')
SWIFT = PROJECT_ROOT / 'metal_renderer' / 'Sources' / 'RealMathUniverseMetalRenderer' / 'main.swift'

if not SWIFT.exists():
    raise SystemExit(f'main.swift not found: {SWIFT}')

text = SWIFT.read_text(encoding='utf-8')
original = text

# Patch the actual v1.1B key handler.
replacements = [
    (
        'if characters == "p", shiftDown { renderer?.toggleBottomPanelMode(); hud?.updateText(); return }',
        'if characters == "d", shiftDown { renderer?.toggleBottomPanelMode(); hud?.updateText(); return }',
        'key handler SHIFT+P -> SHIFT+D',
    ),
    (
        'CONTROLS: SHIFT+P field/data panel SHIFT+N data on/off | terminal: ./scripts/rmu_data_mode.sh on/off/toggle/status',
        'CONTROLS: SHIFT+D field/data panel SHIFT+N data on/off | terminal: ./scripts/rmu_data_mode.sh on/off/toggle/status',
        'dataset panel text control label',
    ),
    (
        'SHIFT+C safe mode SHIFT+P data panel',
        'SHIFT+C safe mode SHIFT+D data panel',
        'field panel footer control label',
    ),
]

changed = []
for old, new, label in replacements:
    if old in text:
        text = text.replace(old, new)
        changed.append(label)

# Fallback patch for compact/formatting variations.
if 'SHIFT+P' in text:
    text = text.replace('SHIFT+P field/data panel', 'SHIFT+D field/data panel')
    text = text.replace('SHIFT+P data panel', 'SHIFT+D data panel')
    changed.append('fallback text labels')

if 'characters == "p", shiftDown { renderer?.toggleBottomPanelMode()' in text:
    text = text.replace('characters == "p", shiftDown { renderer?.toggleBottomPanelMode()', 'characters == "d", shiftDown { renderer?.toggleBottomPanelMode()')
    changed.append('fallback key expression')

if text == original:
    print('No v1.1B SHIFT+P dataset-panel code found. Nothing changed.')
    print('This usually means v1.1B did not patch main.swift, or the key was already changed.')
    raise SystemExit(0)

marker = '/* v1.1B1 SHIFT+D DATA PANEL HOTFIX */'
if marker not in text:
    text = text.replace('/* v1.1B DATASET PANEL PATCH */', '/* v1.1B DATASET PANEL PATCH */ ' + marker, 1)

SWIFT.write_text(text, encoding='utf-8')
print('v1.1B1 hotfix applied to:', SWIFT)
print('Changes:', ', '.join(changed))

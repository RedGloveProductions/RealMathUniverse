# RealMathUniverse v1.6B Renderer Species Identity + Metal

## Purpose

v1.6A created the missing per-particle species identity sidecar:

```text
data/processed/species_identity_v1_6A.bin
```

v1.6B consumes that sidecar in the Swift/Metal renderer.

## Scope

This is a renderer/Metal patch. It does not change the v1.5D bridge and it does not rewrite the VCV channel contract.

The patch adds:

```text
species_id buffer        buffer(20)
family_id buffer         buffer(21)
species_weight buffer    buffer(22)
probability bank         buffer(23)
speed bank               buffer(24)
mass bank                buffer(25)
turbulence bank          buffer(26)
cohesion bank            buffer(27)
color RGB bank           buffer(28)
species control enabled buffer(30)
```

## Install

```bash
cd /Users/Joe/Downloads
unzip -o RealMathUniverse_v1_6B_RENDERER_SPECIES_IDENTITY_METAL.zip
./rmu_v1_6B_renderer_species_identity_metal/INSTALL_v1_6B_RENDERER_SPECIES_IDENTITY_METAL.sh /Users/Joe/Documents/RealMathUniverse
```

## Validate

```bash
cd /Users/Joe/Documents/RealMathUniverse
source .venv/bin/activate
python3 tools/validate_v1_6B_renderer_species_identity.py
```

## Monitor

```bash
python3 tools/monitor_v1_6B_species_identity_metal.py
```

## Recovery

The installer backs up `main.swift` before patching. If Swift build fails, the patcher restores the backup automatically and reports failure rather than leaving the renderer broken.

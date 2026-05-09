#!/usr/bin/env bash
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
# RealMathUniverse v1.7A Effective State Monitor
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

set -euo pipefail

PROJECT_ROOT="${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "${PROJECT_ROOT}"

STATE_FILE="output/effective_state.json"

if [[ ! -f "${STATE_FILE}" ]]; then
  echo "No ${STATE_FILE} found yet."
  echo "Start the resolver first:"
  echo "  ./scripts/run_authority_resolver.sh"
  exit 1
fi

while true; do
  clear
  echo "============================================================"
  echo "RealMathUniverse effective_state.json monitor"
  echo "============================================================"
  python3 - <<'PY'
import json
from pathlib import Path

path = Path("output/effective_state.json")
try:
    data = json.loads(path.read_text())
except Exception as exc:
    print(f"ERROR reading {path}: {exc}")
    raise SystemExit(1)

lifecycle = data.get("lifecycle", {})
sources = data.get("sources", {})
authority = data.get("authority", {})
effective = data.get("effective", {})
diagnostics = data.get("diagnostics", {})

behavior = effective.get("behavior", {})
field = effective.get("field", {})
gravity = effective.get("gravity", {})
particles = effective.get("particles", {})
vcv = sources.get("vcv", {})
dataset = sources.get("dataset", {})
species = sources.get("species_identity", {})

print(f"schema:        {data.get('schema')}")
print(f"version:       {data.get('version')}")
print(f"timestamp:     {data.get('timestamp_utc')}")
print()
print(f"runtime_mode:  {lifecycle.get('runtime_mode')}")
print(f"armed:         {lifecycle.get('physics_armed')}")
print(f"paused:        {lifecycle.get('simulation_paused')}")
print()
print(f"vcv fresh:     {vcv.get('fresh')}")
print(f"vcv version:   {vcv.get('version')}")
print(f"channels seen: {vcv.get('channels_seen')}")
print(f"vcv age ms:    {vcv.get('last_update_age_ms')}")
print()
print(f"dataset loaded:   {dataset.get('loaded')}")
print(f"dataset rows:     {dataset.get('row_count')}")
print(f"dataset mode:     {dataset.get('mode')}")
print(f"dataset fallback: {dataset.get('fallback_active')}")
print()
print(f"species loaded:   {species.get('loaded')}")
print(f"species records:  {species.get('records')}")
print(f"species count:    {species.get('species_count')}")
print()
print(f"behavior src:  {authority.get('behavior', {}).get('source')}")
print(f"behavior gate: {authority.get('behavior', {}).get('gate_voltage')}")
print(f"behavior:      {behavior.get('code')}  {behavior.get('name')}  enabled={behavior.get('enabled')}")
print()
print(f"field src:     {authority.get('field_recipe', {}).get('source')}")
print(f"scene index:   {field.get('scene_index')}")
print(f"field recipe:  {field.get('recipe_name')}")
print(f"field weights: {field.get('weights')}")
print()
print(f"gravity src:   {gravity.get('source')}")
print(f"gravity pos:   {gravity.get('well_position')}")
print(f"gravity str:   {gravity.get('well_strength')}")
print()
print(f"particles:     {particles.get('count')}")
print(f"live owner:    {particles.get('live_owner')}")
print(f"seed source:   {particles.get('seed_source')}")
print()
print(f"warnings:      {diagnostics.get('warnings')}")
print(f"stale sources: {diagnostics.get('stale_sources')}")
print(f"fallbacks:     {diagnostics.get('fallbacks_active')}")
PY

  sleep "${RMU_MONITOR_INTERVAL:-1}"
done

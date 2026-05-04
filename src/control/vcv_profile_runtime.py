#!/usr/bin/env python3
"""
RealMathUniverse v0.9C
VCV profile runtime helpers.

Purpose:
    Keep OSC channel numbers fixed as /ch/1 through /ch/8 while allowing
    patch-specific meanings, clamps, smoothing, statistics, and documentation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional
import json
import math
import time


DEFAULT_CHANNELS = [f"/ch/{i}" for i in range(1, 9)]


@dataclass
class ChannelStats:
    count: int = 0
    raw_min: Optional[float] = None
    raw_max: Optional[float] = None
    raw_sum: float = 0.0
    value_min: Optional[float] = None
    value_max: Optional[float] = None
    value_sum: float = 0.0

    def update(self, raw: float, value: float) -> None:
        self.count += 1
        self.raw_sum += raw
        self.value_sum += value
        self.raw_min = raw if self.raw_min is None else min(self.raw_min, raw)
        self.raw_max = raw if self.raw_max is None else max(self.raw_max, raw)
        self.value_min = value if self.value_min is None else min(self.value_min, value)
        self.value_max = value if self.value_max is None else max(self.value_max, value)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "count": self.count,
            "raw_min": self.raw_min,
            "raw_max": self.raw_max,
            "raw_avg": (self.raw_sum / self.count) if self.count else None,
            "value_min": self.value_min,
            "value_max": self.value_max,
            "value_avg": (self.value_sum / self.count) if self.count else None,
        }


@dataclass
class VCVProfileRuntime:
    project_root: Path
    profile_name: str = "default_generic"
    config_path: Path = field(init=False)
    profile_config: Dict[str, Any] = field(default_factory=dict)
    profile: Dict[str, Any] = field(default_factory=dict)
    smoothed: Dict[str, float] = field(default_factory=dict)
    raw_values: Dict[str, float] = field(default_factory=dict)
    last_seen: Dict[str, float] = field(default_factory=dict)
    stats: Dict[str, ChannelStats] = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        self.project_root = Path(self.project_root).expanduser().resolve()
        self.config_path = self.project_root / "config" / "vcv_profiles.json"
        self.load()

    def load(self) -> None:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Missing VCV profile config: {self.config_path}")
        self.profile_config = json.loads(self.config_path.read_text(encoding="utf-8"))
        profiles = self.profile_config.get("profiles", {})
        if self.profile_name not in profiles:
            available = ", ".join(sorted(profiles.keys()))
            raise KeyError(f"Unknown VCV profile '{self.profile_name}'. Available: {available}")
        self.profile = profiles[self.profile_name]
        for address in DEFAULT_CHANNELS:
            channel = self.profile.get("channels", {}).get(address, {})
            default = float(channel.get("default", 0.0))
            self.smoothed[address] = default
            self.raw_values[address] = default
            self.last_seen[address] = 0.0
            self.stats[address] = ChannelStats()

    @property
    def global_config(self) -> Dict[str, Any]:
        return self.profile_config.get("global", {})

    @property
    def state_path(self) -> Path:
        return self.project_root / self.global_config.get("state_path", "runtime/vcv_osc_state.json")

    @property
    def profile_state_path(self) -> Path:
        return self.project_root / self.global_config.get("profile_state_path", "runtime/vcv_profile_state.json")

    @property
    def stats_path(self) -> Path:
        return self.project_root / self.global_config.get("stats_path", "runtime/vcv_profile_stats.json")

    @staticmethod
    def _finite_number(value: Any) -> Optional[float]:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(number):
            return None
        return number

    def channel_config(self, address: str) -> Dict[str, Any]:
        return self.profile.get("channels", {}).get(address, {})

    def process(self, address: str, value: Any) -> Optional[Dict[str, Any]]:
        if address not in DEFAULT_CHANNELS:
            return None
        raw = self._finite_number(value)
        if raw is None:
            return None

        cfg = self.channel_config(address)
        min_value = float(cfg.get("min", 0.0))
        max_value = float(cfg.get("max", 1.0))
        smoothing = float(cfg.get("smoothing", self.global_config.get("default_smoothing", 0.22)))
        smoothing = max(0.0, min(0.995, smoothing))

        if bool(self.global_config.get("safe_clamp", True)) or bool(self.profile.get("safe", True)):
            clamped = max(min_value, min(max_value, raw))
        else:
            clamped = raw

        previous = self.smoothed.get(address, float(cfg.get("default", 0.0)))
        smoothed_value = (previous * smoothing) + (clamped * (1.0 - smoothing))

        if cfg.get("polarity") == "stepped":
            smoothed_value = round(smoothed_value)

        self.raw_values[address] = raw
        self.smoothed[address] = smoothed_value
        self.last_seen[address] = time.time()
        self.stats[address].update(raw, smoothed_value)

        return self.channel_payload(address)

    def channel_payload(self, address: str) -> Dict[str, Any]:
        cfg = self.channel_config(address)
        return {
            "address": address,
            "name": cfg.get("name", address.strip("/")),
            "field": cfg.get("field", cfg.get("name", address.strip("/"))),
            "role": cfg.get("role", ""),
            "raw": self.raw_values.get(address, float(cfg.get("default", 0.0))),
            "value": self.smoothed.get(address, float(cfg.get("default", 0.0))),
            "min": cfg.get("min", 0.0),
            "max": cfg.get("max", 1.0),
            "smoothing": cfg.get("smoothing", self.global_config.get("default_smoothing", 0.22)),
            "last_seen_age": max(0.0, time.time() - self.last_seen.get(address, 0.0)) if self.last_seen.get(address, 0.0) else None,
            "stats": self.stats[address].as_dict(),
        }

    def state_dict(self) -> Dict[str, Any]:
        now = time.time()
        channels = {address: self.channel_payload(address) for address in DEFAULT_CHANNELS}
        values_by_name = {payload["name"]: payload["value"] for payload in channels.values()}
        raw_by_address = {address: self.raw_values.get(address, 0.0) for address in DEFAULT_CHANNELS}
        normalized_by_address = {address: self.smoothed.get(address, 0.0) for address in DEFAULT_CHANNELS}
        active_addresses = [address for address in DEFAULT_CHANNELS if self.last_seen.get(address, 0.0) > 0.0]

        return {
            "version": "0.9C",
            "timestamp": now,
            "age": 0.0,
            "uptime": now - self.start_time,
            "active": bool(active_addresses),
            "status": "active" if active_addresses else "waiting",
            "profile": self.profile_name,
            "profile_title": self.profile.get("title", self.profile_name),
            "profile_intent": self.profile.get("intent", ""),
            "safe": bool(self.profile.get("safe", True)),
            "field_control_default": bool(self.profile.get("field_control_default", True)),
            "channels": channels,
            "values": values_by_name,
            "raw": raw_by_address,
            "normalized": normalized_by_address,
            "active_addresses": active_addresses,
            "channel_order": DEFAULT_CHANNELS,
            "hud": {
                "vcv_profile": self.profile_name,
                "vcv_profile_title": self.profile.get("title", self.profile_name),
                "vcv_status": "ACTIVE" if active_addresses else "WAITING",
                "field_control": "ON" if self.profile.get("field_control_default", True) else "OFF",
                "safe": "ON" if self.profile.get("safe", True) else "OFF",
                "active_channels": ", ".join(active_addresses) if active_addresses else "none",
                "compact_line": self.compact_line(),
            },
        }

    def compact_line(self) -> str:
        parts = []
        for address in DEFAULT_CHANNELS:
            cfg = self.channel_config(address)
            name = cfg.get("name", address)
            raw = self.raw_values.get(address, 0.0)
            val = self.smoothed.get(address, 0.0)
            parts.append(f"{address} {name}={val:.2f} raw={raw:.2f}")
        return " | ".join(parts)

    def write_state(self) -> None:
        state = self.state_dict()
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.profile_state_path.parent.mkdir(parents=True, exist_ok=True)
        self.stats_path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(state, indent=2, sort_keys=True)
        self.state_path.write_text(text + "\n", encoding="utf-8")
        self.profile_state_path.write_text(text + "\n", encoding="utf-8")
        self.stats_path.write_text(json.dumps({
            "version": "0.9C",
            "profile": self.profile_name,
            "profile_title": self.profile.get("title", self.profile_name),
            "uptime": time.time() - self.start_time,
            "channels": {address: self.stats[address].as_dict() for address in DEFAULT_CHANNELS},
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_available_profiles(project_root: Path) -> Dict[str, Any]:
    config_path = Path(project_root).expanduser().resolve() / "config" / "vcv_profiles.json"
    data = json.loads(config_path.read_text(encoding="utf-8"))
    return data.get("profiles", {})

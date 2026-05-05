#!/usr/bin/env python3
"""
RealMathUniverse OSC 32-Channel Monitor

Purpose:
    Listen on local loopback for OSC messages from VCV Rack / cvOSCcv
    and print live readings for /ch/1 through /ch/32.

Default:
    Host: 127.0.0.1
    Port: 9000

Usage:
    cd /Users/Joe/Documents/RealMathUniverse
    source .venv/bin/activate
    python3 tools/osc_32_channel_monitor.py

Optional:
    python3 tools/osc_32_channel_monitor.py --host 127.0.0.1 --port 9000
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Any

try:
    from pythonosc.dispatcher import Dispatcher
    from pythonosc.osc_server import ThreadingOSCUDPServer
except ImportError:
    print("ERROR: python-osc is not installed in this environment.")
    print()
    print("Run:")
    print("  cd /Users/Joe/Documents/RealMathUniverse")
    print("  source .venv/bin/activate")
    print("  python3 -m pip install python-osc")
    sys.exit(1)


CHANNEL_NAMES = {
    1: "probability",
    2: "radial",
    3: "orbital",
    4: "vertical",
    5: "turbulence",
    6: "shell",
    7: "color",
    8: "scene",
    9: "anchor_strength",
    10: "aux_10",
    11: "aux_11",
    12: "aux_12",
    13: "aux_13",
    14: "aux_14",
    15: "aux_15",
    16: "aux_16",
    17: "aux_17",
    18: "aux_18",
    19: "aux_19",
    20: "aux_20",
    21: "aux_21",
    22: "aux_22",
    23: "aux_23",
    24: "aux_24",
    25: "aux_25",
    26: "aux_26",
    27: "aux_27",
    28: "aux_28",
    29: "aux_29",
    30: "aux_30",
    31: "aux_31",
    32: "aux_32",
}


@dataclass
class ChannelState:
    raw: float = 0.0
    normalized: float = 0.0
    last_seen: float = 0.0
    count: int = 0
    active: bool = False


@dataclass
class OSCMonitorState:
    channels: Dict[int, ChannelState] = field(
        default_factory=lambda: {i: ChannelState() for i in range(1, 33)}
    )
    unknown_messages: List[str] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    last_any_signal: float = 0.0
    lock: threading.Lock = field(default_factory=threading.Lock)


def normalize_cv(value: float) -> float:
    """
    Accept either:
        0.0-1.0 normalized signal
        0.0-10.0 V VCV-style signal

    Negative values clamp to 0.
    Values above 10V clamp to 1 after normalization.
    """
    value = float(value)
    if abs(value) > 1.5:
        value = value / 10.0
    return max(0.0, min(value, 1.0))


def clear_screen() -> None:
    os.system("clear")


def format_age(last_seen: float, now: float) -> str:
    if last_seen <= 0:
        return "never"
    age = now - last_seen
    if age < 0.001:
        return "now"
    return f"{age:5.2f}s"


class OSC32ChannelMonitor:
    def __init__(self, host: str, port: int, refresh_hz: float, stale_after: float, print_each_message: bool):
        self.host = host
        self.port = port
        self.refresh_hz = refresh_hz
        self.stale_after = stale_after
        self.print_each_message = print_each_message
        self.state = OSCMonitorState()

    def handle_channel(self, address: str, *args: Any) -> None:
        try:
            channel_number = int(address.split("/")[-1])
        except Exception:
            self.handle_unknown(address, *args)
            return

        if channel_number < 1 or channel_number > 32:
            self.handle_unknown(address, *args)
            return

        if not args:
            return

        try:
            value = float(args[0])
        except Exception:
            return

        now = time.time()
        normalized = normalize_cv(value)

        with self.state.lock:
            ch = self.state.channels[channel_number]
            ch.raw = value
            ch.normalized = normalized
            ch.last_seen = now
            ch.count += 1
            ch.active = True
            self.state.last_any_signal = now

        if self.print_each_message:
            name = CHANNEL_NAMES.get(channel_number, f"ch_{channel_number}")
            print(f"{address:<8} {name:<18} raw={value:>9.4f} norm={normalized:>6.3f}")

    def handle_unknown(self, address: str, *args: Any) -> None:
        now = time.time()
        msg = f"{time.strftime('%H:%M:%S')} UNKNOWN {address} {args}"
        with self.state.lock:
            self.state.unknown_messages.append(msg)
            self.state.unknown_messages = self.state.unknown_messages[-10:]
            self.state.last_any_signal = now

    def render_dashboard(self) -> None:
        while True:
            now = time.time()
            with self.state.lock:
                snapshot = {
                    i: ChannelState(
                        raw=ch.raw,
                        normalized=ch.normalized,
                        last_seen=ch.last_seen,
                        count=ch.count,
                        active=(ch.last_seen > 0 and (now - ch.last_seen) <= self.stale_after),
                    )
                    for i, ch in self.state.channels.items()
                }
                unknown = list(self.state.unknown_messages)
                last_any = self.state.last_any_signal

            clear_screen()

            print("============================================================")
            print("RealMathUniverse OSC 32-Channel Monitor")
            print("============================================================")
            print(f"Listening:      {self.host}:{self.port}")
            print(f"Watching:       /ch/1 through /ch/32")
            print(f"Stale after:    {self.stale_after:.2f}s")
            print(f"Last signal:    {format_age(last_any, now)}")
            print("Press Ctrl-C to stop.")
            print("============================================================")
            print()

            print(f"{'CH':>3}  {'ADDRESS':<8} {'NAME':<18} {'RAW':>10} {'NORM':>8} {'AGE':>8} {'COUNT':>8} {'STATE':>8}")
            print("-" * 82)

            for i in range(1, 33):
                ch = snapshot[i]
                name = CHANNEL_NAMES.get(i, f"aux_{i}")
                address = f"/ch/{i}"
                state_label = "ACTIVE" if ch.active else "STALE" if ch.last_seen > 0 else "WAIT"
                print(
                    f"{i:>3}  "
                    f"{address:<8} "
                    f"{name:<18} "
                    f"{ch.raw:>10.4f} "
                    f"{ch.normalized:>8.3f} "
                    f"{format_age(ch.last_seen, now):>8} "
                    f"{ch.count:>8} "
                    f"{state_label:>8}"
                )

            if unknown:
                print()
                print("Recent unknown OSC messages:")
                for msg in unknown[-10:]:
                    print(f"  {msg}")

            time.sleep(max(0.05, 1.0 / self.refresh_hz))

    def run(self) -> None:
        dispatcher = Dispatcher()

        for i in range(1, 33):
            dispatcher.map(f"/ch/{i}", self.handle_channel)

        dispatcher.set_default_handler(self.handle_unknown)

        server = ThreadingOSCUDPServer((self.host, self.port), dispatcher)

        dashboard_thread = threading.Thread(target=self.render_dashboard, daemon=True)
        dashboard_thread.start()

        print(f"Listening for OSC on {self.host}:{self.port}")
        server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor OSC /ch/1 through /ch/32 on local loopback.")
    parser.add_argument("--host", default="127.0.0.1", help="OSC listen host. Default: 127.0.0.1")
    parser.add_argument("--port", type=int, default=9000, help="OSC listen port. Default: 9000")
    parser.add_argument("--refresh-hz", type=float, default=8.0, help="Dashboard refresh rate. Default: 8 Hz")
    parser.add_argument("--stale-after", type=float, default=2.0, help="Seconds before a channel is marked stale.")
    parser.add_argument(
        "--print-each-message",
        action="store_true",
        help="Print every incoming OSC message instead of only the dashboard.",
    )

    args = parser.parse_args()

    monitor = OSC32ChannelMonitor(
        host=args.host,
        port=args.port,
        refresh_hz=args.refresh_hz,
        stale_after=args.stale_after,
        print_each_message=args.print_each_message,
    )

    try:
        monitor.run()
    except KeyboardInterrupt:
        print()
        print("OSC monitor stopped.")


if __name__ == "__main__":
    main()

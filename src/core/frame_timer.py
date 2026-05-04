"""
Frame timer for RealMathUniverse v0.2B.

Purpose:
    Track measured-frame update timing separately from warmup frames.

Why:
    GPU backends, especially PyTorch MPS, often have expensive first-frame
    compilation/allocation/synchronization behavior. v0.2B separates warmup
    from measured timing so benchmark reports are more honest.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, asdict


@dataclass
class FrameTimingStats:
    frame_count: int
    last_frame_ms: float
    average_frame_ms: float
    min_frame_ms: float
    max_frame_ms: float
    estimated_fps_from_average: float

    def to_dict(self):
        return asdict(self)


class FrameTimer:
    def __init__(self):
        self._frame_start = None
        self.samples_ms: list[float] = []

    def begin_frame(self) -> None:
        self._frame_start = time.perf_counter()

    def end_frame(self, record: bool = True) -> float:
        if self._frame_start is None:
            return 0.0
        dt_ms = (time.perf_counter() - self._frame_start) * 1000.0
        if record:
            self.samples_ms.append(dt_ms)
        self._frame_start = None
        return dt_ms

    def reset(self) -> None:
        self._frame_start = None
        self.samples_ms.clear()

    def stats(self) -> FrameTimingStats:
        if not self.samples_ms:
            return FrameTimingStats(0, 0.0, 0.0, 0.0, 0.0, 0.0)

        total = sum(self.samples_ms)
        avg = total / len(self.samples_ms)
        fps = 1000.0 / avg if avg > 0 else 0.0
        return FrameTimingStats(
            frame_count=len(self.samples_ms),
            last_frame_ms=self.samples_ms[-1],
            average_frame_ms=avg,
            min_frame_ms=min(self.samples_ms),
            max_frame_ms=max(self.samples_ms),
            estimated_fps_from_average=fps,
        )

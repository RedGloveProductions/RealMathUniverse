"""
$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
RealMathUniverse Buffer Registry
Version: 0.1B

Purpose:
    Own large simulation arrays and record their size, dtype, shape, and backend.

Why:
    GPU-first systems should not allow random modules to blindly allocate huge
    arrays. Centralized buffers make scaling, logging, and memory preflight sane.
$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
"""

from __future__ import annotations

from typing import Any


class BufferRegistry:
    def __init__(self, xp, backend_report, diagnostics):
        self.xp = xp
        self.backend_report = backend_report
        self.diagnostics = diagnostics
        self.buffers: dict[str, Any] = {}
        self.metadata: dict[str, dict[str, Any]] = {}

    def create(self, name: str, shape: tuple[int, ...], dtype):
        if name in self.buffers:
            raise KeyError(f"Buffer already exists: {name}")

        array = self.xp.zeros(shape, dtype=dtype)
        self.buffers[name] = array

        itemsize = self._itemsize(array, dtype)
        bytes_estimate = int(itemsize)
        for dim in shape:
            bytes_estimate *= int(dim)

        self.metadata[name] = {
            "shape": list(shape),
            "dtype": str(dtype),
            "estimated_bytes": bytes_estimate,
            "estimated_mb": bytes_estimate / (1024 ** 2),
            "backend": self.backend_report.backend_name,
        }

        self.diagnostics.info(
            f"Allocated buffer '{name}' shape={shape} "
            f"~{self._format_bytes(bytes_estimate)}"
        )
        return array

    def get(self, name: str):
        if name not in self.buffers:
            raise KeyError(f"Missing buffer: {name}")
        return self.buffers[name]

    def exists(self, name: str) -> bool:
        return name in self.buffers

    def describe_buffers(self) -> dict[str, Any]:
        total_bytes = sum(m["estimated_bytes"] for m in self.metadata.values())
        return {
            "backend": self.backend_report.backend_name,
            "total_estimated_bytes": total_bytes,
            "total_estimated_mb": total_bytes / (1024 ** 2),
            "total_estimated_gb": total_bytes / (1024 ** 3),
            "buffers": self.metadata,
        }

    def _itemsize(self, array, dtype) -> int:
        if hasattr(array, "element_size"):
            return int(array.element_size())
        if hasattr(array, "itemsize"):
            return int(array.itemsize)
        # Conservative fallback for float32/int32.
        return 4

    def _format_bytes(self, value: int) -> str:
        if value >= 1024 ** 3:
            return f"{value / (1024 ** 3):.3f} GB"
        if value >= 1024 ** 2:
            return f"{value / (1024 ** 2):.2f} MB"
        if value >= 1024:
            return f"{value / 1024:.2f} KB"
        return f"{value} bytes"

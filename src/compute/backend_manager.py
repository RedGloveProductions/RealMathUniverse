"""
$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
RealMathUniverse Compute Backend Manager
Version: 0.2E

Purpose:
    Select and initialize the best available compute backend.

Priority:
    1. CuPy CUDA
    2. PyTorch CUDA
    3. PyTorch MPS / Apple Metal Performance Shaders
    4. NumPy CPU fallback, only when the active profile permits it

v0.2E Update:
    TorchArrayAPI exposes indexing/sampling helpers needed for active field
    sampling stress tests.
$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class BackendReport:
    backend_name: str = "uninitialized"
    device_name: str = "unknown"
    is_gpu: bool = False
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TorchArrayAPI:
    """
    Small adapter exposing a NumPy-like subset over torch tensors.
    This keeps simulation modules mostly backend-neutral.
    """

    def __init__(self, torch_module, device: str):
        self.torch = torch_module
        self.device = device
        self.float32 = torch_module.float32
        self.float64 = torch_module.float64
        self.int32 = torch_module.int32
        self.int64 = torch_module.int64

    def zeros(self, shape, dtype=None):
        return self.torch.zeros(shape, dtype=dtype or self.float32, device=self.device)

    def zeros_like(self, value):
        return self.torch.zeros_like(value)

    def ones(self, shape, dtype=None):
        return self.torch.ones(shape, dtype=dtype or self.float32, device=self.device)

    def full(self, shape, fill_value, dtype=None):
        return self.torch.full(shape, fill_value, dtype=dtype or self.float32, device=self.device)

    def full_like(self, value, fill_value):
        return self.torch.full_like(value, fill_value)

    def asarray(self, data, dtype=None):
        return self.torch.tensor(data, dtype=dtype or self.float32, device=self.device)

    def arange(self, *args, dtype=None):
        return self.torch.arange(*args, dtype=dtype or self.float32, device=self.device)

    def linspace(self, start, stop, num=None, dtype=None, **kwargs):
        steps = num if num is not None else kwargs.get("steps")
        if steps is None:
            raise ValueError("TorchArrayAPI.linspace requires num or steps.")
        return self.torch.linspace(start, stop, steps=int(steps), dtype=dtype or self.float32, device=self.device)

    def sin(self, value):
        return self.torch.sin(value)

    def cos(self, value):
        return self.torch.cos(value)

    def sqrt(self, value):
        return self.torch.sqrt(value)

    def abs(self, value):
        return self.torch.abs(value)

    def floor(self, value):
        return self.torch.floor(value)

    def mean(self, value):
        return self.torch.mean(value)

    def min(self, value):
        return self.torch.min(value)

    def max(self, value):
        return self.torch.max(value)

    def clamp(self, value, min=None, max=None):
        return self.torch.clamp(value, min=min, max=max)

    def stack(self, values, axis=0):
        return self.torch.stack(list(values), dim=axis)

    def where(self, condition, a, b):
        return self.torch.where(condition, a, b)

    def astype(self, value, dtype):
        return value.to(dtype=dtype)

    def to_float(self, value) -> float:
        if hasattr(value, "detach"):
            return float(value.detach().cpu().item())
        if hasattr(value, "item"):
            return float(value.item())
        return float(value)

    def to_cpu_list(self, value):
        if hasattr(value, "detach"):
            return value.detach().cpu().tolist()
        if hasattr(value, "tolist"):
            return value.tolist()
        return value


class ComputeBackendManager:
    def __init__(self, profile, gpu_config: dict[str, Any], diagnostics):
        self.profile = profile
        self.gpu_config = gpu_config
        self.diagnostics = diagnostics
        self.xp = None
        self.backend_report = BackendReport()
        self.float32_dtype = None
        self.float64_dtype = None
        self.int32_dtype = None
        self.int64_dtype = None

        self._backend_kind = "none"
        self._cupy = None
        self._torch = None
        self._torch_device = None

    def initialize(self) -> None:
        backend_priority = self.gpu_config["gpu"].get("backend_priority", [])
        requested = self.profile.compute_backend

        if requested not in ("auto", "cuda_or_metal"):
            backend_priority = [requested] + [b for b in backend_priority if b != requested]

        self.diagnostics.info(f"Backend priority: {backend_priority}")

        for backend in backend_priority:
            try:
                if backend == "cupy" and self._try_cupy():
                    return
                if backend == "torch_cuda" and self._try_torch_cuda():
                    return
                if backend == "torch_mps" and self._try_torch_mps():
                    return
                if backend == "numpy" and self._try_numpy():
                    return
            except Exception as exc:
                self.diagnostics.warn(f"Backend candidate '{backend}' failed: {exc}")

        if self.profile.strict_gpu or not self.profile.allow_cpu_fallback:
            raise RuntimeError(
                "No acceptable GPU backend was found and this profile does not allow CPU fallback."
            )

        if self._try_numpy():
            return

        raise RuntimeError("No compute backend could be initialized.")

    def _try_cupy(self) -> bool:
        import importlib

        cupy = importlib.import_module("cupy")
        device_count = int(cupy.cuda.runtime.getDeviceCount())
        if device_count < 1:
            return False

        device_id = 0
        device = cupy.cuda.Device(device_id)
        props = cupy.cuda.runtime.getDeviceProperties(device_id)
        device_name = props["name"].decode("utf-8") if isinstance(props["name"], bytes) else str(props["name"])
        free_bytes, total_bytes = cupy.cuda.runtime.memGetInfo()

        self.xp = cupy
        self._cupy = cupy
        self._backend_kind = "cupy"
        self.float32_dtype = cupy.float32
        self.float64_dtype = cupy.float64
        self.int32_dtype = cupy.int32
        self.int64_dtype = cupy.int64
        self.backend_report = BackendReport(
            backend_name="cupy",
            device_name=device_name,
            is_gpu=True,
            details={
                "device_count": device_count,
                "device_id": device.id,
                "free_bytes": int(free_bytes),
                "total_bytes": int(total_bytes),
            },
        )
        self.diagnostics.info(f"Initialized CuPy CUDA backend: {device_name}")
        return True

    def _try_torch_cuda(self) -> bool:
        import importlib

        torch = importlib.import_module("torch")
        if not torch.cuda.is_available():
            return False

        device_name = torch.cuda.get_device_name(0)
        free_bytes, total_bytes = torch.cuda.mem_get_info(0)

        self.xp = TorchArrayAPI(torch, "cuda")
        self._torch = torch
        self._torch_device = "cuda"
        self._backend_kind = "torch_cuda"
        self.float32_dtype = torch.float32
        self.float64_dtype = torch.float64
        self.int32_dtype = torch.int32
        self.int64_dtype = torch.int64
        self.backend_report = BackendReport(
            backend_name="torch_cuda",
            device_name=device_name,
            is_gpu=True,
            details={
                "device": "cuda",
                "free_bytes": int(free_bytes),
                "total_bytes": int(total_bytes),
                "torch_version": str(torch.__version__),
            },
        )
        self.diagnostics.info(f"Initialized PyTorch CUDA backend: {device_name}")
        return True

    def _try_torch_mps(self) -> bool:
        import importlib
        import platform

        torch = importlib.import_module("torch")
        if not hasattr(torch.backends, "mps") or not torch.backends.mps.is_available():
            return False

        self.xp = TorchArrayAPI(torch, "mps")
        self._torch = torch
        self._torch_device = "mps"
        self._backend_kind = "torch_mps"
        self.float32_dtype = torch.float32
        self.float64_dtype = torch.float64
        self.int32_dtype = torch.int32
        self.int64_dtype = torch.int64
        self.backend_report = BackendReport(
            backend_name="torch_mps",
            device_name="Apple Metal Performance Shaders",
            is_gpu=True,
            details={
                "device": "mps",
                "torch_version": str(torch.__version__),
                "platform": platform.platform(),
                "available_memory_note": "PyTorch MPS does not report free VRAM like CUDA.",
            },
        )
        self.diagnostics.info("Initialized PyTorch MPS backend.")
        return True

    def _try_numpy(self) -> bool:
        if self.profile.strict_gpu or not self.profile.allow_cpu_fallback:
            self.diagnostics.warn("NumPy CPU fallback rejected by active profile.")
            return False

        import numpy as np

        self.xp = np
        self._backend_kind = "numpy"
        self.float32_dtype = np.float32
        self.float64_dtype = np.float64
        self.int32_dtype = np.int32
        self.int64_dtype = np.int64
        self.backend_report = BackendReport(
            backend_name="numpy",
            device_name="CPU fallback",
            is_gpu=False,
            details={"fallback": True},
        )
        self.diagnostics.warn("Initialized NumPy CPU fallback backend.")
        return True

    def dtype_from_profile(self, precision: str):
        if precision in ("float64", "double"):
            return self.float64_dtype
        return self.float32_dtype

    def to_float(self, value) -> float:
        if hasattr(self.xp, "to_float"):
            return self.xp.to_float(value)
        if hasattr(value, "item"):
            return float(value.item())
        return float(value)

    def available_device_memory_bytes(self) -> int | None:
        if self._backend_kind == "cupy" and self._cupy is not None:
            free_bytes, _total_bytes = self._cupy.cuda.runtime.memGetInfo()
            return int(free_bytes)

        if self._backend_kind == "torch_cuda" and self._torch is not None:
            free_bytes, _total_bytes = self._torch.cuda.mem_get_info(0)
            return int(free_bytes)

        return None

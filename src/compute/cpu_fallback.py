"""
CPU fallback marker.

The actual CPU fallback is NumPy through backend_manager.py. This file exists so
future code has an obvious place for CPU-specific optimized paths.
"""

from __future__ import annotations


CPU_FALLBACK_AVAILABLE = True

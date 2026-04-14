"""Watermark verification (Chatterbox = PerTh).

We do NOT apply a watermark for Chatterbox — Resemble bakes one in already.
We only verify it survived our pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class WatermarkResult:
    scheme: str
    detected: bool


_perth_wm = None


def _get_perth():
    global _perth_wm
    if _perth_wm is None:
        import perth
        _perth_wm = perth.PerthImplicitWatermarker()
    return _perth_wm


def verify_perth(samples: np.ndarray, sample_rate: int) -> WatermarkResult:
    wm = _get_perth()
    score = float(wm.get_watermark(samples.astype(np.float32), sample_rate=sample_rate))
    return WatermarkResult(scheme="perth", detected=score >= 0.5)


def verify(scheme: str, samples: np.ndarray, sample_rate: int) -> WatermarkResult:
    if scheme == "perth":
        return verify_perth(samples, sample_rate)
    # OmniVoice/Qwen3 (M6/M7) get AudioSeal applied here, then verified.
    raise ValueError(f"unsupported watermark scheme: {scheme}")

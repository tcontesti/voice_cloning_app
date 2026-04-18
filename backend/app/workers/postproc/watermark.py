"""Watermark apply + verify.

Per-model policy (M6):
- chatterbox  → Resemble PerTh embedded by the model itself; only verify.
- omnivoice   → no native watermark; AudioSeal applied post-hoc + verified.
- qwen3tts    → idem (M7).

AudioSeal generator/detector are loaded lazily and kept as singletons because
they're small (~50 MB) and re-used across every job. PerTh detector likewise.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import gcd
from typing import Any

import numpy as np
from scipy.signal import resample_poly

# AudioSeal operates internally at 16 kHz.
AUDIOSEAL_SR = 16000


@dataclass(frozen=True)
class WatermarkResult:
    scheme: str
    detected: bool
    confidence: float | None = None


_perth: Any = None
_audioseal_gen: Any = None
_audioseal_det: Any = None
_torch: Any = None


def _resample(samples: np.ndarray, src_sr: int, dst_sr: int) -> np.ndarray:
    if src_sr == dst_sr:
        return samples
    g = gcd(src_sr, dst_sr)
    return resample_poly(samples, dst_sr // g, src_sr // g).astype(np.float32)


def _get_perth() -> Any:
    global _perth
    if _perth is None:
        import perth
        _perth = perth.PerthImplicitWatermarker()
    return _perth


def _get_audioseal() -> tuple[Any, Any, Any]:
    global _audioseal_gen, _audioseal_det, _torch
    if _audioseal_gen is None:
        import torch as _t
        from audioseal import AudioSeal
        _torch = _t
        _audioseal_gen = AudioSeal.load_generator("audioseal_wm_16bits")
        _audioseal_det = AudioSeal.load_detector("audioseal_detector_16bits")
        if _t.cuda.is_available():
            _audioseal_gen = _audioseal_gen.cuda()
            _audioseal_det = _audioseal_det.cuda()
    return _audioseal_gen, _audioseal_det, _torch


# ── verify ────────────────────────────────────────────────────────────────────

def verify_perth(samples: np.ndarray, sample_rate: int) -> WatermarkResult:
    score = float(_get_perth().get_watermark(samples.astype(np.float32),
                                             sample_rate=sample_rate))
    return WatermarkResult(scheme="perth", detected=score >= 0.5, confidence=score)


def verify_audioseal(samples: np.ndarray, sample_rate: int) -> WatermarkResult:
    _gen, det, torch = _get_audioseal()
    audio = _resample(samples.astype(np.float32), sample_rate, AUDIOSEAL_SR)
    t = torch.from_numpy(audio).unsqueeze(0).unsqueeze(0)  # [B=1, C=1, T]
    if torch.cuda.is_available():
        t = t.cuda()
    with torch.no_grad():
        result, _msg = det.detect_watermark(t, sample_rate=AUDIOSEAL_SR)
    confidence = float(result)
    return WatermarkResult(scheme="audioseal", detected=confidence >= 0.5,
                           confidence=confidence)


def verify(scheme: str, samples: np.ndarray, sample_rate: int) -> WatermarkResult:
    if scheme == "perth":
        return verify_perth(samples, sample_rate)
    if scheme == "audioseal":
        return verify_audioseal(samples, sample_rate)
    if scheme == "none":
        # Non-watermarked models (e.g. cloud adapters like ElevenLabs). We
        # report this transparently rather than pretend verification passed:
        # detected=False + confidence=0 tells the UI "no watermark to check".
        return WatermarkResult(scheme="none", detected=False, confidence=0.0)
    raise ValueError(f"unsupported watermark scheme: {scheme}")


# ── apply (only for non-watermarked models) ──────────────────────────────────

def apply_audioseal(samples: np.ndarray, sample_rate: int) -> tuple[np.ndarray, int]:
    """Add AudioSeal watermark. Returns (samples_with_wm, AUDIOSEAL_SR).

    We emit at AUDIOSEAL_SR (16 kHz) because the detector runs at 16 kHz too;
    keeping the same rate through verify avoids resample-induced attenuation.
    Final loudness/format normalization downstream may resample to 24 kHz —
    verification was already done at 16 kHz, so any small attenuation after
    the fact only affects re-detectability by external auditors. We accept
    that trade-off in exchange for a uniform 24 kHz output policy.
    """
    gen, _det, torch = _get_audioseal()
    audio = _resample(samples.astype(np.float32), sample_rate, AUDIOSEAL_SR)
    t = torch.from_numpy(audio).unsqueeze(0).unsqueeze(0)
    if torch.cuda.is_available():
        t = t.cuda()
    with torch.no_grad():
        delta = gen.get_watermark(t, sample_rate=AUDIOSEAL_SR)
        wm = (t + delta).squeeze().cpu().numpy().astype(np.float32)
    return wm, AUDIOSEAL_SR


# ── policy: which scheme per model ───────────────────────────────────────────

def scheme_for_model(model: str) -> tuple[str, bool]:
    """Returns (scheme, must_apply). must_apply=False means model embeds it."""
    if model == "chatterbox":
        return "perth", False
    if model in ("omnivoice", "qwen3tts"):
        return "audioseal", True
    if model == "elevenlabs":
        # Cloud adapter — audio leaves the hospital and comes back already
        # generated. We intentionally don't re-watermark it with AudioSeal
        # because the adapter's whole contract is "non-clinical, data-left":
        # quietly applying our WM would imply clinical-grade provenance we
        # can't stand behind for this path. The UI already shows an amber
        # "datos salen del hospital" strip when model==elevenlabs.
        return "none", False
    raise ValueError(f"unknown model: {model}")

"""Loudness normalization and WAV encoding (24 kHz mono 16-bit, -23 LUFS)."""

from __future__ import annotations

import io
from math import gcd

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy.signal import resample_poly

TARGET_SR = 24000
TARGET_LUFS = -23.0


def to_wav_bytes(samples: np.ndarray, sample_rate: int) -> tuple[bytes, int, float]:
    """Resample → mono → -23 LUFS → PCM 16-bit WAV. Returns (bytes, sr, duration_s)."""
    audio = samples.astype(np.float32)
    if audio.ndim == 2:
        audio = audio.mean(axis=1)

    if sample_rate != TARGET_SR:
        g = gcd(sample_rate, TARGET_SR)
        audio = resample_poly(audio, TARGET_SR // g, sample_rate // g).astype(np.float32)

    try:
        meter = pyln.Meter(TARGET_SR)
        loudness = meter.integrated_loudness(audio)
        if np.isfinite(loudness):
            audio = pyln.normalize.loudness(audio, loudness, TARGET_LUFS)
    except Exception:
        pass  # leave unnormalized on degenerate inputs

    audio = np.clip(audio, -1.0, 1.0)

    buf = io.BytesIO()
    sf.write(buf, audio, TARGET_SR, subtype="PCM_16", format="WAV")
    return buf.getvalue(), TARGET_SR, float(len(audio) / TARGET_SR)

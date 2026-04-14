"""Validation + acoustic metrics for uploaded reference audio.

Steps:
1. Decode WAV (PCM 16-bit) via soundfile.
2. Enforce mono / supported sample rate / duration bounds.
3. webrtcvad-based speech detection at 16 kHz (resample if needed) → speech_ratio.
4. SNR estimate = 20 log10(rms_speech / rms_nonspeech).
5. LUFS via pyloudnorm.
"""

from __future__ import annotations

import io
import math
from dataclasses import dataclass

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
import webrtcvad
from scipy.signal import resample_poly

SUPPORTED_SAMPLE_RATES = (16000, 22050, 24000, 44100, 48000)
MIN_DURATION_S = 1.0
MAX_DURATION_S = 60.0
MIN_SNR_DB = 15.0
VAD_FRAME_MS = 30


class AudioValidationError(ValueError):
    """Raised when uploaded audio fails validation."""


@dataclass(frozen=True)
class AudioMetrics:
    duration_s: float
    sample_rate: int
    channels: int
    snr_db: float | None
    lufs: float | None
    speech_ratio: float


def _resample_to_16k(samples: np.ndarray, sr: int) -> np.ndarray:
    if sr == 16000:
        return samples
    g = math.gcd(sr, 16000)
    return resample_poly(samples, 16000 // g, sr // g).astype(np.float32)


def _rms(x: np.ndarray) -> float:
    if x.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(x.astype(np.float64) ** 2)))


def _vad_speech_ratio_and_rms(
    samples_f32: np.ndarray, sr16k: int = 16000, aggressiveness: int = 2
) -> tuple[float, float, float]:
    """Returns (speech_ratio, rms_speech, rms_nonspeech) using webrtcvad."""
    vad = webrtcvad.Vad(aggressiveness)
    frame_len = int(sr16k * VAD_FRAME_MS / 1000)  # 480 samples @ 16 kHz
    pcm16 = (np.clip(samples_f32, -1.0, 1.0) * 32767).astype(np.int16)

    n_frames = len(pcm16) // frame_len
    if n_frames == 0:
        return 0.0, 0.0, 0.0

    speech_frames: list[np.ndarray] = []
    silence_frames: list[np.ndarray] = []
    for i in range(n_frames):
        chunk = pcm16[i * frame_len : (i + 1) * frame_len]
        if vad.is_speech(chunk.tobytes(), sr16k):
            speech_frames.append(chunk)
        else:
            silence_frames.append(chunk)

    speech_ratio = len(speech_frames) / n_frames
    rms_s = _rms(np.concatenate(speech_frames)) if speech_frames else 0.0
    rms_n = _rms(np.concatenate(silence_frames)) if silence_frames else 0.0
    return speech_ratio, rms_s, rms_n


def analyze(raw_bytes: bytes) -> AudioMetrics:
    """Decode + analyze. Raises AudioValidationError on hard failures."""
    try:
        samples, sr = sf.read(io.BytesIO(raw_bytes), dtype="float32", always_2d=True)
    except Exception as e:
        raise AudioValidationError(f"cannot decode audio: {e}") from e

    channels = samples.shape[1]
    if channels > 2:
        raise AudioValidationError(f"unsupported channel count: {channels}")
    mono = samples[:, 0] if channels == 1 else samples.mean(axis=1)

    if sr not in SUPPORTED_SAMPLE_RATES:
        raise AudioValidationError(
            f"unsupported sample rate {sr}; supported: {SUPPORTED_SAMPLE_RATES}"
        )

    duration_s = len(mono) / sr
    if duration_s < MIN_DURATION_S:
        raise AudioValidationError(f"audio too short ({duration_s:.2f}s < {MIN_DURATION_S}s)")
    if duration_s > MAX_DURATION_S:
        raise AudioValidationError(f"audio too long ({duration_s:.2f}s > {MAX_DURATION_S}s)")

    mono16 = _resample_to_16k(mono, sr)
    speech_ratio, rms_s, rms_n = _vad_speech_ratio_and_rms(mono16)

    if rms_s > 0 and rms_n > 0:
        snr_db: float | None = float(20.0 * math.log10(rms_s / rms_n))
    elif rms_s > 0 and rms_n == 0:
        snr_db = 60.0  # no detectable noise — cap at +60 dB so DB column stays bounded
    else:
        snr_db = None

    try:
        meter = pyln.Meter(sr)
        lufs: float | None = float(meter.integrated_loudness(mono))
        if not math.isfinite(lufs):
            lufs = None
    except Exception:
        lufs = None

    return AudioMetrics(
        duration_s=float(duration_s),
        sample_rate=int(sr),
        channels=int(channels),
        snr_db=snr_db,
        lufs=lufs,
        speech_ratio=float(speech_ratio),
    )


def assert_acceptable(m: AudioMetrics) -> None:
    """Apply policy gates after analyze()."""
    if m.snr_db is not None and m.snr_db < MIN_SNR_DB:
        raise AudioValidationError(
            f"SNR too low ({m.snr_db:.1f} dB < {MIN_SNR_DB} dB) — busque un lugar más silencioso"
        )
    if m.speech_ratio < 0.30:
        raise AudioValidationError(
            f"speech_ratio too low ({m.speech_ratio:.2f}) — la grabación apenas contiene voz"
        )

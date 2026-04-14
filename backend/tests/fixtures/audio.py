"""Synthetic WAV generators for tests.

Real VoxPopuli-ES samples are documented as future fixtures (M4) — for unit
testing of upload/validation we only need WAVs with controllable acoustic
properties (duration, SNR, speech-likeness).

`speechlike_wav` modulates a tone with low-frequency envelope so webrtcvad
classifies most frames as speech. `silence_wav` is below the VAD threshold.
"""

from __future__ import annotations

import io

import numpy as np
import soundfile as sf


def _to_wav_bytes(samples: np.ndarray, sample_rate: int) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, samples, sample_rate, subtype="PCM_16", format="WAV")
    return buf.getvalue()


def speechlike_wav(
    *,
    duration_s: float = 4.0,
    sample_rate: int = 16000,
    fundamental_hz: float = 180.0,
    snr_db: float | None = None,
    seed: int = 0,
) -> bytes:
    """Generate a WAV with speech-like content webrtcvad will classify as speech.

    Sum of harmonics with formant-band shaping + a vowel-like envelope, plus
    optional white noise sized to hit a target SNR.
    """
    rng = np.random.default_rng(seed)
    n = int(duration_s * sample_rate)
    t = np.arange(n) / sample_rate

    # Envelope: 4 Hz amplitude modulation simulating syllables (~typical speech rate).
    env = 0.5 + 0.5 * np.sin(2 * np.pi * 4.0 * t)

    # Harmonics — first 8 of the fundamental.
    sig = sum(
        (1.0 / k) * np.sin(2 * np.pi * fundamental_hz * k * t + rng.uniform(0, np.pi))
        for k in range(1, 9)
    )
    sig = (sig * env).astype(np.float32)
    sig /= np.max(np.abs(sig)) + 1e-9
    sig *= 0.6  # headroom

    if snr_db is not None:
        rms_sig = np.sqrt(np.mean(sig**2))
        target_noise_rms = rms_sig / (10 ** (snr_db / 20))
        noise = rng.standard_normal(n).astype(np.float32) * target_noise_rms
        sig = sig + noise
        sig = np.clip(sig, -1.0, 1.0)

    return _to_wav_bytes(sig, sample_rate)


def silence_wav(*, duration_s: float = 4.0, sample_rate: int = 16000) -> bytes:
    samples = np.zeros(int(duration_s * sample_rate), dtype=np.float32)
    return _to_wav_bytes(samples, sample_rate)


def too_short_wav() -> bytes:
    return speechlike_wav(duration_s=0.3)


def stereo_speechlike_wav(duration_s: float = 4.0, sample_rate: int = 16000) -> bytes:
    mono = sf.read(io.BytesIO(speechlike_wav(duration_s=duration_s, sample_rate=sample_rate)))[0]
    stereo = np.column_stack([mono, mono])
    return _to_wav_bytes(stereo, sample_rate)

"""Audio validation unit tests — pure Python, no DB / no MinIO."""

from __future__ import annotations

import pytest

from app.services import audio_validation as av
from tests.fixtures import audio as audio_fx


def test_clean_speechlike_passes() -> None:
    m = av.analyze(audio_fx.speechlike_wav(duration_s=3.0))
    assert m.duration_s == pytest.approx(3.0, abs=0.01)
    assert m.sample_rate == 16000
    assert m.channels == 1
    assert m.speech_ratio > 0.5
    av.assert_acceptable(m)


def test_too_short_rejected() -> None:
    with pytest.raises(av.AudioValidationError, match="too short"):
        av.analyze(audio_fx.too_short_wav())


def test_silence_rejected_by_speech_ratio() -> None:
    m = av.analyze(audio_fx.silence_wav(duration_s=3.0))
    assert m.speech_ratio < 0.30
    with pytest.raises(av.AudioValidationError, match="speech_ratio"):
        av.assert_acceptable(m)


def test_low_snr_rejected() -> None:
    raw = audio_fx.speechlike_wav(duration_s=3.0, snr_db=5.0)
    m = av.analyze(raw)
    if m.snr_db is not None and m.snr_db < av.MIN_SNR_DB:
        with pytest.raises(av.AudioValidationError, match="SNR"):
            av.assert_acceptable(m)


def test_unsupported_sample_rate_rejected() -> None:
    import io

    import numpy as np
    import soundfile as sf

    samples = np.zeros(8000, dtype=np.float32)
    buf = io.BytesIO()
    sf.write(buf, samples, 8000, subtype="PCM_16", format="WAV")
    with pytest.raises(av.AudioValidationError, match="sample rate"):
        av.analyze(buf.getvalue())


def test_stereo_is_downmixed() -> None:
    m = av.analyze(audio_fx.stereo_speechlike_wav(duration_s=3.0))
    assert m.channels == 2
    assert m.speech_ratio > 0.5


def test_garbage_bytes_rejected() -> None:
    with pytest.raises(av.AudioValidationError, match="cannot decode"):
        av.analyze(b"not a wav file at all")

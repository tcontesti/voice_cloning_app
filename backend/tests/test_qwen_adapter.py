"""Qwen3TTSAdapter unit tests using a fake subprocess script.

Real Qwen3 cannot run inside the backend container (no torch, no qwen venv).
We point the adapter at a tiny stand-in script that speaks the same JSON
protocol; this validates lifecycle (load/synth/unload), error handling,
WAV round-trip, and timeout behavior.
"""

from __future__ import annotations

import io
import json
import os
import sys
import textwrap
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from app.workers.adapters.qwen3 import Qwen3TTSAdapter

FAKE_SCRIPT = textwrap.dedent('''
    """Fake qwen subprocess worker — same protocol, no model."""
    import json, sys, time
    from pathlib import Path
    from uuid import uuid4

    import numpy as np
    import soundfile as sf

    sys.stdout.write(json.dumps({"ok": True, "ready": True, "model": "fake"}) + "\\n")
    sys.stdout.flush()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        cmd = json.loads(line)
        action = cmd.get("action")
        if action == "ping":
            sys.stdout.write(json.dumps({"ok": True, "pong": True}) + "\\n")
        elif action == "shutdown":
            sys.stdout.write(json.dumps({"ok": True, "bye": True}) + "\\n")
            sys.stdout.flush()
            break
        elif action == "synth":
            text = cmd["text"]
            ref_path = cmd["ref_path"]
            if not Path(ref_path).exists():
                sys.stdout.write(json.dumps({"ok": False, "error": "ref missing"}) + "\\n")
                sys.stdout.flush()
                continue
            sr = 24000
            seconds = max(0.5, min(3.0, len(text) * 0.05))
            samples = (0.3 * np.sin(2 * np.pi * 220 * np.arange(int(sr * seconds)) / sr)).astype(np.float32)
            out = Path(f"/tmp/vcqwen-fake-{uuid4().hex}.wav")
            sf.write(str(out), samples, sr, subtype="FLOAT", format="WAV")
            sys.stdout.write(json.dumps({
                "ok": True, "wav_path": str(out), "sample_rate": sr, "gen_time_s": 0.05,
            }) + "\\n")
        else:
            sys.stdout.write(json.dumps({"ok": False, "error": f"unknown {action}"}) + "\\n")
        sys.stdout.flush()
''')


@pytest.fixture
def fake_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    script = tmp_path / "fake_qwen.py"
    script.write_text(FAKE_SCRIPT)
    monkeypatch.setenv("VC_QWEN_PYTHON", sys.executable)
    monkeypatch.setenv("VC_QWEN_WORKER_SCRIPT", str(script))
    return script


@pytest.fixture
def ref_wav(tmp_path: Path) -> Path:
    p = tmp_path / "ref.wav"
    sr = 16000
    samples = (0.3 * np.sin(2 * np.pi * 200 * np.arange(sr) / sr)).astype(np.float32)
    sf.write(str(p), samples, sr, subtype="FLOAT", format="WAV")
    return p


def test_load_starts_subprocess_and_emits_ready(fake_env: Path) -> None:
    a = Qwen3TTSAdapter()
    a.load()
    assert a.loaded
    a.unload()
    assert not a.loaded


def test_synthesize_round_trips_wav_and_returns_metrics(
    fake_env: Path, ref_wav: Path
) -> None:
    a = Qwen3TTSAdapter()
    try:
        a.load()
        out = a.synthesize(text="Hola, prueba.", reference_wav=ref_wav)
        assert out.sample_rate == 24000
        assert out.samples.dtype == np.float32
        assert out.samples.size > 0
        assert out.gen_time_s >= 0
    finally:
        a.unload()


def test_synthesize_propagates_subprocess_error(
    fake_env: Path, tmp_path: Path
) -> None:
    a = Qwen3TTSAdapter()
    try:
        a.load()
        with pytest.raises(RuntimeError, match="ref missing"):
            a.synthesize(text="hi", reference_wav=tmp_path / "does-not-exist.wav")
    finally:
        a.unload()


def test_unload_is_idempotent(fake_env: Path) -> None:
    a = Qwen3TTSAdapter()
    a.unload()  # before load — no-op
    a.load()
    a.unload()
    a.unload()  # after — no-op


def test_load_raises_when_subprocess_dies_immediately(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bad = tmp_path / "bad.py"
    bad.write_text("import sys; sys.exit(7)")
    monkeypatch.setenv("VC_QWEN_PYTHON", sys.executable)
    monkeypatch.setenv("VC_QWEN_WORKER_SCRIPT", str(bad))
    a = Qwen3TTSAdapter()
    with pytest.raises(RuntimeError, match="EOF"):
        a.load()

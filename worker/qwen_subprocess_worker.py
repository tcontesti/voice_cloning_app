#!/usr/bin/env python
"""Long-lived Qwen3-TTS subprocess worker.

Runs in `~/voice_cloning_qwen_env/.venv` (transformers<5). Communicates with
the parent Celery worker (in the main venv) via line-delimited JSON over
stdin/stdout.

Protocol:
    parent → child  (one JSON object per line):
        {"action": "synth", "text": "...", "ref_path": "...", "options": {...}}
        {"action": "ping"}
        {"action": "shutdown"}

    child → parent  (one JSON object per line):
        {"ok": true,  "wav_path": "/tmp/...", "sample_rate": 24000, "gen_time_s": 1.23}
        {"ok": true,  "pong": true}
        {"ok": false, "error": "..."}

The child writes WAV output to `/tmp/vcqwen-<uuid>.wav` (the parent reads,
deletes). Synth happens once per command; the model loads at startup and
stays resident until shutdown / SIGTERM.
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback
from pathlib import Path
from uuid import uuid4

# qwen_tts / transformers prints banners and warnings to stdout (e.g.
# "Warning: flash-attn is not installed ..."), which would corrupt the
# JSON-line protocol. Redirect stdout → stderr during imports and restore
# it only for _emit().
_real_stdout = sys.stdout
sys.stdout = sys.stderr

# Apply Qwen-specific patches (transformers 5 shims) before any qwen import.
_SCRIPTS = os.environ.get("VC_SCRIPTS_DIR", "/home/husll-spark-01/voice_cloning/scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)
import _patches_qwen  # noqa: F401, E402

import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402
import torch  # noqa: E402
from qwen_tts import Qwen3TTSModel  # noqa: E402

# Keep stdout pointed at stderr by default; only _emit() writes to the real
# stdout pipe. This insulates the JSON protocol from every print() inside
# qwen_tts / transformers (banners, progress, deprecation warnings, etc.).
sys.stdout = sys.stderr

MODEL_ID = os.environ.get("VC_QWEN_MODEL", "Qwen/Qwen3-TTS-12Hz-0.6B-Base")
TMPDIR = Path(os.environ.get("VC_TMPDIR", "/tmp"))


def _emit(obj: dict) -> None:
    _real_stdout.write(json.dumps(obj, separators=(",", ":")) + "\n")
    _real_stdout.flush()


def _load_model() -> Qwen3TTSModel:
    m = Qwen3TTSModel.from_pretrained(MODEL_ID, torch_dtype=torch.float32)
    if torch.cuda.is_available():
        try:
            m.model.to("cuda")
            m.device = torch.device("cuda")
        except Exception as e:
            sys.stderr.write(f"[qwen-sub] cuda failed: {e}\n")
            sys.stderr.flush()
    return m


def _synth(model: Qwen3TTSModel, payload: dict) -> dict:
    text = payload["text"]
    ref_path = payload["ref_path"]
    opts = payload.get("options") or {}
    t0 = time.perf_counter()
    wavs, sr = model.generate_voice_clone(
        text=text,
        language=opts.get("language", "spanish"),
        ref_audio=ref_path,
        x_vector_only_mode=True,
        non_streaming_mode=True,
    )
    elapsed = time.perf_counter() - t0
    wav = wavs[0] if isinstance(wavs, (list, tuple)) else wavs
    arr = np.asarray(wav, dtype=np.float32).reshape(-1)
    sample_rate = int(sr) if isinstance(sr, int) else 24000
    out_path = TMPDIR / f"vcqwen-{uuid4().hex}.wav"
    sf.write(str(out_path), arr, sample_rate, subtype="FLOAT", format="WAV")
    return {
        "ok": True,
        "wav_path": str(out_path),
        "sample_rate": sample_rate,
        "gen_time_s": elapsed,
    }


def main() -> int:
    try:
        model = _load_model()
    except Exception as e:
        _emit({"ok": False, "error": f"load failed: {e}", "trace": traceback.format_exc()})
        return 2

    _emit({"ok": True, "ready": True, "model": MODEL_ID})

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            cmd = json.loads(line)
        except Exception as e:
            _emit({"ok": False, "error": f"bad json: {e}"})
            continue

        action = cmd.get("action")
        try:
            if action == "ping":
                _emit({"ok": True, "pong": True})
            elif action == "shutdown":
                _emit({"ok": True, "bye": True})
                return 0
            elif action == "synth":
                _emit(_synth(model, cmd))
            else:
                _emit({"ok": False, "error": f"unknown action: {action}"})
        except Exception as e:
            _emit({"ok": False, "error": str(e), "trace": traceback.format_exc()})

    return 0


if __name__ == "__main__":
    sys.exit(main())

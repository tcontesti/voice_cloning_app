"""Qwen3-TTS adapter via long-lived subprocess.

Why subprocess: Qwen3-TTS requires `transformers<5` (and several other shims
in `_patches_qwen`). The main venv runs `transformers>=5` for chatterbox.
Co-installing them is incompatible — we keep them in separate venvs.

Lifecycle:
- load(): spawn `~/voice_cloning_qwen_env/.venv/bin/python qwen_subprocess_worker.py`
  with PYTHONUNBUFFERED=1, wait for the initial `{"ok": true, "ready": true}` line.
- synthesize(): write one JSON command line to stdin, read one JSON response
  line from stdout, mmap-read the WAV file the child wrote, delete it.
- unload(): send `{"action": "shutdown"}`; if no clean exit in 5 s, SIGTERM,
  then SIGKILL.

Concurrency: Celery prefetch=1 → adapter is single-threaded by construction.
The LRU registry already serializes get()/unload() with a lock.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf

from app.workers.adapters.base import ModelAdapter, SynthesisOutput


def _default_qwen_python() -> str:
    return os.environ.get(
        "VC_QWEN_PYTHON",
        str(Path.home() / "voice_cloning_qwen_env" / ".venv" / "bin" / "python"),
    )


def _default_worker_script() -> str:
    return os.environ.get(
        "VC_QWEN_WORKER_SCRIPT",
        str(Path.home() / "voice_cloning_app" / "worker" / "qwen_subprocess_worker.py"),
    )


class Qwen3TTSAdapter(ModelAdapter):
    name = "qwen3tts"

    READY_TIMEOUT_S = 120.0  # cold load can take ~30 s; allow margin
    CALL_TIMEOUT_S = 600.0
    SHUTDOWN_GRACE_S = 5.0

    def __init__(self) -> None:
        self._proc: subprocess.Popen[str] | None = None
        self._lock = threading.Lock()

    @property
    def loaded(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def load(self) -> None:
        with self._lock:
            if self.loaded:
                return
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            self._proc = subprocess.Popen(
                [_default_qwen_python(), "-u", _default_worker_script()],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
                bufsize=1,
            )
            ready = self._read_line(timeout_s=self.READY_TIMEOUT_S)
            if not ready.get("ready"):
                stderr = self._drain_stderr()
                self._kill()
                raise RuntimeError(f"qwen subprocess failed to load: {ready} stderr={stderr}")

    def unload(self) -> None:
        with self._lock:
            if not self.loaded:
                self._proc = None
                return
            try:
                self._send({"action": "shutdown"})
                self._proc.wait(timeout=self.SHUTDOWN_GRACE_S)
            except Exception:
                self._terminate()
            finally:
                self._proc = None

    def synthesize(
        self, *, text: str, reference_wav: Path, options: dict | None = None
    ) -> SynthesisOutput:
        with self._lock:
            if not self.loaded:
                # released by reaper while we were waiting; reload
                self.load()
            assert self._proc is not None
            self._send({
                "action": "synth",
                "text": text,
                "ref_path": str(reference_wav),
                "options": options or {},
            })
            t0 = time.perf_counter()
            resp = self._read_line(timeout_s=self.CALL_TIMEOUT_S)
            elapsed = time.perf_counter() - t0

            if not resp.get("ok"):
                err = resp.get("error", "unknown")
                raise RuntimeError(f"qwen subprocess synth failed: {err}")

            wav_path = Path(resp["wav_path"])
            try:
                samples, sr = sf.read(str(wav_path), dtype="float32", always_2d=False)
            finally:
                try:
                    wav_path.unlink(missing_ok=True)
                except Exception:
                    pass

            if samples.ndim == 2:
                samples = samples.mean(axis=1)
            return SynthesisOutput(
                samples=np.asarray(samples, dtype=np.float32),
                sample_rate=int(sr if isinstance(sr, int) else resp["sample_rate"]),
                ttfa_ms=float(resp.get("gen_time_s", elapsed)) * 1000.0,
                gen_time_s=float(resp.get("gen_time_s", elapsed)),
            )

    # ── private ────────────────────────────────────────────────────────────

    def _send(self, obj: dict[str, Any]) -> None:
        assert self._proc is not None and self._proc.stdin is not None
        self._proc.stdin.write(json.dumps(obj) + "\n")
        self._proc.stdin.flush()

    def _read_line(self, timeout_s: float) -> dict[str, Any]:
        """Blocking line read with a deadline; raises on timeout/EOF."""
        assert self._proc is not None and self._proc.stdout is not None
        deadline = time.time() + timeout_s
        result: dict[str, Any] = {}
        line_holder: list[str] = []

        def _reader() -> None:
            line = self._proc.stdout.readline() if self._proc and self._proc.stdout else ""
            line_holder.append(line)

        t = threading.Thread(target=_reader, daemon=True)
        t.start()
        t.join(max(0.0, deadline - time.time()))
        if t.is_alive():
            self._kill()
            raise TimeoutError(f"qwen subprocess timeout after {timeout_s}s")
        line = line_holder[0]
        if not line:
            stderr = self._drain_stderr()
            raise RuntimeError(f"qwen subprocess EOF; stderr={stderr}")
        try:
            result = json.loads(line.strip())
        except Exception as e:
            raise RuntimeError(f"qwen subprocess bad json: {e!r} line={line!r}") from e
        return result

    def _drain_stderr(self) -> str:
        if self._proc is None or self._proc.stderr is None:
            return ""
        try:
            return self._proc.stderr.read() or ""
        except Exception:
            return ""

    def _terminate(self) -> None:
        if self._proc is None:
            return
        try:
            self._proc.terminate()
            self._proc.wait(timeout=2)
        except Exception:
            self._kill()

    def _kill(self) -> None:
        if self._proc is None:
            return
        try:
            self._proc.send_signal(signal.SIGKILL)
        except Exception:
            pass
        try:
            self._proc.wait(timeout=2)
        except Exception:
            pass

"""Chatterbox adapter (Resemble, MIT, PerTh nativo).

Reuses the proven import order from `~/voice_cloning/scripts/run_benchmark.py`:
    1) sys.path += scripts/   2) import _patches   3) import chatterbox

The adapter is GPU-bound; load/unload move the model on/off CUDA so the LRU
registry can free VRAM for OmniVoice / Qwen3 in M6/M7.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

from app.workers.adapters.base import ModelAdapter, SynthesisOutput

# Lazy imports — only when load() is called, so the FastAPI container can
# import this module without _patches / torch / chatterbox being installed.
_ChatterboxTTS: Any = None
_torch: Any = None


def _lazy_import() -> None:
    global _ChatterboxTTS, _torch
    if _ChatterboxTTS is not None:
        return
    patches_dir = os.environ.get("VC_SCRIPTS_DIR", "/home/SPARK_USER/voice_cloning/scripts")
    if patches_dir not in sys.path:
        sys.path.insert(0, patches_dir)
    import _patches  # noqa: F401
    import torch as _t
    from chatterbox.tts import ChatterboxTTS as _C
    _torch, _ChatterboxTTS = _t, _C


class ChatterboxAdapter(ModelAdapter):
    name = "chatterbox"

    def __init__(self) -> None:
        self._model: Any = None
        self._device: str = "cuda" if os.environ.get("VC_FORCE_CPU") != "1" else "cpu"

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def load(self) -> None:
        if self._model is not None:
            return
        _lazy_import()
        self._model = _ChatterboxTTS.from_pretrained(device=self._device)

    def unload(self) -> None:
        if self._model is None:
            return
        try:
            self._model = None
            if _torch is not None and self._device == "cuda":
                _torch.cuda.empty_cache()
        except Exception:
            pass

    def synthesize(
        self, *, text: str, reference_wav: Path, options: dict | None = None
    ) -> SynthesisOutput:
        if self._model is None:
            self.load()
        opts = options or {}
        t0 = time.perf_counter()
        wav = self._model.generate(
            text,
            audio_prompt_path=str(reference_wav),
            exaggeration=float(opts.get("exaggeration", 0.5)),
            cfg_weight=float(opts.get("cfg_weight", 0.5)),
        )
        elapsed = time.perf_counter() - t0
        # Chatterbox returns torch tensor [1, N] at 24 kHz
        samples = wav.detach().cpu().numpy().squeeze().astype(np.float32)
        return SynthesisOutput(
            samples=samples,
            sample_rate=int(self._model.sr),
            ttfa_ms=elapsed * 1000.0,
            gen_time_s=elapsed,
        )

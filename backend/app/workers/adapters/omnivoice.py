"""OmniVoice adapter (k2-fsa, Apache-2.0).

Patrón idéntico al ChatterboxAdapter: lazy imports tras `_patches`, load/unload
controlados por el LRU registry. La diferencia clave: OmniVoice no embebe
watermark — el postproc aplicará AudioSeal después.

Cache de voice_clone_prompt por ruta de referencia: si dentro de la misma
sesión del worker el paciente sintetiza varios textos con la misma referencia,
se ahorra el coste del speaker encoding.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

from app.workers.adapters.base import ModelAdapter, SynthesisOutput

_PATCHES_DIR = os.environ.get("VC_SCRIPTS_DIR", "/home/husll-spark-01/voice_cloning/scripts")
if _PATCHES_DIR not in sys.path:
    sys.path.insert(0, _PATCHES_DIR)
import _patches  # noqa: F401, E402

_OmniVoice: Any = None
_torch: Any = None


def _lazy_import() -> None:
    global _OmniVoice, _torch
    if _OmniVoice is not None:
        return
    import torch as _t
    from omnivoice import OmniVoice as _O
    _torch, _OmniVoice = _t, _O


class OmniVoiceAdapter(ModelAdapter):
    name = "omnivoice"

    def __init__(self) -> None:
        self._model: Any = None
        self._device: str = "cuda" if os.environ.get("VC_FORCE_CPU") != "1" else "cpu"
        self._prompt_cache: dict[str, Any] = {}
        self._sr: int = 24000

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def load(self) -> None:
        if self._model is not None:
            return
        _lazy_import()
        m = _OmniVoice.from_pretrained("k2-fsa/OmniVoice")
        if self._device == "cuda":
            m = m.cuda()
        self._model = m

    def unload(self) -> None:
        self._model = None
        self._prompt_cache.clear()
        if _torch is not None and self._device == "cuda":
            try:
                _torch.cuda.empty_cache()
            except Exception:
                pass

    def synthesize(
        self, *, text: str, reference_wav: Path, options: dict | None = None
    ) -> SynthesisOutput:
        if self._model is None:
            self.load()
        opts = options or {}
        ref_key = str(reference_wav)
        if ref_key not in self._prompt_cache:
            self._prompt_cache[ref_key] = self._model.create_voice_clone_prompt(
                ref_audio=ref_key,
                ref_text=opts.get("ref_text"),
            )
        prompt = self._prompt_cache[ref_key]
        t0 = time.perf_counter()
        wavs = self._model.generate(
            text=text,
            language=opts.get("language", "spanish"),
            voice_clone_prompt=prompt,
        )
        elapsed = time.perf_counter() - t0
        w = wavs[0]
        if hasattr(w, "detach"):  # torch.Tensor
            w = w.detach().cpu().numpy().reshape(-1)
        samples = np.asarray(w, dtype=np.float32)
        return SynthesisOutput(
            samples=samples,
            sample_rate=self._sr,
            ttfa_ms=elapsed * 1000.0,
            gen_time_s=elapsed,
        )

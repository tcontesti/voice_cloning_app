"""AASIST anti-spoofing scorer.

Reuses model weights downloaded under
`$VC_AASIST_DIR` (default: `/home/SPARK_USER/voice_cloning/models/aasist/`).
We load lazily and keep a singleton so subsequent calls reuse VRAM.

Output range convention: higher = more "spoof-like" per the upstream model
(softmax probability of the SPOOF class). Threshold is policy.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
from scipy.signal import resample_poly

AASIST_DIR = Path(os.environ.get("VC_AASIST_DIR", "/home/SPARK_USER/voice_cloning/models/aasist"))

_model = None
_torch = None


def _ensure() -> None:
    global _model, _torch
    if _model is not None:
        return
    if str(AASIST_DIR) not in sys.path:
        sys.path.insert(0, str(AASIST_DIR))
    import json

    import torch as _t
    from models.AASIST import Model  # type: ignore[import-not-found]

    cfg_path = AASIST_DIR / "config" / "AASIST.conf"
    weights = AASIST_DIR / "models" / "weights" / "AASIST.pth"
    cfg = json.loads(cfg_path.read_text())
    m = Model(cfg["model_config"])
    state = _t.load(weights, map_location="cpu", weights_only=True)
    m.load_state_dict(state)
    m.eval()
    if _t.cuda.is_available():
        m = m.cuda()
    _torch, _model = _t, m


def score(samples: np.ndarray, sample_rate: int) -> float:
    """Return spoofing probability in [0, 1]."""
    _ensure()
    audio = samples.astype(np.float32)
    if sample_rate != 16000:
        from math import gcd
        g = gcd(sample_rate, 16000)
        audio = resample_poly(audio, 16000 // g, sample_rate // g).astype(np.float32)
    # AASIST expects ~4 s at 16 kHz (64600 samples) — trim or repeat-pad.
    target = 64600
    if audio.size < target:
        audio = np.tile(audio, (target // audio.size) + 1)[:target]
    audio = audio[:target]
    t = _torch.from_numpy(audio).unsqueeze(0)
    if _torch.cuda.is_available():
        t = t.cuda()
    with _torch.no_grad():
        _, out = _model(t)
        prob_spoof = float(_torch.softmax(out, dim=1)[0, 0].cpu())
    return prob_spoof

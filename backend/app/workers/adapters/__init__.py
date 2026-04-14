from __future__ import annotations

from app.workers.adapters.base import ModelAdapter, SynthesisOutput
from app.workers.adapters.chatterbox import ChatterboxAdapter

__all__ = ["ChatterboxAdapter", "ModelAdapter", "SynthesisOutput"]


def get_adapter(model: str) -> ModelAdapter:
    if model == "chatterbox":
        return ChatterboxAdapter()
    raise ValueError(f"unsupported model in M5: {model}")

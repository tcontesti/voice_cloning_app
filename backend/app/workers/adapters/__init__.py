from __future__ import annotations

from app.workers.adapters.base import ModelAdapter, SynthesisOutput
from app.workers.adapters.chatterbox import ChatterboxAdapter
from app.workers.adapters.omnivoice import OmniVoiceAdapter

__all__ = ["ChatterboxAdapter", "ModelAdapter", "OmniVoiceAdapter", "SynthesisOutput"]


def get_adapter(model: str) -> ModelAdapter:
    if model == "chatterbox":
        return ChatterboxAdapter()
    if model == "omnivoice":
        return OmniVoiceAdapter()
    raise ValueError(f"unsupported model: {model}")

from __future__ import annotations

from app.workers.adapters.base import ModelAdapter, SynthesisOutput
from app.workers.adapters.chatterbox import ChatterboxAdapter
from app.workers.adapters.omnivoice import OmniVoiceAdapter
from app.workers.adapters.qwen3 import Qwen3TTSAdapter

__all__ = [
    "ChatterboxAdapter",
    "ModelAdapter",
    "OmniVoiceAdapter",
    "Qwen3TTSAdapter",
    "SynthesisOutput",
]


def get_adapter(model: str) -> ModelAdapter:
    if model == "chatterbox":
        return ChatterboxAdapter()
    if model == "omnivoice":
        return OmniVoiceAdapter()
    if model == "qwen3tts":
        return Qwen3TTSAdapter()
    raise ValueError(f"unsupported model: {model}")

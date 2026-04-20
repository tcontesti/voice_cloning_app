from __future__ import annotations

from app.workers.adapters.base import ModelAdapter, SynthesisOutput
from app.workers.adapters.chatterbox import ChatterboxAdapter
from app.workers.adapters.omnivoice import OmniVoiceAdapter
from app.workers.adapters.qwen3 import Qwen3TTSAdapter
from app.workers.adapters.elevenlabs import ElevenLabsAdapter

__all__ = [
    "ChatterboxAdapter",
    "ElevenLabsAdapter",
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
    if model == "elevenlabs":
        return ElevenLabsAdapter()
    raise ValueError(f"unsupported model: {model}")

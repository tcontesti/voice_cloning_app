from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class SynthesisOutput:
    """Raw model output before post-processing."""
    samples: np.ndarray   # float32, mono, in [-1, 1]
    sample_rate: int
    ttfa_ms: float        # time to first audio (placeholder if non-streaming)
    gen_time_s: float


class ModelAdapter(ABC):
    """Single-model interface. Adapters are stateful (load/unload).

    LRU registry owns instance lifecycle; tasks never instantiate directly.
    """

    name: str

    @abstractmethod
    def load(self) -> None: ...

    @abstractmethod
    def unload(self) -> None: ...

    @property
    @abstractmethod
    def loaded(self) -> bool: ...

    @abstractmethod
    def synthesize(
        self, *, text: str, reference_wav: Path, options: dict | None = None
    ) -> SynthesisOutput: ...

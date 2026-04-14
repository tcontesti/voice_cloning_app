"""Watermark scheme policy is data, not code paths through the worker.

These tests pin the contract: which model gets which scheme, and which models
require post-hoc apply. If somebody adds a new model and forgets to pick a
scheme, this test fails loudly.
"""

import pytest

from app.workers.postproc.watermark import scheme_for_model


def test_chatterbox_uses_perth_no_apply() -> None:
    assert scheme_for_model("chatterbox") == ("perth", False)


def test_omnivoice_uses_audioseal_with_apply() -> None:
    assert scheme_for_model("omnivoice") == ("audioseal", True)


def test_qwen3tts_uses_audioseal_with_apply() -> None:
    assert scheme_for_model("qwen3tts") == ("audioseal", True)


def test_unknown_model_raises() -> None:
    with pytest.raises(ValueError, match="unknown model"):
        scheme_for_model("does-not-exist")

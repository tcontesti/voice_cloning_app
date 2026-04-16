"""Worker-side hygiene tests.

The synthesize task stashes the reference audio on /tmp before calling the
TTS adapter. A prior regression left those files behind (one per job) which
would eventually fill the Spark's disk. These tests lock in the cleanup
contract for both the happy path and the failure path.

We patch everything external (DB session factory, MinIO fetch, adapter,
postproc, audit, emit) so the test runs with no broker, no CUDA, no
network.
"""

from __future__ import annotations

import glob
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import numpy as np
import pytest


def _count_ref_tempfiles() -> int:
    return len(glob.glob("/tmp/vcref-*.wav"))


@pytest.fixture
def patched_world():
    """Patch every boundary the synthesize task reaches so only the
    tempfile lifecycle exercises real I/O."""
    from app.workers import tasks as tasks_mod

    # Sync DB session that yields deterministic ORM-like objects.
    syn_obj = SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        profile_id=uuid4(),
        text="hola",
        options={},
        status=None,
        started_at=None,
        completed_at=None,
        s3_key_output=None,
        duration_s=None,
        rtf=None,
        watermark_scheme=None,
        watermark_verified=None,
        aasist_score=None,
        error=None,
    )
    profile_obj = SimpleNamespace(reference_ids=[uuid4()])
    rec_obj = SimpleNamespace(id=profile_obj.reference_ids[0], s3_key="ref/key.wav")

    fake_session = MagicMock()
    fake_session.get.side_effect = lambda cls, _id: {
        "Synthesis": syn_obj,
        "VoiceProfile": profile_obj,
    }.get(cls.__name__)
    fake_session.scalar.return_value = rec_obj

    SessionFn = MagicMock(return_value=fake_session)

    wm_result = SimpleNamespace(scheme="audioseal", detected=True)
    adapter = MagicMock()
    adapter.synthesize.return_value = SimpleNamespace(
        samples=np.zeros(16000, dtype=np.float32),
        sample_rate=16000,
        gen_time_s=0.1,
    )

    with patch.object(tasks_mod, "_session_factory", return_value=SessionFn), \
         patch.object(tasks_mod, "_fetch_reference_wav", return_value=b"RIFF....WAVE"), \
         patch.object(tasks_mod, "emit"), \
         patch.object(tasks_mod, "_audit_sync"), \
         patch("app.workers.registry.registry.get", return_value=adapter), \
         patch("app.workers.postproc.watermark.scheme_for_model",
               return_value=("audioseal", False)), \
         patch("app.workers.postproc.watermark.verify", return_value=wm_result), \
         patch("app.workers.postproc.aasist.score", return_value=0.9), \
         patch("app.workers.postproc.normalize.to_wav_bytes",
               return_value=(b"wav", 22050, 1.0)), \
         patch("app.services.storage.put_object"):
        yield SimpleNamespace(syn=syn_obj, adapter=adapter)


def test_reference_tempfile_is_cleaned_on_success(patched_world, tmp_path):
    from app.workers.tasks import synthesize

    before = _count_ref_tempfiles()
    synthesize.run(synthesis_id=str(patched_world.syn.id), model="chatterbox")
    after = _count_ref_tempfiles()

    assert after == before, (
        f"tempfile leaked on success: {before} -> {after} "
        f"(current: {glob.glob('/tmp/vcref-*.wav')})"
    )


def test_reference_tempfile_is_cleaned_on_adapter_failure(patched_world):
    from app.workers.tasks import synthesize

    patched_world.adapter.synthesize.side_effect = RuntimeError("boom")

    before = _count_ref_tempfiles()
    with pytest.raises(RuntimeError):
        synthesize.run(synthesis_id=str(patched_world.syn.id), model="chatterbox")
    after = _count_ref_tempfiles()

    assert after == before, (
        f"tempfile leaked on failure: {before} -> {after} "
        f"(current: {glob.glob('/tmp/vcref-*.wav')})"
    )


def test_tempfile_path_generated_is_unique():
    """Sanity check that the helper doesn't collide across calls — the
    cleanup assertion above relies on that."""
    from app.workers.tasks import _persist_reference_to_disk

    a = _persist_reference_to_disk(b"x")
    b = _persist_reference_to_disk(b"y")
    try:
        assert a != b
        assert Path(a).exists() and Path(b).exists()
    finally:
        Path(a).unlink(missing_ok=True)
        Path(b).unlink(missing_ok=True)

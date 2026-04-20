"""ElevenLabs adapter (cloud, NON-CLINICAL).

HTTP client against the ElevenLabs public API. Unlike the Spark-native adapters
(chatterbox / omnivoice / qwen3tts), this one:

- runs inside the backend container on the PC, not on Spark;
- has no torch / no GPU;
- does not embed a watermark (AudioSeal is skipped too — we leave scheme="none"
  so the audit log and UI expose that fact honestly);
- MUST never process clinical voices. The UI forces a confirmation modal and the
  audit log marks every job with `external_processor="elevenlabs", deployment_safe=false`.

Cloning is cached in Redis keyed by a stable hash over the sorted per-file
sha256 digests so the same set of references doesn't spend the IVC quota twice;
TTL is driven by `settings.elevenlabs_voice_cache_ttl_s` (24 h by default).
"""

from __future__ import annotations

import hashlib
import io
import time
from pathlib import Path
from typing import Any

import httpx
import numpy as np

from app.core.config import get_settings
from app.workers.adapters.base import ModelAdapter, SynthesisOutput

API_BASE = "https://api.elevenlabs.io/v1"

# Redis key that memoizes hash(refs) → voice_id (string).
_CACHE_KEY_PREFIX = "eleven:voice:"

# PCM 24 kHz, 16-bit little-endian mono. Matches the other adapters' rate so
# the rest of the pipeline (loudness norm, AASIST) stays consistent.
OUTPUT_FORMAT = "pcm_24000"
OUTPUT_SR = 24000

# IVC upload limits (ElevenLabs API): 25 files max, 11 MB total payload.
IVC_MAX_TOTAL_BYTES = 11 * 1024 * 1024


class ElevenLabsAPIError(RuntimeError):
    """Non-retryable API error (4xx that isn't 429)."""

    def __init__(self, status: int, body: str) -> None:
        super().__init__(f"elevenlabs API {status}: {body[:300]}")
        self.status = status
        self.body = body


class ElevenLabsAdapter(ModelAdapter):
    """HTTP adapter. `load`/`unload` are no-ops — no resident state."""

    name = "elevenlabs"

    def __init__(self, client: httpx.Client | None = None, redis_client: Any | None = None) -> None:
        self._s = get_settings()
        self._client = client
        self._owns_client = client is None
        self._redis = redis_client
        self._owns_redis = redis_client is None

    # ── ModelAdapter interface ────────────────────────────────────────────────

    @property
    def loaded(self) -> bool:
        return True

    def load(self) -> None:
        return None

    def unload(self) -> None:
        if self._owns_client and self._client is not None:
            self._client.close()
            self._client = None
        if self._owns_redis and self._redis is not None:
            try:
                self._redis.close()
            except Exception:
                pass
            self._redis = None

    def synthesize(
        self, *, text: str, reference_wav: Path, options: dict | None = None
    ) -> SynthesisOutput:
        if not self._s.elevenlabs_api_key:
            raise RuntimeError("ELEVENLABS_API_KEY is empty; set it in .env.multihost")

        opts = options or {}
        # Multi-reference path: `options["reference_wavs"]` is a list of paths
        # that already includes the primary reference. When absent, fall back to
        # the single `reference_wav` from the base interface.
        extra_refs = opts.get("reference_wavs")
        if extra_refs:
            ref_paths = [Path(p) for p in extra_refs]
        else:
            ref_paths = [Path(reference_wav)]

        ref_bytes_list = [p.read_bytes() for p in ref_paths]
        filenames = [p.name or f"ref_{i}.wav" for i, p in enumerate(ref_paths)]
        self._validate_refs(ref_bytes_list)
        voice_id = self._get_or_clone_voice(ref_bytes_list, filenames)

        t0 = time.perf_counter()
        samples = self._tts(voice_id=voice_id, text=text, options=opts)
        elapsed = time.perf_counter() - t0

        return SynthesisOutput(
            samples=samples,
            sample_rate=OUTPUT_SR,
            ttfa_ms=elapsed * 1000.0,  # non-streaming: full response time
            gen_time_s=elapsed,
        )

    # ── HTTP helpers ──────────────────────────────────────────────────────────

    def _http(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                timeout=self._s.elevenlabs_http_timeout_s,
                headers={"xi-api-key": self._s.elevenlabs_api_key},
            )
        return self._client

    def _get_redis(self) -> Any:
        if self._redis is None:
            import redis
            self._redis = redis.Redis(
                host=self._s.redis_host,
                port=self._s.redis_port,
                password=self._s.redis_password or None,
                db=0,
                decode_responses=True,
            )
        return self._redis

    def _request_with_retry(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """Exponential backoff on 429 / 5xx. 4xx (other than 429) fails fast."""
        last_exc: Exception | None = None
        for attempt in range(self._s.elevenlabs_retry_max_attempts):
            try:
                r = self._http().request(method, url, **kwargs)
            except httpx.HTTPError as e:
                last_exc = e
                backoff = 2 ** attempt
                time.sleep(backoff)
                continue
            if r.status_code < 400:
                return r
            if r.status_code == 429 or r.status_code >= 500:
                # retry
                retry_after = r.headers.get("retry-after")
                sleep_s = float(retry_after) if retry_after else 2 ** attempt
                time.sleep(sleep_s)
                last_exc = ElevenLabsAPIError(r.status_code, r.text)
                continue
            # 4xx not in retry bucket
            raise ElevenLabsAPIError(r.status_code, r.text)
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("elevenlabs: retries exhausted with no response")

    # ── voice clone + cache ───────────────────────────────────────────────────

    def _validate_refs(self, ref_bytes_list: list[bytes]) -> None:
        if not ref_bytes_list:
            raise ValueError("elevenlabs: at least one reference is required")
        max_refs = int(self._s.elevenlabs_max_refs)
        if len(ref_bytes_list) > max_refs:
            raise ValueError(
                f"elevenlabs: too many references ({len(ref_bytes_list)} > {max_refs})"
            )
        total = sum(len(b) for b in ref_bytes_list)
        if total > IVC_MAX_TOTAL_BYTES:
            raise ValueError(
                f"elevenlabs: references exceed {IVC_MAX_TOTAL_BYTES // (1024*1024)} MB "
                f"total (got {total} bytes)"
            )

    @staticmethod
    def _cache_key(ref_bytes_list: list[bytes]) -> str:
        # Hash-of-hashes, sorted so reference order doesn't affect the cache key.
        per_file = sorted(hashlib.sha256(b).hexdigest() for b in ref_bytes_list)
        digest = hashlib.sha256("|".join(per_file).encode("ascii")).hexdigest()
        return _CACHE_KEY_PREFIX + digest

    def _get_or_clone_voice(
        self, ref_bytes_list: list[bytes], filenames: list[str]
    ) -> str:
        key = self._cache_key(ref_bytes_list)
        try:
            cached = self._get_redis().get(key)
        except Exception:
            cached = None  # Redis hiccup → fall through to cloning
        if cached:
            return cached if isinstance(cached, str) else cached.decode()

        # Fresh clone (IVC). Plan requirement: Creator tier or above.
        # Multipart upload: repeat the "files" field once per reference.
        files = [
            ("files", (filenames[i] or f"ref_{i}.wav", b, "audio/wav"))
            for i, b in enumerate(ref_bytes_list)
        ]
        data = {"name": f"vcapp-{key[len(_CACHE_KEY_PREFIX):len(_CACHE_KEY_PREFIX)+12]}"}
        r = self._request_with_retry("POST", f"{API_BASE}/voices/add", files=files, data=data)
        voice_id = r.json().get("voice_id")
        if not voice_id:
            raise ElevenLabsAPIError(r.status_code, f"no voice_id in response: {r.text[:200]}")
        try:
            self._get_redis().set(key, voice_id, ex=self._s.elevenlabs_voice_cache_ttl_s)
        except Exception:
            pass
        return voice_id

    # ── TTS ──────────────────────────────────────────────────────────────────

    def _tts(self, *, voice_id: str, text: str, options: dict) -> np.ndarray:
        model_id = str(options.get("model_id") or self._s.elevenlabs_model_id)
        body = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": float(options.get("stability", 0.5)),
                "similarity_boost": float(options.get("similarity_boost", 0.85)),
                "style": float(options.get("style", 0.0)),
                "use_speaker_boost": bool(options.get("use_speaker_boost", True)),
            },
        }
        r = self._request_with_retry(
            "POST",
            f"{API_BASE}/text-to-speech/{voice_id}?output_format={OUTPUT_FORMAT}",
            json=body,
            headers={"accept": "audio/pcm"},
        )
        return _pcm_s16le_to_float32(r.content)


def _pcm_s16le_to_float32(raw: bytes) -> np.ndarray:
    """Decode raw PCM 16-bit LE mono into float32 in [-1, 1]."""
    if len(raw) % 2 != 0:
        raw = raw[: len(raw) - 1]
    a = np.frombuffer(raw, dtype=np.int16)
    return (a.astype(np.float32) / 32768.0).copy()


# mypy placeholder: io is imported so tests can monkeypatch file-like objects
_ = io

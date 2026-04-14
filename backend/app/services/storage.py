"""MinIO object storage with SSE-C.

Per-object data encryption key (DEK) derived from a master KMS key + the
object's S3 key. In dev the master key lives in env (KMS_MOCK_KEY base64).
In prod (M8) the master key is fetched from Vault transit and rotated.

Why per-object derivation: with SSE-C the client must present the same key
to download. By deriving from object-key, we don't have to store the DEK —
recovering the master from KMS is enough to recover all DEKs.
"""

from __future__ import annotations

import base64
import hashlib
import io
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import timedelta

from minio import Minio
from minio.error import S3Error
from minio.sse import SseCustomerKey

from app.core.config import get_settings


_master_key_cache: bytes | None = None


def _master_key_mock() -> bytes:
    raw = base64.b64decode(get_settings().kms_mock_key)
    if len(raw) < 32:
        raise RuntimeError("KMS_MOCK_KEY must decode to >= 32 bytes")
    return raw[:32]


def _master_key_vault() -> bytes:
    """Fetch+cache the master key from Vault KV v2 at secret/data/vcapp/master.

    For transit-only deployments, replace this with `client.secrets.transit.*`.
    Cached for the process lifetime; rotation requires restart (acceptable
    at our scale; M8+ script can trigger SIGHUP to reload).
    """
    import hvac

    s = get_settings()
    if not s.vault_addr or not s.vault_token:
        raise RuntimeError("VAULT_ADDR and VAULT_TOKEN must be set for kms_mode=vault")
    client = hvac.Client(url=s.vault_addr, token=s.vault_token)
    if not client.is_authenticated():
        raise RuntimeError("Vault authentication failed")
    resp = client.secrets.kv.v2.read_secret_version(path="vcapp/master", raise_on_deleted_version=True)
    b64 = resp["data"]["data"].get("key")
    if not b64:
        raise RuntimeError("Vault secret/data/vcapp/master missing 'key' field (base64, >=32 bytes)")
    raw = base64.b64decode(b64)
    if len(raw) < 32:
        raise RuntimeError("Vault master key must decode to >= 32 bytes")
    return raw[:32]


def _master_key() -> bytes:
    global _master_key_cache
    if _master_key_cache is not None:
        return _master_key_cache
    mode = get_settings().kms_mode
    if mode == "mock":
        _master_key_cache = _master_key_mock()
    elif mode == "vault":
        _master_key_cache = _master_key_vault()
    else:
        raise RuntimeError(f"unsupported KMS mode: {mode}")
    return _master_key_cache


def derive_dek(s3_key: str) -> SseCustomerKey:
    """32-byte DEK = HMAC-SHA256(master_key, s3_key)."""
    import hmac

    dek = hmac.new(_master_key(), s3_key.encode("utf-8"), hashlib.sha256).digest()
    return SseCustomerKey(dek)


def _client() -> Minio:
    s = get_settings()
    return Minio(
        f"{s.minio_host}:{s.minio_port}",
        access_key=s.minio_root_user,
        secret_key=s.minio_root_password,
        secure=s.minio_secure,
    )


def _sse_for_put(key: str):
    s = get_settings()
    if s.storage_encryption == "sse-c":
        return derive_dek(key)
    return None


def _sse_for_get(key: str):
    s = get_settings()
    if s.storage_encryption == "sse-c":
        return derive_dek(key)
    return None


def ensure_buckets() -> None:
    s = get_settings()
    c = _client()
    for bucket in (s.minio_bucket_recordings, s.minio_bucket_syntheses):
        if not c.bucket_exists(bucket):
            c.make_bucket(bucket)


def put_object(*, bucket: str, key: str, data: bytes, content_type: str) -> None:
    c = _client()
    c.put_object(
        bucket,
        key,
        io.BytesIO(data),
        length=len(data),
        content_type=content_type,
        sse=_sse_for_put(key),
    )


def get_object(*, bucket: str, key: str) -> bytes:
    c = _client()
    resp = c.get_object(bucket, key, ssec=_sse_for_get(key))
    try:
        return resp.read()
    finally:
        resp.close()
        resp.release_conn()


def remove_object(*, bucket: str, key: str) -> None:
    c = _client()
    try:
        c.remove_object(bucket, key)
    except S3Error:
        pass  # idempotent — soft-delete is the source of truth


def presigned_get_url(*, bucket: str, key: str, expires_minutes: int = 60) -> str:
    """Note: SSE-C objects require the SSE-C headers on GET — the presigned URL
    alone is insufficient. Used for non-SSE-C objects (M5+ public synthesis
    artifacts); for SSE-C reads always go through the API.
    """
    c = _client()
    return c.presigned_get_object(bucket, key, expires=timedelta(minutes=expires_minutes))


@contextmanager
def temporary_bucket(name: str) -> Iterator[str]:
    c = _client()
    if not c.bucket_exists(name):
        c.make_bucket(name)
    try:
        yield name
    finally:
        try:
            objs = list(c.list_objects(name, recursive=True))
            for o in objs:
                c.remove_object(name, o.object_name)
            c.remove_bucket(name)
        except S3Error:
            pass

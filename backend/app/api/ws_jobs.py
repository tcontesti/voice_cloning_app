"""WebSocket: per-job progress stream backed by Redis pub/sub.

Auth: token passed as query param `?token=<jwt>` since browsers can't set
Authorization headers on WebSocket. The token is validated identically to
HTTP requests; on failure we close with policy-violation 1008.
"""

from __future__ import annotations

import json
from uuid import UUID

import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.core.config import get_settings
from app.core.security import decode_token
from app.db.session import AsyncSessionLocal
from app.services import synthesis as syn_svc

log = structlog.get_logger(__name__)

router = APIRouter(tags=["ws"])


# ---------------------------------------------------------------------------
# Shared Redis connection pool.
#
# Before this was a per-connection aioredis.Redis() with contextlib.suppress
# around aclose(). Under a client that reconnects often (or one that crashes
# mid-heartbeat), the pubsub subscription and the underlying connection stayed
# half-open on the server. Redis eventually reaps them but ulimit hits first
# under load. A single app-scoped pool with clean shutdown fixes both: one
# connection per WS, all cleaned up via try/except that actually logs.
# ---------------------------------------------------------------------------
_pool: aioredis.ConnectionPool | None = None


def _get_pool() -> aioredis.ConnectionPool:
    global _pool
    if _pool is None:
        s = get_settings()
        _pool = aioredis.ConnectionPool(
            host=s.redis_host,
            port=s.redis_port,
            password=s.redis_password,
            decode_responses=True,
            max_connections=64,
        )
    return _pool


async def _resolve_user_id(token: str | None) -> UUID | None:
    if not token:
        return None
    try:
        claims = decode_token(token)
        return UUID(claims["sub"])
    except Exception:
        return None


@router.websocket("/ws/jobs/{synthesis_id}")
async def job_progress(
    websocket: WebSocket,
    synthesis_id: UUID,
    token: str | None = Query(default=None),
) -> None:
    user_id = await _resolve_user_id(token)
    if user_id is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Authorization: the synthesis must belong to the caller.
    async with AsyncSessionLocal() as session:
        syn = await syn_svc.get_owned(session, user_id=user_id, synthesis_id=synthesis_id)
        if syn is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        # Send current snapshot first so reconnects don't miss already-emitted state.
        snapshot = {
            "stage": syn.status.value,
            "pct": 100 if syn.status.value in ("succeeded", "failed") else 0,
            "message": "snapshot",
            "payload": {
                "watermark_verified": syn.watermark_verified,
                "aasist_score": syn.aasist_score,
                "s3_key_output": syn.s3_key_output,
            },
        }

    await websocket.accept()
    await websocket.send_text(json.dumps(snapshot))

    r = aioredis.Redis(connection_pool=_get_pool())
    pubsub = r.pubsub()
    channel = f"progress:job:{synthesis_id}"
    await pubsub.subscribe(channel)

    try:
        while True:
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=30.0)
            if msg is None:
                # Heartbeat keeps nginx/reverse proxies from idle-timing us out.
                # If the send fails the client is gone; break so the finally
                # block releases the pubsub subscription.
                try:
                    await websocket.send_text('{"stage":"heartbeat","pct":-1}')
                except Exception:
                    log.debug("ws.heartbeat_send_failed", synthesis_id=str(synthesis_id))
                    break
                continue
            await websocket.send_text(msg["data"])
            try:
                evt = json.loads(msg["data"])
            except Exception:
                evt = None
            if evt and evt.get("stage") in ("done", "failed"):
                break
    except WebSocketDisconnect:
        pass
    finally:
        # Don't swallow cleanup errors silently — they hint at pool/stream
        # leaks that bite under load. Log at warning; the connection is
        # already being torn down either way.
        try:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()
        except Exception:
            log.warning("ws.pubsub_cleanup_failed", synthesis_id=str(synthesis_id), exc_info=True)
        # Release the Redis client back to the pool without closing the pool
        # itself (that's owned at app scope, see _get_pool).
        try:
            await r.aclose()
        except Exception:
            log.warning("ws.redis_client_aclose_failed",
                        synthesis_id=str(synthesis_id), exc_info=True)
        try:
            await websocket.close()
        except Exception:
            pass  # already closed is fine


async def shutdown_pool() -> None:
    """Called from the FastAPI lifespan on shutdown so the pool drains."""
    global _pool
    if _pool is not None:
        try:
            await _pool.aclose()
        except Exception:
            log.warning("ws.pool_shutdown_failed", exc_info=True)
        _pool = None

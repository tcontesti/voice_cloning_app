"""WebSocket: per-job progress stream backed by Redis pub/sub.

Auth: token passed as query param `?token=<jwt>` since browsers can't set
Authorization headers on WebSocket. The token is validated identically to
HTTP requests; on failure we close with policy-violation 1008.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from uuid import UUID

import redis.asyncio as aioredis
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.core.config import get_settings
from app.core.security import decode_token
from app.db.session import AsyncSessionLocal
from app.services import synthesis as syn_svc

router = APIRouter(tags=["ws"])


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

    s = get_settings()
    r = aioredis.Redis(host=s.redis_host, port=s.redis_port, password=s.redis_password,
                       decode_responses=True)
    pubsub = r.pubsub()
    channel = f"progress:job:{synthesis_id}"
    await pubsub.subscribe(channel)

    try:
        while True:
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=30.0)
            if msg is None:
                # heartbeat to keep proxies happy
                with contextlib.suppress(Exception):
                    await websocket.send_text('{"stage":"heartbeat","pct":-1}')
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
        with contextlib.suppress(Exception):
            await pubsub.unsubscribe(channel)
            await pubsub.close()
            await r.aclose()
        with contextlib.suppress(Exception):
            await websocket.close()
        # silence unused warning when asyncio is only imported for typing context
        _ = asyncio

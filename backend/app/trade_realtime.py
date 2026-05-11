from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from fastapi import WebSocket


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass
class _SocketClient:
    websocket: WebSocket
    user_id: str


class TradeRealtimeHub:
    def __init__(self) -> None:
        self._by_session: dict[str, list[_SocketClient]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def connect(self, session_id: str, user_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._by_session[session_id].append(_SocketClient(websocket=websocket, user_id=user_id))

    async def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            clients = self._by_session.get(session_id, [])
            self._by_session[session_id] = [client for client in clients if client.websocket is not websocket]
            if not self._by_session[session_id]:
                self._by_session.pop(session_id, None)

    async def publish(
        self,
        session_id: str,
        event_type: str,
        payload: dict[str, Any],
        target_user_ids: set[str] | None = None,
    ) -> None:
        now = _utc_now()
        event = {
            "eventId": f"ev-{now.timestamp():.6f}",
            "eventType": event_type,
            "sessionId": session_id,
            "sentAt": now.isoformat(),
            "payload": payload,
        }
        message = json.dumps(event, ensure_ascii=False)

        async with self._lock:
            clients = list(self._by_session.get(session_id, []))

        stale: list[WebSocket] = []
        for client in clients:
            if target_user_ids and client.user_id not in target_user_ids:
                continue
            try:
                await client.websocket.send_text(message)
            except Exception:
                stale.append(client.websocket)

        for socket in stale:
            await self.disconnect(session_id, socket)


trade_realtime_hub = TradeRealtimeHub()

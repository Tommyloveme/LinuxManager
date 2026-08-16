from __future__ import annotations

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.adapters.executor import LinuxExecutor
from app.adapters.pty_session import PtySession
from app.core.security import decode_token
from app.db.session import SessionLocal
from app.modules.audit.service import AuditService

router = APIRouter(tags=["terminal"])


@router.websocket("/ws/terminal")
async def terminal_ws(ws: WebSocket) -> None:
    await ws.accept()
    token = ws.query_params.get("token") or ""
    payload = decode_token(token)
    if not payload:
        await ws.send_json({"type": "error", "message": "未登录"})
        await ws.close()
        return

    linux_user = ws.query_params.get("user") or None
    cols = int(ws.query_params.get("cols") or 120)
    rows = int(ws.query_params.get("rows") or 32)
    executor = LinuxExecutor()
    cwd = ws.query_params.get("cwd") or executor.home_for(linux_user)

    session = PtySession(linux_user=linux_user, cwd=cwd, cols=cols, rows=rows)

    def on_data(data: bytes) -> None:
        try:
            import asyncio

            asyncio.create_task(ws.send_bytes(data))
        except Exception:
            pass

    session.on_data = on_data
    try:
        await session.start()
        await ws.send_json({"type": "ready", "cwd": cwd, "user": linux_user or executor.current_user()})
        async with SessionLocal() as db:
            await AuditService(db).record(
                actor=str(payload.get("sub")),
                linux_user=linux_user or "",
                action="terminal.open",
                target=cwd,
            )
        while True:
            message = await ws.receive()
            if message.get("type") == "websocket.disconnect":
                break
            data = message.get("bytes")
            text = message.get("text")
            if data:
                await session.write(data)
            elif text:
                try:
                    obj = json.loads(text)
                except json.JSONDecodeError:
                    await session.write(text.encode("utf-8"))
                    continue
                if obj.get("type") == "resize":
                    session.resize(int(obj.get("cols") or cols), int(obj.get("rows") or rows))
                elif obj.get("type") == "input":
                    await session.write(obj.get("data", "").encode("utf-8"))
    except WebSocketDisconnect:
        pass
    finally:
        await session.close()

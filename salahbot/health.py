"""
Optional HTTP health endpoint.

Fly.io / Render / Northflank sometimes insist on an HTTP health check even for
a worker process.  Discord bots never bind a port, so those checks time out and
the deploy is marked as failed.  This module starts a tiny aiohttp server on
``$PORT`` (if set) that answers 200 OK, which keeps every host happy without
affecting the gateway connection.

If ``PORT`` is not set the module does nothing, so local runs are unaffected.
"""

from __future__ import annotations

import asyncio
import logging
import os

from aiohttp import web

log = logging.getLogger(__name__)

DEFAULT_PORT = 8080


class HealthServer:
    """Tiny HTTP server for platform health checks."""

    def __init__(self, port: int | None = None) -> None:
        self.port = port if port is not None else _port_from_env()
        self._runner: web.AppRunner | None = None

    @property
    def enabled(self) -> bool:
        return self.port is not None

    async def start(self) -> None:
        if not self.enabled:
            log.debug("health server disabled (PORT not set)")
            return
        app = web.Application()
        app.router.add_get("/", self._ok)
        app.router.add_get("/health", self._ok)
        app.router.add_get("/healthz", self._ok)
        app.router.add_route("*", "/{tail:.*}", self._ok)

        self._runner = web.AppRunner(app, access_log=None)
        await self._runner.setup()
        site = web.TCPSite(self._runner, "0.0.0.0", self.port)
        await site.start()
        log.info("health endpoint listening on :%s", self.port)

    async def stop(self) -> None:
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None

    # -- handlers --------------------------------------------------------- #
    async def _ok(self, request: web.Request) -> web.Response:
        return web.json_response(
            {"status": "ok", "service": "salah-bot"},
            headers={"Cache-Control": "no-store"},
        )


def _port_from_env() -> int | None:
    raw = os.environ.get("PORT")
    if not raw:
        return None
    try:
        port = int(raw)
    except ValueError:
        log.warning("PORT=%r is not a number — health server disabled", raw)
        return None
    if not 1 <= port <= 65535:
        log.warning("PORT=%r out of range — health server disabled", raw)
        return None
    return port


def start_background(port: int | None = None) -> HealthServer:
    """Create and start a health server without blocking the caller.

    Returns the instance so the caller can stop it on shutdown.  Never raises:
    a busy port must not crash the bot.
    """
    server = HealthServer(port)

    async def _run() -> None:
        try:
            await server.start()
        except OSError as exc:
            log.warning("health endpoint could not start: %s", exc)

    asyncio.get_running_loop().create_task(_run())
    return server

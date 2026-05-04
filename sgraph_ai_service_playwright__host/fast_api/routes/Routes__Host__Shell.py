# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Routes__Host__Shell
# POST /host/shell/execute  → Schema__Shell__Execute__Response
# WS   /host/shell/stream   → interactive pty (xterm.js client)
#
# /execute is allowlist-gated via Safe_Str__Shell__Command at schema level.
# /stream uses /bin/rbash to prevent path manipulation; it bypasses the
# allowlist because rbash itself is the security boundary.
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                                            import HTTPException, WebSocket, WebSocketDisconnect

from osbot_fast_api.api.routes.Fast_API__Routes                                        import Fast_API__Routes

from sgraph_ai_service_playwright__host.shell.schemas.Schema__Shell__Execute__Request  import Schema__Shell__Execute__Request
from sgraph_ai_service_playwright__host.shell.service.Shell__Executor                  import Shell__Executor

TAG__ROUTES_HOST_SHELL = 'host'


class Routes__Host__Shell(Fast_API__Routes):
    tag : str = TAG__ROUTES_HOST_SHELL

    def execute(self, body: Schema__Shell__Execute__Request) -> dict:               # POST /host/shell/execute
        try:
            return Shell__Executor().execute(body).json()
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
    execute.__route_path__ = '/shell/execute'

    async def shell_stream(self, websocket: WebSocket):                             # WS /host/shell/stream
        await websocket.accept()
        import asyncio
        proc = await asyncio.create_subprocess_shell(
            '/bin/rbash',
            stdin  = asyncio.subprocess.PIPE,
            stdout = asyncio.subprocess.PIPE,
            stderr = asyncio.subprocess.STDOUT,
        )
        async def _reader():
            while True:
                chunk = await proc.stdout.read(1024)
                if not chunk:
                    break
                await websocket.send_bytes(chunk)
        reader_task = asyncio.ensure_future(_reader())
        try:
            while True:
                data = await websocket.receive_bytes()
                if proc.stdin:
                    proc.stdin.write(data)
                    await proc.stdin.drain()
        except WebSocketDisconnect:
            pass
        finally:
            reader_task.cancel()
            proc.kill()
    shell_stream.__route_path__ = '/shell/stream'

    def setup_routes(self):
        self.add_route_post(self.execute)
        self.router.add_api_websocket_route('/shell/stream', self.shell_stream)

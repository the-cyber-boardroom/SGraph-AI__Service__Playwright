# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Shell__Executor
# Executes allowlist-gated shell commands via subprocess.
# The command is already validated by Safe_Str__Shell__Command at schema
# construction; Shell__Executor enforces the timeout cap and captures output.
# ═══════════════════════════════════════════════════════════════════════════════

import subprocess
import time

from osbot_utils.type_safe.Type_Safe                                                        import Type_Safe

from sgraph_ai_service_playwright__host.shell.schemas.Schema__Shell__Execute__Request       import Schema__Shell__Execute__Request
from sgraph_ai_service_playwright__host.shell.schemas.Schema__Shell__Execute__Response      import Schema__Shell__Execute__Response

MAX_TIMEOUT_SECONDS = 120


class Shell__Executor(Type_Safe):

    def execute(self, request: Schema__Shell__Execute__Request) -> Schema__Shell__Execute__Response:
        command = str(request.command)
        if not command:
            raise ValueError('shell command must not be empty')
        timeout     = min(request.timeout or 30, MAX_TIMEOUT_SECONDS)
        working_dir = request.working_dir or None
        start       = time.monotonic()
        timed_out   = False
        try:
            result = subprocess.run(
                command,
                shell       = True,
                capture_output = True,
                text        = True,
                timeout     = timeout,
                cwd         = working_dir,
            )
            stdout    = result.stdout
            stderr    = result.stderr
            exit_code = result.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            stdout    = ''
            stderr    = f'command timed out after {timeout}s'
            exit_code = -1
        duration = time.monotonic() - start
        return Schema__Shell__Execute__Response(
            stdout    = stdout,
            stderr    = stderr,
            exit_code = exit_code,
            duration  = round(duration, 3),
            timed_out = timed_out,
        )

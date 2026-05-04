# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Routes__Host__Logs
# GET /host/logs/boot  → Schema__Host__Boot__Log
#
# Reads the tail of /var/log/cloud-init-output.log so the UI can display
# EC2 provisioning progress for a newly-launched node.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import subprocess

from osbot_fast_api.api.routes.Fast_API__Routes                             import Fast_API__Routes

from sg_compute.host_plane.host.schemas.Schema__Host__Boot__Log             import Schema__Host__Boot__Log

TAG__ROUTES_HOST_LOGS = 'host'

BOOT_LOG_SOURCES = [
    '/var/log/cloud-init-output.log',
    '/var/log/cloud-init.log',
]
MAX_BOOT_LOG_LINES = 2000


class Routes__Host__Logs(Fast_API__Routes):
    tag : str = TAG__ROUTES_HOST_LOGS

    def boot_log(self, lines: int = 200) -> dict:                           # GET /host/logs/boot
        lines = min(max(1, lines), MAX_BOOT_LOG_LINES)
        for source in BOOT_LOG_SOURCES:
            if not os.path.exists(source):
                continue
            wc_result  = subprocess.run(['wc', '-l', source], capture_output=True, text=True)
            total_lines = int(wc_result.stdout.split()[0]) if wc_result.returncode == 0 else 0
            tail_result = subprocess.run(['tail', '-n', str(lines), source],
                                         capture_output=True, text=True)
            content      = tail_result.stdout
            actual_lines = len(content.strip().splitlines()) if content.strip() else 0
            return Schema__Host__Boot__Log(
                source    = source,
                lines     = actual_lines,
                content   = content,
                truncated = total_lines > lines,
            ).json()
        return Schema__Host__Boot__Log(
            source    = '',
            lines     = 0,
            content   = 'cloud-init log not found',
            truncated = False,
        ).json()
    boot_log.__route_path__ = '/logs/boot'

    def setup_routes(self):
        self.add_route_get(self.boot_log)

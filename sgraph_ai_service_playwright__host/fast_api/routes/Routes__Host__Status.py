# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Routes__Host__Status
# GET /host/status  → Schema__Host__Status  (CPU, mem, disk, net)
# GET /host/runtime → Schema__Host__Runtime (docker|podman, version)
# Uses psutil for system metrics; falls back to zeros when unavailable.
# ═══════════════════════════════════════════════════════════════════════════════

import subprocess

from osbot_fast_api.api.routes.Fast_API__Routes                                         import Fast_API__Routes

from sgraph_ai_service_playwright__host.containers.service.Container__Runtime__Factory  import get_container_runtime
from sgraph_ai_service_playwright__host.host.schemas.Schema__Host__Runtime               import Schema__Host__Runtime
from sgraph_ai_service_playwright__host.host.schemas.Schema__Host__Status                import Schema__Host__Status

TAG__ROUTES_HOST_STATUS = 'host'


class Routes__Host__Status(Fast_API__Routes):
    tag : str = TAG__ROUTES_HOST_STATUS

    def status(self) -> dict:                                                       # GET /host/status
        try:
            import psutil
            cpu     = psutil.cpu_percent(interval=0.1)
            mem     = psutil.virtual_memory()
            disk    = psutil.disk_usage('/')
            uptime  = int(psutil.boot_time())
            import time
            uptime_sec = int(time.time() - psutil.boot_time())
        except ImportError:
            cpu = 0.0; mem = type('m', (), {'total': 0, 'used': 0})(); disk = type('d', (), {'total': 0, 'used': 0})(); uptime_sec = 0
        try:
            count = get_container_runtime().list().count
        except Exception:
            count = 0
        return Schema__Host__Status(
            cpu_percent     = cpu,
            mem_total_mb    = getattr(mem,  'total', 0) // (1024 * 1024),
            mem_used_mb     = getattr(mem,  'used',  0) // (1024 * 1024),
            disk_total_gb   = getattr(disk, 'total', 0) // (1024 ** 3),
            disk_used_gb    = getattr(disk, 'used',  0) // (1024 ** 3),
            uptime_seconds  = uptime_sec,
            container_count = count,
        ).json()
    status.__route_path__ = '/status'

    def runtime(self) -> dict:                                                      # GET /host/runtime
        import shutil
        if shutil.which('docker'):
            binary = 'docker'
        elif shutil.which('podman'):
            binary = 'podman'
        else:
            return Schema__Host__Runtime(runtime='none', version='').json()
        try:
            result = subprocess.run([binary, 'version', '--format', '{{.Server.Version}}'],
                                    capture_output=True, text=True, timeout=5)
            version = result.stdout.strip()
        except Exception:
            version = ''
        return Schema__Host__Runtime(runtime=binary, version=version).json()
    runtime.__route_path__ = '/runtime'

    def setup_routes(self):
        self.add_route_get(self.status )
        self.add_route_get(self.runtime)

# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Pod__Runtime__Docker
# Docker CLI adapter — all operations shell out to `docker` binary.
# No docker-py SDK: keeps the dependency graph minimal and avoids SDK version
# drift between the host package and the Playwright service image.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import subprocess

from sg_compute.host_plane.pods.schemas.Schema__Pod__Info                   import Schema__Pod__Info
from sg_compute.host_plane.pods.schemas.Schema__Pod__List                   import Schema__Pod__List, List__Schema__Pod__Info
from sg_compute.host_plane.pods.schemas.Schema__Pod__Logs__Response         import Schema__Pod__Logs__Response
from sg_compute.host_plane.pods.schemas.Schema__Pod__Start__Request         import Schema__Pod__Start__Request
from sg_compute.host_plane.pods.schemas.Schema__Pod__Start__Response        import Schema__Pod__Start__Response
from sg_compute.host_plane.pods.schemas.Schema__Pod__Stop__Response         import Schema__Pod__Stop__Response
from sg_compute.host_plane.pods.service.Pod__Runtime                        import Pod__Runtime

FORMAT = '{{json .}}'                                                       # --format for docker ps; produces one JSON object per line


class Pod__Runtime__Docker(Pod__Runtime):

    def _run(self, args: list[str], timeout: int = 30) -> tuple[str, str, int]:
        result = subprocess.run(['docker'] + args, capture_output=True, text=True, timeout=timeout)
        return result.stdout, result.stderr, result.returncode

    def list(self) -> Schema__Pod__List:
        stdout, _, _ = self._run(['ps', '--no-trunc', '--format', FORMAT])
        items = List__Schema__Pod__Info()
        for line in stdout.strip().splitlines():
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            items.append(Schema__Pod__Info(
                name       = d.get('Names', '') or '',
                image      = d.get('Image', '')  or '',
                status     = d.get('Status', '') or '',
                state      = d.get('State', '')  or '',
                ports      = {},                            # docker ps --format json omits port detail; populated via inspect
                created_at = d.get('CreatedAt', '') or '',
                type_id    = '',
            ))
        return Schema__Pod__List(pods=items, count=len(items))

    def start(self, req: Schema__Pod__Start__Request) -> Schema__Pod__Start__Response:
        args = ['run', '-d', '--name', req.name]
        for host_port, container_port in (req.ports or {}).items():
            args += ['-p', f'{host_port}:{container_port}']
        for key, val in (req.env or {}).items():
            args += ['-e', f'{key}={val}']
        if req.type_id:
            args += ['--label', f'sp.type_id={req.type_id}']
        args.append(req.image)
        stdout, stderr, rc = self._run(args)
        return Schema__Pod__Start__Response(
            name         = req.name,
            container_id = stdout.strip()[:12],
            started      = rc == 0,
            error        = stderr.strip() if rc != 0 else '',
        )

    def info(self, name: str) -> Schema__Pod__Info | None:
        stdout, _, rc = self._run(['inspect', '--format', '{{json .}}', name])
        if rc != 0 or not stdout.strip():
            return None
        try:
            d = json.loads(stdout.strip())
        except json.JSONDecodeError:
            return None
        if isinstance(d, list):
            if not d:
                return None
            d = d[0]
        cfg    = d.get('Config', {})
        state  = d.get('State', {})
        net    = d.get('NetworkSettings', {})
        return Schema__Pod__Info(
            name       = d.get('Name', '').lstrip('/'),
            image      = cfg.get('Image', ''),
            status     = state.get('Status', ''),
            state      = 'Up' if state.get('Running') else 'Exited',
            ports      = net.get('Ports', {}),
            created_at = d.get('Created', ''),
            type_id    = cfg.get('Labels', {}).get('sp.type_id', ''),
        )

    def logs(self, name: str, tail: int = 100) -> Schema__Pod__Logs__Response:
        stdout, stderr, _ = self._run(['logs', '--tail', str(tail), name])
        return Schema__Pod__Logs__Response(name=name, logs=stdout + stderr, tail=tail)

    def stop(self, name: str) -> Schema__Pod__Stop__Response:
        _, stderr, rc = self._run(['stop', name])
        return Schema__Pod__Stop__Response(name=name, stopped=rc == 0,
                                           error=stderr.strip() if rc != 0 else '')

    def remove(self, name: str) -> Schema__Pod__Stop__Response:
        _, stderr_stop, _   = self._run(['stop', name])
        _, stderr_rm,   rc  = self._run(['rm', name])
        return Schema__Pod__Stop__Response(name=name, stopped=True, removed=rc == 0,
                                           error=stderr_rm.strip() if rc != 0 else '')

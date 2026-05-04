# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Pod__Runtime__Podman
# Podman CLI adapter — mirrors Pod__Runtime__Docker but calls `podman`.
# The `podman ps --format json` output is compatible with docker ps --format json
# for the fields we consume.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import subprocess

from sg_compute.host_plane.pods.schemas.Schema__Pod__Info                   import Schema__Pod__Info
from sg_compute.host_plane.pods.schemas.Schema__Pod__List                   import Schema__Pod__List, List__Schema__Pod__Info
from sg_compute.host_plane.pods.schemas.Schema__Pod__Logs__Response         import Schema__Pod__Logs__Response
from sg_compute.host_plane.pods.schemas.Schema__Pod__Start__Request         import Schema__Pod__Start__Request
from sg_compute.host_plane.pods.schemas.Schema__Pod__Start__Response        import Schema__Pod__Start__Response
from sg_compute.host_plane.pods.schemas.Schema__Pod__Stats                  import Schema__Pod__Stats
from sg_compute.host_plane.pods.schemas.Schema__Pod__Stop__Response         import Schema__Pod__Stop__Response
from sg_compute.host_plane.pods.service.Pod__Runtime                        import Pod__Runtime
from sg_compute.host_plane.pods.service.Pod__Runtime__Docker                import _parse_mb, _parse_percent


class Pod__Runtime__Podman(Pod__Runtime):

    def _run(self, args: list[str], timeout: int = 30) -> tuple[str, str, int]:
        result = subprocess.run(['podman'] + args, capture_output=True, text=True, timeout=timeout)
        return result.stdout, result.stderr, result.returncode

    def list(self) -> Schema__Pod__List:
        stdout, _, _ = self._run(['ps', '--format', 'json'])
        items = List__Schema__Pod__Info()
        try:
            rows = json.loads(stdout.strip()) if stdout.strip() else []
        except json.JSONDecodeError:
            rows = []
        for d in rows:
            items.append(Schema__Pod__Info(
                name       = (d.get('Names') or [''])[0],
                image      = d.get('Image', '')     or '',
                status     = d.get('Status', '')    or '',
                state      = d.get('State', '')     or '',
                ports      = {},
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
        stdout, _, rc = self._run(['inspect', name])
        if rc != 0 or not stdout.strip():
            return None
        try:
            rows = json.loads(stdout.strip())
        except json.JSONDecodeError:
            return None
        if not rows:
            return None
        d      = rows[0]
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

    def logs(self, name: str, tail: int = 100,
             timestamps: bool = False) -> Schema__Pod__Logs__Response | None:
        args = ['logs', '--tail', str(tail)]
        if timestamps:
            args.append('--timestamps')
        args.append(name)
        stdout, stderr, rc = self._run(args)
        if rc != 0 and not stdout.strip() and not stderr.strip():
            return None
        content       = stdout + stderr
        content_lines = content.strip().splitlines() if content.strip() else []
        actual_lines  = len(content_lines)
        return Schema__Pod__Logs__Response(
            container = name,
            lines     = actual_lines,
            content   = content,
            truncated = actual_lines >= tail,
        )

    def stats(self, name: str) -> Schema__Pod__Stats | None:               # podman stats --format json returns array
        stdout, _, rc = self._run(['stats', '--no-stream', '--format', 'json', name])
        if rc != 0 or not stdout.strip():
            return None
        try:
            rows = json.loads(stdout.strip())
            d    = rows[0] if isinstance(rows, list) and rows else {}
        except (json.JSONDecodeError, IndexError):
            return None
        mem_parts   = d.get('MemUsage', '0B / 0B').split(' / ')
        net_parts   = d.get('NetIO',    '0B / 0B').split(' / ')
        block_parts = d.get('BlockIO',  '0B / 0B').split(' / ')
        return Schema__Pod__Stats(
            container      = name,
            cpu_percent    = _parse_percent(d.get('CPU',     '0%')),
            mem_usage_mb   = _parse_mb(mem_parts[0])   if len(mem_parts)   > 0 else 0.0,
            mem_limit_mb   = _parse_mb(mem_parts[1])   if len(mem_parts)   > 1 else 0.0,
            mem_percent    = _parse_percent(d.get('MemPerc', '0%')),
            net_rx_mb      = _parse_mb(net_parts[0])   if len(net_parts)   > 0 else 0.0,
            net_tx_mb      = _parse_mb(net_parts[1])   if len(net_parts)   > 1 else 0.0,
            block_read_mb  = _parse_mb(block_parts[0]) if len(block_parts) > 0 else 0.0,
            block_write_mb = _parse_mb(block_parts[1]) if len(block_parts) > 1 else 0.0,
            pids           = int(d.get('PIDs', 0) or 0),
        )

    def stop(self, name: str) -> Schema__Pod__Stop__Response:
        _, stderr, rc = self._run(['stop', name])
        return Schema__Pod__Stop__Response(name=name, stopped=rc == 0,
                                           error=stderr.strip() if rc != 0 else '')

    def remove(self, name: str) -> Schema__Pod__Stop__Response:
        _, stderr_stop, _  = self._run(['stop', name])
        _, stderr_rm,   rc = self._run(['rm', name])
        return Schema__Pod__Stop__Response(name=name, stopped=True, removed=rc == 0,
                                           error=stderr_rm.strip() if rc != 0 else '')

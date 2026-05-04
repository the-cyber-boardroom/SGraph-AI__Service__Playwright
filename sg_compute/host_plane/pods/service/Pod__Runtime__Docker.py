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
from sg_compute.host_plane.pods.schemas.Schema__Pod__Stats                  import Schema__Pod__Stats
from sg_compute.host_plane.pods.schemas.Schema__Pod__Stop__Response         import Schema__Pod__Stop__Response
from sg_compute.host_plane.pods.service.Pod__Runtime                        import Pod__Runtime

FORMAT = '{{json .}}'                                                       # --format for docker ps; one JSON object per line


def _parse_percent(s: str) -> float:                                        # "1.40%" → 1.4
    try:
        return round(float(s.strip().rstrip('%')), 1)
    except ValueError:
        return 0.0


def _parse_mb(s: str) -> float:                                             # "48.2MiB" / "1GiB" / "122kB" → float MB
    s = s.strip()
    for suffix, factor in [('GiB', 1024.0), ('GIB', 1024.0),
                            ('GB',  1000.0), ('gB',  1000.0),
                            ('MiB', 1.0),    ('MIB', 1.0),
                            ('MB',  1.0),    ('mB',  1.0),
                            ('kB',  1/1024.0),('KB', 1/1024.0),
                            ('B',   1/(1024.0*1024.0))]:
        if s.endswith(suffix):
            try:
                return round(float(s[:-len(suffix)]) * factor, 1)
            except ValueError:
                return 0.0
    return 0.0


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

    def logs(self, name: str, tail: int = 100,
             timestamps: bool = False) -> Schema__Pod__Logs__Response | None:
        args = ['logs', '--tail', str(tail)]
        if timestamps:
            args.append('--timestamps')
        args.append(name)
        stdout, stderr, rc = self._run(args)
        if rc != 0 and not stdout.strip():
            return None                                                      # container not found (stderr holds docker error, no log content) → 404
        content       = stdout + stderr
        content_lines = content.strip().splitlines() if content.strip() else []
        actual_lines  = len(content_lines)
        return Schema__Pod__Logs__Response(
            container = name,
            lines     = actual_lines,
            content   = content,
            truncated = actual_lines >= tail,                               # if we got exactly `tail` lines, more likely exist
        )

    def stats(self, name: str) -> Schema__Pod__Stats | None:
        stdout, _, rc = self._run(['stats', '--no-stream', '--format', FORMAT, name])
        if rc != 0 or not stdout.strip():
            return None                                                      # container not found → 404
        try:
            d = json.loads(stdout.strip().splitlines()[0])
        except (json.JSONDecodeError, IndexError):
            return None
        mem_parts   = d.get('MemUsage', '0B / 0B').split(' / ')
        net_parts   = d.get('NetIO',    '0B / 0B').split(' / ')
        block_parts = d.get('BlockIO',  '0B / 0B').split(' / ')
        return Schema__Pod__Stats(
            container      = name,
            cpu_percent    = _parse_percent(d.get('CPUPerc',  '0%')),
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
        _, stderr_stop, _   = self._run(['stop', name])
        _, stderr_rm,   rc  = self._run(['rm', name])
        return Schema__Pod__Stop__Response(name=name, stopped=True, removed=rc == 0,
                                           error=stderr_rm.strip() if rc != 0 else '')

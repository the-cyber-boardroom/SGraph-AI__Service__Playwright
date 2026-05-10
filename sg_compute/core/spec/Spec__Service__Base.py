# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Spec__Service__Base
# Optional base class that gives every spec free implementations of:
#   health(region, name, timeout_sec=0, poll_sec=10) → Schema__CLI__Health__Probe
#   exec  (region, name, command, timeout_sec=60, cwd='') → Schema__CLI__Exec__Result
#   connect_target(region, name) → str (instance_id)
# Sub-classes override cli_spec() and the four abstract methods.
# ═══════════════════════════════════════════════════════════════════════════════

import time

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Spec__Service__Base(Type_Safe):

    def cli_spec(self):                                                       # MUST be overridden
        raise NotImplementedError('cli_spec() must be implemented by the subclass')

    # ── abstract — subclass MUST override ─────────────────────────────────────

    def setup(self):
        raise NotImplementedError

    def create_stack(self, request):
        raise NotImplementedError

    def list_stacks(self, region):
        raise NotImplementedError

    def get_stack_info(self, region, name):
        raise NotImplementedError

    def delete_stack(self, region, name):
        raise NotImplementedError

    # ── default implementations ───────────────────────────────────────────────

    def health(self, region: str, name: str, timeout_sec: int = 0, poll_sec: int = 10):
        from sg_compute.cli.base.schemas.Schema__CLI__Health__Probe import Schema__CLI__Health__Probe
        t0    = time.monotonic()
        probe = Schema__CLI__Health__Probe()
        try:
            spec = self.cli_spec()
            info = self.get_stack_info(region, name)
            if info is None:
                probe.last_error = f'no stack matched {name!r}'
                probe.elapsed_ms = int((time.monotonic() - t0) * 1000)
                return probe

            public_ip = str(getattr(info, 'public_ip', '') or '')
            if not public_ip:
                probe.state     = 'pending'
                probe.last_error = 'instance has no public IP yet'
                probe.elapsed_ms = int((time.monotonic() - t0) * 1000)
                return probe

            port       = getattr(spec, 'health_port', 80)
            path       = getattr(spec, 'health_path', '/')
            url        = (f'https://{public_ip}:{port}{path}' if port != 443
                          else f'https://{public_ip}{path}')
            deadline   = time.monotonic() + max(timeout_sec, 0)

            import urllib.request, ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode    = ssl.CERT_NONE

            while True:
                try:
                    with urllib.request.urlopen(url, timeout=5, context=ctx) as resp:
                        if resp.status < 500:
                            probe.healthy    = True
                            probe.state      = 'running'
                            break
                except Exception as exc:
                    probe.last_error = str(exc)[:512]

                if time.monotonic() >= deadline:
                    break
                time.sleep(poll_sec)

        except Exception as exc:
            probe.last_error = str(exc)[:512]

        probe.elapsed_ms = int((time.monotonic() - t0) * 1000)
        return probe

    def exec(self, region: str, name: str, command: str,
             timeout_sec: int = 60, cwd: str = '') -> object:
        from sg_compute.cli.base.schemas.Schema__CLI__Exec__Result  import Schema__CLI__Exec__Result
        from sg_compute.platforms.ec2.helpers.EC2__Instance__Helper import EC2__Instance__Helper
        t0     = time.monotonic()
        result = Schema__CLI__Exec__Result()
        info   = self.get_stack_info(region, name)
        if info is None:
            raise ValueError(f'no stack matched {name!r}')
        instance_id = str(getattr(info, 'instance_id', '') or '')
        helper      = EC2__Instance__Helper()
        output      = helper.run_command(region, instance_id,
                                         f'cd {cwd} && {command}' if cwd else command)
        result.stdout = output
        result.transport   = 'ssm'
        result.duration_ms = int((time.monotonic() - t0) * 1000)
        return result

    def connect_target(self, region: str, name: str) -> str:
        info = self.get_stack_info(region, name)
        if info is None:
            raise ValueError(
                f'no {self.cli_spec().spec_id} stack matched {name!r}')
        return str(getattr(info, 'instance_id', '') or '')

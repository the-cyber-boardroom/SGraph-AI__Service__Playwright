# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — playwright: Playwright__Service
# Orchestrator for the playwright stack. Extends Spec__Service__Base —
# health/exec/connect_target inherited; spec-specific bits below.
#
# Containers on the launched node:
#   default          — host-plane + sg-playwright                (2 containers)
#   --with-mitmproxy — + agent-mitmproxy                         (3 containers)
# ═══════════════════════════════════════════════════════════════════════════════

import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing   import Optional

from sg_compute.core.spec.Spec__Service__Base                   import Spec__Service__Base
from sg_compute.platforms.ec2.networking.Caller__IP__Detector   import Caller__IP__Detector
from sg_compute.platforms.ec2.networking.Stack__Name__Generator import Stack__Name__Generator

from sg_compute_specs.playwright.schemas.Schema__Playwright__Create__Request  import Schema__Playwright__Create__Request
from sg_compute_specs.playwright.schemas.Schema__Playwright__Create__Response import Schema__Playwright__Create__Response
from sg_compute_specs.playwright.schemas.Schema__Playwright__Delete__Response import Schema__Playwright__Delete__Response
from sg_compute_specs.playwright.schemas.Schema__Playwright__List             import Schema__Playwright__List
from sg_compute_specs.playwright.service.Playwright__AMI__Helper              import Playwright__AMI__Helper
from sg_compute_specs.playwright.service.Playwright__AWS__Client              import Playwright__AWS__Client, ecr_registry_host
from sg_compute_specs.playwright.service.Playwright__Stack__Mapper            import (Playwright__Stack__Mapper,
                                                                                       STACK_TYPE               ,
                                                                                       TAG_API_KEY              ,
                                                                                       TAG_TERMINATE_AT         ,
                                                                                       TAG_WITH_MITMPROXY       )
from sg_compute_specs.playwright.service.Playwright__User_Data__Builder       import Playwright__User_Data__Builder

DEFAULT_REGION        = os.environ.get('AWS_DEFAULT_REGION', 'eu-west-2')
DEFAULT_INSTANCE_TYPE = 't3.medium'
PROFILE_NAME          = 'playwright-ec2'             # IAM profile granting SSM + ECR access
PLAYWRIGHT_PORT       = 8000                         # sg-playwright FastAPI — the public surface
SIDECAR_ADMIN_PORT    = 8001                         # agent-mitmproxy admin API — published only with --with-mitmproxy


class Playwright__Service(Spec__Service__Base):
    aws_client        : Optional[Playwright__AWS__Client]        = None
    user_data_builder : Optional[Playwright__User_Data__Builder] = None
    mapper            : Optional[Playwright__Stack__Mapper]      = None
    ip_detector       : Optional[Caller__IP__Detector]          = None
    name_gen          : Optional[Stack__Name__Generator]        = None
    ami_helper        : Optional[Playwright__AMI__Helper]        = None

    def setup(self) -> 'Playwright__Service':
        self.aws_client        = Playwright__AWS__Client       ().setup()
        self.user_data_builder = Playwright__User_Data__Builder()
        self.mapper            = Playwright__Stack__Mapper     ()
        self.ip_detector       = Caller__IP__Detector          ()
        self.name_gen          = Stack__Name__Generator        ()
        self.ami_helper        = Playwright__AMI__Helper       ()
        return self

    def cli_spec(self):
        from sg_compute.cli.base.Schema__Spec__CLI__Spec import Schema__Spec__CLI__Spec
        return Schema__Spec__CLI__Spec(
            spec_id               = 'playwright'                               ,
            display_name          = 'Playwright'                               ,
            default_instance_type = DEFAULT_INSTANCE_TYPE                      ,
            create_request_cls    = Schema__Playwright__Create__Request         ,
            service_factory       = lambda: Playwright__Service().setup()      ,
            health_path           = '/health/status'                           ,
            health_port           = PLAYWRIGHT_PORT                            ,
            health_scheme         = 'http'                                     ,
        )

    def create_stack(self, request : Schema__Playwright__Create__Request,
                           creator : str = '') -> Schema__Playwright__Create__Response:
        t0           = time.monotonic()
        stack_name   = str(request.stack_name)    or self.name_gen.generate()
        region       = str(request.region)        or DEFAULT_REGION
        caller_ip    = str(request.caller_ip)     or self.ip_detector.detect()
        if not caller_ip:
            raise ValueError(
                'Could not detect your public IP automatically.\n'
                '  Pass it explicitly: sg playwright create --caller-ip <your-ip>')
        ami_id       = str(request.from_ami)      or self.ami_helper.resolve(region)
        itype        = str(request.instance_type) or DEFAULT_INSTANCE_TYPE
        api_key      = str(request.api_key)       or secrets.token_urlsafe(24)
        ecr_registry = ecr_registry_host(region)

        # sg-playwright (:8000) is always published; agent-mitmproxy's admin API
        # (:8001) only when --with-mitmproxy. host-plane stays internal.
        inbound_ports = [PLAYWRIGHT_PORT]
        if bool(request.with_mitmproxy):
            inbound_ports.append(SIDECAR_ADMIN_PORT)
        sg_id = self.aws_client.sg.ensure_security_group(
            region, stack_name, caller_ip,
            inbound_ports=inbound_ports,
            extra_cidrs={})

        extra = {TAG_WITH_MITMPROXY: 'true' if request.with_mitmproxy else 'false',
                 TAG_API_KEY       : api_key                                       }   # surfaced by `sg playwright info`; visible via ec2:DescribeInstances (same trade-off as vault-app's AccessToken)
        if float(request.max_hours) > 0:
            terminate_at = datetime.now(timezone.utc) + timedelta(hours=float(request.max_hours))
            extra[TAG_TERMINATE_AT] = terminate_at.strftime('%Y-%m-%dT%H:%M:%SZ')
        tags = self.aws_client.tags.build(stack_name, caller_ip, creator, extra_tags=extra)

        user_data = self.user_data_builder.render(
            stack_name       = stack_name                    ,
            region           = region                        ,
            ecr_registry     = ecr_registry                  ,
            api_key          = api_key                        ,
            with_mitmproxy   = bool(request.with_mitmproxy)   ,
            intercept_script = str(request.intercept_script)  ,
            image_tag        = str(request.image_tag) or 'latest' ,
            max_hours        = float(request.max_hours)       )
        iid = self.aws_client.launch.run_instance(
            region                = region                   ,
            ami_id                = ami_id                   ,
            sg_id                 = sg_id                    ,
            user_data             = user_data                ,
            tags                  = tags                     ,
            instance_type         = itype                    ,
            max_hours             = int(request.max_hours)    ,
            instance_profile_name = PROFILE_NAME              ,
            disk_size_gb          = int(request.disk_size_gb) ,
            use_spot              = bool(request.use_spot)    )
        info = self.mapper.to_info({'InstanceId'    : iid                  ,
                                    'InstanceType'  : itype                ,
                                    'ImageId'       : ami_id               ,
                                    'State'         : {'Name': 'pending'}  ,
                                    'SecurityGroups': [{'GroupId': sg_id}] ,
                                    'Tags'          : tags                 },
                                   region)
        mode = 'with-mitmproxy (3 containers)' if request.with_mitmproxy else 'default (2 containers)'
        return Schema__Playwright__Create__Response(
            stack_info = info                                       ,
            api_key    = api_key                                    ,
            message    = f'Instance {iid} launching ({mode})'      ,
            elapsed_ms = int((time.monotonic() - t0) * 1000)        )

    def list_stacks(self, region: str = '') -> Schema__Playwright__List:
        region = region or DEFAULT_REGION
        raw    = self.aws_client.instance.list_by_stack_type(region, STACK_TYPE)
        stacks = [self.mapper.to_info(d, region) for d in raw.values()]
        return Schema__Playwright__List(region=region, stacks=stacks, total=len(stacks))

    def get_stack_info(self, region: str, stack_name: str):
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        return self.mapper.to_info(details, region) if details else None

    # ─── health probe — staged-progress override (mirrors Vault_App__Service) ───
    # During `wait` (timeout_sec > 0) the probe polls every poll_sec and prints
    # a timestamped progress line for every state/ip/stage/container change.
    # During `health` (timeout_sec == 0) one poll runs silently.

    def health(self, region: str, name: str, timeout_sec: int = 0, poll_sec: int = 10):
        from sg_compute.cli.base.schemas.Schema__CLI__Health__Probe import Schema__CLI__Health__Probe
        import re, time
        from rich.console import Console

        c        = Console(highlight=False)
        t0       = time.monotonic()
        probe    = Schema__CLI__Health__Probe()
        deadline = time.monotonic() + max(timeout_sec, 0)
        is_wait  = timeout_sec > 0

        # Boot log markers come from Section__Base / the playwright user-data:
        # "[ephemeral-ec2] boot starting…" / "[playwright] installing Docker CE…"
        # / "[playwright] Docker ready" / "[playwright] stack started …" /
        # "[playwright] boot complete …". Strip the source bracket prefix so
        # the rendered stage is plain text (and so rich doesn't swallow the
        # bracket as a markup tag).
        prefix_re = re.compile(r'^\[[^\]]+\]\s*')

        timeline    : list = []      # [(elapsed_s, label)] for the post-wait timings table
        last_sig    : tuple = ()      # (state, ip, stage, containers) — last printed signature
        last_stage  : str  = ''
        last_cont   : str  = ''

        if is_wait:
            c.print(f'\n  [dim]Polling {name} every {poll_sec}s  (timeout {timeout_sec}s) —'
                    f' run [cyan]sg playwright logs[/] for the full boot log[/]\n')

        while True:
            elapsed = int(time.monotonic() - t0)
            try:
                info = self.get_stack_info(region, name)
            except Exception as exc:
                probe.last_error = str(exc)[:512]
                if is_wait:
                    c.print(f'  [dim][t+{elapsed:>3}s][/]  [red]describe-instances failed[/]  [dim]{str(exc)[:80]}[/]')
            else:
                if info is None:
                    probe.state      = 'missing'
                    probe.last_error = f'no stack matched {name!r}'
                    break

                state     = str(getattr(info, 'state', '') or '')
                public_ip = str(getattr(info, 'public_ip', '') or '')
                probe.state = state

                status, err = (0, '')
                if public_ip:
                    status, err = self._probe_endpoint(public_ip)

                # Any HTTP response (incl. 401/403 auth gate) means sg-playwright is up.
                if status and status < 500:
                    probe.healthy    = True
                    probe.state      = 'running'
                    probe.last_error = ''
                    if is_wait:
                        gate = '  [dim](auth-gated — expected)[/]' if status in (401, 403) else ''
                        url  = f'http://{public_ip}:{PLAYWRIGHT_PORT}/health/status'
                        c.print(f'  [dim][t+{elapsed:>3}s][/]  [green]✓ healthy[/]  HTTP {status}  {url}{gate}')
                        timeline.append((elapsed, f'HTTP up — HTTP {status}'))
                    break

                probe.last_error = err or (f'HTTP {status}' if status else 'awaiting boot')
                if is_wait:
                    stage_raw, containers = ('', '')
                    if public_ip:
                        stage_raw, containers = self._probe_progress(region, name)
                    stage_clean = prefix_re.sub('', stage_raw).strip() if stage_raw else ''

                    # Only print when something actually changed — drops the noisy
                    # 5-identical-lines-per-stage repetition.
                    signature = (state, public_ip, stage_clean, containers)
                    if signature != last_sig:
                        if not public_ip:
                            line = f'state=[yellow]{state}[/]  [dim]awaiting public IP…[/]'
                        else:
                            bits = [f'state=[cyan]{state}[/]', f'ip={public_ip}']
                            if stage_clean:
                                bits.append(f'stage=[bold]{stage_clean}[/]')
                            if containers:
                                bits.append(f'containers=[bold]{containers}[/]')
                            if not stage_clean and not containers:
                                bits.append('[dim]waiting on boot…[/]')
                            line = '  '.join(bits)
                        c.print(f'  [dim][t+{elapsed:>3}s][/]  {line}')
                        last_sig = signature

                    if stage_clean and stage_clean != last_stage:
                        timeline.append((elapsed, stage_clean))
                        last_stage = stage_clean
                    if containers and containers != last_cont:
                        timeline.append((elapsed, f'containers: {containers}'))
                        last_cont = containers

            if time.monotonic() >= deadline:
                if is_wait and not probe.healthy:
                    self._print_boot_log_tail(region, name, c)
                break
            time.sleep(poll_sec)

        probe.elapsed_ms = int((time.monotonic() - t0) * 1000)
        if is_wait and timeline:
            self._print_stage_timings(c, timeline)
        return probe

    # ─── health probe helpers ────────────────────────────────────────────────

    def _http_status(self, url: str) -> tuple:
        # (status_code, error_str). 0 = unreachable (connection refused / timeout).
        # A 4xx (incl. 401/403 auth gate) still means the server is up.
        import urllib.error, urllib.request
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                return resp.status, ''
        except urllib.error.HTTPError as exc:
            return exc.code, ''
        except Exception as exc:
            return 0, str(exc)[:200]

    def _probe_endpoint(self, public_ip: str) -> tuple:
        # (status, error). sg-playwright is plain HTTP on PLAYWRIGHT_PORT.
        return self._http_status(f'http://{public_ip}:{PLAYWRIGHT_PORT}/health/status')

    def _probe_progress(self, region: str, name: str) -> tuple:
        # One SSM round-trip → (boot_stage, containers_status).
        # boot_stage    — latest [playwright]/[ephemeral-ec2] line from the boot log
        # containers    — `docker ps` summary for the compose project (e.g. "2 Up")
        try:
            result = self.exec(
                region, name,
                "grep -E '^\\[(playwright|ephemeral-ec2)\\]' "
                "/var/log/ephemeral-ec2-boot.log 2>/dev/null | tail -n 1 || true; "
                "echo '|||CONTAINERS|||'; "
                "docker ps --filter label=com.docker.compose.project=sg-playwright "
                "--format '{{.Names}}={{.Status}}' 2>/dev/null | "
                "awk -F'=' '{n++; if ($2 ~ /^Up/) up++} END "
                "{if (n) printf \"%d/%d Up\", (up?up:0), n; else print \"-\"}' || true",
                timeout_sec=30)
            out = str(getattr(result, 'stdout', '') or '')
            stage_part, _, cont_part = out.partition('|||CONTAINERS|||')
            return stage_part.strip()[:80], cont_part.strip()[:32]
        except Exception:
            return '', ''

    def _print_stage_timings(self, c, timeline: list) -> None:
        from rich.table import Table
        table = Table(box=None, show_header=False, padding=(0, 2))
        table.add_column(style='dim', justify='right', no_wrap=True)
        table.add_column(no_wrap=False)
        prev = 0
        for elapsed_s, label in timeline:
            delta = elapsed_s - prev
            table.add_row(f't+{elapsed_s}s', f'{label}  [dim]+{delta}s[/]')
            prev = elapsed_s
        c.print()
        c.print('  [bold]Stage timings[/]')
        c.print(table)
        c.print()

    def _print_boot_log_tail(self, region: str, name: str, c) -> None:
        try:
            result = self.exec(region, name, 'tail -n 20 /var/log/ephemeral-ec2-boot.log', timeout_sec=8)
            stdout = str(getattr(result, 'stdout', '') or '').strip()
            if stdout:
                c.print(f'\n  [dim]── last 20 lines of boot log (via SSM) ──[/]')
                for line in stdout.splitlines():
                    c.print(f'  [dim]{line}[/]')
                c.print()
        except Exception:
            pass

    def delete_stack(self, region: str, stack_name: str) -> Schema__Playwright__Delete__Response:
        t0      = time.monotonic()
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        if not details:
            return Schema__Playwright__Delete__Response(
                stack_name = stack_name       ,
                message    = 'stack not found',
                elapsed_ms = int((time.monotonic() - t0) * 1000))
        iid   = details.get('InstanceId', '')
        sg_id = (details.get('SecurityGroups') or [{}])[0].get('GroupId', '')
        ok    = self.aws_client.instance.terminate(region, iid)
        if ok and sg_id:
            self.aws_client.sg.delete_security_group(region, sg_id)
        return Schema__Playwright__Delete__Response(
            stack_name = stack_name                                         ,
            deleted    = ok                                                 ,
            message    = f'terminated {iid}' if ok else 'terminate failed' ,
            elapsed_ms = int((time.monotonic() - t0) * 1000)               )

# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-app: Vault_App__Service
# Orchestrator for the vault-app stack. Extends Spec__Service__Base —
# health/exec/connect_target inherited; spec-specific bits below.
#
# Modes (set on the create request):
#   just-vault     (default)  — host-plane + sg-send-vault         (2 containers)
#   with-playwright           — + sg-playwright + agent-mitmproxy  (4 containers)
# ═══════════════════════════════════════════════════════════════════════════════

import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing   import Optional

from sg_compute.core.spec.Spec__Service__Base                   import Spec__Service__Base
from sg_compute.platforms.ec2.networking.Caller__IP__Detector   import Caller__IP__Detector
from sg_compute.platforms.ec2.networking.Stack__Name__Generator import Stack__Name__Generator

from sg_compute_specs.vault_app.schemas.Schema__Vault_App__Create__Request  import Schema__Vault_App__Create__Request
from sg_compute_specs.vault_app.schemas.Schema__Vault_App__Create__Response import Schema__Vault_App__Create__Response
from sg_compute_specs.vault_app.schemas.Schema__Vault_App__Delete__Response import Schema__Vault_App__Delete__Response
from sg_compute_specs.vault_app.schemas.Schema__Vault_App__List             import Schema__Vault_App__List
from sg_compute_specs.vault_app.service.Vault_App__AMI__Helper              import Vault_App__AMI__Helper
from sg_compute_specs.vault_app.service.Vault_App__AWS__Client              import Vault_App__AWS__Client, ecr_registry_host
from sg_compute_specs.vault_app.service.Vault_App__Stack__Mapper            import (Vault_App__Stack__Mapper,
                                                                                    STACK_TYPE              ,
                                                                                    TAG_ACCESS_TOKEN        ,
                                                                                    TAG_ENGINE              ,
                                                                                    TAG_TERMINATE_AT        ,
                                                                                    TAG_TLS_ENABLED         ,
                                                                                    TAG_WITH_PLAYWRIGHT     )
from sg_compute_specs.vault_app.service.Vault_App__User_Data__Builder       import Vault_App__User_Data__Builder

DEFAULT_REGION        = os.environ.get('AWS_DEFAULT_REGION', 'eu-west-2')
DEFAULT_INSTANCE_TYPE = 't3.medium'
PROFILE_NAME          = 'playwright-ec2'             # IAM profile granting SSM + ECR access
VAULT_PORT            = 8080                         # only host port published by the stack


class Vault_App__Service(Spec__Service__Base):
    aws_client        : Optional[Vault_App__AWS__Client]        = None
    user_data_builder : Optional[Vault_App__User_Data__Builder] = None
    mapper            : Optional[Vault_App__Stack__Mapper]      = None
    ip_detector       : Optional[Caller__IP__Detector]          = None
    name_gen          : Optional[Stack__Name__Generator]        = None
    ami_helper        : Optional[Vault_App__AMI__Helper]        = None

    def setup(self) -> 'Vault_App__Service':
        self.aws_client        = Vault_App__AWS__Client       ().setup()
        self.user_data_builder = Vault_App__User_Data__Builder()
        self.mapper            = Vault_App__Stack__Mapper     ()
        self.ip_detector       = Caller__IP__Detector         ()
        self.name_gen          = Stack__Name__Generator       ()
        self.ami_helper        = Vault_App__AMI__Helper       ()
        return self

    def cli_spec(self):
        from sg_compute.cli.base.Schema__Spec__CLI__Spec import Schema__Spec__CLI__Spec
        return Schema__Spec__CLI__Spec(
            spec_id               = 'vault-app'                                 ,
            display_name          = 'Vault App'                                 ,
            default_instance_type = DEFAULT_INSTANCE_TYPE                       ,
            create_request_cls    = Schema__Vault_App__Create__Request           ,
            service_factory       = lambda: Vault_App__Service().setup()        ,
            health_path           = '/info/health'                              ,
            health_port           = VAULT_PORT                                  ,
            health_scheme         = 'http'                                      ,
        )

    def create_stack(self, request : Schema__Vault_App__Create__Request,
                           creator : str = '') -> Schema__Vault_App__Create__Response:
        t0           = time.monotonic()
        stack_name   = str(request.stack_name)    or self.name_gen.generate()
        region       = str(request.region)        or DEFAULT_REGION
        caller_ip    = str(request.caller_ip)     or self.ip_detector.detect()
        if not caller_ip:
            raise ValueError(
                'Could not detect your public IP automatically.\n'
                '  Pass it explicitly: sg vault-app create --caller-ip <your-ip>')
        ami_id       = str(request.from_ami)      or self.ami_helper.resolve(region)
        itype        = str(request.instance_type) or DEFAULT_INSTANCE_TYPE
        engine       = str(request.container_engine) or 'docker'
        access_token = str(request.access_token) or secrets.token_urlsafe(24)
        ecr_registry = ecr_registry_host(region)

        # Only the vault UI port is published — playwright / mitmproxy stay internal.
        # --with-tls-check serves HTTPS on :443; that port (and :80 for the ACME
        # http-01 challenge) must be world-open — Let's Encrypt validates from
        # unpredictable source IPs, and the vault is access-token-gated anyway
        # (architecture doc Q7, resolved: leave :443 world-open).
        extra_cidrs = {}
        if bool(request.with_tls_check):
            extra_cidrs = {443: '0.0.0.0/0', 80: '0.0.0.0/0'}
        sg_id = self.aws_client.sg.ensure_security_group(
            region, stack_name, caller_ip,
            inbound_ports=[VAULT_PORT],
            extra_cidrs=extra_cidrs)

        extra = {
            TAG_WITH_PLAYWRIGHT: 'true' if request.with_playwright else 'false',
            TAG_ENGINE         : engine                                        ,
            TAG_TLS_ENABLED    : 'true' if request.with_tls_check else 'false' ,
            TAG_ACCESS_TOKEN   : access_token                                  ,   # surfaced by `sp vault-app info`; visible via ec2:DescribeInstances
        }
        if float(request.max_hours) > 0:
            terminate_at = datetime.now(timezone.utc) + timedelta(hours=float(request.max_hours))
            extra[TAG_TERMINATE_AT] = terminate_at.strftime('%Y-%m-%dT%H:%M:%SZ')
        tags = self.aws_client.tags.build(stack_name, caller_ip, creator, extra_tags=extra)

        user_data = self.user_data_builder.render(
            stack_name       = stack_name              ,
            region           = region                  ,
            ecr_registry     = ecr_registry            ,
            access_token     = access_token            ,
            with_playwright  = bool(request.with_playwright) ,
            container_engine = engine                   ,
            storage_mode     = str(request.storage_mode) or 'disk' ,
            seed_vault_keys  = str(request.seed_vault_keys)        ,
            max_hours        = float(request.max_hours) ,
            with_tls_check   = bool(request.with_tls_check)        ,
            tls_mode         = str(request.tls_mode) or 'self-signed' ,
            acme_prod        = bool(request.acme_prod)             ,
        )
        iid = self.aws_client.launch.run_instance(
            region                = region              ,
            ami_id                = ami_id              ,
            sg_id                 = sg_id               ,
            user_data             = user_data           ,
            tags                  = tags                ,
            instance_type         = itype               ,
            max_hours             = int(request.max_hours) ,
            instance_profile_name = PROFILE_NAME        ,
            disk_size_gb          = int(request.disk_size_gb) ,
            use_spot              = bool(request.use_spot)    ,
        )
        info = self.mapper.to_info({'InstanceId'   : iid                                     ,
                                    'InstanceType' : itype                                   ,
                                    'ImageId'      : ami_id                                  ,
                                    'State'        : {'Name': 'pending'}                     ,
                                    'SecurityGroups': [{'GroupId': sg_id}]                   ,
                                    'Tags'         : tags                                    },
                                   region)
        return Schema__Vault_App__Create__Response(
            stack_info   = info                                  ,
            access_token = access_token                          ,
            message      = f'Instance {iid} launching ({"with-playwright" if request.with_playwright else "just-vault"}, {engine})',
            elapsed_ms   = int((time.monotonic() - t0) * 1000)   ,
        )

    def list_stacks(self, region: str = '') -> Schema__Vault_App__List:
        region = region or DEFAULT_REGION
        raw    = self.aws_client.instance.list_by_stack_type(region, STACK_TYPE)
        stacks = [self.mapper.to_info(d, region) for d in raw.values()]
        return Schema__Vault_App__List(region=region, stacks=stacks, total=len(stacks))

    def get_stack_info(self, region: str, stack_name: str):
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        return self.mapper.to_info(details, region) if details else None

    def health(self, region: str, name: str, timeout_sec: int = 0, poll_sec: int = 10):
        from sg_compute.cli.base.schemas.Schema__CLI__Health__Probe import Schema__CLI__Health__Probe
        import ssl, time
        from rich.console import Console

        c        = Console(highlight=False)
        t0       = time.monotonic()
        probe    = Schema__CLI__Health__Probe()
        deadline = time.monotonic() + max(timeout_sec, 0)
        ctx      = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode    = ssl.CERT_NONE
        is_wait  = timeout_sec > 0

        if is_wait:
            c.print(f'\n  [dim]Polling {name} every {poll_sec}s  (timeout {timeout_sec}s) —'
                    f' run [cyan]sp vault-app diag[/] for the full boot checklist[/]\n')

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

                if not public_ip:
                    probe.last_error = 'instance has no public IP yet'
                    if is_wait:
                        c.print(f'  [dim][t+{elapsed:>3}s][/]  state=[yellow]{state}[/]  [dim]awaiting public IP…[/]')
                else:
                    # TLS-aware: HTTPS :443 (TLS stack) is tried before HTTP :8080 (plain).
                    status, scheme, err = self._probe_endpoints(public_ip, ctx)
                    # Any HTTP response (incl. 401/403 auth gate) means the vault is up.
                    if status and status < 500:
                        probe.healthy    = True
                        probe.state      = 'running'
                        probe.last_error = ''
                        if scheme == 'https':
                            probe.cert_summary = self._probe_cert(public_ip)
                        if is_wait:
                            gate = '  [dim](auth-gated — expected)[/]' if status in (401, 403) else ''
                            url  = f'https://{public_ip}' if scheme == 'https' else f'http://{public_ip}:{VAULT_PORT}'
                            cert = f'  [dim]{probe.cert_summary}[/]' if probe.cert_summary else ''
                            c.print(f'  [dim][t+{elapsed:>3}s][/]  [green]✓ healthy[/]  HTTP {status}  {url}{gate}{cert}')
                        break
                    probe.last_error = err or f'HTTP {status}'
                    if is_wait:
                        stage, cert_init = self._probe_progress(region, name)
                        bits = []
                        if cert_init:
                            bits.append(f'cert-init=[bold]{cert_init}[/]')
                        if stage:
                            bits.append(f'stage=[bold]{stage}[/]')
                        detail = ('  ' + '  '.join(bits)) if bits else ''
                        c.print(f'  [dim][t+{elapsed:>3}s][/]  state=[cyan]{state}[/]  ip={public_ip}'
                                f'{detail}  [dim]{err or ("HTTP " + str(status))}[/]')

            if time.monotonic() >= deadline:
                if is_wait and not probe.healthy:
                    self._print_boot_log_tail(region, name, c)
                break
            time.sleep(poll_sec)

        probe.elapsed_ms = int((time.monotonic() - t0) * 1000)
        return probe

    def _http_status(self, url: str, ctx) -> tuple:
        # (status_code, error_str). status_code 0 = unreachable (connection refused
        # / timeout). A 4xx — including a 401/403 auth gate — still means the
        # server is up and responding, which is what a readiness probe cares about.
        import urllib.error, urllib.request
        try:
            with urllib.request.urlopen(url, timeout=5, context=ctx) as resp:
                return resp.status, ''
        except urllib.error.HTTPError as exc:
            return exc.code, ''
        except Exception as exc:
            return 0, str(exc)[:200]

    def _probe_endpoints(self, public_ip: str, ctx) -> tuple:
        # (status, scheme, error). Tries HTTPS :443 first — a TLS-enabled stack
        # binds :443 only — then falls back to plain HTTP :8080. scheme is '' when
        # neither responds (status 0).
        https_status, https_err = self._http_status(f'https://{public_ip}/info/health', ctx)
        if https_status:
            return https_status, 'https', https_err
        http_status, http_err = self._http_status(f'http://{public_ip}:{VAULT_PORT}/info/health', ctx)
        if http_status:
            return http_status, 'http', http_err
        return 0, '', https_err or http_err

    def _probe_cert(self, public_ip: str) -> str:
        # One TLS handshake — decode the cert the vault is serving for the wait
        # line: 'self-signed · 159d left' or 'CA-signed · 6d left'.
        try:
            from sg_compute.platforms.tls.Cert__Inspector import Cert__Inspector
            info = Cert__Inspector().inspect_host(public_ip, 443)
            kind = 'self-signed' if info.is_self_signed else 'CA-signed'
            days = int(getattr(info, 'days_remaining', 0) or 0)
            return f'cert: {kind} · {days}d left'
        except Exception:
            return ''

    def _probe_progress(self, region: str, name: str) -> tuple:
        # One SSM round-trip → (boot_stage, cert_init_status). boot_stage is the
        # latest [vault-app]/[ephemeral-ec2] boot-log marker; cert_init_status is
        # the one-shot cert-init container's docker status line. Either is '' when
        # absent or SSM is not reachable yet.
        try:
            result = self.exec(
                region, name,
                "grep -E '^\\[(vault-app|ephemeral-ec2)\\]' "
                "/var/log/ephemeral-ec2-boot.log 2>/dev/null | tail -n 1 || true; "
                "echo '|||CERT|||'; "
                "(docker ps -a --filter name=cert-init --format '{{.Status}}' 2>/dev/null || "
                "podman ps -a --filter name=cert-init --format '{{.Status}}' 2>/dev/null) "
                "| head -n 1 || true",
                timeout_sec=30)
            out = str(getattr(result, 'stdout', '') or '')
            stage_part, _, cert_part = out.partition('|||CERT|||')
            return stage_part.strip()[:80], cert_part.strip()[:48]
        except Exception:
            return '', ''

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

    # ── boot-sequence diagnostic checklist ───────────────────────────────────────
    # Generator protocol: yields (name, 'checking', '') for each active check so
    # the CLI can show a live indicator, then yields the final (name, status,
    # detail). Skipped checks are yielded directly. Mirrors local-claude's
    # diagnose() — vault-app stages: ec2 → ssm → boot-failed → container-engine
    # → images-pulled → containers-up → vault-http → boot-ok.

    def diagnose(self, region: str, name: str):
        _REST = ('ssm-reachable', 'boot-failed', 'container-engine',
                 'images-pulled', 'containers-up', 'vault-http', 'boot-ok')

        # ── check 1: ec2-state ─────────────────────────────────────────────────
        yield ('ec2-state', 'checking', '')
        info = self.get_stack_info(region, name)
        if info is None:
            yield ('ec2-state', 'fail', 'stack not found')
            return
        ec2_state = str(getattr(info, 'state', '') or '')
        ec2_ok    = ec2_state == 'running'
        yield ('ec2-state', 'ok' if ec2_ok else 'fail', ec2_state or '?')
        if not ec2_ok:
            for n in _REST:
                yield (n, 'skip', f'skipped — ec2 is {ec2_state!r}')
            return

        engine = str(getattr(info, 'container_engine', '') or '') or 'docker'

        # ── check 2: ssm-reachable ─────────────────────────────────────────────
        yield ('ssm-reachable', 'checking', '')
        try:
            self.exec(region, name, 'echo ok', timeout_sec=30)
            ssm_ok = True
            yield ('ssm-reachable', 'ok', 'responsive')
        except Exception as exc:
            ssm_ok = False
            yield ('ssm-reachable', 'fail', str(exc)[:120])
        if not ssm_ok:
            for n in _REST[1:]:
                yield (n, 'skip', 'skipped — SSM unreachable')
            return

        def ssm(cmd, timeout=30):                       # SSM SendCommand requires TimeoutSeconds >= 30
            r = self.exec(region, name, cmd, timeout_sec=timeout)
            return str(getattr(r, 'stdout', '') or '').strip()

        # ── check 3: boot-failed ───────────────────────────────────────────────
        yield ('boot-failed', 'checking', '')
        try:
            out = ssm('test -f /var/lib/sg-compute-boot-failed && echo YES || echo NO')
            if 'YES' in out:
                tail = ssm('tail -n 15 /var/log/ephemeral-ec2-boot.log 2>/dev/null || true')
                yield ('boot-failed', 'fail', ('boot script error:\n' + tail) if tail else 'boot script error')
            else:
                yield ('boot-failed', 'ok', 'absent')
        except Exception:
            yield ('boot-failed', 'warn', 'could not check')

        # ── check 4: container-engine ──────────────────────────────────────────
        yield ('container-engine', 'checking', '')
        engine_ok = False
        try:
            unit = 'podman.socket' if engine == 'podman' else 'docker'
            out  = ssm(f'systemctl is-active {unit} 2>&1 || true')
            if out == 'active':
                engine_ok = True
                yield ('container-engine', 'ok', f'{engine} active')
            else:
                yield ('container-engine', 'warn', f'{engine} state={out!r} — boot may still be installing it')
        except Exception:
            yield ('container-engine', 'warn', 'could not check')

        # ── check 5: images-pulled ─────────────────────────────────────────────
        yield ('images-pulled', 'checking', '')
        images_ok = False
        try:
            out        = ssm(f'sudo {engine} images --format "{{{{.Repository}}}}" 2>/dev/null || true')
            have_vault = 'sg-send-vault' in out
            have_host  = 'sgraph_ai_service_playwright_host' in out
            if have_vault and have_host:
                images_ok = True
                yield ('images-pulled', 'ok', 'sg-send-vault + host-plane present')
            elif not engine_ok:
                yield ('images-pulled', 'warn', 'not yet — container engine not ready')
            else:
                missing = [n for n, ok in (('sg-send-vault', have_vault),
                                            ('host-plane', have_host)) if not ok]
                yield ('images-pulled', 'warn', f'pulling… still missing: {", ".join(missing)}')
        except Exception:
            yield ('images-pulled', 'warn', 'could not check')

        # ── check 6: containers-up ─────────────────────────────────────────────
        yield ('containers-up', 'checking', '')
        containers_ok = False
        try:
            out      = ssm(f'sudo {engine} ps --format "{{{{.Names}}}}  {{{{.Status}}}}" 2>/dev/null || true')
            up_lines = [l for l in out.splitlines() if 'Up' in l]
            if len(up_lines) >= 2:
                containers_ok = True
                yield ('containers-up', 'ok', f'{len(up_lines)} running — ' + '; '.join(up_lines)[:160])
            elif not images_ok:
                yield ('containers-up', 'warn', 'not yet — images still pulling')
            else:
                all_ct = ssm(f'sudo {engine} ps -a --format "{{{{.Names}}}}  {{{{.Status}}}}" 2>/dev/null | head -5 || true')
                yield ('containers-up', 'warn', f'not all up — {all_ct or "no containers yet"}')
        except Exception:
            yield ('containers-up', 'warn', 'could not check')

        # ── check 7: vault-http ────────────────────────────────────────────────
        if not containers_ok:
            yield ('vault-http', 'skip', 'skipped — containers not running')
        else:
            yield ('vault-http', 'checking', '')
            try:
                code = ssm('curl -s -o /dev/null -w "%{http_code}" '
                           f'http://127.0.0.1:{VAULT_PORT}/info/health 2>&1 || echo 000', timeout=30)
                code = code.strip()
                if code in ('200', '204'):
                    yield ('vault-http', 'ok', f'HTTP {code}')
                elif code in ('401', '403'):
                    yield ('vault-http', 'ok', f'HTTP {code} — up, auth-gated (expected)')
                elif code and code != '000':
                    yield ('vault-http', 'warn', f'HTTP {code} — up but not ready')
                else:
                    yield ('vault-http', 'warn', 'no response on :8080 — vault still warming up')
            except Exception as exc:
                yield ('vault-http', 'fail', str(exc)[:120])

        # ── check 8: boot-ok ───────────────────────────────────────────────────
        yield ('boot-ok', 'checking', '')
        try:
            out = ssm('test -f /var/lib/sg-compute-boot-ok && echo YES || echo NO')
            if 'YES' in out:
                yield ('boot-ok', 'ok', 'present — boot script completed')
            else:
                stage = ssm("grep -E '^\\[(vault-app|ephemeral-ec2)\\]' "
                            "/var/log/ephemeral-ec2-boot.log 2>/dev/null | tail -n 1 || true")
                yield ('boot-ok', 'warn', f'not yet — current stage: {stage[:160]}' if stage else 'not yet')
        except Exception:
            yield ('boot-ok', 'warn', 'could not check')

    def delete_stack(self, region: str, stack_name: str) -> Schema__Vault_App__Delete__Response:
        t0      = time.monotonic()
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        if not details:
            return Schema__Vault_App__Delete__Response(
                stack_name = stack_name       ,
                message    = 'stack not found',
                elapsed_ms = int((time.monotonic() - t0) * 1000))
        iid   = details.get('InstanceId', '')
        sg_id = (details.get('SecurityGroups') or [{}])[0].get('GroupId', '')
        ok    = self.aws_client.instance.terminate(region, iid)
        if ok and sg_id:
            self.aws_client.sg.delete_security_group(region, sg_id)
        return Schema__Vault_App__Delete__Response(
            stack_name = stack_name                                         ,
            deleted    = ok                                                 ,
            message    = f'terminated {iid}' if ok else 'terminate failed' ,
            elapsed_ms = int((time.monotonic() - t0) * 1000)               ,
        )

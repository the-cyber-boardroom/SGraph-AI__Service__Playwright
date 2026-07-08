# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Content_Proxy__Service
# Tier-1 orchestrator. Launches the content-transformation proxy EC2 stack via the
# SAME shared EC2 foundation `sg va create` uses (Content_Proxy__AWS__Client →
# EC2__* helpers). health/exec/connect inherited from Spec__Service__Base.
# ═══════════════════════════════════════════════════════════════════════════════

import math
import os
import time
import uuid

from typing                                                                         import Optional

from sg_compute.cli.base.Schema__Spec__CLI__Spec                                    import Schema__Spec__CLI__Spec
from sg_compute.cli.base.schemas.Schema__CLI__Health__Probe                         import Schema__CLI__Health__Probe
from sg_compute.core.spec.Spec__Service__Base                                       import Spec__Service__Base
from sg_compute.platforms.ec2.networking.Caller__IP__Detector                       import Caller__IP__Detector
from sg_compute.platforms.ec2.networking.Stack__Name__Generator                     import Stack__Name__Generator

from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Edge                   import Enum__Content_Proxy__Edge
from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Tls                    import Enum__Content_Proxy__Tls
from sg_compute_specs.content_proxy.schemas.Schema__Content_Proxy__Create__Request   import Schema__Content_Proxy__Create__Request
from sg_compute_specs.content_proxy.schemas.Schema__Content_Proxy__Create__Response  import Schema__Content_Proxy__Create__Response
from sg_compute_specs.content_proxy.schemas.Schema__Content_Proxy__Delete__Response  import Schema__Content_Proxy__Delete__Response
from sg_compute_specs.content_proxy.schemas.Schema__Content_Proxy__List              import Schema__Content_Proxy__List
from sg_compute_specs.content_proxy.schemas.Schema__Content_Proxy__Stack__Info       import Schema__Content_Proxy__Stack__Info
from sg_compute_specs.content_proxy.service.Content_Proxy__AWS__Client               import Content_Proxy__AWS__Client, STACK_TYPE
from sg_compute_specs.content_proxy.service.Content_Proxy__Stack__Mapper             import (Content_Proxy__Stack__Mapper, TAG_MODE,
                                                                                            TAG_TLS, TAG_EDGE, TAG_HOSTNAME, TAG_ACCESS,
                                                                                            TAG_FIREFOX)
from sg_compute_specs.content_proxy.service.Content_Proxy__User_Data__Builder        import (Content_Proxy__User_Data__Builder,
                                                                                            LOG_FILE)


DEFAULT_REGION        = 'eu-west-2'
DEFAULT_INSTANCE_TYPE = 't3.large'
PROFILE_NAME          = 'playwright-ec2'                                            # IAM instance profile (SSM + ECR), shared
DEFAULT_AWS_DNS_ZONE  = 'sg-compute.sgraph.ai'                                      # same default as sg va / aws dns — single source via env
BOOT_LOG              = LOG_FILE                                                    # /var/log/sg-content-proxy-boot.log (source of truth: User_Data__Builder)


def _default_aws_dns_zone() -> str:
    return os.environ.get('SG_AWS__DNS__DEFAULT_ZONE', DEFAULT_AWS_DNS_ZONE)


def resolve_proxyauth(user: str, password: str, has_env_file: bool) -> tuple:       # ext (Mode 1) basic-auth: an --env-file ships its own; else default the user to 'demo' and GENERATE a GUID pass so the internet-facing proxy never boots with empty auth (proxyauth=:)
    if has_env_file:                                                                # the shipped .env carries CONTENT_PROXY__PROXYAUTH_* verbatim
        return user, password
    return (user or 'demo'), (password or str(uuid.uuid4()))


def derive_account_id(region: str) -> str:                                          # deploying account (operator's session) — written to the box .env so the mitm-service app has AWS_ACCOUNT_ID even on the instance-role path
    try:
        from osbot_aws.AWS_Config import AWS_Config
        return str(AWS_Config().aws_session_account_id() or '')
    except Exception:                                                               # offline / no creds at create time → leave blank (app can still derive via STS at runtime)
        return ''


def derive_fqdn(stack_name: str, request) -> str:
    # explicit --hostname wins; else --with-aws-dns auto-derives <stack>.<zone>; else blank (IP only)
    explicit = str(getattr(request, 'hostname', '') or '').strip()
    if explicit:
        return explicit
    if bool(getattr(request, 'with_aws_dns', False)):
        return f'{stack_name}.{_default_aws_dns_zone()}'
    return ''


def _parse_env(text: str) -> dict:                                                  # KEY=VALUE lines from a .env string
    env = {}
    for line in (text or '').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip()
    return env


ACCESS_TOKEN_ENV_KEYS       = ('FAST_API__AUTH__API_KEY__VALUE', 'SGRAPH_SEND__ACCESS_TOKEN')  # one access token in two vars — must be identical
ACCESS_TOKEN_ENV_CANONICAL  = 'SGRAPH_SEND__ACCESS_TOKEN'                                       # survivor when a shipped --env-file has two divergent reals (operator-facing)


def couple_env_access_token(env_text: str) -> tuple:                                # (rewritten_env, token). A supplied --env-file skips the CLI's realize_secrets, so guard it here: unify the token pair (else /pw fails 'Invalid API key value'). Empty token (env-file defines neither) → env unchanged, token ''.
    env   = _parse_env(env_text)
    order = (ACCESS_TOKEN_ENV_CANONICAL,) + tuple(k for k in ACCESS_TOKEN_ENV_KEYS if k != ACCESS_TOKEN_ENV_CANONICAL)
    token = next((env[k] for k in order if str(env.get(k, '')).strip()), '')
    if not token:
        return env_text, ''
    out, seen = [], set()
    for line in env_text.splitlines():
        s = line.strip()
        if s and not s.startswith('#') and '=' in s and s.split('=', 1)[0].strip() in ACCESS_TOKEN_ENV_KEYS:
            k = s.split('=', 1)[0].strip()
            out.append(f'{k}={token}')
            seen.add(k)
            continue
        out.append(line)
    for k in ACCESS_TOKEN_ENV_KEYS:                                                 # append any missing so both are present + identical
        if k not in seen:
            out.append(f'{k}={token}')
    return '\n'.join(out), token
EXT_PROXY_PORT        = 8080                                                        # mitmproxy-ext (human browser, Mode 1)
VAULT_PORT            = 443                                                         # vault-app front door (Mode 2 / UX)
ACME_PORT             = 80                                                          # cert-init http-01 (letsencrypt-ip only)


def sg_rules(tls, edge=Enum__Content_Proxy__Edge.NONE, hostname=''):                # → (inbound_ports[caller /32], extra_cidrs{port: cidr})
    inbound = [EXT_PROXY_PORT, VAULT_PORT]                                          # proxy + vault open to the caller only
    extra   = {}
    if tls == Enum__Content_Proxy__Tls.LETSENCRYPT:                                 # ACME http-01 is validated by LE's servers, not the caller
        extra[ACME_PORT] = '0.0.0.0/0'
    if edge == Enum__Content_Proxy__Edge.CADDY and hostname:                        # public hostname → world must reach :443 (Claude) + :80 (Caddy ACME http-01)
        extra[VAULT_PORT] = '0.0.0.0/0'
        extra[ACME_PORT]  = '0.0.0.0/0'
    return inbound, extra


def localhost_probe_command(https: bool) -> str:                                   # curl the vault on the box (SSM) — no SG/IP/cert deps
    url  = 'https://localhost/' if https else 'http://localhost:443/'
    flag = '-k ' if https else ''
    return f"curl -s {flag}-o /dev/null --max-time 5 -w '%{{http_code}}' {url}"


def parse_http_code(stdout: str) -> int:                                            # SSM stdout → numeric http code (0 = no response)
    digits = ''.join(ch for ch in str(stdout or '') if ch.isdigit())
    return int(digits[:3]) if digits else 0


def is_healthy_code(code: int) -> bool:                                             # vault answered (any non-5xx) ⇒ stack serving
    return 100 <= code < 500


# ── diagnose: pure parsers (unit-tested without AWS/SSM) ─────────────────────────
# The diagnose() generator below shells out via SSM, then hands the raw stdout to
# these pure functions. Keeping the parsing here (not inline in the generator) lets
# tests assert "given this `docker ps` output → which cp-* containers are up" with
# zero AWS. Boot stages mirror sg va's Vault_App__Service.diagnose, adapted for
# content_proxy: the boot script writes NO sentinel files (it uses `set -euo
# pipefail` + an "[content-proxy] boot complete" marker), and cert-init does NOT
# bind-mount a host stage file — so boot/cert health is read from the boot log and
# the container's exit state instead.

# The full cp-* container set published by Content_Proxy__Compose__Template.
# tls=self-signed/letsencrypt (non-caddy) adds cp-cert-init; edge=caddy adds cp-caddy.
BASE_CONTAINERS = ('cp-mitm-service', 'cp-mitmproxy-int', 'cp-mitmproxy-ext',
                   'cp-sg-playwright', 'cp-vault-app')


def expected_containers(tls, edge, firefox_count: int = 0) -> tuple:               # → cp-* names this stack shape should run
    names = list(BASE_CONTAINERS)
    if edge == Enum__Content_Proxy__Edge.CADDY:                                    # dedicated edge owns :443 + /pw
        names.append('cp-caddy')
    elif tls in (Enum__Content_Proxy__Tls.SELF_SIGNED, Enum__Content_Proxy__Tls.LETSENCRYPT):
        names.append('cp-cert-init')                                               # one-shot TLS sidecar (vault-as-edge TLS stacks only)
    names += [f'cp-firefox-{i}' for i in range(1, int(firefox_count) + 1)]         # interactive Firefox fleet (/browser/firefox/{i})
    return tuple(names)


def has_cert_init(tls, edge) -> bool:                                              # cert-init runs only on non-caddy TLS stacks
    return (edge != Enum__Content_Proxy__Edge.CADDY
            and tls in (Enum__Content_Proxy__Tls.SELF_SIGNED, Enum__Content_Proxy__Tls.LETSENCRYPT))


def parse_ps_names_status(stdout: str) -> dict:                                    # `docker ps -a --format "{{.Names}}<TAB>{{.Status}}"` → {name: status}
    out = {}
    for line in str(stdout or '').splitlines():
        line = line.strip()
        if not line:
            continue
        parts  = line.split('\t', 1) if '\t' in line else line.split(None, 1)
        name   = parts[0].strip()
        status = parts[1].strip() if len(parts) > 1 else ''
        if name:
            out[name] = status
    return out


def containers_up_status(stdout: str, expected: tuple) -> tuple:                   # → (all_up, up_names, down_or_missing)
    by_name  = parse_ps_names_status(stdout)
    up, down = [], []
    for name in expected:
        status = by_name.get(name, '')
        if status.startswith('Up'):
            up.append(name)
        elif name == 'cp-cert-init' and status.startswith('Exited (0)'):           # one-shot sidecar: a clean exit IS healthy
            up.append(name)
        else:
            down.append(name)                                                      # missing entirely OR not in a healthy state
    return (len(down) == 0, up, down)


def engine_active(stdout: str) -> bool:                                            # `systemctl is-active docker` stdout → active?
    return str(stdout or '').strip() == 'active'


def boot_log_failed(text: str) -> bool:                                            # the boot log shows a script failure (no sentinel file on this spec)
    body = str(text or '')
    if '[content-proxy] boot complete' in body:                                    # an explicit success marker overrides earlier noise
        return False
    low     = body.lower()
    markers = ('command not found', 'no such file', 'permission denied',           # specific script-failure signatures only — 'failed to'/'cannot ' were dropped: they match benign docker-pull noise (e.g. "failed to get default registry endpoint") during an in-progress boot
               'error response from daemon', 'fatal:',
               'traceback (most recent call last)')
    return any(m in low for m in markers)


def boot_log_complete(text: str) -> bool:                                          # the boot script ran to the end
    return '[content-proxy] boot complete' in str(text or '')


def boot_log_last_stage(text: str) -> str:                                         # most recent [content-proxy] marker line — the current boot stage
    last = ''
    for line in str(text or '').splitlines():
        if '[content-proxy]' in line:
            last = line.strip()
    return last


def boot_log_tail_is_firefox_prep(text: str) -> bool:                              # the only work left is the (cosmetic) Firefox profile prep
    # The Firefox profiles are prepared LAST, after the whole stack is up and
    # serving. If the last marker is a Firefox-prep line, the core stack is already
    # running — so boot-ok shouldn't stay WARN (which would block `wait`) on it.
    return 'firefox' in boot_log_last_stage(text).lower()


def cert_init_status(stdout: str) -> tuple:                                        # `docker ps -a` row for cp-cert-init → (status_kind, detail)
    by_name = parse_ps_names_status(stdout)
    status  = by_name.get('cp-cert-init', '')
    if not status:
        return ('warn', 'not yet — cp-cert-init container has not been created')
    if status.startswith('Exited (0)'):
        return ('ok', f'completed — {status}')
    if status.startswith('Exited'):                                                # any non-zero exit ⇒ issuance failed
        return ('fail', f'cert-init exited non-zero — {status}')
    if status.startswith(('Up', 'Restarting', 'Created')):
        return ('warn', f'still running — {status}')                               # issuing / waiting for ACME
    return ('warn', status)


class Content_Proxy__Service(Spec__Service__Base):
    aws_client        : Optional[Content_Proxy__AWS__Client]      = None
    mapper            : Optional[Content_Proxy__Stack__Mapper]    = None
    ip_detector       : Optional[Caller__IP__Detector]           = None
    name_gen          : Optional[Stack__Name__Generator]         = None
    user_data_builder : Optional[Content_Proxy__User_Data__Builder] = None

    def setup(self) -> 'Content_Proxy__Service':
        self.aws_client        = Content_Proxy__AWS__Client().setup()
        self.mapper            = Content_Proxy__Stack__Mapper()
        self.ip_detector       = Caller__IP__Detector()
        self.name_gen          = Stack__Name__Generator()
        self.user_data_builder = Content_Proxy__User_Data__Builder()
        return self

    def cli_spec(self) -> Schema__Spec__CLI__Spec:
        return Schema__Spec__CLI__Spec(
            spec_id               = 'content_proxy'                          ,
            display_name          = 'Content-Transformation Proxy'           ,
            default_instance_type = DEFAULT_INSTANCE_TYPE                     ,
            create_request_cls    = Schema__Content_Proxy__Create__Request   ,
            service_factory       = lambda: Content_Proxy__Service().setup() ,
            health_path           = '/'                                      ,
            health_port           = VAULT_PORT                               ,
            health_scheme         = 'http'                                   )   # unused: health() probes via SSM on the box (below)

    def health(self, region: str, name: str, timeout_sec: int = 0, poll_sec: int = 10):
        # Probe the vault ON THE BOX via SSM (localhost) — robust vs SG/IP and self-signed TLS.
        t0       = time.monotonic()
        probe    = Schema__CLI__Health__Probe()
        deadline = time.monotonic() + max(timeout_sec, 0)
        while True:
            try:
                info = self.get_stack_info(region, name)
                if info is None:
                    probe.state, probe.last_error = 'missing', f'no stack matched {name!r}'
                else:
                    instance_id = str(getattr(info, 'instance_id', '') or '')
                    state       = info.state.value if hasattr(info.state, 'value') else str(info.state or '')
                    if not instance_id:
                        probe.state, probe.last_error = state or 'pending', 'no instance id yet'
                    else:
                        edge_tls = getattr(info, 'edge', None) == Enum__Content_Proxy__Edge.CADDY  # caddy always serves :443 TLS
                        https    = edge_tls or getattr(info, 'tls', None) not in (None, Enum__Content_Proxy__Tls.NONE)
                        cmd      = localhost_probe_command(https)
                        try:
                            stdout, _ = self.aws_client.instance.run_command(region, instance_id, cmd, timeout_sec=30)
                            code = parse_http_code(stdout)
                            if is_healthy_code(code):
                                probe.healthy, probe.state, probe.last_error = True, 'running', ''
                                break
                            probe.state     = state or 'starting'
                            probe.last_error = f'vault http {code or "no-response"} (via ssm)'
                        except Exception as exc:                                    # SSM/agent not ready yet → keep polling
                            probe.state, probe.last_error = state or 'starting', str(exc)[:200]
            except Exception as exc:
                probe.last_error = str(exc)[:200]
            if time.monotonic() >= deadline:
                break
            time.sleep(poll_sec)
        probe.elapsed_ms = int((time.monotonic() - t0) * 1000)
        return probe

    def create_stack(self, request: Schema__Content_Proxy__Create__Request,
                           creator: str = '') -> Schema__Content_Proxy__Create__Response:
        t0         = time.monotonic()
        stack_name = str(request.stack_name)    or self.name_gen.generate()
        region     = str(request.region)        or DEFAULT_REGION
        caller_ip  = str(request.caller_ip)     or self.ip_detector.detect()
        ami_id     = str(request.from_ami)      or self.aws_client.ami.latest_al2023_ami(region)
        itype      = str(request.instance_type) or DEFAULT_INSTANCE_TYPE
        request.stack_name = stack_name                                             # so user-data / tags see the resolved name
        firefox_count      = int(getattr(request, 'firefox_count', 0) or 0)          # N interactive Firefox browsers
        fqdn               = derive_fqdn(stack_name, request)                        # explicit --hostname or <stack>.<zone> (--with-aws-dns); else ''
        if fqdn or firefox_count > 0:                                               # --hostname/--with-aws-dns/--firefox imply the Caddy edge (MVP routes /browser only via the edge)
            request.edge = Enum__Content_Proxy__Edge.CADDY
        request.hostname = fqdn

        inbound, extra_cidrs = sg_rules(request.tls, request.edge, fqdn)
        sg_id = self.aws_client.sg.ensure_security_group(region, stack_name, caller_ip,
                                                         inbound_ports=inbound, extra_cidrs=extra_cidrs)
        # app secrets: reuse what a supplied --env-file already defines; generate only if absent
        if str(request.env_inline):                                                              # a shipped .env skips the CLI's realize_secrets — couple its token pair here so a divergent pair can't deploy (→ /pw 'Invalid API key value')
            request.env_inline, _ = couple_env_access_token(str(request.env_inline))
        env_map       = _parse_env(str(request.env_inline))
        fastapi_key   = env_map.get('FASTAPI_API_KEY_VALUE') or str(uuid.uuid4())                 # interceptor ↔ mitm-service (mitm-service requires a GUID)
        env_token     = (env_map.get('FAST_API__AUTH__API_KEY__VALUE')                            # the access token (sg va model): vault key + sg-playwright key (/pw) + set-cookie
                         or env_map.get('SGRAPH_SEND__ACCESS_TOKEN'))
        # env-file path: the response/tag token MUST reflect what the box actually has — never fabricate a uuid the box lacks
        access_token  = env_token if str(request.env_inline) else (env_token or str(uuid.uuid4()))
        keys_from_env = bool(env_map.get('FAST_API__AUTH__API_KEY__VALUE')
                             or env_map.get('SGRAPH_SEND__ACCESS_TOKEN')
                             or env_map.get('FASTAPI_API_KEY_VALUE'))
        request.proxyauth_user, request.proxyauth_pass = resolve_proxyauth(          # ext (internet-facing) proxy needs real basic-auth — local `up` fills it via realize_secrets, the EC2 path must too (else proxyauth=: → empty/broken Mode 1)
            str(request.proxyauth_user), str(request.proxyauth_pass), bool(str(request.env_inline)))
        extra_tags = {TAG_MODE  : request.mode.value,
                      TAG_TLS   : request.tls.value ,
                      TAG_EDGE  : request.edge.value,
                      TAG_ACCESS: access_token       }
        if fqdn:
            extra_tags[TAG_HOSTNAME] = fqdn
        if firefox_count > 0:                                                        # surfaced in info → per-browser /browser/firefox/{i} URLs
            extra_tags[TAG_FIREFOX] = str(firefox_count)
        tags = self.aws_client.tags.build(stack_name, caller_ip, creator,                         # access token tagged → recoverable for info
                                          extra_tags=extra_tags)
        aws_creds = {}
        if bool(request.forward_aws_creds):                                          # parity path — bake operator creds; else instance role
            for k in ('AWS_ACCOUNT_ID', 'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY'):
                v = os.environ.get(k, '')
                if v:
                    aws_creds[k] = v
        account_id = derive_account_id(region) or aws_creds.get('AWS_ACCOUNT_ID', '')  # always set AWS_ACCOUNT_ID on the box, even on the instance-role path
        user_data = self.user_data_builder.render(request,
                                                  fastapi_api_key    = fastapi_key        ,
                                                  access_token       = access_token       ,
                                                  region             = region             ,
                                                  account_id         = account_id         ,
                                                  aws_creds          = aws_creds          ,
                                                  env_override       = str(request.env_inline),
                                                  hostname           = fqdn               ,
                                                  firefox_count      = firefox_count      )
        iid = self.aws_client.launch.run_instance(region                = region            ,
                                                  ami_id                = ami_id            ,
                                                  sg_id                 = sg_id             ,
                                                  user_data             = user_data         ,
                                                  tags                  = tags              ,
                                                  instance_type         = itype             ,
                                                  instance_profile_name = PROFILE_NAME      ,
                                                  max_hours             = int(math.ceil(request.max_hours)),  # >0 → on-demand terminate-on-shutdown flag
                                                  disk_size_gb          = int(request.disk_size_gb),
                                                  use_spot              = bool(request.use_spot))
        info = self.mapper.to_info({'InstanceId'    : iid                          ,
                                    'InstanceType'  : itype                        ,
                                    'ImageId'       : ami_id                       ,
                                    'State'         : {'Name': 'pending'}          ,
                                    'SecurityGroups': [{'GroupId': sg_id}]         ,
                                    'Tags'          : tags                         }, region)
        env_src    = 'env-file' if str(request.env_inline) else ('baked AWS creds' if aws_creds else 'instance role')
        creds_path = env_src
        return Schema__Content_Proxy__Create__Response(
            stack_info         = info                                        ,
            fastapi_api_key    = fastapi_key                                 ,
            access_token       = access_token                                ,
            secrets_from_env   = keys_from_env                              ,
            proxyauth_user     = str(request.proxyauth_user)                 ,
            proxyauth_pass     = str(request.proxyauth_pass)                 ,
            message    = f'Instance {iid} launching ({STACK_TYPE}, {request.proxy_tool.value}, S3 via {creds_path})',
            elapsed_ms = int((time.monotonic() - t0) * 1000)                 )

    def list_stacks(self, region: str = '') -> Schema__Content_Proxy__List:
        region = region or DEFAULT_REGION
        raw    = self.aws_client.instance.list_by_stack_type(region, STACK_TYPE)
        stacks = [self.mapper.to_info(d, region) for d in raw.values()]
        return Schema__Content_Proxy__List(region=region, stacks=stacks, total=len(stacks))

    def get_stack_info(self, region: str, stack_name: str) -> Optional[Schema__Content_Proxy__Stack__Info]:
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        return self.mapper.to_info(details, region) if details else None

    # ── boot-sequence diagnostic checklist ──────────────────────────────────────
    # Generator protocol (mirrors Vault_App__Service.diagnose): yields
    # (name, 'checking', '') for each active check, then the final
    # (name, status, detail). Skipped checks are yielded directly. The CLI drives
    # this into a live rich.Table. The pure parsing is delegated to the module-level
    # helpers above so it can be unit-tested without AWS/SSM.
    # Stages: ec2-state → ssm-reachable → boot-failed → container-engine →
    #         containers-up → cert-init (TLS stacks only) → vault-http → boot-ok.

    def diagnose(self, region: str, name: str):
        _REST = ('ssm-reachable', 'boot-failed', 'container-engine',
                 'containers-up', 'vault-http', 'boot-ok')

        # ── check 1: ec2-state ─────────────────────────────────────────────────
        yield ('ec2-state', 'checking', '')
        info = self.get_stack_info(region, name)
        if info is None:
            yield ('ec2-state', 'fail', 'stack not found')
            return
        ec2_state = info.state.value if hasattr(info.state, 'value') else str(getattr(info, 'state', '') or '')
        ec2_ok    = ec2_state == 'running'
        yield ('ec2-state', 'ok' if ec2_ok else 'fail', ec2_state or '?')
        if not ec2_ok:
            for n in _REST:
                yield (n, 'skip', f'skipped — ec2 is {ec2_state!r}')
            return

        tls  = getattr(info, 'tls',  Enum__Content_Proxy__Tls.NONE)
        edge = getattr(info, 'edge', Enum__Content_Proxy__Edge.NONE)
        firefox_count = int(getattr(info, 'firefox_count', 0) or 0)                 # interactive Firefox fleet — verify each cp-firefox-{i} in containers-up
        tls_stack = has_cert_init(tls, edge)

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
        # No sentinel file on this spec — read the boot log and look for failure
        # markers (the success marker '[content-proxy] boot complete' clears them).
        yield ('boot-failed', 'checking', '')
        boot_text = ''
        try:
            boot_text = ssm(f'tail -n 60 {BOOT_LOG} 2>/dev/null || true')
            if boot_log_failed(boot_text):
                tail = '\n'.join(boot_text.splitlines()[-15:])
                yield ('boot-failed', 'fail', ('boot script error:\n' + tail) if tail else 'boot script error')
            else:
                yield ('boot-failed', 'ok', 'no failure markers in boot log')
        except Exception:
            yield ('boot-failed', 'warn', 'could not check')

        # ── check 4: container-engine ──────────────────────────────────────────
        yield ('container-engine', 'checking', '')
        engine_ok = False
        try:
            out = ssm('systemctl is-active docker 2>&1 || true')
            if engine_active(out):
                engine_ok = True
                yield ('container-engine', 'ok', 'docker active')
            else:
                yield ('container-engine', 'warn', f'docker state={out!r} — boot may still be installing it')
        except Exception:
            yield ('container-engine', 'warn', 'could not check')

        # ── check 5: containers-up ─────────────────────────────────────────────
        expected      = expected_containers(tls, edge, firefox_count)
        containers_ok = False
        yield ('containers-up', 'checking', '')
        try:
            out = ssm('sudo docker ps -a --format "{{.Names}}\t{{.Status}}" 2>/dev/null || true')
            all_up, up, down = containers_up_status(out, expected)
            if all_up:
                containers_ok = True
                yield ('containers-up', 'ok', f'{len(up)}/{len(expected)} up — ' + ', '.join(up))
            elif not engine_ok:
                yield ('containers-up', 'warn', 'not yet — container engine not ready')
            elif up:
                yield ('containers-up', 'warn', f'{len(up)}/{len(expected)} up — still down: {", ".join(down)}')
            else:
                yield ('containers-up', 'warn', f'none up yet — expecting: {", ".join(expected)}')
        except Exception:
            yield ('containers-up', 'warn', 'could not check')

        # ── check 6: cert-init (TLS stacks only) ───────────────────────────────
        # cert-init does NOT bind-mount a host stage file here (unlike sg va), so we
        # read the one-shot sidecar's container state via `docker ps -a`. THIS is the
        # key cert-debug signal: a non-zero exit means ACME/self-signed issuance failed.
        if tls_stack:
            yield ('cert-init', 'checking', '')
            try:
                out = ssm('sudo docker ps -a --format "{{.Names}}\t{{.Status}}" 2>/dev/null || true')
                status, detail = cert_init_status(out)
                yield ('cert-init', status, detail)
            except Exception as exc:
                yield ('cert-init', 'warn', f'could not check: {str(exc)[:120]}')
        else:
            # No cert-init on plain (tls=none) or caddy stacks — Caddy self-manages
            # TLS, plain stacks have no sidecar. Mark it skipped so the live table
            # settles (a 'pending' cert-init would block `wait` forever).
            yield ('cert-init', 'skip', 'no cert-init sidecar (caddy or tls=none stack)')

        # ── check 7: vault-http ────────────────────────────────────────────────
        if not containers_ok:
            yield ('vault-http', 'skip', 'skipped — containers not running')
        else:
            https = (edge == Enum__Content_Proxy__Edge.CADDY) or (tls != Enum__Content_Proxy__Tls.NONE)
            yield ('vault-http', 'checking', '')
            try:
                code = parse_http_code(ssm(localhost_probe_command(https), timeout=30))
                if code in (200, 204):
                    yield ('vault-http', 'ok', f'HTTP {code}')
                elif code in (401, 403):
                    yield ('vault-http', 'ok', f'HTTP {code} — up, auth-gated (expected)')
                elif code and is_healthy_code(code):
                    yield ('vault-http', 'warn', f'HTTP {code} — up but not ready')
                elif code:
                    yield ('vault-http', 'warn', f'HTTP {code} — vault still warming up')
                else:
                    yield ('vault-http', 'warn', 'no response on :443 — vault still warming up')
            except Exception as exc:
                yield ('vault-http', 'fail', str(exc)[:120])

        # ── check 8: boot-ok ───────────────────────────────────────────────────
        yield ('boot-ok', 'checking', '')
        try:
            text = boot_text or ssm(f'tail -n 60 {BOOT_LOG} 2>/dev/null || true')
            if boot_log_complete(text):
                yield ('boot-ok', 'ok', 'boot script completed')
            elif containers_ok and boot_log_tail_is_firefox_prep(text):             # core stack up; only the cosmetic FF profile prep remains → don't block `wait`
                yield ('boot-ok', 'ok', 'core stack up — Firefox profile prep still finishing (non-blocking)')
            else:
                stage = boot_log_last_stage(text)
                yield ('boot-ok', 'warn', f'not yet — current stage: {stage[:160]}' if stage else 'not yet')
        except Exception:
            yield ('boot-ok', 'warn', 'could not check')

    def delete_stack(self, region: str, stack_name: str) -> Schema__Content_Proxy__Delete__Response:
        t0      = time.monotonic()
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        if not details:
            return Schema__Content_Proxy__Delete__Response(stack_name=stack_name, deleted=False,
                                                          message='stack not found',
                                                          elapsed_ms=int((time.monotonic() - t0) * 1000))
        iid   = details.get('InstanceId', '')
        sg_id = (details.get('SecurityGroups') or [{}])[0].get('GroupId', '')
        ok    = self.aws_client.instance.terminate(region, iid)
        if ok and sg_id:
            self.aws_client.sg.delete_security_group(region, sg_id)
        return Schema__Content_Proxy__Delete__Response(stack_name=stack_name, deleted=bool(ok),
                                                      message=f'terminated {iid}' if ok else 'terminate failed',
                                                      elapsed_ms=int((time.monotonic() - t0) * 1000))

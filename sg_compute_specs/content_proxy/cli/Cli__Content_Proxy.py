# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Cli__Content_Proxy
# Builder-driven CLI (8 standard verbs from Spec__CLI__Builder) + extras:
#   - local up|down|status  : run/stop/inspect the stack locally via docker compose
# Mounted in sg_compute/cli/Cli__SG.py as `sg content-proxy` (alias `cp`).
# ═══════════════════════════════════════════════════════════════════════════════

import re
import shlex
import subprocess
import threading
import uuid
from pathlib       import Path
from typing        import List, Optional

import typer
from rich.console  import Console

from sg_compute.cli.base.Schema__Spec__CLI__Spec import Schema__Spec__CLI__Spec
from sg_compute.cli.base.Spec__CLI__Builder      import Spec__CLI__Builder
from sg_compute.cli.base.Spec__CLI__Defaults     import DEFAULT_REGION
from sg_compute.cli.base.Spec__CLI__Errors       import spec_cli_errors

from sg_compute_specs.content_proxy.cli.Renderers                       import render_create, render_info
from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Browser__Engine import Enum__Content_Proxy__Browser__Engine
from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Edge        import Enum__Content_Proxy__Edge
from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Mode        import Enum__Content_Proxy__Mode
from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Proxy__Tool import Enum__Content_Proxy__Proxy__Tool
from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Tls         import Enum__Content_Proxy__Tls
from sg_compute_specs.content_proxy.schemas.Schema__Content_Proxy__Create__Request import Schema__Content_Proxy__Create__Request
from sg_compute_specs.content_proxy.service.Content_Proxy__Service                  import Content_Proxy__Service


# ── committed local compose (the `docker compose up` target) ────────────────────
import sg_compute_specs.content_proxy as _pkg
COMPOSE_DIR       = Path(_pkg.__file__).parent / 'docker' / 'compose'
COMPOSE_FILE      = COMPOSE_DIR / 'docker-compose.yml'
COMPOSE_FILE_CADDY = COMPOSE_DIR / 'docker-compose.caddy.yml'                        # dedicated-edge variant (PoC)
COMPOSE_GENERATED  = COMPOSE_DIR / 'docker-compose.generated.yml'                    # `local up --browsers N` renders here (gitignored — parameterised, never committed)
CADDYFILE_GENERATED = COMPOSE_DIR / 'Caddyfile.generated'
ENV_FILE          = COMPOSE_DIR / '.env'
ENV_EXAMPLE       = COMPOSE_DIR / '.env.example'


def write_generated_local_files(browsers: int, browser_engine: str) -> Path:        # → compose path for `local up --browsers N` (same dir as the committed files so ../../interceptors mounts resolve)
    from sg_compute_specs.content_proxy.service.Content_Proxy__Compose__Template import Content_Proxy__Compose__Template
    from sg_compute_specs.content_proxy.service.Content_Proxy__Edge__Template    import Content_Proxy__Edge__Template
    compose = Content_Proxy__Compose__Template().render(edge          = Enum__Content_Proxy__Edge.CADDY,
                                                        browser_count = browsers                       ,
                                                        browser_engine= browser_engine                 )
    compose = compose.replace('./Caddyfile:/etc/caddy/Caddyfile:ro',                 # the generated caddy config, not the committed one
                              './Caddyfile.generated:/etc/caddy/Caddyfile:ro')
    COMPOSE_GENERATED.write_text(compose)
    CADDYFILE_GENERATED.write_text(Content_Proxy__Edge__Template().render(browser_count=browsers))
    return COMPOSE_GENERATED


def _set_extras(request, mode='direct_proxy', tls='none', edge='none', hostname='',
                with_aws_dns=False, proxy_tool='mitmdump',
                proxyauth_user='', proxyauth_pass='', proxy_ca_cert='', proxy_ca_key='',
                scripts_bucket='', forward_aws_creds=False, env_file='', ca_from_local=False,
                use_spot=True, disk_size=0, mitm_service_image='', edge_auth=False,
                browsers=0, browser_engine='chromium', tag=None):
    if env_file:                                                                     # MVP: ship a full .env verbatim to the box
        request.env_inline = Path(env_file).read_text()
    if ca_from_local:                                                                # reuse the local docker mitmproxy CA (already trusted in your browser)
        ca = COMPOSE_DIR / 'certs' / 'mitmproxy-ca.pem'
        if not ca.exists():
            raise FileNotFoundError(f'{ca} not found — run `sg content-proxy local up` once to generate it')
        request.proxy_ca_pem = ca.read_text()
    elif proxy_ca_cert or proxy_ca_key:                                              # ship a supplied CA (cert + key) — mitmproxy needs BOTH to sign intercepted TLS
        if not (proxy_ca_cert and proxy_ca_key):
            raise ValueError('--proxy-ca-cert and --proxy-ca-key must be supplied together '
                             '(mitmproxy needs the CA cert AND its private key to intercept TLS)')
        cert_pem = Path(proxy_ca_cert).read_text().strip()
        key_pem  = Path(proxy_ca_key).read_text().strip()
        request.proxy_ca_pem = f'{key_pem}\n{cert_pem}\n'                            # mitmproxy-ca.pem format = private key then cert
    request.mode              = Enum__Content_Proxy__Mode(mode)
    request.tls               = Enum__Content_Proxy__Tls(tls)
    request.edge              = Enum__Content_Proxy__Edge(edge)
    request.hostname          = hostname
    request.with_aws_dns      = bool(with_aws_dns)
    request.edge_auth         = bool(edge_auth)
    request.browser_count     = int(browsers)
    request.browser_engine    = Enum__Content_Proxy__Browser__Engine(browser_engine)
    if hostname or with_aws_dns:                                                     # a public hostname requires the Caddy edge (auto-ACME)
        request.edge          = Enum__Content_Proxy__Edge.CADDY
    if int(browsers) > 0:                                                            # the interactive browser fleet is reached only via the Caddy edge
        request.edge          = Enum__Content_Proxy__Edge.CADDY
    if bool(edge_auth):                                                              # the token gate lives at the Caddy edge — no edge, nothing to gate
        request.edge          = Enum__Content_Proxy__Edge.CADDY
    request.proxy_tool        = Enum__Content_Proxy__Proxy__Tool(proxy_tool)
    request.proxyauth_user    = proxyauth_user
    request.proxyauth_pass    = proxyauth_pass
    request.proxy_ca_cert     = proxy_ca_cert
    request.proxy_ca_key      = proxy_ca_key
    local_env                 = read_env_file(ENV_FILE)
    request.scripts_bucket    = resolve_scripts_bucket(scripts_bucket, local_env)    # explicit flag wins; else inherit the local .env's CACHE__SERVICE__BUCKET_NAME
    stack_creds               = resolve_stack_aws_creds(local_env)                   # S3 creds for the box, from the local stack .env (not the deploy session)
    request.aws_access_key_id     = stack_creds.get('AWS_ACCESS_KEY_ID'    , '')
    request.aws_secret_access_key = stack_creds.get('AWS_SECRET_ACCESS_KEY', '')
    request.aws_session_token     = stack_creds.get('AWS_SESSION_TOKEN'    , '')
    tag_lines = []                                                                   # --tag KEY=VALUE (repeatable): shape validated here; reserved-key collisions rejected in the service before any AWS call
    for kv in (tag or []):
        key = kv.split('=', 1)[0].strip() if '=' in kv else ''
        if not key:
            raise typer.BadParameter(f'--tag expects KEY=VALUE (non-empty key), got {kv!r}')
        tag_lines.append(kv.strip())
    request.custom_tags       = '\n'.join(tag_lines)
    request.forward_aws_creds = bool(forward_aws_creds)
    request.use_spot          = bool(use_spot)
    request.disk_size_gb      = int(disk_size)
    if mitm_service_image:
        request.mitm_service_image = mitm_service_image


def resolve_stack_aws_creds(local_env: dict) -> dict:                              # AWS creds the STACK runs with (mitm-service → S3), inherited from the LOCAL stack .env — deliberately NOT os.environ, which holds the operator session used to deploy (an S3-only user there would break the EC2/Route53 calls)
    keys = ('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN')
    return {k: str(local_env.get(k, '') or '') for k in keys if str(local_env.get(k, '') or '')}


def resolve_scripts_bucket(explicit: str, local_env: dict) -> str:                 # explicit --scripts-bucket wins; else inherit the local .env's CACHE__SERVICE__BUCKET_NAME (single-source, like `local up`)
    return str(explicit or local_env.get('CACHE__SERVICE__BUCKET_NAME', '') or '')


# ── --with-aws-dns / --hostname: post-launch Route 53 (reuses the sg va flow) ──
# Kicked off after create_stack returns, BEFORE _wait_healthy blocks on EC2 boot.
# Polls for the public IP, then upserts <fqdn> A → IP + waits INSYNC + authoritative.
# By the time Caddy reaches its ACME http-01 challenge, DNS has typically converged.
def _content_proxy_post_launch(svc, region, request, response, kwargs, console):
    fqdn = str(getattr(request, 'hostname', '') or '').strip()                      # service derived this from --hostname/--with-aws-dns
    if not fqdn or not bool(getattr(request, 'with_aws_dns', False)):
        return None
    info       = getattr(response, 'stack_info', None) or response
    stack_name = str(getattr(info, 'stack_name', '') or '')

    def _worker():
        import time as _time
        from sg_compute_specs.vault_app.service.Vault_App__Auto_DNS import Vault_App__Auto_DNS
        public_ip = ''
        deadline  = _time.time() + 60
        while _time.time() < deadline:
            fresh = svc.get_stack_info(region, stack_name)
            ip    = str(getattr(fresh, 'public_ip', '') or '') if fresh is not None else ''
            if ip:
                public_ip = ip
                break
            _time.sleep(2)
        if not public_ip:
            console.print('  [yellow]⚠[/]  auto-dns: gave up waiting for public IP after 60s — skipping Route 53 work')
            return
        console.print(f'  [dim]auto-dns:[/] starting  {fqdn} → {public_ip}')
        def _progress(stage, detail):
            console.print(f'  [dim]auto-dns:[/] {stage}  [dim]{detail}[/]')
        result = Vault_App__Auto_DNS().run(fqdn=fqdn, public_ip=public_ip, on_progress=_progress)
        if result.error:
            console.print(f'  [red]✗[/]  auto-dns failed: {result.error}')
        else:
            console.print(f'  [green]✓[/]  auto-dns: {fqdn} → {public_ip}  (INSYNC + authoritative, {result.elapsed_ms}ms)')

    thread = threading.Thread(target=_worker, daemon=True, name='content-proxy-auto-dns')
    thread.start()
    return thread                                                                  # Spec__CLI__Builder joins after _wait_healthy


# ── diagnose check-table config (shared renderer) ───────────────────────────────
# Pre-known check order — matches Content_Proxy__Service.diagnose() yield order.
# 'cert-init' is yielded only on non-caddy TLS stacks (yielded as 'skip' otherwise);
# 'external-http' is the renderer's own svc.health() probe appended after the
# generator. All shown up-front as 'pending' so the live table doesn't grow
# top-down. Carried on _cli_spec so `create --wait` renders the same table (via
# Spec__CLI__Builder._wait_healthy) as the standalone `check` / `wait` commands.
DIAGNOSE_CHECK_ORDER = ('ec2-state', 'ssm-reachable', 'boot-failed', 'container-engine',
                        'containers-up', 'cert-init', 'vault-http', 'browser-http',
                        'boot-ok', 'external-http')

# per-check log source to suggest when a check fails / warns — keys reuse LOG_SOURCES
# (defined further down; the shared renderer filters against LOG_SOURCES at print).
DIAGNOSE_HINTS = {
    'ssm-reachable'    : [('boot'        , 'see if boot completed at all')],
    'boot-failed'      : [('boot'        , 'full boot log with the error')],
    'container-engine' : [('boot'        , 'engine install stage'), ('journal', 'systemd unit errors')],
    'containers-up'    : [('boot'        , 'compose up output'), ('vault', 'vault-app container')],
    'cert-init'        : [('cert-init'   , 'one-shot TLS sidecar — self-signed gen / ACME issuance')],
    'vault-http'       : [('vault'        , 'cp-vault-app container output'), ('caddy', 'edge TLS/routing (caddy stacks)')],
    'browser-http'     : [('browser-1'   , 'first interactive browser — supervisord/xvfb/novnc startup'), ('caddy', 'edge /browser routing')],
    'boot-ok'          : [('boot'        , 'watch boot progress')],
    'external-http'    : [('vault'        , 'cp-vault-app container output'), ('caddy', 'edge TLS/routing (caddy stacks)')],
}
DIAGNOSE_LOG_PREFIX = 'sg cp logs'


_cli_spec = Schema__Spec__CLI__Spec(
    spec_id               = 'content_proxy'                          ,
    display_name          = 'Content-Transformation Proxy'           ,
    default_instance_type = 't3.large'                               ,
    create_request_cls    = Schema__Content_Proxy__Create__Request   ,
    service_factory       = lambda: Content_Proxy__Service().setup() ,
    health_path           = '/'                                      ,
    health_port           = 443                                      ,
    health_scheme         = 'http'                                   ,   # NONE/MVP: vault plain HTTP behind :443 (TLS stacks → https)
    extra_create_field_setters = _set_extras                         ,
    render_info_fn             = render_info                         ,
    render_create_fn           = render_create                       ,
    post_launch_fn             = _content_proxy_post_launch          ,
    diagnose_check_order       = DIAGNOSE_CHECK_ORDER                ,
    diagnose_hints             = DIAGNOSE_HINTS                       ,
    diagnose_log_prefix        = DIAGNOSE_LOG_PREFIX                  )


app = Spec__CLI__Builder(
    cli_spec              = _cli_spec,
    skip_default_commands = ['wait'],                                                # replaced below by the diagnose-driven live check table
    extra_create_options  = [
        ('mode'          , str , 'direct_proxy', 'direct_proxy (NLB) or vault_web (ALB).'),
        ('tls'           , str , 'none'        , 'Vault TLS on :443 — none | self-signed (IP, browser warns) | letsencrypt (real IP cert, opens :80) | acm (ALB, not wired). Ignored when --edge caddy (the edge terminates TLS).'),
        ('edge'          , str , 'none'        , 'Front door: none (vault-as-edge) | caddy (dedicated edge owns :443, /pw routed, vault is a plain origin). --hostname/--with-aws-dns force caddy.'),
        ('hostname'      , str , ''            , 'Public FQDN for the Caddy edge (e.g. my-stack.sg-compute.sgraph.ai) — Caddy does auto-ACME for a real trusted cert (opens :80+:443 to the world). Implies --edge caddy.'),
        ('with_aws_dns'  , bool, False         , 'Auto-create the Route 53 A record <stack>.sg-compute.sgraph.ai → public IP at create (reuses the sg va flow). Implies --edge caddy + a derived hostname.'),
        ('edge_auth'     , bool, False         , 'Token-gate /pw and /browser at the Caddy edge (401 unless the access token is sent as an X-API-Key header or the cp_access cookie; set the cookie once via /edge/auth?token=…). Forces --edge caddy. Default off = open edge.'),
        ('browsers'      , int , 0             , 'Number of interactive browsers (sg-playwright-vnc: headed browser + noVNC; each = one user at /browser/{n}, browsing through the mitmproxy). Forces --edge caddy. 0 = none.'),
        ('browser_engine', str , 'chromium'    , 'Engine the interactive browsers autostart: chromium | firefox (env choice on the same image).'),
        ('tag'           , List[str], []       , 'Extra EC2 tag, KEY=VALUE; repeat for multiple (e.g. --tag Project=akeia --tag CostCenter=42). Reserved stack keys (StackName/StackType/Name/cp:*) are rejected.'),
        ('proxy_tool'    , str , 'mitmdump'    , 'mitmweb (dev, TUI /flows, in-memory) or mitmdump (prod, headless).'),
        ('proxyauth_user', str , ''            , 'mitmproxy-ext basic-auth user (Mode 1).'),
        ('proxyauth_pass', str , ''            , 'mitmproxy-ext basic-auth pass (Mode 1).'),
        ('proxy_ca_cert' , str , ''            , 'Path to the user-supplied proxy CA cert (Mode 1 browser trust).'),
        ('proxy_ca_key'  , str , ''            , 'Path to the user-supplied proxy CA key.'),
        ('env_file'      , str , ''            , 'Path to a full .env shipped verbatim to the box (MVP: overrides generated env — ship your working local .env).'),
        ('ca_from_local' , bool, False         , 'Ship the local docker mitmproxy CA (docker/compose/certs/mitmproxy-ca.pem) so the EC2 proxy uses the CA already trusted in your browser.'),
        ('scripts_bucket', str , ''            , 'S3 bucket the MITM service reads injection scripts from (CACHE__SERVICE__BUCKET_NAME). Defaults to the local .env value when blank.'),
        ('forward_aws_creds', bool, False      , 'Bake the operator AWS_* creds into the box .env (local-parity; default off → instance role).'),
        ('use_spot'      , bool, True          , 'Spot instance (~70%% cheaper). --no-use-spot for on-demand.'),
        ('disk_size'     , int , 0             , 'Root volume GiB. 0 = AMI default.'),
        # ── advanced ──
        ('mitm_service_image', str, '', 'Override the MITM service image (default diniscruz/mgraph-ai-service-mitmproxy).', True),
    ],
).build()


# ── local lifecycle (docker compose) ───────────────────────────────────────────

local_app = typer.Typer(no_args_is_help=True,
                        help='Run the content-proxy stack locally via docker compose.')


CERTS_DIR     = COMPOSE_DIR / 'certs'
OVERRIDES_DIR = COMPOSE_DIR / 'overrides'                                            # /pw runtime-injection files (generated)


def _ensure_overrides() -> None:
    # write the sg_overrides package the vault container's custom entrypoint loads (/pw)
    from sg_compute_specs.vault_app.service.Vault_App__Reverse_Proxy__Override import (Vault_App__Reverse_Proxy__Override,
                                                                                       SERVE_WITH_PROXY)
    OVERRIDES_DIR.mkdir(parents=True, exist_ok=True)
    (OVERRIDES_DIR / '__init__.py').write_text('')
    (OVERRIDES_DIR / 'Fast_API__Reverse_Proxy.py').write_text(Vault_App__Reverse_Proxy__Override().reverse_proxy_source())
    (OVERRIDES_DIR / 'serve_with_proxy.py').write_text(SERVE_WITH_PROXY)


def _ensure_env(c: Console) -> None:
    if not ENV_FILE.exists():
        ENV_FILE.write_text(ENV_EXAMPLE.read_text())
        c.print(f'  [yellow]⚠[/]  created {ENV_FILE} from .env.example — edit the secrets before any real use')
    else:                                                                            # a pre-existing .env may predate newer keys (e.g. SGRAPH_SEND__ACCESS_TOKEN)
        have    = set(read_env_file(ENV_FILE).keys())
        example = read_env_file(ENV_EXAMPLE)
        missing = [(k, v) for k, v in example.items() if k not in have]
        if missing:
            with ENV_FILE.open('a') as fh:
                fh.write('\n# ── appended by `sg content-proxy local` (keys added since this .env was created) ──\n')
                for k, v in missing:
                    fh.write(f'{k}={v}\n')
            c.print(f'  [yellow]⚠[/]  appended {len(missing)} missing key(s) to {ENV_FILE.name}: '
                    f'[dim]{", ".join(k for k, _ in missing)}[/]')
    updates = realize_secrets(read_env_file(ENV_FILE))                               # placeholder/blank secrets → real GUIDs (mitm-service rejects 'change-me')
    if updates:
        apply_env_updates(ENV_FILE, updates)
        c.print(f'  [green]✓[/]  generated GUIDs for {len(updates)} secret(s) in {ENV_FILE.name}: '
                f'[dim]{", ".join(sorted(updates))}[/]')
    if not CERTS_DIR.exists():                                                       # mitmproxy self-generates its CA here (rw mount)
        CERTS_DIR.mkdir(parents=True, exist_ok=True)
        CERTS_DIR.chmod(0o777)                                                       # container user (uid 1000) must be able to write
    _ensure_overrides()                                                              # /pw entrypoint override (always refresh)


def _compose(*args: str, compose_file: Path = None):
    return subprocess.run(['docker', 'compose', '--env-file', str(ENV_FILE),
                           '-f', str(compose_file or COMPOSE_FILE), *args])


# ── secret realization (the mitm-service rejects placeholders — keys must be GUIDs) ─
PLACEHOLDER_VALUE = 'change-me'
GUID_SECRET_KEYS  = ('FASTAPI_API_KEY_VALUE', 'CONTENT_PROXY__PROXYAUTH_PASS')      # standalone secrets → own GUID each
ACCESS_TOKEN_KEYS = ('FAST_API__AUTH__API_KEY__VALUE', 'SGRAPH_SEND__ACCESS_TOKEN')  # ONE access token in two vars — must be identical
ACCESS_TOKEN__CANONICAL = 'SGRAPH_SEND__ACCESS_TOKEN'                               # survivor when two reals diverge — operator-facing (printed by `up`, paid into the vault cookie)


def _needs_value(v: str) -> bool:                                                  # blank or the shipped placeholder ⇒ generate
    return (v or '').strip() in ('', PLACEHOLDER_VALUE)


def realize_secrets(env: dict) -> dict:                                            # → {key: new_value} for keys that must change
    updates = {}
    survivor_order = (ACCESS_TOKEN__CANONICAL,) + tuple(k for k in ACCESS_TOKEN_KEYS if k != ACCESS_TOKEN__CANONICAL)
    real_token = next((env[k] for k in survivor_order if not _needs_value(env.get(k, ''))), '')  # prefer the operator-facing token when picking the survivor
    diverged   = len({env.get(k, '') for k in ACCESS_TOKEN_KEYS}) > 1               # two real-but-different reals: Caddy forwards one, sg-playwright validates the other → 'Invalid API key value'
    if any(_needs_value(env.get(k, '')) for k in ACCESS_TOKEN_KEYS) or diverged:   # keep the pair coupled to one GUID (placeholder/blank OR divergent)
        token = real_token or str(uuid.uuid4())
        for k in ACCESS_TOKEN_KEYS:
            if env.get(k, '') != token:
                updates[k] = token
    for k in GUID_SECRET_KEYS:                                                     # mitm-service requires a real GUID, not 'change-me'
        if _needs_value(env.get(k, '')):
            updates[k] = str(uuid.uuid4())
    return updates


def apply_env_updates(path: Path, updates: dict) -> None:                          # rewrite KEY= lines in place; append any missing
    if not updates:
        return
    lines, seen, out = path.read_text().splitlines(), set(), []
    for line in lines:
        s = line.strip()
        if s and not s.startswith('#') and '=' in s:
            k = s.split('=', 1)[0].strip()
            if k in updates:
                out.append(f'{k}={updates[k]}')
                seen.add(k)
                continue
        out.append(line)
    out += [f'{k}={v}' for k, v in updates.items() if k not in seen]
    path.write_text('\n'.join(out) + '\n')


# ── pure helpers (unit-tested) ──────────────────────────────────────────────────

def read_env_file(path: Path) -> dict:                                             # KEY=VALUE → dict; ignores comments/blanks
    env = {}
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip()
    return env


def auth_help_lines(base_url: str, token: str) -> List[str]:                       # the "how to authenticate the browser" block for `local up`
    # the vault (and /pw behind it) require the access token as a header or cookie;
    # the set-cookie form is the one-click way to plant the cookie in the browser.
    token_note = (f'[bold yellow]{token}[/]' if token and token != 'change-me'
                  else f'[yellow]{token or "<unset>"}[/]  [dim](still the .env placeholder — set a real value)[/]')
    return [
        f'  access token  : {token_note}  [dim](SGRAPH_SEND__ACCESS_TOKEN in .env)[/]',
        f'  vault cookie  : [cyan]{base_url}/auth/set-cookie-form[/]  [dim]— paste the token → auths the vault UI ( / )[/]',
        f'  /pw cookie    : [cyan]{base_url}/pw/auth/set-cookie-form[/]  [dim]— paste the token → auths sg-playwright ( /pw )[/]',
        f'  or header     : [dim]curl -k -H "x-api-key: <token>" {base_url}/pw/info/health[/]',
    ]


def smoke_curl_args(url: str, user: str = '', password: str = '') -> List[str]:    # /mitm-proxy chain check via mitmproxy-ext
    proxy = f'http://{user}:{password}@localhost:8080' if user else 'http://localhost:8080'
    return ['curl', '-sS', '--max-time', '15', '-o', '-',
            '-w', '\n[http %{http_code}]\n', '-x', proxy, url]


def remote_smoke_command(url: str) -> str:                                         # runs ON the EC2 box (SSM); reads creds from its .env
    return ('set -a; . /opt/content-proxy/.env 2>/dev/null; set +a; '
            "curl -sS --max-time 15 -w '\\n[http %{http_code}]\\n' "
            '-x "http://$CONTENT_PROXY__PROXYAUTH_USER:$CONTENT_PROXY__PROXYAUTH_PASS@localhost:8080" '
            + shlex.quote(url))


@local_app.command(name='up')
@spec_cli_errors
def local_up(detach  : bool = typer.Option(True, '--detach/--attach', '-d',
                                          help='Run detached (default) or attached.'),
             pull    : bool = typer.Option(False, '--pull',
                                          help='Pull the latest images first (up --pull always).'),
             recreate: bool = typer.Option(True, '--recreate/--no-recreate',
                                          help='Force-recreate containers so .env + the bind-mounted Caddyfile always take effect '
                                               '(docker compose does NOT recreate on bind-mount content changes). --no-recreate to skip.'),
             edge    : str  = typer.Option('none', '--edge',
                                          help='Front door: none (vault-as-edge) | caddy (dedicated edge, /pw routed, no vault patch).'),
             browsers: int  = typer.Option(0, '--browsers',
                                          help='Interactive sg-playwright-vnc browsers at /browser/{n} (forces --edge caddy; renders a generated compose+Caddyfile).'),
             browser_engine: str = typer.Option('chromium', '--browser-engine',
                                          help='Engine the interactive browsers autostart: chromium | firefox.')):
    """Bring the stack up locally (mitmweb by default → TUI /flows)."""
    c = Console(highlight=False)
    _ensure_env(c)
    if int(browsers) > 0:                                                            # fleet → render generated variants next to the committed files (same relative mounts)
        edge         = 'caddy'
        compose_file = write_generated_local_files(int(browsers), str(browser_engine))
        c.print(f'  [dim]rendered {compose_file.name} + {CADDYFILE_GENERATED.name} (browsers={browsers}, engine={browser_engine})[/]')
    else:
        compose_file = COMPOSE_FILE_CADDY if edge == 'caddy' else COMPOSE_FILE
    c.print(f'  [dim]docker compose up ({compose_file.name})[/]')
    up_args = ['up', '-d'] if detach else ['up']
    if recreate:                                                                      # bind-mounted Caddyfile / changed .env only load on (re)create
        up_args.append('--force-recreate')
    if pull:
        up_args += ['--pull', 'always']
    rc = _compose(*up_args, compose_file=compose_file)
    if rc.returncode == 0:
        c.print('  [green]✓[/]  stack up. /mitm-proxy smoke:  '
                '[cyan]curl -x http://localhost:8080 http://example.com/mitm-proxy[/]')
        if edge == 'caddy':
            c.print('     edge:  [cyan]https://localhost/[/]  ·  [cyan]https://localhost/pw/[/]  '
                    '[dim](Caddy internal CA → curl -k, or trust /data root)[/]')
            for i in range(1, int(browsers) + 1):
                c.print(f'     browser {i}: [cyan]https://localhost/browser/{i}/[/]  [dim](interactive noVNC)[/]')
        else:
            c.print('     vault front door: [cyan]https://localhost/[/]   (self-signed)')
        token = read_env_file(ENV_FILE).get('SGRAPH_SEND__ACCESS_TOKEN', '')         # vault + /pw need this (header or cookie)
        c.print()
        for line in auth_help_lines('https://localhost', token):
            c.print(line)
    raise typer.Exit(rc.returncode)


@local_app.command(name='down')
@spec_cli_errors
def local_down(volumes: bool = typer.Option(False, '--volumes', '-v', help='Also remove volumes.')):
    """Stop and clean up the local stack."""
    c = Console(highlight=False)
    c.print(f'  [dim]docker compose down ({COMPOSE_FILE})[/]')
    rc = _compose('down', '-v') if volumes else _compose('down')
    raise typer.Exit(rc.returncode)


@local_app.command(name='status')
@spec_cli_errors
def local_status():
    """Show the local stack containers (docker compose ps)."""
    raise typer.Exit(_compose('ps').returncode)


@local_app.command(name='ca')
@spec_cli_errors
def local_ca(pem: bool = typer.Option(False, '--pem', help='Print the PEM to stdout instead of the path.')):
    """Show the mitmproxy CA cert to import into a browser (Mode 1 trust).

    mitmproxy self-generates it into the mounted certs/ dir on first boot. Import
    the .pem into Firefox: Settings → Privacy & Security → Certificates → View
    Certificates → Authorities → Import → trust for websites.
    """
    c  = Console(highlight=False)
    ca = CERTS_DIR / 'mitmproxy-ca-cert.pem'
    if not ca.exists():
        c.print(f'  [yellow]⚠[/]  {ca} not found yet — run [cyan]sg content-proxy local up[/] first '
                '(mitmproxy generates it on boot).')
        raise typer.Exit(1)
    if pem:
        c.print(ca.read_text())
    else:
        c.print(f'  CA cert: [cyan]{ca}[/]')
        c.print('  [dim]Firefox: Settings → Privacy & Security → Certificates → View Certificates →[/]')
        c.print('  [dim]Authorities → Import → select this file → "Trust this CA to identify websites".[/]')


@local_app.command(name='pull')
@spec_cli_errors
def local_pull():
    """Pull the latest images for the stack (refresh diniscruz/* :latest)."""
    c = Console(highlight=False)
    c.print('  [dim]docker compose pull[/]')
    rc = _compose('pull')
    if rc.returncode == 0:
        c.print('  [green]✓[/]  images refreshed — now: [cyan]sg content-proxy local up[/]')
    raise typer.Exit(rc.returncode)


@local_app.command(name='logs')
@spec_cli_errors
def local_logs(service: Optional[str] = typer.Argument(None,
                          help='Service to tail (mitm-service / mitmproxy-ext / sg-playwright / …); all if omitted.'),
               follow : bool          = typer.Option(False, '--follow', '-f', help='Stream logs.'),
               tail   : int           = typer.Option(200,  '--tail', help='Lines from the end.')):
    """Tail docker compose logs for the local stack."""
    args = ['logs', '--tail', str(tail)]
    if follow:
        args.append('--follow')
    if service:
        args.append(service)
    raise typer.Exit(_compose(*args).returncode)


@local_app.command(name='smoke')
@spec_cli_errors
def local_smoke(url: str = typer.Option('http://example.com/mitm-proxy', '--url',
                          help='Target whose /mitm-proxy path proves the chain (host is irrelevant — always processed).')):
    """The /mitm-proxy chain check: curl through mitmproxy-ext → FastAPI injected UI.

    A 2xx with MITM-UI markup means mitmproxy → interceptor → FastAPI → browser all work.
    """
    c     = Console(highlight=False)
    env   = read_env_file(ENV_FILE)
    user  = env.get('CONTENT_PROXY__PROXYAUTH_USER', '')
    pwd   = env.get('CONTENT_PROXY__PROXYAUTH_PASS', '')
    args  = smoke_curl_args(url, user, pwd)
    c.print(f'  [dim]curl -x http://{user + "@" if user else ""}localhost:8080 {url}[/]')
    rc = subprocess.run(args)
    if rc.returncode == 0:
        c.print('  [green]✓[/]  proxy reachable. A 200 + MITM UI markup above = chain OK '
                '([yellow]503/fallback[/] = mitm-service still down).')
    else:
        c.print('  [red]✗[/]  could not reach mitmproxy-ext on :8080 — is the stack up? '
                '[dim](sg content-proxy local up)[/]')
    raise typer.Exit(rc.returncode)


app.add_typer(local_app, name='local')


# ── remote smoke (EC2, over SSM — no SSH) ───────────────────────────────────────

@app.command()
@spec_cli_errors
def smoke(name  : Optional[str] = typer.Argument(None,
                  help='Stack name; auto-selected when only one exists.'),
          region: str           = typer.Option(DEFAULT_REGION, '--region', '-r'),
          url   : str           = typer.Option('http://example.com/mitm-proxy', '--url',
                  help='Target whose /mitm-proxy path proves the chain (host irrelevant — always processed).')):
    """Run the /mitm-proxy chain check ON the EC2 box via SSM (no SSH).

    Reads the proxyauth creds from the box's /opt/content-proxy/.env and curls
    through mitmproxy-ext → FastAPI. A 2xx/3xx + MITM-UI markup means the whole
    chain works on the instance.
    """
    c    = Console(highlight=False)
    svc  = Content_Proxy__Service().setup()
    name = Spec__CLI__Builder(_cli_spec).resolver.resolve(svc, name, region, 'content_proxy')
    c.print(f'  [dim]ssm exec on {name} → curl …/mitm-proxy via mitmproxy-ext[/]')
    result = svc.exec(region, name, remote_smoke_command(url), timeout_sec=60)
    out = str(getattr(result, 'stdout', '') or '')
    c.print(out)
    ok = ('[http 2' in out or '[http 3' in out) and 'mitm-proxy' in out.lower()
    if ok:
        c.print('  [green]✓[/]  chain OK on the instance (mitmproxy → interceptor → FastAPI).')
    else:
        c.print('  [yellow]⚠[/]  no MITM-UI redirect seen — check [cyan]sg content-proxy exec <name> '
                'docker ps[/] and [cyan]… logs[/] (mitm-service up? scripts bucket reachable?).')


# ── remote logs (EC2, over SSM — no SSH) ────────────────────────────────────────

BOOT_LOG = '/var/log/sg-content-proxy-boot.log'                                     # must match Content_Proxy__User_Data__Builder.LOG_FILE


def _dlogs(container: str) -> str:                                                  # docker|podman logs template ({tail} filled at call time; container is fixed)
    return ('(docker logs --tail {tail} ' + container + ' 2>&1 || '
            'podman logs --tail {tail} ' + container + ' 2>&1) || true')


LOG_SOURCES = {                                                                     # name → (shell command template, ssm timeout, one-line description)
    'boot'         : (f'tail -n {{tail}} {BOOT_LOG}'            , 60, 'EC2 user-data boot script — stage markers, available within seconds'),
    'cloud-init'   : ('tail -n {tail} /var/log/cloud-init-output.log', 60, 'cloud-init full output — slightly behind the boot log'),
    'journal'      : ('journalctl -n {tail} --no-pager'        , 60, 'full systemd journal — always available'),
    'cert-init'    : (_dlogs('cp-cert-init')                   , 60, 'one-shot TLS cert sidecar — why it exited (self-signed gen / ACME issuance)'),
    'vault'        : (_dlogs('cp-vault-app')                   , 60, 'sg-send-vault container — vault UI + /pw proxy + :443 TLS'),
    'sg-playwright': (_dlogs('cp-sg-playwright')               , 60, 'sg-playwright container — the browser automation service'),
    'mitm-service' : (_dlogs('cp-mitm-service')                , 60, 'FastAPI MITM service — request/response transform decisions'),
    'mitmproxy-int': (_dlogs('cp-mitmproxy-int')               , 60, 'internal mitmproxy (Playwright path) — one line per proxied request'),
    'mitmproxy-ext': (_dlogs('cp-mitmproxy-ext')               , 60, 'external mitmproxy (human browser, Mode 1) — proxied requests + proxyauth'),
    'caddy'        : (_dlogs('cp-caddy')                       , 60, 'Caddy edge (--edge caddy only) — TLS/ACME issuance + /pw routing'),
    'browser-1'    : (_dlogs('cp-browser-1')                   , 60, 'interactive browser 1 (sg-playwright-vnc) — supervisord: xvfb/x11vnc/novnc/fastapi'),
    'browser-2'    : (_dlogs('cp-browser-2')                   , 60, 'interactive browser 2 — any browser-N works for larger fleets'),
}


BROWSER_SOURCE_RE = re.compile(r'^browser-(\d+)$')                                  # browser-N beyond the two listed → cp-browser-N (fleet size is a create-time choice)


def log_source_entry(source: str):                                                   # → (cmd_tpl, timeout, desc) | None — LOG_SOURCES plus the dynamic browser-N pattern
    if source in LOG_SOURCES:
        return LOG_SOURCES[source]
    m = BROWSER_SOURCE_RE.match(str(source or ''))
    if m:
        return (_dlogs(f'cp-browser-{m.group(1)}'), 60, f'interactive browser {m.group(1)} (sg-playwright-vnc)')
    return None


def resolve_log_source(name: Optional[str], source: str) -> tuple:                  # pure: a numeric positional is a source index (mirrors the prompt numbering)
    if name and str(name).isdigit():
        keys = list(LOG_SOURCES)
        idx  = int(name)
        if 1 <= idx <= len(keys):
            return (source or keys[idx - 1]), None                                  # name consumed as the index → auto-resolve the stack below
    return source, name


def _prompt_for_log_source(c: Console) -> str:
    c.print()
    c.print('  [bold]Which log source?[/]')
    keys = list(LOG_SOURCES)
    for i, k in enumerate(keys, 1):
        _, _, desc = LOG_SOURCES[k]
        c.print(f'    [cyan]{i}[/]  [bold]{k:13}[/] [dim]{desc}[/]')
    c.print()
    ans = typer.prompt('  Pick a number or name', default='boot').strip()
    if ans.isdigit() and 1 <= int(ans) <= len(keys):
        return keys[int(ans) - 1]
    if ans in LOG_SOURCES:
        return ans
    raise typer.BadParameter(f'unknown source {ans!r}; pick from: {", ".join(LOG_SOURCES)}')


@app.command(help='''Stream logs from the content-proxy EC2 host via SSM (no SSH).

\b
Sources (pick with --source / -s, a positional index, or omit to be prompted):
  boot          EC2 user-data boot script — stage markers
  cloud-init    cloud-init full output
  journal       full systemd journal
  cert-init     one-shot TLS cert sidecar — ACME/self-signed issuance (TLS stacks)
  vault         sg-send-vault container — vault UI + /pw + :443
  sg-playwright sg-playwright container — browser automation
  mitm-service  FastAPI MITM service — transform decisions
  mitmproxy-int internal mitmproxy (Playwright path)
  mitmproxy-ext external mitmproxy (human browser, Mode 1)
  caddy         Caddy edge (--edge caddy only)

\b
Add --follow / -f to poll for new lines every few seconds (Ctrl-C to stop).
''')
@spec_cli_errors
def logs(name  : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
         tail  : int           = typer.Option(30,    '--tail', '-n',   help='Number of log lines to fetch.'),
         follow: bool          = typer.Option(False, '--follow', '-f', help='Poll for new lines every few seconds (Ctrl-C to stop).'),
         source: str           = typer.Option('',    '--source', '-s',
                  help='boot | cloud-init | journal | cert-init | vault | sg-playwright | mitm-service | mitmproxy-int | mitmproxy-ext | caddy. Omit to be prompted.'),
         region: str           = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """Stream logs from the stack host via SSM (no SSH)."""
    import time
    c = Console(highlight=False)

    source, name = resolve_log_source(name, source)                                 # 'sg cp logs 4' → cert-init index
    if not source:
        source = _prompt_for_log_source(c)
    entry = log_source_entry(source)                                                # LOG_SOURCES + the dynamic browser-N pattern
    if entry is None:
        raise typer.BadParameter(f'unknown source {source!r}; pick from: {", ".join(LOG_SOURCES)} (or browser-N)')

    cmd_tpl, timeout, _desc = entry
    svc        = Content_Proxy__Service().setup()
    name       = Spec__CLI__Builder(_cli_spec).resolver.resolve(svc, name, region, 'content_proxy')
    others     = '  '.join(k for k in LOG_SOURCES if k != source)
    fetch_tail = max(tail, 500) if follow else tail
    ssm_cmd    = cmd_tpl.format(tail=fetch_tail)

    c.print(f'  [bold]{source}[/] [dim]──  other sources: {others}[/]')
    c.print(f'  [dim]via SSM:[/] [cyan]{ssm_cmd}[/]')
    if follow:
        c.print('  [dim]following — Ctrl-C to stop[/]')
    c.print()

    def fetch():
        r = svc.exec(region, name, ssm_cmd, timeout_sec=timeout)
        return str(getattr(r, 'stdout', '') or '').splitlines()

    if not follow:
        c.print('\n'.join(fetch()))
        return

    shown_anchor = ''                                                               # last printed line — used to find new content each poll
    try:
        while True:
            lines = fetch()
            if not shown_anchor:
                for line in lines:
                    c.print(line)
                shown_anchor = lines[-1] if lines else ''
            else:
                idx = next((i for i in range(len(lines) - 1, -1, -1)
                            if lines[i] == shown_anchor), None)
                new_lines = lines[idx + 1:] if idx is not None else lines
                for line in new_lines:
                    c.print(line)
                if new_lines:
                    shown_anchor = new_lines[-1]
            time.sleep(4)
    except KeyboardInterrupt:
        c.print('\n  [dim]stopped[/]')


# ── check / wait: unified boot checklist + external HTTP probe ───────────────────
# Both commands drive Content_Proxy__Service.diagnose() + an external svc.health()
# probe through the SHARED Spec__Diagnose__Renderer (sg_compute/cli/base) — the same
# renderer `create --wait` now uses via Spec__CLI__Builder._wait_healthy. `check`
# runs once; `wait` loops until every row is ok/skip or the timeout expires. The
# spec-specific bits (check order, `sg cp logs --source <x>` hints) are the
# module-level DIAGNOSE_* constants carried on _cli_spec, kept out of shared code.

from sg_compute.cli.base import Spec__Diagnose__Renderer as _diag                    # noqa: E402


@app.command()
@spec_cli_errors
def check(name  : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
          region: str           = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """Run the full stack boot checklist and show one row per check.

    \b
    Checks (in order):
      ec2-state         EC2 instance is in running state
      ssm-reachable     SSM exec can reach the instance
      boot-failed       boot log shows no failure markers
      container-engine  docker service is active
      containers-up     the cp-* compose containers are running
      cert-init         TLS stacks only — cp-cert-init exit state (self-signed / ACME)
      vault-http        :443 responds from inside the host (via SSM)
      boot-ok           boot log reached '[content-proxy] boot complete'
      external-http     vault serving (svc.health SSM probe)
    """
    c    = Console(highlight=False)
    svc  = Content_Proxy__Service().setup()
    name = Spec__CLI__Builder(_cli_spec).resolver.resolve(svc, name, region, 'content_proxy')
    rows = _diag.run_once(svc, region, name, console=c,
                          check_order        = DIAGNOSE_CHECK_ORDER,
                          hints              = DIAGNOSE_HINTS       ,
                          log_command_prefix = DIAGNOSE_LOG_PREFIX  ,
                          valid_sources      = set(LOG_SOURCES)     )
    if any(s == 'fail' for _, s, _ in rows):
        raise typer.Exit(1)


@app.command()
@spec_cli_errors
def wait(name   : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
         region : str           = typer.Option(DEFAULT_REGION, '--region', '-r'),
         timeout: int           = typer.Option(600, '--timeout', '-t',
                                               help='Max seconds to wait before giving up.'),
         poll   : int           = typer.Option(15, '--poll', '-p',
                                               help='Seconds between re-runs of the full checklist.')):
    """Re-run the check table on a loop until every row is OK (or timeout).

    \b
    The same diagnose generator that powers `check` runs in a loop, updating the
    Live table in place — letting the operator watch boot progress through each
    stage (engine install → containers up → cert-init → vault HTTP) instead of a
    silent external probe. Especially useful for TLS/cert issuance debugging.
    """
    c    = Console(highlight=False)
    svc  = Content_Proxy__Service().setup()
    name = Spec__CLI__Builder(_cli_spec).resolver.resolve(svc, name, region, 'content_proxy')
    _rows, all_ok = _diag.run_until_ok(svc, region, name, console=c,
                                       check_order        = DIAGNOSE_CHECK_ORDER,
                                       timeout            = timeout             ,
                                       poll               = poll                ,
                                       hints              = DIAGNOSE_HINTS       ,
                                       log_command_prefix = DIAGNOSE_LOG_PREFIX  ,
                                       valid_sources      = set(LOG_SOURCES)     )
    if not all_ok:
        raise typer.Exit(1)

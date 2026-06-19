# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Cli__Content_Proxy
# Builder-driven CLI (8 standard verbs from Spec__CLI__Builder) + extras:
#   - local up|down|status  : run/stop/inspect the stack locally via docker compose
# Mounted in sg_compute/cli/Cli__SG.py as `sg content-proxy` (alias `cp`).
# ═══════════════════════════════════════════════════════════════════════════════

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
ENV_FILE          = COMPOSE_DIR / '.env'
ENV_EXAMPLE       = COMPOSE_DIR / '.env.example'


def _set_extras(request, mode='direct_proxy', tls='none', edge='none', hostname='',
                with_aws_dns=False, proxy_tool='mitmdump',
                proxyauth_user='', proxyauth_pass='', proxy_ca_cert='', proxy_ca_key='',
                scripts_bucket='', forward_aws_creds=False, env_file='', ca_from_local=False,
                use_spot=True, disk_size=0, mitm_service_image=''):
    if env_file:                                                                     # MVP: ship a full .env verbatim to the box
        request.env_inline = Path(env_file).read_text()
    if ca_from_local:                                                                # reuse the local docker mitmproxy CA (already trusted in your browser)
        ca = COMPOSE_DIR / 'certs' / 'mitmproxy-ca.pem'
        if not ca.exists():
            raise FileNotFoundError(f'{ca} not found — run `sg content-proxy local up` once to generate it')
        request.proxy_ca_pem = ca.read_text()
    request.mode              = Enum__Content_Proxy__Mode(mode)
    request.tls               = Enum__Content_Proxy__Tls(tls)
    request.edge              = Enum__Content_Proxy__Edge(edge)
    request.hostname          = hostname
    request.with_aws_dns      = bool(with_aws_dns)
    if hostname or with_aws_dns:                                                     # a public hostname requires the Caddy edge (auto-ACME)
        request.edge          = Enum__Content_Proxy__Edge.CADDY
    request.proxy_tool        = Enum__Content_Proxy__Proxy__Tool(proxy_tool)
    request.proxyauth_user    = proxyauth_user
    request.proxyauth_pass    = proxyauth_pass
    request.proxy_ca_cert     = proxy_ca_cert
    request.proxy_ca_key      = proxy_ca_key
    request.scripts_bucket    = scripts_bucket
    request.forward_aws_creds = bool(forward_aws_creds)
    request.use_spot          = bool(use_spot)
    request.disk_size_gb      = int(disk_size)
    if mitm_service_image:
        request.mitm_service_image = mitm_service_image


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
    post_launch_fn             = _content_proxy_post_launch          )


app = Spec__CLI__Builder(
    cli_spec             = _cli_spec,
    extra_create_options = [
        ('mode'          , str , 'direct_proxy', 'direct_proxy (NLB) or vault_web (ALB).'),
        ('tls'           , str , 'none'        , 'Vault TLS on :443 — none | self-signed (IP, browser warns) | letsencrypt (real IP cert, opens :80) | acm (ALB, not wired). Ignored when --edge caddy (the edge terminates TLS).'),
        ('edge'          , str , 'none'        , 'Front door: none (vault-as-edge) | caddy (dedicated edge owns :443, /pw routed, vault is a plain origin). --hostname/--with-aws-dns force caddy.'),
        ('hostname'      , str , ''            , 'Public FQDN for the Caddy edge (e.g. my-stack.sg-compute.sgraph.ai) — Caddy does auto-ACME for a real trusted cert (opens :80+:443 to the world). Implies --edge caddy.'),
        ('with_aws_dns'  , bool, False         , 'Auto-create the Route 53 A record <stack>.sg-compute.sgraph.ai → public IP at create (reuses the sg va flow). Implies --edge caddy + a derived hostname.'),
        ('proxy_tool'    , str , 'mitmdump'    , 'mitmweb (dev, TUI /flows, in-memory) or mitmdump (prod, headless).'),
        ('proxyauth_user', str , ''            , 'mitmproxy-ext basic-auth user (Mode 1).'),
        ('proxyauth_pass', str , ''            , 'mitmproxy-ext basic-auth pass (Mode 1).'),
        ('proxy_ca_cert' , str , ''            , 'Path to the user-supplied proxy CA cert (Mode 1 browser trust).'),
        ('proxy_ca_key'  , str , ''            , 'Path to the user-supplied proxy CA key.'),
        ('env_file'      , str , ''            , 'Path to a full .env shipped verbatim to the box (MVP: overrides generated env — ship your working local .env).'),
        ('ca_from_local' , bool, False         , 'Ship the local docker mitmproxy CA (docker/compose/certs/mitmproxy-ca.pem) so the EC2 proxy uses the CA already trusted in your browser.'),
        ('scripts_bucket', str , ''            , 'S3 bucket the MITM service reads injection scripts from (CACHE__SERVICE__BUCKET_NAME).'),
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


def _needs_value(v: str) -> bool:                                                  # blank or the shipped placeholder ⇒ generate
    return (v or '').strip() in ('', PLACEHOLDER_VALUE)


def realize_secrets(env: dict) -> dict:                                            # → {key: new_value} for keys that must change
    updates = {}
    real_token = next((env[k] for k in ACCESS_TOKEN_KEYS if not _needs_value(env.get(k, ''))), '')
    if any(_needs_value(env.get(k, '')) for k in ACCESS_TOKEN_KEYS):               # keep the pair coupled to one GUID
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
def local_up(detach: bool = typer.Option(True, '--detach/--attach', '-d',
                                         help='Run detached (default) or attached.'),
             pull  : bool = typer.Option(False, '--pull',
                                         help='Pull the latest images first (up --pull always).'),
             edge  : str  = typer.Option('none', '--edge',
                                         help='Front door: none (vault-as-edge) | caddy (dedicated edge, /pw routed, no vault patch).')):
    """Bring the stack up locally (mitmweb by default → TUI /flows)."""
    c = Console(highlight=False)
    _ensure_env(c)
    compose_file = COMPOSE_FILE_CADDY if edge == 'caddy' else COMPOSE_FILE
    c.print(f'  [dim]docker compose up ({compose_file.name})[/]')
    up_args = ['up', '-d'] if detach else ['up']
    if pull:
        up_args += ['--pull', 'always']
    rc = _compose(*up_args, compose_file=compose_file)
    if rc.returncode == 0:
        c.print('  [green]✓[/]  stack up. /mitm-proxy smoke:  '
                '[cyan]curl -x http://localhost:8080 http://example.com/mitm-proxy[/]')
        if edge == 'caddy':
            c.print('     edge:  [cyan]https://localhost/[/]  ·  [cyan]https://localhost/pw/[/]  '
                    '[dim](Caddy internal CA → curl -k, or trust /data root)[/]')
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

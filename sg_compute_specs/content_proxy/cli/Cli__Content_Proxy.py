# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Cli__Content_Proxy
# Builder-driven CLI (8 standard verbs from Spec__CLI__Builder) + extras:
#   - local up|down|status  : run/stop/inspect the stack locally via docker compose
# Mounted in sg_compute/cli/Cli__SG.py as `sg content-proxy` (alias `cp`).
# ═══════════════════════════════════════════════════════════════════════════════

import subprocess
from pathlib       import Path
from typing        import List, Optional

import typer
from rich.console  import Console

from sg_compute.cli.base.Schema__Spec__CLI__Spec import Schema__Spec__CLI__Spec
from sg_compute.cli.base.Spec__CLI__Builder      import Spec__CLI__Builder
from sg_compute.cli.base.Spec__CLI__Errors       import spec_cli_errors

from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Mode        import Enum__Content_Proxy__Mode
from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Proxy__Tool import Enum__Content_Proxy__Proxy__Tool
from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Tls         import Enum__Content_Proxy__Tls
from sg_compute_specs.content_proxy.schemas.Schema__Content_Proxy__Create__Request import Schema__Content_Proxy__Create__Request
from sg_compute_specs.content_proxy.service.Content_Proxy__Service                  import Content_Proxy__Service


# ── committed local compose (the `docker compose up` target) ────────────────────
import sg_compute_specs.content_proxy as _pkg
COMPOSE_DIR  = Path(_pkg.__file__).parent / 'docker' / 'compose'
COMPOSE_FILE = COMPOSE_DIR / 'docker-compose.yml'
ENV_FILE     = COMPOSE_DIR / '.env'
ENV_EXAMPLE  = COMPOSE_DIR / '.env.example'


def _set_extras(request, mode='direct_proxy', tls='none', proxy_tool='mitmdump',
                proxyauth_user='', proxyauth_pass='', proxy_ca_cert='', proxy_ca_key='',
                use_spot=True, disk_size=0, mitm_service_image=''):
    request.mode           = Enum__Content_Proxy__Mode(mode)
    request.tls            = Enum__Content_Proxy__Tls(tls)
    request.proxy_tool     = Enum__Content_Proxy__Proxy__Tool(proxy_tool)
    request.proxyauth_user = proxyauth_user
    request.proxyauth_pass = proxyauth_pass
    request.proxy_ca_cert  = proxy_ca_cert
    request.proxy_ca_key   = proxy_ca_key
    request.use_spot       = bool(use_spot)
    request.disk_size_gb   = int(disk_size)
    if mitm_service_image:
        request.mitm_service_image = mitm_service_image


_cli_spec = Schema__Spec__CLI__Spec(
    spec_id               = 'content_proxy'                          ,
    display_name          = 'Content-Transformation Proxy'           ,
    default_instance_type = 't3.large'                               ,
    create_request_cls    = Schema__Content_Proxy__Create__Request   ,
    service_factory       = lambda: Content_Proxy__Service().setup() ,
    health_path           = '/'                                      ,
    health_port           = 443                                      ,
    health_scheme         = 'https'                                  ,
    extra_create_field_setters = _set_extras                         )


app = Spec__CLI__Builder(
    cli_spec             = _cli_spec,
    extra_create_options = [
        ('mode'          , str , 'direct_proxy', 'direct_proxy (NLB) or vault_web (ALB).'),
        ('tls'           , str , 'none'        , 'EC2 TLS: none | letsencrypt | acm.'),
        ('proxy_tool'    , str , 'mitmdump'    , 'mitmweb (dev, TUI /flows, in-memory) or mitmdump (prod, headless).'),
        ('proxyauth_user', str , ''            , 'mitmproxy-ext basic-auth user (Mode 1).'),
        ('proxyauth_pass', str , ''            , 'mitmproxy-ext basic-auth pass (Mode 1).'),
        ('proxy_ca_cert' , str , ''            , 'Path to the user-supplied proxy CA cert (Mode 1 browser trust).'),
        ('proxy_ca_key'  , str , ''            , 'Path to the user-supplied proxy CA key.'),
        ('use_spot'      , bool, True          , 'Spot instance (~70%% cheaper). --no-use-spot for on-demand.'),
        ('disk_size'     , int , 0             , 'Root volume GiB. 0 = AMI default.'),
        # ── advanced ──
        ('mitm_service_image', str, '', 'Override the MITM service image (default diniscruz/mgraph-ai-service-mitmproxy).', True),
    ],
).build()


# ── local lifecycle (docker compose) ───────────────────────────────────────────

local_app = typer.Typer(no_args_is_help=True,
                        help='Run the content-proxy stack locally via docker compose.')


CERTS_DIR = COMPOSE_DIR / 'certs'


def _ensure_env(c: Console) -> None:
    if not ENV_FILE.exists():
        ENV_FILE.write_text(ENV_EXAMPLE.read_text())
        c.print(f'  [yellow]⚠[/]  created {ENV_FILE} from .env.example — edit the secrets before any real use')
    if not CERTS_DIR.exists():                                                       # mitmproxy self-generates its CA here (rw mount)
        CERTS_DIR.mkdir(parents=True, exist_ok=True)
        CERTS_DIR.chmod(0o777)                                                       # container user (uid 1000) must be able to write


def _compose(*args: str):
    return subprocess.run(['docker', 'compose', '--env-file', str(ENV_FILE),
                           '-f', str(COMPOSE_FILE), *args])


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


def smoke_curl_args(url: str, user: str = '', password: str = '') -> List[str]:    # /mitm-proxy chain check via mitmproxy-ext
    proxy = f'http://{user}:{password}@localhost:8080' if user else 'http://localhost:8080'
    return ['curl', '-sS', '--max-time', '15', '-o', '-',
            '-w', '\n[http %{http_code}]\n', '-x', proxy, url]


@local_app.command(name='up')
@spec_cli_errors
def local_up(detach: bool = typer.Option(True, '--detach/--attach', '-d',
                                         help='Run detached (default) or attached.'),
             pull  : bool = typer.Option(False, '--pull',
                                         help='Pull the latest images first (up --pull always).')):
    """Bring the 5-service stack up locally (mitmweb by default → TUI /flows)."""
    c = Console(highlight=False)
    _ensure_env(c)
    c.print(f'  [dim]docker compose up ({COMPOSE_FILE})[/]')
    up_args = ['up', '-d'] if detach else ['up']
    if pull:
        up_args += ['--pull', 'always']
    rc = _compose(*up_args)
    if rc.returncode == 0:
        c.print('  [green]✓[/]  stack up. Try the /mitm-proxy smoke:')
        c.print('     [cyan]curl -x http://localhost:8080 http://example.com/mitm-proxy[/]')
        c.print('     vault front door: [cyan]https://localhost/[/]   (self-signed)')
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

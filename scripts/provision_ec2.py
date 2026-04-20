# ═══════════════════════════════════════════════════════════════════════════════
# SG Playwright — provision_ec2.py (v0.1.33 — two-container EC2 stack)
#
# Provisions an EC2 instance running the full Playwright + agent_mitmproxy
# two-container stack via docker compose. Replaces the separate per-image
# spike scripts (provision_ec2.py v0.1.31 + provision_mitmproxy_ec2.py).
#
# What it does:
#   1. Ensures an IAM role + instance profile with ECR read + SSM access.
#   2. Ensures a security group allowing :8000 (Playwright API) and :8001
#      (sidecar admin API) ingress. The sidecar proxy (:8080) stays on the
#      Docker bridge — never exposed to the host.
#   3. Runs a t3.large AL2023 instance. UserData installs Docker + the Compose
#      plugin, logs into ECR, pulls both images, writes docker-compose.yml and
#      runs `docker compose up -d`.
#   4. Waits for the instance to reach `running`, prints both service URLs.
#
# Cleanup: re-run with --terminate. The SG + IAM role survive between runs
# (idempotent re-create). Delete them manually when the stack is fully torn down.
#
# Direct boto3 use — same narrow exception as earlier versions: osbot_aws
# EC2.instance_create() does not expose the UserData kwarg.
#
# Cost note: t3.large on-demand is ~$0.083/h. Always --terminate when done.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import secrets
import sys
import textwrap
import time
from typing import Optional

import requests
import typer
from rich.console import Console
from rich.panel   import Panel
from rich.table   import Table

from osbot_aws.AWS_Config                                                                import AWS_Config
from osbot_aws.aws.ec2.EC2                                                               import EC2
from osbot_aws.aws.iam.IAM_Role                                                          import IAM_Role
from osbot_utils.utils.Env                                                               import get_env

from sgraph_ai_service_playwright.docker.Docker__SGraph_AI__Service__Playwright__Base    import IMAGE_NAME as PLAYWRIGHT_IMAGE_NAME
from agent_mitmproxy.docker.Docker__Agent_Mitmproxy__Base                                import IMAGE_NAME as SIDECAR_IMAGE_NAME


EC2__INSTANCE_TYPE           = 't3.large'                                               # 2 vCPU / 8 GB RAM — Playwright + sidecar fit; Firefox + WebKit need the headroom
EC2__AMI_NAME_AL2023         = 'al2023-ami-2023.*-x86_64'
EC2__AMI_OWNER_AMAZON        = 'amazon'
EC2__PLAYWRIGHT_PORT         = 8000                                                     # Playwright API — exposed to the world via SG
EC2__SIDECAR_ADMIN_PORT      = 8001                                                     # Sidecar admin API (host port mapping of container :8000) — exposed via SG, API-key gated

WATCHDOG_MAX_REQUEST_MS      = 120_000                                                  # 120s — covers Firefox + long upstream-proxy round-trips

IAM__ROLE_NAME               = 'playwright-ec2'                                         # AWS reserves 'sg-*' prefix — applies to SG names, IAM instance profiles, and resource tags
IAM__ECR_READONLY_POLICY_ARN = 'arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly'
IAM__SSM_CORE_POLICY_ARN     = 'arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore'  # SSM session manager — no SSH needed
IAM__POLICY_ARNS             = (IAM__ECR_READONLY_POLICY_ARN, IAM__SSM_CORE_POLICY_ARN)
IAM__ASSUME_ROLE_SERVICE     = 'ec2.amazonaws.com'

SG__NAME                     = 'playwright-ec2'                                         # AWS reserves 'sg-*' prefix for SG IDs
SG__DESCRIPTION              = 'SG Playwright EC2 stack - ingress :8000 (API) + :8001 (sidecar admin)'

TAG__NAME                    = 'playwright-ec2'
TAG__STAGE_KEY               = 'stage'
TAG__NICKNAME_KEY            = 'sg:nickname'                                            # Human-readable label; used by connect/delete to target a specific instance
DEFAULT_STAGE                = 'dev'


COMPOSE_YAML_TEMPLATE = textwrap.dedent("""\
    services:

      playwright:
        image: {playwright_image_uri}
        ports:
          - "{playwright_port}:{playwright_port}"
        environment:
          FAST_API__AUTH__API_KEY__NAME:          '{api_key_name}'
          FAST_API__AUTH__API_KEY__VALUE:         '{api_key_value}'
          SG_PLAYWRIGHT__DEPLOYMENT_TARGET:       container
          SG_PLAYWRIGHT__DEFAULT_PROXY_URL:       http://agent-mitmproxy:8080
          SG_PLAYWRIGHT__IGNORE_HTTPS_ERRORS:     'true'
          SG_PLAYWRIGHT__WATCHDOG_MAX_REQUEST_MS: {watchdog_max_request_ms}
        networks:
          - sg-net
        depends_on:
          - agent-mitmproxy
        restart: always

      agent-mitmproxy:
        image: {sidecar_image_uri}
        ports:
          - "{sidecar_admin_port}:8000"
        environment:
          FAST_API__AUTH__API_KEY__NAME:  '{api_key_name}'
          FAST_API__AUTH__API_KEY__VALUE: '{api_key_value}'
          AGENT_MITMPROXY__UPSTREAM_URL:  '{upstream_url}'
          AGENT_MITMPROXY__UPSTREAM_USER: '{upstream_user}'
          AGENT_MITMPROXY__UPSTREAM_PASS: '{upstream_pass}'
        networks:
          - sg-net
        restart: always

    networks:
      sg-net:
        driver: bridge
""")


USER_DATA_TEMPLATE = """\
#!/bin/bash
set -euxo pipefail

dnf install -y docker docker-compose-plugin
systemctl enable --now docker

TOKEN=$(aws ecr get-login-password --region {region})
echo "$TOKEN" | docker login --username AWS --password-stdin {registry}

docker pull {playwright_image_uri}
docker pull {sidecar_image_uri}

mkdir -p /opt/sg-playwright

cat > /opt/sg-playwright/docker-compose.yml << 'SG_COMPOSE_EOF'
{compose_content}
SG_COMPOSE_EOF

docker compose -f /opt/sg-playwright/docker-compose.yml up -d
"""


def aws_account_id() -> str:
    return AWS_Config().aws_session_account_id()


def aws_region() -> str:
    return AWS_Config().aws_session_region_name()


def ecr_registry_host() -> str:
    return f'{aws_account_id()}.dkr.ecr.{aws_region()}.amazonaws.com'


def default_playwright_image_uri() -> str:
    return f'{ecr_registry_host()}/{PLAYWRIGHT_IMAGE_NAME}:latest'


def default_sidecar_image_uri() -> str:
    return f'{ecr_registry_host()}/{SIDECAR_IMAGE_NAME}:latest'


def preflight_check(playwright_image_uri: str = None, sidecar_image_uri: str = None) -> dict:
    """Validate AWS credentials + resolve config. Prints a summary and exits on failure."""
    errors   = []
    warnings = []

    # ── AWS credentials ───────────────────────────────────────────────────────
    _CREDS_HELP = [
        'AWS credentials not found or not valid.',
        '',
        'Provide credentials via one of:',
        '  export AWS_ACCESS_KEY_ID=...    AWS_SECRET_ACCESS_KEY=...    AWS_DEFAULT_REGION=...',
        '  export AWS_PROFILE=<profile>    (uses ~/.aws/credentials)',
        '  aws configure                   (interactive)',
    ]
    try:
        account = aws_account_id()
        region  = aws_region()
    except Exception as exc:
        _print_preflight_error(_CREDS_HELP + ['', f'  Error: {exc}'])

    if not account:                                                                      # AWS_Config returns None (not an exception) when STS call fails
        _print_preflight_error(_CREDS_HELP)

    registry = ecr_registry_host()

    resolved_playwright = playwright_image_uri or f'{registry}/{PLAYWRIGHT_IMAGE_NAME}:latest'
    resolved_sidecar    = sidecar_image_uri    or f'{registry}/{SIDECAR_IMAGE_NAME}:latest'

    # ── API key ───────────────────────────────────────────────────────────────
    api_key_name  = get_env('FAST_API__AUTH__API_KEY__NAME' ) or 'X-API-Key'
    api_key_value = get_env('FAST_API__AUTH__API_KEY__VALUE')
    if not api_key_value:
        api_key_value = secrets.token_urlsafe(32)
        warnings.append(f'FAST_API__AUTH__API_KEY__VALUE not set — generated a random key for this deployment: {api_key_value}')

    # ── Upstream forwarding (optional) ────────────────────────────────────────
    upstream_url  = get_env('AGENT_MITMPROXY__UPSTREAM_URL' ) or ''
    upstream_user = get_env('AGENT_MITMPROXY__UPSTREAM_USER') or ''
    upstream_pass = get_env('AGENT_MITMPROXY__UPSTREAM_PASS') or ''
    if upstream_url and not (upstream_user and upstream_pass):
        errors.append('AGENT_MITMPROXY__UPSTREAM_URL is set but UPSTREAM_USER/PASS are missing — sidecar will try unauthenticated upstream.')

    # ── Print summary ─────────────────────────────────────────────────────────
    _print_preflight_summary(account, region, registry,
                             resolved_playwright, resolved_sidecar,
                             api_key_name, api_key_value,
                             upstream_url, upstream_user, upstream_pass,
                             warnings, errors)
    return {'account': account, 'region': region, 'registry': registry, 'api_key_value': api_key_value}


def _kv_table(*rows) -> Table:
    t = Table(box=None, show_header=False, padding=(0, 2), expand=False)
    t.add_column(style='dim white', min_width=12, no_wrap=True)
    t.add_column(style='white')
    for k, v in rows:
        t.add_row(k, str(v))
    return t


def _print_preflight_summary(account, region, registry,
                              playwright_uri, sidecar_uri,
                              api_key_name, api_key_value,
                              upstream_url, upstream_user, upstream_pass,
                              warnings, errors) -> None:
    c = Console(highlight=False, width=200)

    c.print(Panel('[bold white] 🎭  SG Playwright EC2 Provisioner[/]  ·  [dim]preflight check[/]',
                  border_style='bright_blue', expand=False))
    c.print()

    c.print('  [bold bright_cyan]☁️  AWS[/]')
    c.print(_kv_table(('account',  account ),
                      ('region',   region  ),
                      ('registry', registry)))
    c.print()

    c.print('  [bold bright_cyan]🐳  Images[/]')
    c.print(_kv_table(('🎭 playwright', playwright_uri),
                      ('🔭 sidecar',    sidecar_uri   )))
    c.print()

    c.print('  [bold bright_cyan]🔑  API key[/]')
    c.print(_kv_table(('name',  api_key_name                         ),
                      ('value', f'[bold green]{api_key_value}[/bold green]')))
    c.print()

    if upstream_url:
        c.print('  [bold bright_cyan]🌐  Upstream forwarding[/]')
        c.print(_kv_table(('url',  upstream_url                                              ),
                          ('user', '[green](set)[/]' if upstream_user else '[red](not set)[/]'),
                          ('pass', '[green](set)[/]' if upstream_pass else '[red](not set)[/]')))
    else:
        c.print('  [bold bright_cyan]🌐  Upstream[/]  [dim]none — sidecar runs in direct mode[/]')
    c.print()

    c.print(f'  [bold bright_cyan]⚙️  Stack[/]   [dim]t3.large · AL2023 · '
            f'IAM={IAM__ROLE_NAME} · SG={SG__NAME} · tag={TAG__NAME}[/]')
    c.print()

    c.print('  [bold bright_cyan]🔌  Ports[/]')
    c.print(_kv_table((f':{EC2__PLAYWRIGHT_PORT}',    f'playwright API       [dim](public)[/]'         ),
                      (f':{EC2__SIDECAR_ADMIN_PORT}', f'sidecar admin API    [dim](public)[/]'         ),
                      (':8080',                        '[dim]mitmproxy proxy   (Docker-network-only)[/]')))
    c.print()

    for w in warnings:
        c.print(f'  [bold yellow]⚠️  [/][yellow]{w}[/]')
    if warnings:
        c.print()

    for e in errors:
        c.print(f'  [bold red]✗  [/][red]{e}[/]')
    if errors:
        c.print()


def _print_preflight_error(lines: list) -> None:
    c = Console(highlight=False, stderr=True)
    c.print(Panel('\n'.join(lines), title='[bold red]ERROR[/]', border_style='red', expand=False))
    sys.exit(1)


def ensure_instance_profile() -> str:
    role = IAM_Role(role_name=IAM__ROLE_NAME)
    if role.not_exists():
        role.create_for_service__assume_role(IAM__ASSUME_ROLE_SERVICE)
    # Always ensure the instance profile exists and the role is attached —
    # these calls are idempotent: catch EntityAlreadyExists / LimitExceeded
    # so a partial previous run doesn't leave the profile missing.
    try:
        role.create_instance_profile()
    except Exception:
        pass
    try:
        role.add_to_instance_profile()
    except Exception:
        pass
    for policy_arn in IAM__POLICY_ARNS:
        role.iam.role_policy_attach(policy_arn)
    return IAM__ROLE_NAME


def ensure_security_group(ec2: EC2) -> str:
    existing = ec2.security_group(security_group_name=SG__NAME)
    if existing:
        return existing.get('GroupId')
    create_result     = ec2.security_group_create(security_group_name=SG__NAME, description=SG__DESCRIPTION)
    security_group_id = create_result.get('data', {}).get('security_group_id')
    ec2.security_group_authorize_ingress(security_group_id=security_group_id, port=EC2__PLAYWRIGHT_PORT)    # :8000 — Playwright API
    ec2.security_group_authorize_ingress(security_group_id=security_group_id, port=EC2__SIDECAR_ADMIN_PORT) # :8001 — sidecar admin API
    return security_group_id


def latest_al2023_ami_id(ec2: EC2) -> str:
    images = ec2.amis(owner=EC2__AMI_OWNER_AMAZON, name=EC2__AMI_NAME_AL2023, architecture='x86_64')
    images = sorted(images, key=lambda image: image.get('CreationDate', ''), reverse=True)
    if not images:
        raise RuntimeError(f'No AL2023 AMI found matching {EC2__AMI_NAME_AL2023!r} in region {aws_region()!r}')
    return images[0].get('ImageId')


def render_compose_yaml(playwright_image_uri : str,
                         sidecar_image_uri    : str,
                         api_key_name         : str,
                         api_key_value        : str,
                         upstream_url         : str = '',
                         upstream_user        : str = '',
                         upstream_pass        : str = '',
                         watchdog_max_request_ms: int = WATCHDOG_MAX_REQUEST_MS) -> str:
    return COMPOSE_YAML_TEMPLATE.format(playwright_image_uri    = playwright_image_uri    ,
                                        sidecar_image_uri       = sidecar_image_uri       ,
                                        playwright_port         = EC2__PLAYWRIGHT_PORT    ,
                                        sidecar_admin_port      = EC2__SIDECAR_ADMIN_PORT ,
                                        api_key_name            = api_key_name            ,
                                        api_key_value           = api_key_value           ,
                                        upstream_url            = upstream_url            ,
                                        upstream_user           = upstream_user           ,
                                        upstream_pass           = upstream_pass           ,
                                        watchdog_max_request_ms = watchdog_max_request_ms )


def render_user_data(playwright_image_uri : str,
                      sidecar_image_uri    : str,
                      compose_content      : str) -> str:
    return USER_DATA_TEMPLATE.format(region               = aws_region()           ,
                                     registry             = ecr_registry_host()    ,
                                     playwright_image_uri = playwright_image_uri   ,
                                     sidecar_image_uri    = sidecar_image_uri      ,
                                     compose_content      = compose_content        )


def run_instance(ec2: EC2, ami_id: str, security_group_id: str, instance_profile_name: str, user_data: str, stage: str, nickname: str = '') -> str:
    tags = [{'Key': 'Name', 'Value': TAG__NAME}, {'Key': TAG__STAGE_KEY, 'Value': stage}]
    if nickname:
        tags.append({'Key': TAG__NICKNAME_KEY, 'Value': nickname})
    kwargs = {'ImageId'           : ami_id                                                  ,
              'InstanceType'      : EC2__INSTANCE_TYPE                                      ,
              'MinCount'          : 1                                                       ,
              'MaxCount'          : 1                                                       ,
              'IamInstanceProfile': {'Name': instance_profile_name}                         ,
              'SecurityGroupIds'  : [security_group_id]                                     ,
              'UserData'          : user_data                                               ,
              'TagSpecifications' : [{'ResourceType': 'instance', 'Tags': tags}]            }
    for attempt in range(5):
        try:
            result      = ec2.client().run_instances(**kwargs)
            instance_id = result.get('Instances', [{}])[0].get('InstanceId')
            return instance_id
        except Exception as exc:
            if 'Invalid IAM Instance Profile' in str(exc) and attempt < 4:
                wait = 5 * (attempt + 1)
                print(f'  IAM profile not yet visible to EC2, retrying in {wait}s (attempt {attempt + 1}/5)...')
                time.sleep(wait)
                continue
            raise


def find_instances(ec2: EC2) -> dict:
    filters   = [{'Name': 'tag:Name'           , 'Values': [TAG__NAME]                                },
                 {'Name': 'instance-state-name', 'Values': ['pending', 'running', 'stopping', 'stopped']}]
    return ec2.instances_details(filters=filters)


def find_instance_ids(ec2: EC2) -> list:
    return list(find_instances(ec2).keys())


def _instance_nickname(details: dict) -> str:
    for tag in details.get('tags', []):
        if tag.get('Key') == TAG__NICKNAME_KEY:
            return tag.get('Value', '')
    return ''


def _resolve_instance_id(ec2: EC2, target: str) -> str:
    """Accept an instance-id (i-…) or a nickname; return the instance-id."""
    if target.startswith('i-'):
        return target
    for iid, details in find_instances(ec2).items():
        if _instance_nickname(details) == target:
            return iid
    raise ValueError(f'No instance found with nickname {target!r}')


def terminate_instances(ec2: EC2, nickname: str = '') -> list:
    instances = find_instances(ec2)
    to_kill   = [iid for iid, d in instances.items()
                 if not nickname or _instance_nickname(d) == nickname]
    for iid in to_kill:
        ec2.instance_terminate(iid)
    return to_kill


def provision(stage                  : str  = DEFAULT_STAGE ,
               playwright_image_uri  : str  = None          ,
               sidecar_image_uri     : str  = None          ,
               nickname              : str  = ''            ,
               terminate             : bool = False         ) -> dict:
    ec2 = EC2()

    if terminate:
        terminated = terminate_instances(ec2)
        return {'action': 'terminate', 'instance_ids': terminated}

    preflight             = preflight_check(playwright_image_uri=playwright_image_uri,
                                             sidecar_image_uri=sidecar_image_uri)
    api_key_name          = get_env('FAST_API__AUTH__API_KEY__NAME' ) or 'X-API-Key'
    api_key_value         = get_env('FAST_API__AUTH__API_KEY__VALUE') or preflight['api_key_value']
    upstream_url          = get_env('AGENT_MITMPROXY__UPSTREAM_URL' ) or ''
    upstream_user         = get_env('AGENT_MITMPROXY__UPSTREAM_USER') or ''
    upstream_pass         = get_env('AGENT_MITMPROXY__UPSTREAM_PASS') or ''
    playwright_image_uri  = playwright_image_uri or default_playwright_image_uri()
    sidecar_image_uri     = sidecar_image_uri    or default_sidecar_image_uri()

    compose_content       = render_compose_yaml(playwright_image_uri = playwright_image_uri ,
                                                 sidecar_image_uri    = sidecar_image_uri    ,
                                                 api_key_name         = api_key_name         ,
                                                 api_key_value        = api_key_value        ,
                                                 upstream_url         = upstream_url         ,
                                                 upstream_user        = upstream_user        ,
                                                 upstream_pass        = upstream_pass        )
    user_data             = render_user_data(playwright_image_uri = playwright_image_uri ,
                                              sidecar_image_uri    = sidecar_image_uri    ,
                                              compose_content      = compose_content      )

    instance_profile_name = ensure_instance_profile()
    security_group_id     = ensure_security_group(ec2)
    ami_id                = latest_al2023_ami_id(ec2)
    instance_id           = run_instance(ec2                   = ec2                   ,
                                          ami_id                = ami_id                ,
                                          security_group_id     = security_group_id     ,
                                          instance_profile_name = instance_profile_name ,
                                          user_data             = user_data             ,
                                          stage                 = stage                 ,
                                          nickname              = nickname              )

    ec2.wait_for_instance_running(instance_id)
    details       = ec2.instance_details(instance_id)
    public_ip     = details.get('public_ip')
    playwright_url = f'http://{public_ip}:{EC2__PLAYWRIGHT_PORT}'    if public_ip else None
    sidecar_url    = f'http://{public_ip}:{EC2__SIDECAR_ADMIN_PORT}' if public_ip else None

    return {'action'              : 'create'               ,
            'instance_id'        : instance_id             ,
            'nickname'           : nickname                ,
            'public_ip'          : public_ip               ,
            'playwright_url'     : playwright_url          ,
            'sidecar_admin_url'  : sidecar_url             ,
            'playwright_image_uri': playwright_image_uri   ,
            'sidecar_image_uri'  : sidecar_image_uri       ,
            'ami_id'             : ami_id                  ,
            'stage'              : stage                   ,
            'api_key_name'       : api_key_name            ,
            'api_key_value'      : api_key_value           }


# ── Typer CLI ─────────────────────────────────────────────────────────────────

app = typer.Typer(name           = 'provision_ec2'                                     ,
                   help           = 'Manage the Playwright + agent_mitmproxy EC2 stack.',
                   no_args_is_help = True                                              ,
                   add_completion  = False                                             )


def _health_check_once(base_url: str, api_key_name: str, api_key_value: str) -> dict:
    headers = {api_key_name: api_key_value} if api_key_value else {}
    results = {}
    for path in ('health/info', 'health/status', 'health/capabilities'):
        try:
            r = requests.get(f'{base_url}/{path}', headers=headers, timeout=10)
            results[path] = {'status': r.status_code, 'body': r.json()}
        except Exception as exc:
            results[path] = {'error': str(exc)}
    return results


@app.command()
def create(stage                : str           = typer.Option(DEFAULT_STAGE, help='Stage tag applied to the instance.')                          ,
           name                 : Optional[str] = typer.Option(None         , '--name'                , help='Nickname for the instance (used by connect/delete).')  ,
           playwright_image_uri : Optional[str] = typer.Option(None         , '--playwright-image-uri', help='Override Playwright ECR image URI.')  ,
           sidecar_image_uri    : Optional[str] = typer.Option(None         , '--sidecar-image-uri'   , help='Override sidecar ECR image URI.')      ,
           wait                 : bool          = typer.Option(False         , '--wait'                , help='Poll health endpoint until the service is up.') ,
           timeout              : int           = typer.Option(300           , '--timeout'             , help='Max seconds to wait when --wait is set.')      ):
    """Provision a t3.large EC2 instance running the Playwright + agent_mitmproxy stack."""
    result = provision(stage=stage, playwright_image_uri=playwright_image_uri,
                       sidecar_image_uri=sidecar_image_uri, nickname=name or '')
    typer.echo(json.dumps(result, indent=2, default=str))
    if wait and result.get('playwright_url'):
        _cmd_wait(ip            = result['public_ip']    ,
                  api_key_name  = result['api_key_name'] ,
                  api_key_value = result['api_key_value'],
                  timeout       = timeout                 )


@app.command(name='list')
def cmd_list():
    """List all playwright-ec2 instances (pending, running, stopped)."""
    c         = Console(highlight=False, width=200)
    instances = find_instances(EC2())
    if not instances:
        c.print('  [dim]No instances found.[/]')
        return
    t = Table(show_header=True, header_style='bold bright_cyan', box=None, padding=(0, 2))
    t.add_column('instance-id',  style='dim')
    t.add_column('nickname',     style='bold white')
    t.add_column('state')
    t.add_column('public-ip',    style='green')
    t.add_column('playwright-url')
    for iid, d in instances.items():
        state    = d.get('state', '?')
        ip       = d.get('public_ip', '')
        nickname = _instance_nickname(d)
        url      = f'http://{ip}:{EC2__PLAYWRIGHT_PORT}' if ip else ''
        colour   = 'green' if state == 'running' else 'yellow' if state == 'pending' else 'red'
        t.add_row(iid, nickname, f'[{colour}]{state}[/]', ip, url)
    c.print(t)


@app.command(name='delete')
def cmd_delete(name : Optional[str] = typer.Argument(None, help='Nickname or instance-id to delete; omit to delete ALL.')):
    """Delete playwright-ec2 instance(s) by nickname/instance-id, or all if no argument given."""
    ec2      = EC2()
    nickname = '' if (name or '').startswith('i-') else (name or '')
    if name and name.startswith('i-'):
        ec2.instance_terminate(name)
        deleted = [name]
    else:
        deleted = terminate_instances(ec2, nickname=nickname)
    typer.echo(json.dumps({'action': 'delete', 'instance_ids': deleted}, indent=2))


@app.command(name='connect')
def cmd_connect(target : str = typer.Argument(..., help='Nickname (e.g. "mytest") or instance-id (i-…).')):
    """Open an SSM session to an instance by nickname or instance-id (no SSH needed)."""
    import subprocess
    ec2         = EC2()
    instance_id = _resolve_instance_id(ec2, target)
    typer.echo(f'  🔌  Connecting to {instance_id} via SSM...')
    subprocess.run(['aws', 'ssm', 'start-session', '--target', instance_id], check=False)


@app.command(name='wait')
def _cmd_wait(ip            : str           = typer.Argument(...  , help='Public IP or nickname of the instance.')              ,
              port           : int           = typer.Option(EC2__PLAYWRIGHT_PORT, help='Service port.')                          ,
              api_key_name   : Optional[str] = typer.Option(None  , envvar='FAST_API__AUTH__API_KEY__NAME' , help='API key header name.')  ,
              api_key_value  : Optional[str] = typer.Option(None  , envvar='FAST_API__AUTH__API_KEY__VALUE', help='API key value.')         ,
              timeout        : int           = typer.Option(300   , help='Max seconds to wait.')                                 ,
              interval       : int           = typer.Option(10    , help='Seconds between attempts.')                            ):
    """Poll the service health endpoint until it returns 200, then print results."""
    # Resolve nickname → public IP if needed
    actual_ip = ip
    if not ip.replace('.', '').isdigit():
        details    = find_instances(EC2())
        for iid, d in details.items():
            if _instance_nickname(d) == ip:
                actual_ip = d.get('public_ip', '')
                break
    base_url  = f'http://{actual_ip}:{port}'
    key_name  = api_key_name  or get_env('FAST_API__AUTH__API_KEY__NAME' ) or 'X-API-Key'
    key_value = api_key_value or get_env('FAST_API__AUTH__API_KEY__VALUE') or ''
    deadline  = time.time() + timeout
    typer.echo(f'  ⏳  Waiting for {base_url} (timeout {timeout}s)...')
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        try:
            r = requests.get(f'{base_url}/health/status', headers={key_name: key_value}, timeout=8)
            if r.status_code == 200:
                typer.echo(f'  ✅  healthy after {attempt} attempt(s)')
                typer.echo(json.dumps(_health_check_once(base_url, key_name, key_value), indent=2))
                return
            typer.echo(f'  🔄  attempt {attempt}: HTTP {r.status_code} — retrying in {interval}s...')
        except Exception as exc:
            typer.echo(f'  🔄  attempt {attempt}: {exc!s:.80} — retrying in {interval}s...')
        time.sleep(interval)
    typer.echo(f'  ❌  timed out after {timeout}s', err=True)
    raise typer.Exit(1)


@app.command(name='health')
def cmd_health(ip           : str           = typer.Argument(...  , help='Public IP or nickname of the instance.')              ,
               port          : int           = typer.Option(EC2__PLAYWRIGHT_PORT, help='Service port.')                          ,
               api_key_name  : Optional[str] = typer.Option(None  , envvar='FAST_API__AUTH__API_KEY__NAME' , help='API key header name.')  ,
               api_key_value : Optional[str] = typer.Option(None  , envvar='FAST_API__AUTH__API_KEY__VALUE', help='API key value.')         ):
    """Run health checks against a live instance and print results."""
    # Resolve nickname → public IP if needed
    actual_ip = ip
    if not ip.replace('.', '').isdigit():
        for iid, d in find_instances(EC2()).items():
            if _instance_nickname(d) == ip:
                actual_ip = d.get('public_ip', '')
                break
    base_url  = f'http://{actual_ip}:{port}'
    key_name  = api_key_name  or get_env('FAST_API__AUTH__API_KEY__NAME' ) or 'X-API-Key'
    key_value = api_key_value or get_env('FAST_API__AUTH__API_KEY__VALUE') or ''
    results   = _health_check_once(base_url, key_name, key_value)
    typer.echo(json.dumps(results, indent=2))


if __name__ == '__main__':
    app()

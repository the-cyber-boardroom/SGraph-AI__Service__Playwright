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
TAG__SERVICE_KEY             = 'sg:service'                                             # Immutable identifier — find_instances filters on this, not Name (Name is user-editable in console)
TAG__SERVICE_VALUE           = 'playwright-ec2'
TAG__STAGE_KEY               = 'stage'
TAG__DEPLOY_NAME_KEY         = 'sg:deploy-name'                                         # Random two-word name (happy-turing); used by connect/delete/exec
TAG__CREATOR_KEY             = 'sg:creator'                                             # Who launched this instance (git email or $USER)
TAG__API_KEY_NAME_KEY        = 'sg:api-key-name'                                        # Stored so 'list' can show it
TAG__API_KEY_VALUE_KEY       = 'sg:api-key-value'                                       # Stored in tags — only IAM credentials can read EC2 tags
DEFAULT_STAGE                = 'dev'

_ADJECTIVES = ['bold','bright','calm','clever','cool','daring','deep','eager',
               'fast','fierce','fresh','grand','happy','keen','light','lucky',
               'mellow','neat','quick','quiet','sharp','sleek','smart','swift','witty']
_SCIENTISTS = ['bohr','curie','darwin','dirac','einstein','euler','faraday',
               'fermi','feynman','galileo','gauss','hopper','hubble','lovelace',
               'maxwell','newton','noether','pascal','planck','turing','tesla',
               'volta','watt','wien','zeno']

COMPOSE_PROJECT   = 'sg-playwright'
COMPOSE_FILE_PATH = '/opt/sg-playwright/docker-compose.yml'


def _random_deploy_name() -> str:
    return f'{secrets.choice(_ADJECTIVES)}-{secrets.choice(_SCIENTISTS)}'


def _get_creator() -> str:
    import subprocess
    try:
        return subprocess.check_output(['git', 'config', 'user.email'],
                                       stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        import os
        return os.environ.get('USER', 'unknown')


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
exec > >(tee /var/log/sg-playwright-setup.log | logger -t sg-playwright) 2>&1

echo "=== SG Playwright setup starting at $(date) ==="

# docker-compose-plugin is not in AL2023 standard repos; install docker then add compose plugin binary
dnf install -y docker
systemctl enable --now docker

# add ssm-user to docker group so 'docker' works without sudo inside SSM sessions
usermod -aG docker ssm-user 2>/dev/null || true

# install compose v2 as a Docker CLI plugin (no third-party repo needed)
mkdir -p /usr/local/lib/docker/cli-plugins
curl -sSL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" \
     -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

TOKEN=$(aws ecr get-login-password --region {region})
echo "$TOKEN" | docker login --username AWS --password-stdin {registry}

docker pull {playwright_image_uri}
docker pull {sidecar_image_uri}

mkdir -p /opt/sg-playwright

cat > /opt/sg-playwright/docker-compose.yml << 'SG_COMPOSE_EOF'
{compose_content}
SG_COMPOSE_EOF

docker compose -f /opt/sg-playwright/docker-compose.yml up -d

echo "=== SG Playwright setup complete at $(date) ==="
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
    t.add_column(style='#555555', min_width=12, no_wrap=True)
    t.add_column(style='#111111')
    for k, v in rows:
        t.add_row(k, str(v))
    return t


def _print_preflight_summary(account, region, registry,
                              playwright_uri, sidecar_uri,
                              api_key_name, api_key_value,
                              upstream_url, upstream_user, upstream_pass,
                              warnings, errors) -> None:
    c = Console(highlight=False, width=200)

    c.print(Panel('[bold #111111] 🎭  SG Playwright EC2 Provisioner[/]  ·  [#555555]preflight check[/]',
                  border_style='blue', expand=False))
    c.print()

    c.print('  [bold #1a6fa8]☁️  AWS[/]')
    c.print(_kv_table(('account',  account ),
                      ('region',   region  ),
                      ('registry', registry)))
    c.print()

    c.print('  [bold #1a6fa8]🐳  Images[/]')
    c.print(_kv_table(('🎭 playwright', playwright_uri),
                      ('🔭 sidecar',    sidecar_uri   )))
    c.print()

    c.print('  [bold #1a6fa8]🔑  API key[/]')
    c.print(_kv_table(('name',  api_key_name                         ),
                      ('value', f'[bold #1a7a1a]{api_key_value}[/]')))
    c.print()

    if upstream_url:
        c.print('  [bold #1a6fa8]🌐  Upstream forwarding[/]')
        c.print(_kv_table(('url',  upstream_url                                                    ),
                          ('user', '[#1a7a1a](set)[/]' if upstream_user else '[#cc2222](not set)[/]'),
                          ('pass', '[#1a7a1a](set)[/]' if upstream_pass else '[#cc2222](not set)[/]')))
    else:
        c.print('  [bold #1a6fa8]🌐  Upstream[/]  [#555555]none — sidecar runs in direct mode[/]')
    c.print()

    c.print(f'  [bold #1a6fa8]⚙️  Stack[/]   [#555555]t3.large · AL2023 · '
            f'IAM={IAM__ROLE_NAME} · SG={SG__NAME} · tag={TAG__NAME}[/]')
    c.print()

    c.print('  [bold #1a6fa8]🔌  Ports[/]')
    c.print(_kv_table((f':{EC2__PLAYWRIGHT_PORT}',    f'playwright API       [#555555](public)[/]'         ),
                      (f':{EC2__SIDECAR_ADMIN_PORT}', f'sidecar admin API    [#555555](public)[/]'         ),
                      (':8080',                        '[#555555]mitmproxy proxy   (Docker-network-only)[/]')))
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


def run_instance(ec2: EC2, ami_id: str, security_group_id: str, instance_profile_name: str,
                  user_data: str, stage: str, deploy_name: str = '',
                  creator: str = '', api_key_name: str = '', api_key_value: str = '') -> str:
    display_name = f'{TAG__NAME}/{deploy_name}' if deploy_name else TAG__NAME
    tags = [{'Key': 'Name'              , 'Value': display_name    },
            {'Key': TAG__SERVICE_KEY    , 'Value': TAG__SERVICE_VALUE},  # immutable — not shown in Name column, survives console renames
            {'Key': TAG__STAGE_KEY      , 'Value': stage            },
            {'Key': TAG__DEPLOY_NAME_KEY, 'Value': deploy_name      },
            {'Key': TAG__CREATOR_KEY    , 'Value': creator      },
            {'Key': TAG__API_KEY_NAME_KEY , 'Value': api_key_name  },
            {'Key': TAG__API_KEY_VALUE_KEY, 'Value': api_key_value }]
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
    filters   = [{'Name': f'tag:{TAG__SERVICE_KEY}', 'Values': [TAG__SERVICE_VALUE]                    },  # immutable — survives console Name renames
                 {'Name': 'instance-state-name'    , 'Values': ['pending', 'running', 'stopping', 'stopped']}]
    return ec2.instances_details(filters=filters)


def find_instance_ids(ec2: EC2) -> list:
    return list(find_instances(ec2).keys())


def _instance_tag(details: dict, key: str) -> str:
    for tag in details.get('tags', []):
        if tag.get('Key') == key:
            return tag.get('Value', '')
    return ''


def _instance_deploy_name(details: dict) -> str:
    return _instance_tag(details, TAG__DEPLOY_NAME_KEY)


def _resolve_instance_id(ec2: EC2, target: str) -> str:
    """Accept an instance-id (i-…) or a deploy-name; return the instance-id."""
    if target.startswith('i-'):
        return target
    for iid, details in find_instances(ec2).items():
        if _instance_deploy_name(details) == target:
            return iid
    raise ValueError(f'No instance found with deploy-name {target!r}')


def terminate_instances(ec2: EC2, nickname: str = '') -> list:
    instances = find_instances(ec2)
    to_kill   = [iid for iid, d in instances.items()
                 if not nickname or _instance_deploy_name(d) == nickname]
    for iid in to_kill:
        ec2.instance_terminate(iid)
    return to_kill


def provision(stage                  : str  = DEFAULT_STAGE ,
               playwright_image_uri  : str  = None          ,
               sidecar_image_uri     : str  = None          ,
               deploy_name           : str  = ''            ,
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
    resolved_deploy_name  = deploy_name or _random_deploy_name()
    creator               = _get_creator()

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
                                          deploy_name           = resolved_deploy_name  ,
                                          creator               = creator               ,
                                          api_key_name          = api_key_name          ,
                                          api_key_value         = api_key_value         )

    ec2.wait_for_instance_running(instance_id)
    details       = ec2.instance_details(instance_id)
    public_ip     = details.get('public_ip')
    playwright_url = f'http://{public_ip}:{EC2__PLAYWRIGHT_PORT}'    if public_ip else None
    sidecar_url    = f'http://{public_ip}:{EC2__SIDECAR_ADMIN_PORT}' if public_ip else None

    return {'action'              : 'create'               ,
            'instance_id'        : instance_id             ,
            'deploy_name'        : resolved_deploy_name    ,
            'creator'            : creator                 ,
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


def _resolve_target(ec2: EC2, target: Optional[str]) -> tuple:
    """Resolve a deploy-name, instance-id, or None (auto-select) → (instance_id, details)."""
    instances = find_instances(ec2)
    if not instances:
        typer.echo('  ❌  No playwright-ec2 instances found.', err=True)
        raise typer.Exit(1)
    if target is None:
        if len(instances) == 1:
            iid     = next(iter(instances))
            return iid, instances[iid]
        # Multiple instances — prompt
        c = Console(highlight=False, width=200)
        c.print('\n  [bold]Multiple instances found — pick one:[/]\n')
        items = list(instances.items())
        for i, (iid, d) in enumerate(items, 1):
            state_raw = d.get('state', {})
            state     = state_raw.get('Name', '?') if isinstance(state_raw, dict) else str(state_raw)
            name      = _instance_deploy_name(d) or iid
            ip        = d.get('public_ip', '?')
            colour    = 'green' if state == 'running' else 'yellow'
            c.print(f'  [{colour}]{i}[/]  {name}  {iid}  {ip}  [{colour}]{state}[/]')
        c.print()
        choice = typer.prompt('  Enter number').strip()
        try:
            iid = items[int(choice) - 1][0]
            return iid, instances[iid]
        except (ValueError, IndexError):
            typer.echo('  ❌  Invalid choice.', err=True)
            raise typer.Exit(1)
    iid = _resolve_instance_id(ec2, target)
    return iid, instances.get(iid, {})


def _resolve_ip(ec2: EC2, target: str) -> str:
    """Resolve a deploy-name, instance-id, or raw IP → public IP string."""
    if target.replace('.', '').isdigit():
        return target
    iid, details = _resolve_target(ec2, target)
    return details.get('public_ip', '')


def _ssm_run(instance_id: str, commands: list, timeout: int = 60) -> tuple:
    """Execute shell commands on an EC2 instance via SSM Run Command. Returns (stdout, stderr)."""
    import boto3
    ssm        = boto3.client('ssm', region_name=aws_region())
    response   = ssm.send_command(InstanceIds      = [instance_id]          ,
                                   DocumentName     = 'AWS-RunShellScript'   ,
                                   Parameters       = {'commands': commands} ,
                                   TimeoutSeconds   = timeout                )
    command_id = response['Command']['CommandId']
    deadline   = time.time() + timeout + 10
    while time.time() < deadline:
        time.sleep(3)
        try:
            inv = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
            if inv['Status'] not in ('Pending', 'InProgress', 'Delayed'):
                return inv.get('StandardOutputContent', ''), inv.get('StandardErrorContent', '')
        except ssm.exceptions.InvocationDoesNotExist:
            pass
    return '', 'Timed out waiting for SSM command result'


def _render_create_result(r: dict) -> None:
    c = Console(highlight=False, width=200)
    c.print()
    c.print(Panel(
        f'[bold green]✅  Instance launched[/]  ·  [bright_white]{r["deploy_name"]}[/]  [dim]{r["instance_id"]}[/]',
        border_style='green', expand=False))
    c.print()

    left = Table(box=None, show_header=False, padding=(0, 2), expand=False)
    left.add_column(style='white',        min_width=14, no_wrap=True)
    left.add_column(style='bright_white')
    left.add_row('deploy-name', r['deploy_name']  )
    left.add_row('stage',       r['stage']        )
    left.add_row('creator',     r['creator']      )
    left.add_row('ami',         r['ami_id']       )
    left.add_row('instance-id', r['instance_id']  )

    right = Table(box=None, show_header=False, padding=(0, 2), expand=False)
    right.add_column(style='white',        min_width=14, no_wrap=True)
    right.add_column(style='bright_white')
    right.add_row('public-ip',    r['public_ip']                               )
    right.add_row('playwright',   r['playwright_url'] or '—'                   )
    right.add_row('sidecar-admin',r['sidecar_admin_url'] or '—'                )
    right.add_row('api-key-name', r['api_key_name']                            )
    right.add_row('api-key-value',f'[bold green]{r["api_key_value"]}[/]'       )

    cols = Table(box=None, show_header=False, padding=(0, 3), expand=False)
    cols.add_column()
    cols.add_column()
    cols.add_row(left, right)
    c.print(cols)

    img = Table(box=None, show_header=False, padding=(0, 2), expand=False)
    img.add_column(style='white',        min_width=10, no_wrap=True)
    img.add_column(style='dim')
    img.add_row('playwright', r['playwright_image_uri'])
    img.add_row('sidecar',    r['sidecar_image_uri']  )
    c.print()
    c.print('  [bold bright_cyan]🐳  Images[/]')
    c.print(img)
    c.print()
    c.print(f'  [dim]sg-ec2 wait {r["deploy_name"]}   ·   sg-ec2 forward 8000   ·   sg-ec2 logs[/]')
    c.print()


def _render_health(results: dict, base_url: str) -> None:
    c   = Console(highlight=False, width=200)
    all_ok = all('status' in v and v['status'] == 200 for v in results.values())
    c.print()
    c.print(Panel(f'[bold]{"✅" if all_ok else "❌"}  Health — [cyan]{base_url}[/cyan][/]',
                  border_style='green' if all_ok else 'red', expand=False))
    for path, v in results.items():
        if 'error' in v:
            # Extract just the root cause from the long urllib3 error
            err = str(v['error'])
            short = err.split('(Caused by')[-1].strip().strip('()')
            c.print(f'  [red]✗[/]  [dim]{path}[/]')
            c.print(f'       [red]{short}[/]')
        else:
            colour = 'green' if v['status'] == 200 else 'yellow'
            c.print(f'  [{colour}]{"✓" if v["status"] == 200 else "!"}[/]  [dim]{path}[/]  '
                    f'[{colour}]HTTP {v["status"]}[/]')
    if not all_ok:
        c.print()
        c.print('  [dim]💡  Service may still be starting — try:[/]  [bold]sg-ec2 wait <ip>[/]')
    c.print()


@app.command()
def create(stage                : str           = typer.Option(DEFAULT_STAGE, help='Stage tag.')                                        ,
           name                 : Optional[str] = typer.Option(None, '--name', help='Deploy name (default: random two-word).')          ,
           playwright_image_uri : Optional[str] = typer.Option(None, '--playwright-image-uri', help='Override Playwright ECR image URI.'),
           sidecar_image_uri    : Optional[str] = typer.Option(None, '--sidecar-image-uri',    help='Override sidecar ECR image URI.')   ,
           wait                 : bool          = typer.Option(False, '--wait',    help='Poll health until up.')                         ,
           timeout              : int           = typer.Option(300,  '--timeout', help='Max seconds to wait when --wait is set.')        ):
    """Provision a t3.large EC2 instance running the Playwright + agent_mitmproxy stack."""
    result = provision(stage=stage, playwright_image_uri=playwright_image_uri,
                       sidecar_image_uri=sidecar_image_uri, deploy_name=name or '')
    _render_create_result(result)
    if wait and result.get('playwright_url'):
        _cmd_wait(ip=result['public_ip'], api_key_name=result['api_key_name'],
                  api_key_value=result['api_key_value'], timeout=timeout)


@app.command(name='list')
def cmd_list():
    """List all playwright-ec2 instances with metadata from tags."""
    c         = Console(highlight=False, width=200)
    instances = find_instances(EC2())
    if not instances:
        c.print('  [dim]No instances found.[/]')
        return
    t = Table(show_header=True, header_style='bold bright_cyan', box=None, padding=(0, 2))
    t.add_column('deploy-name', style='bold white')
    t.add_column('instance-id', style='dim')
    t.add_column('state')
    t.add_column('public-ip',   style='green')
    t.add_column('creator',     style='dim')
    t.add_column('api-key',     style='dim')
    for iid, d in instances.items():
        state_raw  = d.get('state', '?')
        state      = state_raw.get('Name', '?') if isinstance(state_raw, dict) else str(state_raw)
        ip         = d.get('public_ip', '')
        deploy     = _instance_deploy_name(d)
        creator    = _instance_tag(d, TAG__CREATOR_KEY)
        api_key    = _instance_tag(d, TAG__API_KEY_VALUE_KEY)
        colour     = 'green' if state == 'running' else 'yellow' if state == 'pending' else 'red'
        t.add_row(deploy, iid, f'[{colour}]{state}[/]', ip, creator, api_key)
    c.print(t)


@app.command(name='info')
def cmd_info(target: Optional[str] = typer.Argument(None, help='Deploy-name or instance-id (auto if only one).')):
    """Show full details for an instance, reading metadata from its tags."""
    ec2             = EC2()
    instance_id, d  = _resolve_target(ec2, target)
    state_raw       = d.get('state', {})
    state           = state_raw.get('Name', '?') if isinstance(state_raw, dict) else str(state_raw)
    ip              = d.get('public_ip', '')
    deploy_name     = _instance_deploy_name(d)
    r = {
        'instance_id'         : instance_id,
        'deploy_name'         : deploy_name,
        'stage'               : _instance_tag(d, TAG__STAGE_KEY),
        'creator'             : _instance_tag(d, TAG__CREATOR_KEY),
        'ami_id'              : d.get('image_id', '—'),
        'public_ip'           : ip,
        'playwright_url'      : f'http://{ip}:{EC2__PLAYWRIGHT_PORT}'    if ip else '—',
        'sidecar_admin_url'   : f'http://{ip}:{EC2__SIDECAR_ADMIN_PORT}' if ip else '—',
        'api_key_name'        : _instance_tag(d, TAG__API_KEY_NAME_KEY),
        'api_key_value'       : _instance_tag(d, TAG__API_KEY_VALUE_KEY),
        'playwright_image_uri': '(stored in compose file on instance)',
        'sidecar_image_uri'   : '(stored in compose file on instance)',
        'state'               : state,
    }
    colour = 'green' if state == 'running' else 'yellow' if state == 'pending' else 'red'
    c      = Console(highlight=False, width=200)
    c.print()
    c.print(Panel(
        f'[bold]ℹ️   Instance info[/]  ·  [bright_white]{deploy_name}[/]  [dim]{instance_id}[/]  '
        f'[{colour}]{state}[/]',
        border_style=colour, expand=False))
    c.print()

    left = Table(box=None, show_header=False, padding=(0, 2), expand=False)
    left.add_column(style='white',        min_width=14, no_wrap=True)
    left.add_column(style='bright_white')
    left.add_row('deploy-name', r['deploy_name']  )
    left.add_row('stage',       r['stage']        )
    left.add_row('creator',     r['creator']      )
    left.add_row('ami',         r['ami_id']       )
    left.add_row('instance-id', r['instance_id']  )

    right = Table(box=None, show_header=False, padding=(0, 2), expand=False)
    right.add_column(style='white',        min_width=14, no_wrap=True)
    right.add_column(style='bright_white')
    right.add_row('public-ip',     r['public_ip']                          )
    right.add_row('playwright',    r['playwright_url']                     )
    right.add_row('sidecar-admin', r['sidecar_admin_url']                  )
    right.add_row('api-key-name',  r['api_key_name']                       )
    right.add_row('api-key-value', f'[bold green]{r["api_key_value"]}[/]'  )

    cols = Table(box=None, show_header=False, padding=(0, 3), expand=False)
    cols.add_column()
    cols.add_column()
    cols.add_row(left, right)
    c.print(cols)
    c.print()
    c.print(f'  [dim]sg-ec2 forward 8000 --target {deploy_name}   ·   '
            f'sg-ec2 health {deploy_name}   ·   sg-ec2 logs --target {deploy_name}[/]')
    c.print()


@app.command(name='delete')
def cmd_delete(name: Optional[str] = typer.Argument(None, help='Deploy-name or instance-id; omit to delete ALL.')):
    """Delete instance(s) by deploy-name/instance-id, or all if no argument given."""
    ec2     = EC2()
    c       = Console(highlight=False, width=200)
    deleted = []
    if name:
        instance_id, details = _resolve_target(ec2, name)
        deploy = _instance_deploy_name(details) or instance_id
        c.print(f'  🗑️   Deleting [bright_white]{deploy}[/]  [dim]{instance_id}[/]...')
        ec2.instance_terminate(instance_id)
        deleted = [instance_id]
    else:
        deleted = terminate_instances(ec2)
    c.print(f'  ✅  Deleted {len(deleted)} instance(s): [dim]{", ".join(deleted) or "none"}[/]')


@app.command(name='connect')
def cmd_connect(target: Optional[str] = typer.Argument(None, help='Deploy-name or instance-id; auto-selects if only one instance.')):
    """Open an interactive SSM shell session (no SSH/key-pair needed)."""
    import subprocess
    ec2         = EC2()
    instance_id, _ = _resolve_target(ec2, target)
    typer.echo(f'  🔌  Opening SSM session → {instance_id}')
    subprocess.run(['aws', 'ssm', 'start-session', '--target', instance_id], check=False)


@app.command(name='exec')
def cmd_exec(command   : str          = typer.Argument(..., help='Shell command to run on the EC2 host, or inside a container with --container.'),
             target    : Optional[str] = typer.Option(None, '--target', '-t', help='Deploy-name or instance-id (auto if only one).'),
             container : Optional[str] = typer.Option(None, '--container', '-c',
                                                       help='Run inside this Compose service (playwright or agent-mitmproxy).') ):
    """Execute a shell command on the EC2 host or inside a Docker container via SSM."""
    ec2         = EC2()
    instance_id, _ = _resolve_target(ec2, target)
    if container:
        cmd = f'docker compose -f {COMPOSE_FILE_PATH} exec -T {container} {command}'
    else:
        cmd = command
    c = Console(highlight=False, width=200)
    c.print(f'  💻  [{instance_id}]{"[" + container + "]" if container else ""}  [dim]{cmd}[/]')
    stdout, stderr = _ssm_run(instance_id, [cmd])
    if stdout.strip():
        c.print(stdout.rstrip())
    if stderr.strip():
        c.print(f'[yellow]{stderr.rstrip()}[/]')


@app.command(name='logs')
def cmd_logs(service : Optional[str] = typer.Option(None, '--service', '-s', help='Filter to one service (playwright or agent-mitmproxy).'),
             tail    : int           = typer.Option(100, '--tail', help='Number of log lines to fetch.'),
             target  : Optional[str] = typer.Option(None, '--target', '-t', help='Deploy-name or instance-id (auto if only one).') ):
    """Fetch docker compose logs from the EC2 instance via SSM."""
    ec2         = EC2()
    instance_id, _ = _resolve_target(ec2, target)
    svc   = service or ''
    cmd   = f'docker compose -f {COMPOSE_FILE_PATH} logs --no-color --tail={tail} {svc}'.strip()
    c     = Console(highlight=False, width=200)
    c.print(f'  📋  Fetching logs from {instance_id}...')
    stdout, stderr = _ssm_run(instance_id, [cmd], timeout=30)
    if stdout.strip():
        c.print(stdout.rstrip())
    if stderr.strip():
        c.print(f'[yellow]{stderr.rstrip()}[/]')


@app.command(name='forward')
def cmd_forward(port   : str           = typer.Argument('8000', help='Port mapping — local:remote or just remote (uses same local port). e.g. 8000 or 9000:8000.'),
                target : Optional[str] = typer.Option(None, '--target', '-t', help='Deploy-name or instance-id (auto if only one).') ):
    """Forward a local port to the EC2 instance via SSM — no security group rule required."""
    import subprocess
    local_port, remote_port = port.split(':', 1) if ':' in port else (port, port)
    ec2         = EC2()
    instance_id, details = _resolve_target(ec2, target)
    public_ip   = details.get('public_ip', instance_id)
    deploy_name = _instance_deploy_name(details) or instance_id
    c = Console(highlight=False, width=200)
    c.print()
    c.print(Panel(
        f'[bold]🔀  SSM Port Forward[/]\n\n'
        f'  instance   [bright_white]{deploy_name}[/]  [dim]{instance_id}  {public_ip}[/]\n'
        f'  tunnel     [bright_white]localhost:{local_port}[/]  →  [bright_white]{public_ip}:{remote_port}[/]\n\n'
        f'  [green]Access:[/]  [bright_white]http://localhost:{local_port}/[/]\n'
        f'  [dim]Press Ctrl-C to close the tunnel.[/]',
        border_style='bright_blue', expand=False))
    c.print()
    subprocess.run(['aws', 'ssm', 'start-session',
                    '--target'       , instance_id,
                    '--document-name', 'AWS-StartPortForwardingSession',
                    '--parameters'   , json.dumps({'portNumber'     : [remote_port],
                                                   'localPortNumber': [local_port ]})],
                   check=False)


@app.command(name='wait')
def _cmd_wait(ip           : str           = typer.Argument(..., help='Public IP, deploy-name, or instance-id.'),
              port          : int           = typer.Option(EC2__PLAYWRIGHT_PORT, help='Service port.')            ,
              api_key_name  : Optional[str] = typer.Option(None, envvar='FAST_API__AUTH__API_KEY__NAME' )        ,
              api_key_value : Optional[str] = typer.Option(None, envvar='FAST_API__AUTH__API_KEY__VALUE')        ,
              timeout       : int           = typer.Option(300, help='Max seconds to wait.')                     ,
              interval      : int           = typer.Option(10,  help='Seconds between attempts.')                ):
    """Poll the health endpoint until the service responds 200."""
    actual_ip = _resolve_ip(EC2(), ip)
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
                _render_health(_health_check_once(base_url, key_name, key_value), base_url)
                return
            typer.echo(f'  🔄  attempt {attempt}: HTTP {r.status_code} — retrying in {interval}s...')
        except Exception as exc:
            typer.echo(f'  🔄  attempt {attempt}: {str(exc)[:80]} — retrying in {interval}s...')
        time.sleep(interval)
    typer.echo(f'  ❌  timed out after {timeout}s', err=True)
    raise typer.Exit(1)


@app.command(name='health')
def cmd_health(ip           : str           = typer.Argument(..., help='Public IP, deploy-name, or instance-id.'),
               port          : int           = typer.Option(EC2__PLAYWRIGHT_PORT, help='Service port.')           ,
               api_key_name  : Optional[str] = typer.Option(None, envvar='FAST_API__AUTH__API_KEY__NAME' )       ,
               api_key_value : Optional[str] = typer.Option(None, envvar='FAST_API__AUTH__API_KEY__VALUE')       ):
    """Run health checks against a live instance and display results."""
    actual_ip = _resolve_ip(EC2(), ip)
    base_url  = f'http://{actual_ip}:{port}'
    key_name  = api_key_name  or get_env('FAST_API__AUTH__API_KEY__NAME' ) or 'X-API-Key'
    key_value = api_key_value or get_env('FAST_API__AUTH__API_KEY__VALUE') or ''
    _render_health(_health_check_once(base_url, key_name, key_value), base_url)


if __name__ == '__main__':
    app()

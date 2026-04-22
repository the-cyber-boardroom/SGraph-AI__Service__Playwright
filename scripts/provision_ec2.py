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
from typing import List, Optional

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

# ── Instance-type presets (shown by sg-ec2 create --interactive) ──────────────
EC2__INSTANCE_TYPE_PRESETS = [
    ('t3.large'   , 2, 8  , 0.0832, 'burstable · current default'           ),
    ('t3.xlarge'  , 4, 16 , 0.1664, 'burstable · 2× RAM'                    ),
    ('t3.2xlarge' , 8, 32 , 0.3328, 'burstable · 4× RAM'                    ),
    ('c5.xlarge'  , 4, 8  , 0.1700, 'compute-optimised · sustained CPU'      ),
    ('m5.xlarge'  , 4, 16 , 0.1920, 'general purpose · sustained · balanced' ),
]
EC2__AMI_OWNER_AMAZON        = 'amazon'
EC2__PLAYWRIGHT_PORT         = 8000                                                     # Playwright API — exposed to the world via SG
EC2__SIDECAR_ADMIN_PORT      = 8001                                                     # Sidecar admin API (host port mapping of container :8000) — exposed via SG, API-key gated

WATCHDOG_MAX_REQUEST_MS      = 120_000                                                  # 120s — covers Firefox + long upstream-proxy round-trips

IAM__ROLE_NAME               = 'playwright-ec2'                                         # AWS reserves 'sg-*' prefix — applies to SG names, IAM instance profiles, and resource tags
IAM__ECR_READONLY_POLICY_ARN = 'arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly'
IAM__SSM_CORE_POLICY_ARN     = 'arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore'  # SSM session manager — no SSH needed
IAM__POLICY_ARNS             = (IAM__ECR_READONLY_POLICY_ARN, IAM__SSM_CORE_POLICY_ARN)
IAM__PROMETHEUS_RW_POLICY_ARN  = 'arn:aws:iam::aws:policy/AmazonPrometheusRemoteWriteAccess'
IAM__OBSERVABILITY_POLICY_ARNS = (IAM__PROMETHEUS_RW_POLICY_ARN,)                           # OpenSearch write access is domain-specific — added via resource policy (see library/docs/runbooks/aws-observability-setup.md)
IAM__ASSUME_ROLE_SERVICE       = 'ec2.amazonaws.com'

EC2__PROMETHEUS_PORT      = 9090
EC2__BROWSER_INTERNAL_PORT = 3000                                                      # linuxserver/chromium KasmVNC — SSM-forward only, never exposed in SG

SG__NAME                     = 'playwright-ec2'                                         # AWS reserves 'sg-*' prefix for SG IDs
SG__DESCRIPTION              = 'SG Playwright EC2 stack - ingress :8000 (Playwright API) + :8001 (sidecar admin) + :3000 (streaming browser) — all ports behind API key / KasmVNC password auth'

TAG__NAME                    = 'playwright-ec2'
TAG__SERVICE_KEY             = 'sg:service'                                             # Immutable identifier — find_instances filters on this, not Name (Name is user-editable in console)
TAG__SERVICE_VALUE           = 'playwright-ec2'
TAG__STAGE_KEY               = 'stage'
TAG__DEPLOY_NAME_KEY         = 'sg:deploy-name'                                         # Random two-word name (happy-turing); used by connect/delete/exec
TAG__CREATOR_KEY             = 'sg:creator'                                             # Who launched this instance (git email or $USER)
TAG__API_KEY_NAME_KEY        = 'sg:api-key-name'                                        # Stored so 'list' can show it
TAG__API_KEY_VALUE_KEY       = 'sg:api-key-value'                                       # Stored in tags — only IAM credentials can read EC2 tags
TAG__INSTANCE_TYPE_KEY       = 'sg:instance-type'                                        # Stored so 'list' can show it
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

SMOKE_URLS = ['https://www.google.com'   ,
              'https://sgraph.ai'         ,
              'https://send.sgraph.ai'    ,
              'https://news.bbc.co.uk'    ]

TAG__AMI_STATUS_KEY = 'sg:ami-status'    # untested | healthy | unhealthy

# Short user_data for AMI-based launches: Docker + images already baked in,
# just write the compose file (fresh API key) and start containers.
AMI_USER_DATA_TEMPLATE = """\
#!/bin/bash
set -euxo pipefail
exec > >(tee /var/log/sg-playwright-start.log | logger -t sg-playwright) 2>&1

echo "=== SG Playwright AMI boot at $(date) ==="

mkdir -p /opt/sg-playwright/config

cat > /opt/sg-playwright/docker-compose.yml << 'SG_COMPOSE_EOF'
{compose_content}
SG_COMPOSE_EOF

{observability_configs_section}
docker compose -f /opt/sg-playwright/docker-compose.yml up -d

echo "=== SG Playwright AMI start complete at $(date) ==="
"""


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

      browser:
        image: lscr.io/linuxserver/chromium:latest
        ports:
          - "{browser_port}:{browser_port}"
        environment:
          PUID:       1000
          PGID:       1000
          TZ:         Etc/UTC
          PASSWD:     '{api_key_value}'
          CHROME_CLI: >-
            --proxy-server=http://agent-mitmproxy:8080
            --ignore-certificate-errors
            --no-first-run
            --disable-sync
        shm_size: "1gb"
        networks:
          - sg-net
        depends_on:
          - agent-mitmproxy
        restart: unless-stopped

      cadvisor:
        image: gcr.io/cadvisor/cadvisor:v0.49.1
        privileged: true
        volumes:
          - /:/rootfs:ro
          - /var/run:/var/run:ro
          - /sys:/sys:ro
          - /var/lib/docker:/var/lib/docker:ro
        networks:
          - sg-net
        restart: always

      node-exporter:
        image: prom/node-exporter:v1.7.0
        volumes:
          - /proc:/host/proc:ro
          - /sys:/host/sys:ro
          - /:/rootfs:ro
        command:
          - '--path.procfs=/host/proc'
          - '--path.sysfs=/host/sys'
          - '--path.rootfs=/rootfs'
          - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
        networks:
          - sg-net
        restart: always

      prometheus:
        image: prom/prometheus:v2.51.0
        volumes:
          - /opt/sg-playwright/config/prometheus.yml:/etc/prometheus/prometheus.yml:ro
          - prometheus_data:/prometheus
        command:
          - '--config.file=/etc/prometheus/prometheus.yml'
          - '--storage.tsdb.path=/prometheus'
          - '--storage.tsdb.retention.time=24h'
          - '--web.enable-lifecycle'
        networks:
          - sg-net
        restart: always

      fluent-bit:
        image: amazon/aws-for-fluent-bit:stable
        volumes:
          - /var/lib/docker/containers:/var/lib/docker/containers:ro
          - /var/run/docker.sock:/var/run/docker.sock:ro
          - /opt/sg-playwright/config/fluent-bit.conf:/fluent-bit/etc/fluent-bit.conf:ro
        networks:
          - sg-net
        restart: always

    networks:
      sg-net:
        driver: bridge

    volumes:
      prometheus_data:
""")


PROMETHEUS_YML_TEMPLATE = """\
global:
  scrape_interval:     15s
  evaluation_interval: 15s
  external_labels:
    stack: sg-playwright

scrape_configs:
  - job_name: cadvisor
    static_configs:
      - targets: ['cadvisor:8080']

  - job_name: node-exporter
    static_configs:
      - targets: ['node-exporter:9100']
{remote_write_section}"""

PROMETHEUS_REMOTE_WRITE_TEMPLATE = """\
remote_write:
  - url: {amp_remote_write_url}
    sigv4:
      region: {region}
    queue_config:
      max_samples_per_send: 1000
      max_shards:           200
      capacity:             2500
"""

FLUENT_BIT_CONF_TEMPLATE = """\
[SERVICE]
    Flush         1
    Daemon        Off
    Log_Level     info
    Parsers_File  /fluent-bit/etc/parsers.conf

[INPUT]
    Name              tail
    Path              /var/lib/docker/containers/*/*.log
    Parser            docker
    Tag               docker.*
    Refresh_Interval  5
    Mem_Buf_Limit     5MB
    Skip_Long_Lines   On

[FILTER]
    Name    record_modifier
    Match   *
    Record  stack        sg-playwright
    Record  environment  {stage}

{output_section}"""

FLUENT_BIT_OUTPUT_OPENSEARCH = """\
[OUTPUT]
    Name              opensearch
    Match             *
    Host              {opensearch_endpoint}
    Port              443
    TLS               On
    TLS.Verify        On
    AWS_Auth          On
    AWS_Region        {region}
    AWS_Service_Name  es
    Index             sg-playwright-logs
    Suppress_Type_Name On
    Retry_Limit       False
"""

FLUENT_BIT_OUTPUT_STDOUT = """\
[OUTPUT]
    Name   stdout
    Match  *
"""


def render_observability_configs_section(region           : str,
                                          amp_remote_write_url: str = '',
                                          opensearch_endpoint : str = '',
                                          stage               : str = DEFAULT_STAGE) -> str:
    remote_write_section = ''
    if amp_remote_write_url:
        remote_write_section = PROMETHEUS_REMOTE_WRITE_TEMPLATE.format(
            amp_remote_write_url = amp_remote_write_url,
            region               = region)
    prometheus_yml = PROMETHEUS_YML_TEMPLATE.format(remote_write_section=remote_write_section)

    if opensearch_endpoint:
        output_section = FLUENT_BIT_OUTPUT_OPENSEARCH.format(
            opensearch_endpoint = opensearch_endpoint,
            region              = region)
    else:
        output_section = FLUENT_BIT_OUTPUT_STDOUT
    fluent_bit_conf = FLUENT_BIT_CONF_TEMPLATE.format(output_section=output_section, stage=stage)

    parts = [
        f"cat > /opt/sg-playwright/config/prometheus.yml << 'SG_PROM_EOF'\n{prometheus_yml}SG_PROM_EOF",
        f"cat > /opt/sg-playwright/config/fluent-bit.conf << 'SG_FB_EOF'\n{fluent_bit_conf}SG_FB_EOF",
    ]
    return '\n\n'.join(parts) + '\n'


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

# ECR login — disable set -x so the token value is never written to logs
set +x
aws ecr get-login-password --region {region} \
    | docker login --username AWS --password-stdin {registry}
set -x

docker pull {playwright_image_uri}
docker pull {sidecar_image_uri}

# Revoke the stored Docker credential immediately after pull — the instance
# profile (AmazonEC2ContainerRegistryReadOnly) provides fresh tokens on demand
# so nothing needs to persist.  This also keeps AMI snapshots credential-free.
docker logout {registry}
rm -f /root/.docker/config.json

mkdir -p /opt/sg-playwright/config

cat > /opt/sg-playwright/docker-compose.yml << 'SG_COMPOSE_EOF'
{compose_content}
SG_COMPOSE_EOF

{observability_configs_section}
docker compose -f /opt/sg-playwright/docker-compose.yml up -d
{shutdown_section}
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


def preflight_check(playwright_image_uri: str = None, sidecar_image_uri: str = None,
                    instance_type: str = EC2__INSTANCE_TYPE) -> dict:
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

    # ── AWS managed observability (optional) ─────────────────────────────────
    amp_remote_write_url = get_env('AMP_REMOTE_WRITE_URL') or ''
    opensearch_endpoint  = get_env('OPENSEARCH_ENDPOINT' ) or ''
    if not amp_remote_write_url:
        warnings.append('AMP_REMOTE_WRITE_URL not set — Prometheus will run locally only (no remote write to Amazon Managed Prometheus).')
    if not opensearch_endpoint:
        warnings.append('OPENSEARCH_ENDPOINT not set — Fluent Bit will log to stdout only (no shipping to OpenSearch).')

    # ── Print summary ─────────────────────────────────────────────────────────
    _print_preflight_summary(account, region, registry,
                             resolved_playwright, resolved_sidecar,
                             api_key_name, api_key_value,
                             upstream_url, upstream_user, upstream_pass,
                             warnings, errors, instance_type)
    return {'account': account, 'region': region, 'registry': registry, 'api_key_value': api_key_value}


def _kv_table(*rows) -> Table:
    t = Table(box=None, show_header=False, padding=(0, 2), expand=False)
    t.add_column(style='bold',    min_width=12, no_wrap=True)   # bold terminal-default: black on light bg, white on dark
    t.add_column(style='default')                                # plain terminal-default foreground
    for k, v in rows:
        t.add_row(k, str(v))
    return t


def _print_preflight_summary(account, region, registry,
                              playwright_uri, sidecar_uri,
                              api_key_name, api_key_value,
                              upstream_url, upstream_user, upstream_pass,
                              warnings, errors,
                              instance_type: str = EC2__INSTANCE_TYPE) -> None:
    c = Console(highlight=False, width=200)

    c.print(Panel('[bold] 🎭  SG Playwright EC2 Provisioner[/]  ·  preflight check',
                  border_style='blue', expand=False))
    c.print()

    c.print('  [bold blue]☁️  AWS[/]')
    c.print(_kv_table(('account',  account ),
                      ('region',   region  ),
                      ('registry', registry)))
    c.print()

    c.print('  [bold blue]🐳  Images[/]')
    c.print(_kv_table(('🎭 playwright', playwright_uri),
                      ('🔭 sidecar',    sidecar_uri   )))
    c.print()

    c.print('  [bold blue]🔑  API key[/]')
    c.print(_kv_table(('name',  api_key_name                    ),
                      ('value', f'[bold green]{api_key_value}[/]')))
    c.print()

    if upstream_url:
        c.print('  [bold blue]🌐  Upstream forwarding[/]')
        c.print(_kv_table(('url',  upstream_url                                              ),
                          ('user', '[green](set)[/]' if upstream_user else '[red](not set)[/]'),
                          ('pass', '[green](set)[/]' if upstream_pass else '[red](not set)[/]')))
    else:
        c.print('  [bold blue]🌐  Upstream[/]  none — sidecar runs in direct mode')
    c.print()

    c.print(f'  [bold blue]⚙️  Stack[/]   {instance_type} · AL2023 · '
            f'IAM={IAM__ROLE_NAME} · SG={SG__NAME} · tag={TAG__NAME}')
    c.print()

    c.print('  [bold blue]🔌  Ports[/]')
    c.print(_kv_table((f':{EC2__PLAYWRIGHT_PORT}',        'playwright API         (public, API-key gated)' ),
                      (f':{EC2__SIDECAR_ADMIN_PORT}',     'sidecar admin API      (public, API-key gated)' ),
                      (f':{EC2__BROWSER_INTERNAL_PORT}',  'streaming browser      (public, KasmVNC password = API key)'),
                      (':8080',                            'mitmproxy proxy        (Docker-network-only)'   )))
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
    for policy_arn in (*IAM__POLICY_ARNS, *IAM__OBSERVABILITY_POLICY_ARNS):
        role.iam.role_policy_attach(policy_arn)
    return IAM__ROLE_NAME


def ensure_security_group(ec2: EC2) -> str:
    existing = ec2.security_group(security_group_name=SG__NAME)
    if existing:
        security_group_id = existing.get('GroupId')
    else:
        create_result     = ec2.security_group_create(security_group_name=SG__NAME, description=SG__DESCRIPTION)
        security_group_id = create_result.get('data', {}).get('security_group_id')
    for port in (EC2__PLAYWRIGHT_PORT       ,   # :8000 — Playwright API
                 EC2__SIDECAR_ADMIN_PORT    ,   # :8001 — sidecar admin API
                 EC2__BROWSER_INTERNAL_PORT ):  # :3000 — streaming browser (KasmVNC, password-gated)
        try:
            ec2.security_group_authorize_ingress(security_group_id=security_group_id, port=port)
        except Exception:
            pass                                # rule already exists — idempotent
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
    return COMPOSE_YAML_TEMPLATE.format(playwright_image_uri    = playwright_image_uri        ,
                                        sidecar_image_uri       = sidecar_image_uri           ,
                                        playwright_port         = EC2__PLAYWRIGHT_PORT        ,
                                        sidecar_admin_port      = EC2__SIDECAR_ADMIN_PORT     ,
                                        browser_port            = EC2__BROWSER_INTERNAL_PORT  ,
                                        api_key_name            = api_key_name                ,
                                        api_key_value           = api_key_value               ,
                                        upstream_url            = upstream_url                ,
                                        upstream_user           = upstream_user               ,
                                        upstream_pass           = upstream_pass               ,
                                        watchdog_max_request_ms = watchdog_max_request_ms     )


def render_user_data(playwright_image_uri  : str,
                      sidecar_image_uri     : str,
                      compose_content       : str,
                      api_key_value         : str          = '',
                      max_hours             : Optional[int] = None,
                      amp_remote_write_url  : str          = '',
                      opensearch_endpoint   : str          = '',
                      stage                 : str          = DEFAULT_STAGE) -> str:
    if max_hours:
        shutdown_section = (f'\n# Auto-terminate after {max_hours}h\n'
                             f'systemd-run --on-active={max_hours}h /sbin/shutdown -h now\n'
                             f'echo "Auto-terminate timer started: {max_hours}h from now"\n')
    else:
        shutdown_section = ''
    obs_section = render_observability_configs_section(region               = aws_region()       ,
                                                        amp_remote_write_url = amp_remote_write_url,
                                                        opensearch_endpoint  = opensearch_endpoint ,
                                                        stage                = stage               )
    return USER_DATA_TEMPLATE.format(region                        = aws_region()           ,
                                     registry                      = ecr_registry_host()    ,
                                     playwright_image_uri          = playwright_image_uri   ,
                                     sidecar_image_uri             = sidecar_image_uri      ,
                                     compose_content               = compose_content        ,
                                     observability_configs_section = obs_section            ,
                                     shutdown_section              = shutdown_section       )


def run_instance(ec2: EC2, ami_id: str, security_group_id: str, instance_profile_name: str,
                  user_data: str, stage: str, deploy_name: str = '',
                  creator: str = '', api_key_name: str = '', api_key_value: str = '',
                  instance_type: str = EC2__INSTANCE_TYPE,
                  max_hours: Optional[int] = None) -> str:
    display_name = f'{TAG__NAME}/{deploy_name}' if deploy_name else TAG__NAME
    tags = [{'Key': 'Name'              , 'Value': display_name    },
            {'Key': TAG__SERVICE_KEY    , 'Value': TAG__SERVICE_VALUE},  # immutable — not shown in Name column, survives console renames
            {'Key': TAG__STAGE_KEY      , 'Value': stage            },
            {'Key': TAG__DEPLOY_NAME_KEY, 'Value': deploy_name      },
            {'Key': TAG__CREATOR_KEY    , 'Value': creator      },
            {'Key': TAG__API_KEY_NAME_KEY , 'Value': api_key_name   },
            {'Key': TAG__API_KEY_VALUE_KEY, 'Value': api_key_value },
            {'Key': TAG__INSTANCE_TYPE_KEY, 'Value': instance_type }]
    kwargs = {'ImageId'                          : ami_id                                    ,
              'InstanceType'                     : instance_type                             ,
              'MinCount'                         : 1                                         ,
              'MaxCount'                         : 1                                         ,
              'IamInstanceProfile'               : {'Name': instance_profile_name}           ,
              'SecurityGroupIds'                 : [security_group_id]                       ,
              'UserData'                         : user_data                                 ,
              'InstanceInitiatedShutdownBehavior': 'terminate'                               ,  # shutdown → terminate, not stop
              'TagSpecifications'                : [{'ResourceType': 'instance', 'Tags': tags}]}
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


def clean_instance_for_ami(instance_id: str) -> None:
    """Remove credentials, logs, and sensitive files before AMI snapshot."""
    steps = [
        f'docker compose -f {COMPOSE_FILE_PATH} stop',
        'docker logout 2>/dev/null || true',
        'rm -f /root/.docker/config.json',
        f'rm -f {COMPOSE_FILE_PATH}',
        'rm -rf /opt/sg-playwright/config 2>/dev/null || true',
        'rm -f /var/lib/cloud/instance/user-data.txt 2>/dev/null || true',
        'find /var/lib/cloud/instances -name user-data.txt -delete 2>/dev/null || true',
        'truncate -s 0 /var/log/sg-playwright-setup.log 2>/dev/null || true',
        'rm -f /var/log/cloud-init.log /var/log/cloud-init-output.log 2>/dev/null || true',
        'journalctl --vacuum-time=1s 2>/dev/null || true',
        'truncate -s 0 /root/.bash_history 2>/dev/null || true',
        'truncate -s 0 /home/ec2-user/.bash_history 2>/dev/null || true',
        'rm -rf /tmp/* 2>/dev/null || true',
        'sync',
    ]
    for cmd in steps:
        _ssm_run(instance_id, [cmd], timeout=60)


def create_ami(ec2: EC2, instance_id: str, name: str) -> str:
    """Create an AMI from a stopped/running instance. Returns ami_id."""
    resp = ec2.client().create_image(
        InstanceId      = instance_id,
        Name            = name,
        Description     = f'SG Playwright + agent_mitmproxy - {name}',
        NoReboot        = True,
        TagSpecifications = [{'ResourceType': 'image',
                              'Tags': [{'Key': 'Name',              'Value': name            },
                                       {'Key': TAG__SERVICE_KEY,    'Value': TAG__SERVICE_VALUE},
                                       {'Key': TAG__AMI_STATUS_KEY, 'Value': 'untested'      }]}])
    return resp['ImageId']


def wait_ami_available(ec2: EC2, ami_id: str, timeout: int = 900) -> bool:
    """Poll until AMI state is 'available' or 'failed'. Returns True on success."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        images = ec2.client().describe_images(ImageIds=[ami_id]).get('Images', [])
        state  = images[0]['State'] if images else 'pending'
        if state == 'available':
            return True
        if state == 'failed':
            return False
        time.sleep(15)
    return False


def tag_ami(ec2: EC2, ami_id: str, status: str) -> None:
    """Set sg:ami-status tag on an AMI (untested | healthy | unhealthy)."""
    ec2.client().create_tags(Resources=[ami_id],
                              Tags=[{'Key': TAG__AMI_STATUS_KEY, 'Value': status}])


def latest_healthy_ami(ec2: EC2) -> str:
    """Return the most recently created healthy sg-playwright AMI ID, or None."""
    resp   = ec2.client().describe_images(
        Filters = [{'Name': f'tag:{TAG__SERVICE_KEY}',    'Values': [TAG__SERVICE_VALUE]},
                   {'Name': f'tag:{TAG__AMI_STATUS_KEY}', 'Values': ['healthy']         },
                   {'Name': 'state',                      'Values': ['available']       }],
        Owners  = ['self'])
    images = sorted(resp.get('Images', []), key=lambda x: x['CreationDate'], reverse=True)
    return images[0]['ImageId'] if images else None


def provision(stage                  : str          = DEFAULT_STAGE    ,
               playwright_image_uri  : str          = None             ,
               sidecar_image_uri     : str          = None             ,
               deploy_name           : str          = ''               ,
               from_ami              : str          = None             ,    # use pre-baked AMI; skips install+pull
               instance_type         : str          = EC2__INSTANCE_TYPE,
               max_hours             : Optional[int] = None            ,
               terminate             : bool         = False            ) -> dict:
    ec2 = EC2()

    if terminate:
        terminated = terminate_instances(ec2)
        return {'action': 'terminate', 'instance_ids': terminated}

    preflight             = preflight_check(playwright_image_uri=playwright_image_uri,
                                             sidecar_image_uri=sidecar_image_uri,
                                             instance_type=instance_type)
    api_key_name          = get_env('FAST_API__AUTH__API_KEY__NAME' ) or 'X-API-Key'
    api_key_value         = get_env('FAST_API__AUTH__API_KEY__VALUE') or preflight['api_key_value']
    upstream_url          = get_env('AGENT_MITMPROXY__UPSTREAM_URL' ) or ''
    upstream_user         = get_env('AGENT_MITMPROXY__UPSTREAM_USER') or ''
    upstream_pass         = get_env('AGENT_MITMPROXY__UPSTREAM_PASS') or ''
    playwright_image_uri  = playwright_image_uri or default_playwright_image_uri()
    sidecar_image_uri     = sidecar_image_uri    or default_sidecar_image_uri()
    resolved_deploy_name  = deploy_name or _random_deploy_name()
    creator               = _get_creator()

    amp_remote_write_url  = get_env('AMP_REMOTE_WRITE_URL' ) or ''
    opensearch_endpoint   = get_env('OPENSEARCH_ENDPOINT'  ) or ''

    compose_content       = render_compose_yaml(playwright_image_uri = playwright_image_uri ,
                                                 sidecar_image_uri    = sidecar_image_uri    ,
                                                 api_key_name         = api_key_name         ,
                                                 api_key_value        = api_key_value        ,
                                                 upstream_url         = upstream_url         ,
                                                 upstream_user        = upstream_user        ,
                                                 upstream_pass        = upstream_pass        )
    obs_section = render_observability_configs_section(region               = aws_region()       ,
                                                        amp_remote_write_url = amp_remote_write_url,
                                                        opensearch_endpoint  = opensearch_endpoint ,
                                                        stage                = stage               )
    if from_ami:
        user_data = AMI_USER_DATA_TEMPLATE.format(compose_content               = compose_content,
                                                   observability_configs_section = obs_section    )
    else:
        user_data = render_user_data(playwright_image_uri  = playwright_image_uri ,
                                     sidecar_image_uri     = sidecar_image_uri    ,
                                     compose_content       = compose_content      ,
                                     api_key_value         = api_key_value        ,
                                     max_hours             = max_hours            ,
                                     amp_remote_write_url  = amp_remote_write_url ,
                                     opensearch_endpoint   = opensearch_endpoint  ,
                                     stage                 = stage                )

    instance_profile_name = ensure_instance_profile()
    security_group_id     = ensure_security_group(ec2)
    ami_id                = from_ami or latest_al2023_ami_id(ec2)
    instance_id           = run_instance(ec2                   = ec2                   ,
                                          ami_id                = ami_id                ,
                                          security_group_id     = security_group_id     ,
                                          instance_profile_name = instance_profile_name ,
                                          user_data             = user_data             ,
                                          stage                 = stage                 ,
                                          deploy_name           = resolved_deploy_name  ,
                                          creator               = creator               ,
                                          api_key_name          = api_key_name          ,
                                          api_key_value         = api_key_value         ,
                                          instance_type         = instance_type         ,
                                          max_hours             = max_hours             )

    ec2.wait_for_instance_running(instance_id)
    details       = ec2.instance_details(instance_id)
    public_ip     = details.get('public_ip')
    playwright_url = f'http://{public_ip}:{EC2__PLAYWRIGHT_PORT}'        if public_ip else None
    sidecar_url    = f'http://{public_ip}:{EC2__SIDECAR_ADMIN_PORT}'   if public_ip else None
    browser_url    = f'http://{public_ip}:{EC2__BROWSER_INTERNAL_PORT}' if public_ip else None

    return {'action'              : 'create'               ,
            'instance_id'        : instance_id             ,
            'deploy_name'        : resolved_deploy_name    ,
            'creator'            : creator                 ,
            'public_ip'          : public_ip               ,
            'playwright_url'     : playwright_url          ,
            'sidecar_admin_url'  : sidecar_url             ,
            'browser_url'        : browser_url             ,
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


def _resolve_ip(ec2: EC2, target: Optional[str]) -> str:
    """Resolve a deploy-name, instance-id, raw IP, or None (auto) → public IP string."""
    if target and target.replace('.', '').isdigit():
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
        f'[bold green]✅  Instance launched[/]  ·  [bold]{r["deploy_name"]}[/]  [dim]{r["instance_id"]}[/]',
        border_style='green', expand=False))
    c.print()

    left = Table(box=None, show_header=False, padding=(0, 2), expand=False)
    left.add_column(style='bold',    min_width=14, no_wrap=True)
    left.add_column(style='default')
    left.add_row('deploy-name', r['deploy_name']  )
    left.add_row('stage',       r['stage']        )
    left.add_row('creator',     r['creator']      )
    left.add_row('ami',         r['ami_id']       )
    left.add_row('instance-id', r['instance_id']  )

    right = Table(box=None, show_header=False, padding=(0, 2), expand=False)
    right.add_column(style='bold',    min_width=14, no_wrap=True)
    right.add_column(style='default')
    right.add_row('public-ip',    r['public_ip']                               )
    right.add_row('playwright',   r['playwright_url'] or '—'                   )
    right.add_row('sidecar-admin',r['sidecar_admin_url'] or '—'                )
    right.add_row('browser',      r.get('browser_url') or '—'                  )
    right.add_row('api-key-name', r['api_key_name']                            )
    right.add_row('api-key-value',f'[bold green]{r["api_key_value"]}[/]'       )

    cols = Table(box=None, show_header=False, padding=(0, 3), expand=False)
    cols.add_column()
    cols.add_column()
    cols.add_row(left, right)
    c.print(cols)

    img = Table(box=None, show_header=False, padding=(0, 2), expand=False)
    img.add_column(style='bold',    min_width=10, no_wrap=True)
    img.add_column(style='default')
    img.add_row('playwright', r['playwright_image_uri'])
    img.add_row('sidecar',    r['sidecar_image_uri']  )
    c.print()
    c.print('  [bold blue]🐳  Images[/]')
    c.print(img)
    c.print()
    c.print(f'  sg-ec2 wait {r["deploy_name"]}   ·   sg-ec2 forward 8000   ·   sg-ec2 logs')
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


def _resolve_instance_type(raw: Optional[str]) -> str:
    """Accept preset number (1-5) or a literal type string; return the instance type."""
    if raw is None:
        return EC2__INSTANCE_TYPE
    stripped = raw.strip()
    if stripped.isdigit() and 1 <= int(stripped) <= 5:
        return EC2__INSTANCE_TYPE_PRESETS[int(stripped) - 1][0]
    return stripped or EC2__INSTANCE_TYPE


def _pick_instance_type(c: Console) -> str:
    """Interactive instance-type picker — renders a Rich table and reads a choice."""
    c.print()
    t = Table(show_header=True, header_style='bold blue', box=None, padding=(0, 2))
    t.add_column('#',           justify='right',  min_width=2)
    t.add_column('type',        style='bold',     min_width=12, no_wrap=True)
    t.add_column('vCPU',        justify='right',  min_width=5)
    t.add_column('RAM',         justify='right',  min_width=6)
    t.add_column('$/hr',        justify='right',  min_width=8)
    t.add_column('notes',       style='default')
    for i, (itype, vcpu, ram, price, notes) in enumerate(EC2__INSTANCE_TYPE_PRESETS, 1):
        marker = '  [green]←  default[/]' if itype == EC2__INSTANCE_TYPE else ''
        t.add_row(str(i), itype, str(vcpu), f'{ram} GB', f'${price:.4f}', notes + marker)
    t.add_row('6', 'custom', '—', '—', '—', 'enter your own instance type')
    c.print(t)
    c.print()

    while True:
        raw = c.input('  [bold]Choose instance type[/] [dim](1–6)[/] › ').strip()
        if raw.isdigit() and 1 <= int(raw) <= 5:
            chosen = EC2__INSTANCE_TYPE_PRESETS[int(raw) - 1][0]
            c.print(f'  → [green]{chosen}[/]')
            c.print()
            return chosen
        if raw == '6':
            custom = c.input('  [bold]Instance type[/] › ').strip()
            if custom:
                c.print(f'  → [green]{custom}[/]')
                c.print()
                return custom
        c.print('  [red]Enter a number 1–6[/]')


def _ask_smoke_workflow(c: Console) -> bool:
    """Ask the user whether to run the full smoke workflow (create → wait → smoke → delete)."""
    c.print()
    c.rule('[dim]smoke workflow[/]')
    c.print()
    c.print('  After the instance is up, automatically:')
    c.print('    1. [dim]wait[/]   — poll until the service responds')
    c.print('    2. [dim]smoke[/]  — run the full 4-URL smoke test')
    c.print('    3. [dim]delete[/] — terminate the instance (pass or fail)')
    c.print()
    raw = c.input('  [bold]Run smoke workflow?[/] [dim][Y/n][/] › ').strip().lower()
    return raw in ('', 'y', 'yes')


@app.command()
def create(stage                : str           = typer.Option(DEFAULT_STAGE, help='Stage tag.')                                                              ,
           name                 : Optional[str] = typer.Option(None, '--name',             help='Deploy name (default: random two-word).')                   ,
           playwright_image_uri : Optional[str] = typer.Option(None, '--playwright-image-uri', help='Override Playwright ECR image URI.')                    ,
           sidecar_image_uri    : Optional[str] = typer.Option(None, '--sidecar-image-uri',    help='Override sidecar ECR image URI.')                       ,
           from_ami             : Optional[str] = typer.Option(None, '--from-ami',         help='Launch from a pre-baked AMI ID (skips docker install + image pull).'),
           instance_type        : Optional[str] = typer.Option(None, '--instance-type',    help=f'Instance type or preset 1–5 (default: {EC2__INSTANCE_TYPE}). E.g. --instance-type 3 or --instance-type c5.xlarge.'),
           max_hours            : int           = typer.Option(4,    '--max-hours',        help='Auto-terminate after N hours (sets shutdown timer + terminate-on-shutdown). Default: 4.'),
           interactive          : bool          = typer.Option(False, '--interactive', '-i', help='Ask questions before launching (instance type, smoke workflow).')  ,
           smoke                : bool          = typer.Option(False, '--smoke',            help='After instance is up: run smoke test then delete (implies --wait).')  ,
           wait                 : bool          = typer.Option(False, '--wait',             help='Poll health until up.')                                     ,
           timeout              : int           = typer.Option(600,  '--timeout',           help='Max seconds to wait when --wait or --smoke is set.')        ):
    """Provision an EC2 instance running the Playwright + agent_mitmproxy stack."""
    c = Console(highlight=False, width=200)

    resolved_type = _resolve_instance_type(instance_type)
    run_smoke     = smoke

    if interactive:
        c.print()
        c.print(Panel('[bold]⚙️  Create EC2 — configure instance[/]', border_style='blue', expand=False))
        if instance_type is None:
            resolved_type = _pick_instance_type(c)
        if not run_smoke:
            run_smoke = _ask_smoke_workflow(c)
        c.print()

    result           = provision(stage=stage, playwright_image_uri=playwright_image_uri,
                                  sidecar_image_uri=sidecar_image_uri, deploy_name=name or '',
                                  from_ami=from_ami, instance_type=resolved_type,
                                  max_hours=max_hours)
    _render_create_result(result)
    resolved_name    = result['deploy_name']

    if wait or run_smoke:
        _cmd_wait(ip=result['public_ip'], port=EC2__PLAYWRIGHT_PORT,
                  api_key_name=result['api_key_name'], api_key_value=result['api_key_value'],
                  timeout=timeout, interval=10)

    if run_smoke:
        smoke_ok = True
        try:
            cmd_smoke(target=resolved_name, url=(), port=EC2__PLAYWRIGHT_PORT,        # explicit values avoid OptionInfo objects when called from Python
                      no_screenshot=False, req_timeout=120)
        except SystemExit as e:
            smoke_ok = (e.code == 0 or e.code is None)

        c.print()
        c.print(Panel(f'[bold]🗑️  Deleting {resolved_name}[/]', border_style='dim', expand=False))
        cmd_delete(resolved_name)

        if not smoke_ok:
            raise typer.Exit(code=1)


@app.command(name='list')
def cmd_list():
    """List all playwright-ec2 instances with metadata from tags."""
    c         = Console(highlight=False, width=200)
    instances = find_instances(EC2())
    if not instances:
        c.print('  [dim]No instances found.[/]')
        return
    t = Table(show_header=True, header_style='bold blue', box=None, padding=(0, 2))
    t.add_column('deploy-name',    style='bold')
    t.add_column('instance-id',   style='dim')
    t.add_column('state')
    t.add_column('instance-type', style='cyan')
    t.add_column('public-ip',     style='green')
    t.add_column('creator',       style='dim')
    t.add_column('api-key',       style='dim')
    for iid, d in instances.items():
        state_raw      = d.get('state', '?')
        state          = state_raw.get('Name', '?') if isinstance(state_raw, dict) else str(state_raw)
        ip             = d.get('public_ip', '')
        deploy         = _instance_deploy_name(d)
        creator        = _instance_tag(d, TAG__CREATOR_KEY)
        api_key        = _instance_tag(d, TAG__API_KEY_VALUE_KEY)
        instance_type  = _instance_tag(d, TAG__INSTANCE_TYPE_KEY) or d.get('instance_type', '?')
        colour         = 'green' if state == 'running' else 'yellow' if state == 'pending' else 'red'
        t.add_row(deploy, iid, f'[{colour}]{state}[/]', instance_type, ip, creator, api_key)
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
        f'[bold]ℹ️   Instance info[/]  ·  {deploy_name}  [dim]{instance_id}[/]  [{colour}]{state}[/]',
        border_style=colour, expand=False))
    c.print()

    left = Table(box=None, show_header=False, padding=(0, 2), expand=False)
    left.add_column(style='bold',    min_width=14, no_wrap=True)
    left.add_column(style='default')
    left.add_row('deploy-name', r['deploy_name']  )
    left.add_row('stage',       r['stage']        )
    left.add_row('creator',     r['creator']      )
    left.add_row('ami',         r['ami_id']       )
    left.add_row('instance-id', r['instance_id']  )

    right = Table(box=None, show_header=False, padding=(0, 2), expand=False)
    right.add_column(style='bold',    min_width=14, no_wrap=True)
    right.add_column(style='default')
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
    c.print(f'  sg-ec2 forward 8000 --target {deploy_name}   ·   '
            f'sg-ec2 health {deploy_name}   ·   sg-ec2 logs --target {deploy_name}')
    c.print()


@app.command(name='delete')
def cmd_delete(name    : Optional[str] = typer.Argument(None,  help='Deploy-name or instance-id.'),
               all_flag: bool          = typer.Option(False, '--all', help='Delete ALL playwright-ec2 instances.')):
    """Delete one instance by name/id, or all with --all."""
    ec2 = EC2()
    c   = Console(highlight=False, width=200)
    if all_flag:
        instances = find_instances(ec2)
        if not instances:
            c.print('  [dim]No instances found.[/]')
            return
        c.print()
        for iid, d in instances.items():
            deploy = _instance_deploy_name(d) or iid
            c.print(f'  🗑️   [bold]{deploy}[/]  [dim]{iid}[/]')
        c.print()
        confirm = c.input(f'  [bold red]Delete all {len(instances)} instance(s)?[/] [dim][y/N][/] › ').strip().lower()
        if confirm not in ('y', 'yes'):
            c.print('  Aborted.')
            return
        deleted = terminate_instances(ec2)
    elif name:
        instance_id, details = _resolve_target(ec2, name)
        deploy = _instance_deploy_name(details) or instance_id
        c.print(f'  🗑️   Deleting [bold]{deploy}[/]  [dim]{instance_id}[/]...')
        ec2.instance_terminate(instance_id)
        deleted = [instance_id]
    else:
        c.print('  [red]Specify a deploy-name / instance-id, or pass --all to delete everything.[/]')
        raise typer.Exit(code=1)
    c.print(f'  ✅  Deleted {len(deleted)} instance(s): [dim]{", ".join(deleted) or "none"}[/]')


@app.command(name='connect')
def cmd_connect(target: Optional[str] = typer.Argument(None, help='Deploy-name or instance-id; auto-selects if only one instance.')):
    """Open an interactive SSM shell session (no SSH/key-pair needed)."""
    import subprocess
    ec2         = EC2()
    instance_id, _ = _resolve_target(ec2, target)
    typer.echo(f'  🔌  Opening SSM session → {instance_id}')
    subprocess.run(['aws', 'ssm', 'start-session', '--target', instance_id], check=False)


def _env_export_prefix(instance_id: str, details: dict) -> str:
    """Build a shell export block from instance tags — prepend to any command for automatic env injection."""
    deploy_name   = _instance_deploy_name(details)
    api_key_name  = _instance_tag(details, TAG__API_KEY_NAME_KEY)  or 'X-API-Key'
    api_key_value = _instance_tag(details, TAG__API_KEY_VALUE_KEY) or ''
    ip            = details.get('public_ip', '')
    return (f'export DEPLOY_NAME={deploy_name!r} '
            f'API_KEY_NAME={api_key_name!r} '
            f'API_KEY_VALUE={api_key_value!r} '
            f'EC2_IP={ip!r} '
            f'INSTANCE_ID={instance_id!r} '
            f'SG_PLAYWRIGHT_URL=\'http://{ip}:{EC2__PLAYWRIGHT_PORT}\' && ')


@app.command(name='env')
def cmd_env(target: Optional[str] = typer.Argument(None, help='Deploy-name or instance-id; auto-selects if only one instance.')):
    """Print export statements for all instance env vars (eval-able in bash/zsh).

    Usage:
      eval $(sg-play env quiet-volta)   # set vars in your current shell
      sg-play env quiet-volta           # inspect / paste into SSM session
    """
    ec2             = EC2()
    instance_id, d  = _resolve_target(ec2, target)
    deploy_name     = _instance_deploy_name(d)
    api_key_name    = _instance_tag(d, TAG__API_KEY_NAME_KEY)  or 'X-API-Key'
    api_key_value   = _instance_tag(d, TAG__API_KEY_VALUE_KEY) or ''
    ip              = d.get('public_ip', '')
    c               = Console(highlight=False, width=200)
    c.print()
    c.print(f'  [bold]# env — {deploy_name}  [dim]{instance_id}[/][/]')
    c.print()
    for line in [f'export DEPLOY_NAME={deploy_name!r}'              ,
                 f'export API_KEY_NAME={api_key_name!r}'            ,
                 f'export API_KEY_VALUE={api_key_value!r}'          ,
                 f'export EC2_IP={ip!r}'                            ,
                 f'export INSTANCE_ID={instance_id!r}'              ,
                 f"export SG_PLAYWRIGHT_URL='http://{ip}:{EC2__PLAYWRIGHT_PORT}'"]:
        c.print(f'  {line}')
    c.print()


@app.command(name='vault-clone')
def cmd_vault_clone(target : Optional[str] = typer.Argument(None, help='Deploy-name or instance-id; auto-selects if only one instance.'),
                    key    : str           = typer.Argument(...,  help='Vault key (id:secret format from sgit).'),
                    dir    : str           = typer.Option('/home/ssm-user', '--dir', help='Directory to clone into on the instance.')):
    """Install sgit-ai on the EC2 instance and clone a vault into /home/ssm-user (or --dir).

    Usage:
      sg-play vault-clone quiet-volta bql3zl0ky2lhvmhofrj33815:qp0flfte
    """
    ec2             = EC2()
    instance_id, d  = _resolve_target(ec2, target)
    deploy_name     = _instance_deploy_name(d)
    c               = Console(highlight=False, width=200)
    c.print()
    c.print(Panel(f'[bold]📦  Vault clone → {deploy_name}[/]  [dim]{instance_id}[/]',
                  border_style='blue', expand=False))
    c.print()
    steps = [('Installing sgit-ai',      f'pip install sgit-ai --break-system-packages -q'),
             ('Cloning vault',           f'cd {dir} && sgit clone {key}')]
    for label, command in steps:
        c.print(f'  ⏳  {label}...')
        stdout, stderr = _ssm_run(instance_id, [command], timeout=120)
        if stdout.strip():
            c.print(stdout.rstrip())
        if stderr.strip():
            c.print(f'[yellow]{stderr.rstrip()}[/]')
        c.print(f'  ✅  {label} done')
    c.print()
    c.print(f'  [bold green]Vault ready at {dir}[/]')
    c.print(f'  Run: [bold]sg-play env {deploy_name}[/]  to get the instance env vars')
    c.print()


@app.command(name='exec')
def cmd_exec(first      : str           = typer.Argument(...,  help='Deploy-name/instance-id, or shell command when only one instance exists.'),
             second     : Optional[str] = typer.Argument(None, help='Shell command when first arg is the target.'),
             cmd        : Optional[str] = typer.Option(None, '--cmd',         help='Shell command (alternative to positional).'),
             target     : Optional[str] = typer.Option(None, '--target', '-t',help='Force target; first positional arg then becomes the command.'),
             container  : Optional[str] = typer.Option(None, '--container', '-c',
                                                        help='Run inside this Compose service (playwright or agent-mitmproxy).'),
             inject_env : bool          = typer.Option(False, '--inject-env', help='Prepend DEPLOY_NAME/API_KEY_VALUE/EC2_IP/INSTANCE_ID from tags.') ):
    """Execute a shell command on the EC2 host or inside a Docker container via SSM.

    Usage patterns:
      sg-ec2 exec fresh-fermi "docker ps"        # explicit target + command
      sg-ec2 exec "docker ps"                    # auto-select target + command
      sg-ec2 exec fresh-fermi --cmd "docker ps"  # explicit target + --cmd
      sg-ec2 exec --cmd "docker ps"              # auto-select + --cmd
    """
    if target:
        resolved_target = target
        shell_cmd       = second or first or cmd
    elif second or cmd:
        resolved_target = first          # first positional = target
        shell_cmd       = second or cmd  # second positional or --cmd = command
    else:
        resolved_target = None           # auto-select
        shell_cmd       = first          # only arg = command

    if not shell_cmd:
        raise typer.BadParameter('Provide a shell command.')
    ec2             = EC2()
    instance_id, d  = _resolve_target(ec2, resolved_target)
    if inject_env:
        shell_cmd = _env_export_prefix(instance_id, d) + shell_cmd
    if container:
        shell_cmd = f'docker compose -f {COMPOSE_FILE_PATH} exec -T {container} {shell_cmd}'
    c = Console(highlight=False, width=200)
    c.print(f'  💻  [{instance_id}]{"[" + container + "]" if container else ""}  [dim]{shell_cmd}[/]')
    stdout, stderr = _ssm_run(instance_id, [shell_cmd])
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
        f'  instance   [bold]{deploy_name}[/]  [dim]{instance_id}  {public_ip}[/]\n'
        f'  tunnel     [bold]localhost:{local_port}[/]  →  [bold]{public_ip}:{remote_port}[/]\n\n'
        f'  [green]Access:[/]  [bold]http://localhost:{local_port}/[/]\n'
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
def _cmd_wait(ip           : Optional[str] = typer.Argument(None, help='Public IP, deploy-name, or instance-id; auto-selects if only one instance.'),
              port          : int           = typer.Option(EC2__PLAYWRIGHT_PORT, help='Service port.')            ,
              api_key_name  : Optional[str] = typer.Option(None, envvar='FAST_API__AUTH__API_KEY__NAME' )        ,
              api_key_value : Optional[str] = typer.Option(None, envvar='FAST_API__AUTH__API_KEY__VALUE')        ,
              timeout       : int           = typer.Option(300, help='Max seconds to wait.')                     ,
              interval      : int           = typer.Option(10,  help='Seconds between attempts.')                ):
    """Poll the health endpoint until the service responds (401 counts — key is in tags)."""
    ec2 = EC2()
    # Resolve target — also grab stored api key from tags when not supplied via option/env
    if ip and ip.replace('.', '').isdigit():
        actual_ip = ip
        tag_key_name, tag_key_value = '', ''
    else:
        _, details    = _resolve_target(ec2, ip)
        actual_ip     = details.get('public_ip', '')
        tag_key_name  = _instance_tag(details, TAG__API_KEY_NAME_KEY)
        tag_key_value = _instance_tag(details, TAG__API_KEY_VALUE_KEY)

    base_url  = f'http://{actual_ip}:{port}'
    key_name  = api_key_name  or get_env('FAST_API__AUTH__API_KEY__NAME' ) or tag_key_name  or 'X-API-Key'
    key_value = api_key_value or get_env('FAST_API__AUTH__API_KEY__VALUE') or tag_key_value or ''
    deadline  = time.time() + timeout
    typer.echo(f'  ⏳  Waiting for {base_url} (timeout {timeout}s)...')
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        try:
            r = requests.get(f'{base_url}/health/status', headers={key_name: key_value}, timeout=8)
            if r.status_code in (200, 401):              # 401 = service up, auth required
                typer.echo(f'  ✅  service up after {attempt} attempt(s)  (HTTP {r.status_code})')
                _render_health(_health_check_once(base_url, key_name, key_value), base_url)
                return
            typer.echo(f'  🔄  attempt {attempt}: HTTP {r.status_code} — retrying in {interval}s...')
        except Exception as exc:
            typer.echo(f'  🔄  attempt {attempt}: {str(exc)[:80]} — retrying in {interval}s...')
        time.sleep(interval)
    typer.echo(f'  ❌  timed out after {timeout}s', err=True)
    raise typer.Exit(1)


@app.command(name='clean')
def cmd_clean(target: Optional[str] = typer.Argument(None, help='Deploy-name or instance-id; auto-selects if only one instance.')):
    """Remove logs, credentials, and sensitive files from an instance before AMI bake."""
    ec2             = EC2()
    instance_id, d  = _resolve_target(ec2, target)
    deploy_name     = _instance_deploy_name(d)
    c               = Console(highlight=False, width=200)
    c.print()
    c.print(f'  🧹  Cleaning [bold]{deploy_name}[/]  [dim]{instance_id}[/] for AMI bake...')
    clean_instance_for_ami(instance_id)
    c.print(f'  ✅  Clean complete — credentials, logs, and user-data removed.')
    c.print()


@app.command(name='bake-ami')
def cmd_bake_ami(target  : Optional[str] = typer.Argument(None, help='Deploy-name or instance-id; auto-selects if only one instance.'),
                 ami_name : Optional[str] = typer.Option(None, '--name', help='AMI name (default: sg-playwright-{timestamp}).')):
    """Create an AMI from a running instance. Prints the AMI ID to stdout for scripting."""
    import datetime
    ec2             = EC2()
    instance_id, d  = _resolve_target(ec2, target)
    deploy_name     = _instance_deploy_name(d)
    name            = ami_name or f'sg-playwright-{datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")}'
    c               = Console(highlight=False, width=200, stderr=True)
    c.print()
    c.print(f'  📸  Creating AMI from [bold]{deploy_name}[/]  [dim]{instance_id}[/]')
    c.print(f'  name: {name}')
    ami_id = create_ami(ec2, instance_id, name)
    c.print(f'  ✅  AMI creation started: [bold]{ami_id}[/]  (status: untested)')
    c.print(f'  run [bold]sg-ec2 wait-ami {ami_id}[/] to poll until available')
    c.print()
    print(ami_id)                                                           # machine-readable to stdout


@app.command(name='wait-ami')
def cmd_wait_ami(ami_id  : str = typer.Argument(..., help='AMI ID to wait for.'),
                 timeout : int = typer.Option(900, help='Max seconds to wait.')):
    """Wait for an AMI to become available."""
    c = Console(highlight=False, width=200)
    c.print(f'\n  ⏳  Waiting for AMI [bold]{ami_id}[/] (timeout {timeout}s)...')
    ok = wait_ami_available(EC2(), ami_id, timeout=timeout)
    if ok:
        c.print(f'  ✅  AMI {ami_id} is available\n')
    else:
        c.print(f'  ❌  AMI {ami_id} failed or timed out\n', stderr=True)
        raise typer.Exit(1)


@app.command(name='tag-ami')
def cmd_tag_ami(ami_id : str = typer.Argument(..., help='AMI ID to tag.'),
                status : str = typer.Option('healthy', '--status', help='Status tag value: healthy | unhealthy | untested.')):
    """Tag an AMI with sg:ami-status (healthy, unhealthy, or untested)."""
    if status not in ('healthy', 'unhealthy', 'untested'):
        raise typer.BadParameter('--status must be healthy, unhealthy, or untested')
    tag_ami(EC2(), ami_id, status)
    colour = 'green' if status == 'healthy' else 'red' if status == 'unhealthy' else 'yellow'
    Console(highlight=False).print(f'\n  [{colour}]●[/]  {ami_id}  sg:ami-status = {status}\n')


@app.command(name='open')
def cmd_open(target: Optional[str] = typer.Argument(None, help='Deploy-name or instance-id; auto-selects if only one instance.')):
    """Open the launcher UI in a browser, pre-filled with the instance connection details."""
    import json
    import pathlib
    import tempfile
    import webbrowser

    ec2            = EC2()
    instance_id, d = _resolve_target(ec2, target)
    ip             = d.get('public_ip', '')
    deploy_name    = _instance_deploy_name(d)
    api_key_name   = _instance_tag(d, TAG__API_KEY_NAME_KEY)
    api_key_value  = _instance_tag(d, TAG__API_KEY_VALUE_KEY)

    site_dir  = (pathlib.Path(__file__).parent.parent / 'sgraph_ai_service_playwright__api_site').resolve()
    index_url = site_dir.as_uri() + '/index.html'

    config_str = json.dumps({'ip'      : ip                 ,
                              'port'    : EC2__PLAYWRIGHT_PORT,
                              'keyName' : api_key_name       ,
                              'keyValue': api_key_value      })
    bootstrap = (
        '<!DOCTYPE html>\n<script>\n'
        f'localStorage.setItem("sg_playwright_config", {json.dumps(config_str)});\n'
        f'location.replace({json.dumps(index_url)});\n'
        '</script>\n'
    )
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        f.write(bootstrap)
        tmp_path = f.name

    c = Console(highlight=False, width=200)
    c.print()
    c.print(f'  Opening launcher for [bold #111111]{deploy_name}[/]  [#555555]{ip}:{EC2__PLAYWRIGHT_PORT}[/]')
    c.print(f'  [#555555]{index_url}[/]')
    c.print()
    webbrowser.open(f'file://{tmp_path}')


@app.command(name='screenshot')
def cmd_screenshot(
        url         : str            = typer.Argument(...,                    help='URL to screenshot.'),
        target      : Optional[str]  = typer.Option(None, '--target', '-t',  help='Deploy-name or instance-id; auto-selects if only one instance.'),
        full_page   : bool           = typer.Option(True,  '--full-page/--viewport-only',
                                                    help='Capture full page height (default) or only visible viewport.'),
        width       : int            = typer.Option(1280,  '--width',         help='Viewport width in pixels.'),
        height      : int            = typer.Option(800,   '--height',        help='Viewport height in pixels.'),
        wait_until  : str            = typer.Option('load','--wait-until',    help='Playwright waitUntil: load, domcontentloaded, networkidle.'),
        timeout_ms  : int            = typer.Option(0,     '--timeout-ms',    help='Navigation timeout in ms (0 = Playwright default).'),
        port        : int            = typer.Option(EC2__PLAYWRIGHT_PORT,     help='Service port.'),
        save        : Optional[str]  = typer.Option(None, '--save',           help='Save PNG to this path instead of a temp file.'),
        no_open     : bool           = typer.Option(False, '--no-open',       help='Do not open the screenshot in the system viewer.')):
    """Take a quick screenshot — navigate to URL, capture PNG, open locally."""
    import pathlib
    import tempfile
    import webbrowser

    ec2          = EC2()
    _, details   = _resolve_target(ec2, target)
    ip           = details.get('public_ip', '')
    key_name     = _instance_tag(details, TAG__API_KEY_NAME_KEY)  or 'X-API-Key'
    key_value    = _instance_tag(details, TAG__API_KEY_VALUE_KEY) or ''
    deploy_name  = _instance_deploy_name(details)
    base_url     = f'http://{ip}:{port}'

    payload = {
        'url'        : url,
        'full_page'  : full_page,
        'viewport'   : {'width': width, 'height': height},
        'wait_until' : wait_until,
        'timeout_ms' : timeout_ms,
    }

    c = Console(highlight=False, width=200)
    c.print()
    c.print(Panel(f'[bold]📸  Screenshot[/]  ·  {deploy_name}  [dim]{base_url}[/]', border_style='blue', expand=False))
    c.print(f'  [dim]url={url}  full_page={full_page}  {width}×{height}  wait_until={wait_until}[/]')
    c.print()
    c.print('  → requesting...', end='')

    t0 = time.time()
    try:
        resp = requests.post(
            f'{base_url}/browser/screenshot',
            json    = payload,
            headers = {key_name: key_value, 'accept': 'image/png', 'Content-Type': 'application/json'},
            timeout = 120,
        )
    except Exception as exc:
        c.print(f'  [red]ERR  {exc}[/]')
        raise typer.Exit(code=1)

    elapsed_ms = int((time.time() - t0) * 1000)

    if resp.status_code != 200:
        c.print(f'  [red]HTTP {resp.status_code}  {resp.text[:120]}[/]')
        raise typer.Exit(code=1)

    kb = len(resp.content) // 1024
    c.print(f'  [green]{elapsed_ms} ms  {kb} KB[/]')
    c.print()

    out_path = save or tempfile.mktemp(suffix='.png', prefix='sg_screenshot_')
    pathlib.Path(out_path).write_bytes(resp.content)

    c.print(_kv_table(
        ('URL',       url),
        ('Size',      f'{kb} KB  ({len(resp.content):,} bytes)'),
        ('Elapsed',   f'{elapsed_ms} ms'),
        ('Viewport',  f'{width}×{height}  full_page={full_page}'),
        ('Saved to',  out_path),
    ))
    c.print()

    if not no_open:
        webbrowser.open(f'file://{out_path}')
        c.print(f'  [dim]opened in system viewer[/]')
        c.print()


@app.command(name='smoke')
def cmd_smoke(target          : Optional[str]  = typer.Argument(None, help='Deploy-name or instance-id; auto-selects if only one instance.'),
              url             : List[str]       = typer.Option([], '--url', '-u', help='URL to test (repeatable). Default: standard smoke set.'),
              port            : int             = typer.Option(EC2__PLAYWRIGHT_PORT, help='Service port.'),
              no_screenshot   : bool            = typer.Option(False, '--no-screenshot', help='Skip screenshot step (navigate timing only).'),
              req_timeout     : int             = typer.Option(120, '--timeout', help='Per-request timeout in seconds.')):
    """Screenshot smoke test across URLs — reports navigate timing, image size, and mitmproxy flow count."""
    ec2            = EC2()
    _, details     = _resolve_target(ec2, target)
    ip             = details.get('public_ip', '')
    key_name       = _instance_tag(details, TAG__API_KEY_NAME_KEY)  or 'X-API-Key'
    key_value      = _instance_tag(details, TAG__API_KEY_VALUE_KEY) or ''
    deploy_name    = _instance_deploy_name(details)
    test_urls      = list(url) or SMOKE_URLS
    base_url       = f'http://{ip}:{port}'
    sidecar_url    = f'http://{ip}:{EC2__SIDECAR_ADMIN_PORT}'
    auth_headers   = {key_name: key_value}
    json_headers   = {**auth_headers, 'Content-Type': 'application/json', 'accept': 'application/json'}

    c = Console(highlight=False, width=200)
    c.print()
    c.print(Panel(f'[bold]🧪  Smoke Test[/]  ·  {deploy_name}  [dim]{base_url}[/]', border_style='blue', expand=False))
    c.print(f'  [dim]{len(test_urls)} URLs · 3 requests each (1 cold + 2 warm) · screenshot per URL[/]')
    c.print()

    smoke_t0 = time.time()
    rows     = []   # accumulated for summary table
    passed   = 0
    failed   = 0

    for idx, test_url in enumerate(test_urls, 1):
        c.print(f'  [{idx}/{len(test_urls)}] [bold]{test_url}[/]')
        payload = {'url': test_url, 'wait_until': 'load', 'timeout_ms': 0}

        durations = []
        last_nav  = None
        error_msg = None

        for req_num in range(3):
            label = 'cold' if req_num == 0 else f'warm {req_num}'
            c.print(f'        {label:<7}  · ', end='')
            try:
                t0      = time.time()
                nav     = requests.post(f'{base_url}/browser/navigate', json=payload, headers=json_headers, timeout=req_timeout)
                elapsed = int((time.time() - t0) * 1000)
                if nav.status_code == 200:
                    try:
                        ms = nav.json().get('duration_ms') or elapsed
                    except Exception:
                        ms = elapsed
                    c.print(f'[green]{elapsed:>6} ms[/]')
                else:
                    ms = elapsed
                    c.print(f'[red]HTTP {nav.status_code}  {elapsed} ms[/]')
                durations.append(ms)
                if req_num == 0:
                    last_nav = nav
            except Exception as exc:
                error_msg = str(exc)[:60]
                c.print(f'[red]ERR  {error_msg}[/]')
                break

        if error_msg and not durations:
            c.print(f'        [red]✗ connection error[/]')
            c.print()
            rows.append((test_url, '[red]ERR[/]', '—', '—', '—', error_msg))
            failed += 1
            continue

        first_ms = durations[0] if durations else 0
        warm_ms  = int(sum(durations[1:]) / len(durations[1:])) if len(durations) >= 2 else None

        if last_nav and last_nav.status_code == 200:
            try:
                j = last_nav.json()
            except Exception:
                j = {}
            final_url  = j.get('final_url', test_url)
            status_str = '[green]200[/]'
            ok         = True
        else:
            final_url  = test_url
            status_str = f'[red]{last_nav.status_code if last_nav else "ERR"}[/]'
            ok         = False

        image_kb = '—'
        if not no_screenshot and ok:
            c.print(f'        {"shot":<7}  · ', end='')
            try:
                ss = requests.post(f'{base_url}/browser/screenshot', json=payload,
                                   headers={**auth_headers, 'accept': 'image/png',
                                            'Content-Type': 'application/json'},
                                   timeout=req_timeout)
                if ss.status_code == 200:
                    kb       = len(ss.content) // 1024
                    image_kb = f'{kb} KB'
                    c.print(f'[green]{kb:>6} KB[/]')
                else:
                    c.print(f'[red]HTTP {ss.status_code}[/]')
            except Exception:
                c.print('[red]ERR[/]')

        warm_str = f'{warm_ms} ms' if warm_ms is not None else '—'
        if ok:
            c.print(f'        [green]✓ 200[/]  cold=[bold]{first_ms} ms[/]  warm={warm_str}  {image_kb}')
            passed += 1
        else:
            c.print(f'        [red]✗ {status_str}[/]  cold={first_ms} ms')
            failed += 1
        c.print()
        rows.append((test_url, status_str, f'{first_ms} ms', warm_str, image_kb, final_url))

    # ── Summary table ─────────────────────────────────────────────────────────
    elapsed_total = int(time.time() - smoke_t0)
    overall_color = 'green' if failed == 0 else 'red'
    overall_icon  = '✓' if failed == 0 else '✗'
    c.rule(f'[{overall_color}]{overall_icon}  {passed}/{len(test_urls)} passed[/]  ·  {elapsed_total}s total')
    c.print()

    t = Table(show_header=True, header_style='bold blue', box=None, padding=(0, 2))
    t.add_column('url',        style='bold', min_width=28, no_wrap=True)
    t.add_column('status',     min_width=6)
    t.add_column('1st_ms',     min_width=10, justify='right')
    t.add_column('warm_ms',    min_width=10, justify='right')
    t.add_column('image_kb',   min_width=9)
    t.add_column('final_url',  style='default')
    for row in rows:
        t.add_row(*row)
    c.print(t)
    c.print()

    # ── Aggregate stats ───────────────────────────────────────────────────────
    cold_vals  = [int(r[2].replace(' ms','')) for r in rows if r[2] != '—']
    warm_vals  = [int(r[3].replace(' ms','')) for r in rows if r[3] != '—']
    kb_vals    = [int(r[4].replace(' KB','')) for r in rows if r[4] != '—']
    avg_cold   = int(sum(cold_vals) / len(cold_vals)) if cold_vals else None
    avg_warm   = int(sum(warm_vals) / len(warm_vals)) if warm_vals else None
    total_kb   = sum(kb_vals)
    stats = _kv_table(
        ('URLs tested',    f'{len(test_urls)}'),
        ('Passed / failed', f'[green]{passed}[/] / [{"red" if failed else "dim"}]{failed}[/]'),
        ('Avg cold (1st)', f'{avg_cold} ms' if avg_cold else '—'),
        ('Avg warm (2+3)', f'{avg_warm} ms' if avg_warm else '—'),
        ('Total screenshot', f'{total_kb} KB' if kb_vals else '—'),
        ('Total elapsed',   f'{elapsed_total}s'),
    )
    c.print(stats)
    c.print()

    # ── Mitmproxy flow stats ──────────────────────────────────────────────────
    try:
        flows_r = requests.get(f'{sidecar_url}/web/flows', headers=auth_headers, timeout=15)
        if flows_r.status_code == 200:
            flows = flows_r.json()
            if isinstance(flows, list):
                hosts = {}
                for f in flows:
                    host = (f.get('request', {}) or {}).get('host', '?')
                    hosts[host] = hosts.get(host, 0) + 1
                c.print(f'  🔭  mitmproxy: [bold]{len(flows)}[/] flows across {len(hosts)} hosts')
                for host, count in sorted(hosts.items(), key=lambda x: -x[1])[:6]:
                    c.print(f'      [dim]{count:3d}[/]  {host}')
            else:
                c.print(f'  🔭  mitmproxy flows: {flows_r.text[:120]}')
        else:
            c.print(f'  🔭  mitmproxy /web/flows → HTTP {flows_r.status_code}')
    except Exception as exc:
        c.print(f'  🔭  mitmproxy flows unavailable: {str(exc)[:80]}')

    c.print()
    c.print(f'  Mitmproxy UI  →  sg-ec2 forward {EC2__SIDECAR_ADMIN_PORT}    then  http://localhost:{EC2__SIDECAR_ADMIN_PORT}/web/')
    c.print(f'  Browser       →  sg-ec2 forward-browser       then  http://localhost:{EC2__BROWSER_INTERNAL_PORT}/')
    c.print(f'  Prometheus    →  sg-ec2 forward-prometheus     then  http://localhost:{EC2__PROMETHEUS_PORT}/')
    c.print()

    if failed:
        raise typer.Exit(code=1)


@app.command(name='health')
def cmd_health(ip           : Optional[str] = typer.Argument(None, help='Public IP, deploy-name, or instance-id; auto-selects if only one instance.'),
               port          : int           = typer.Option(EC2__PLAYWRIGHT_PORT, help='Service port.')           ,
               api_key_name  : Optional[str] = typer.Option(None, envvar='FAST_API__AUTH__API_KEY__NAME' )       ,
               api_key_value : Optional[str] = typer.Option(None, envvar='FAST_API__AUTH__API_KEY__VALUE')       ):
    """Run health checks against a live instance and display results."""
    ec2           = EC2()
    tag_key_name  = ''
    tag_key_value = ''
    if ip and ip.replace('.', '').isdigit():
        actual_ip = ip
    else:
        _, details    = _resolve_target(ec2, ip)
        actual_ip     = details.get('public_ip', '')
        tag_key_name  = _instance_tag(details, TAG__API_KEY_NAME_KEY)
        tag_key_value = _instance_tag(details, TAG__API_KEY_VALUE_KEY)
    base_url  = f'http://{actual_ip}:{port}'
    key_name  = api_key_name  or get_env('FAST_API__AUTH__API_KEY__NAME' ) or tag_key_name  or 'X-API-Key'
    key_value = api_key_value or get_env('FAST_API__AUTH__API_KEY__VALUE') or tag_key_value or ''
    _render_health(_health_check_once(base_url, key_name, key_value), base_url)


@app.command(name='forward-prometheus')
def cmd_forward_prometheus(target: Optional[str] = typer.Argument(None, help='Deploy-name or instance-id; auto-selects if only one instance.')):
    """Forward Prometheus (port 9090) to localhost via SSM."""
    import subprocess
    ec2                  = EC2()
    instance_id, details = _resolve_target(ec2, target)
    deploy_name          = _instance_deploy_name(details) or instance_id
    c = Console(highlight=False, width=200)
    c.print()
    c.print(Panel(
        f'[bold]🔥  Prometheus Forward[/]\n\n'
        f'  instance   [bold]{deploy_name}[/]  [dim]{instance_id}[/]\n'
        f'  tunnel     [bold]localhost:{EC2__PROMETHEUS_PORT}[/]\n\n'
        f'  [green]Access:[/]  [bold]http://localhost:{EC2__PROMETHEUS_PORT}/[/]\n'
        f'  [dim]Press Ctrl-C to close the tunnel.[/]',
        border_style='bright_blue', expand=False))
    c.print()
    subprocess.run(['aws', 'ssm', 'start-session',
                    '--target'       , instance_id,
                    '--document-name', 'AWS-StartPortForwardingSession',
                    '--parameters'   , json.dumps({'portNumber'     : [str(EC2__PROMETHEUS_PORT)],
                                                   'localPortNumber': [str(EC2__PROMETHEUS_PORT)]})],
                   check=False)


@app.command(name='forward-browser')
def cmd_forward_browser(target: Optional[str] = typer.Argument(None, help='Deploy-name or instance-id; auto-selects if only one instance.')):
    """Forward the streaming browser (linuxserver/chromium) to localhost via SSM.

    Opens a real Chrome session pre-configured to route through mitmproxy —
    the manual equivalent of what the playwright containers do automatically.
    All traffic is visible in real time at sg-ec2 forward 8001 → /web/flows.
    """
    import subprocess
    ec2                  = EC2()
    instance_id, details = _resolve_target(ec2, target)
    deploy_name          = _instance_deploy_name(details) or instance_id
    c = Console(highlight=False, width=200)
    c.print()
    c.print(Panel(
        f'[bold]🌐  Browser Forward[/]\n\n'
        f'  instance   [bold]{deploy_name}[/]  [dim]{instance_id}[/]\n'
        f'  tunnel     [bold]localhost:{EC2__BROWSER_INTERNAL_PORT}[/]\n\n'
        f'  [green]Access:[/]  [bold]http://localhost:{EC2__BROWSER_INTERNAL_PORT}/[/]\n'
        f'  [dim]All traffic routes through mitmproxy — flows visible via sg-ec2 forward {EC2__SIDECAR_ADMIN_PORT}[/]\n'
        f'  [dim]Press Ctrl-C to close the tunnel.[/]',
        border_style='bright_blue', expand=False))
    c.print()
    subprocess.run(['aws', 'ssm', 'start-session',
                    '--target'       , instance_id,
                    '--document-name', 'AWS-StartPortForwardingSession',
                    '--parameters'   , json.dumps({'portNumber'     : [str(EC2__BROWSER_INTERNAL_PORT)],
                                                   'localPortNumber': [str(EC2__BROWSER_INTERNAL_PORT)]})],
                   check=False)


@app.command(name='metrics')
def cmd_metrics(service : str           = typer.Argument('playwright', help='Service to query: playwright or mitmproxy.'),
                target  : Optional[str] = typer.Option(None, '--target', '-t', help='Deploy-name or instance-id (auto if only one).') ):
    """Fetch Prometheus metrics text from a service on the EC2 host via SSM."""
    ec2             = EC2()
    instance_id, d  = _resolve_target(ec2, target)
    deploy_name     = _instance_deploy_name(d)
    api_key_name    = _instance_tag(d, TAG__API_KEY_NAME_KEY)  or 'X-API-Key'
    api_key_value   = _instance_tag(d, TAG__API_KEY_VALUE_KEY) or ''
    port_map        = {'playwright': EC2__PLAYWRIGHT_PORT, 'mitmproxy': EC2__SIDECAR_ADMIN_PORT}
    port            = port_map.get(service, EC2__PLAYWRIGHT_PORT)
    cmd             = f"curl -s http://localhost:{port}/metrics -H '{api_key_name}: {api_key_value}'"
    c = Console(highlight=False, width=200)
    c.print(f'\n  📈  metrics [{service}] from [bold]{deploy_name}[/]  [dim]{instance_id}[/]')
    stdout, stderr = _ssm_run(instance_id, [cmd], timeout=30)
    if stdout.strip():
        c.print(stdout.rstrip())
    if stderr.strip():
        c.print(f'[yellow]{stderr.rstrip()}[/]')
    c.print()


if __name__ == '__main__':
    app()

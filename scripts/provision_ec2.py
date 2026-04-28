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
#   3. Runs a m6i.xlarge AL2023 instance. UserData installs Docker + the Compose
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
# Cost note: m6i.xlarge on-demand is ~$0.192/h. Always --terminate when done.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import secrets
import shlex
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
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

from sgraph_ai_service_playwright__cli.ec2.service.Ec2__AWS__Client                      import (Ec2__AWS__Client                                            ,
                                                                                                  EC2__AMI_NAME_AL2023                                        ,
                                                                                                  EC2__AMI_OWNER_AMAZON                                       ,
                                                                                                  EC2__BROWSER_INTERNAL_PORT                                  ,
                                                                                                  EC2__PLAYWRIGHT_PORT                                        ,
                                                                                                  EC2__SIDECAR_ADMIN_PORT                                     ,
                                                                                                  IAM__ASSUME_ROLE_SERVICE                                    ,
                                                                                                  IAM__ECR_READONLY_POLICY_ARN                                ,
                                                                                                  IAM__OBSERVABILITY_POLICY_ARNS                              ,
                                                                                                  IAM__PASSROLE_POLICY_NAME                                   ,
                                                                                                  IAM__POLICY_ARNS                                            ,
                                                                                                  IAM__PROMETHEUS_RW_POLICY_ARN                               ,
                                                                                                  IAM__ROLE_NAME                                              ,
                                                                                                  IAM__SSM_CORE_POLICY_ARN                                    ,
                                                                                                  SG__DESCRIPTION                                             ,
                                                                                                  SG__NAME                                                    ,
                                                                                                  TAG__AMI_STATUS_KEY                                         ,
                                                                                                  aws_account_id                                              ,
                                                                                                  aws_region                                                  ,
                                                                                                  decode_aws_auth_error        as _decode_aws_auth_error     ,
                                                                                                  default_playwright_image_uri                                ,
                                                                                                  default_sidecar_image_uri                                   ,
                                                                                                  ecr_registry_host                                           ,
                                                                                                  ensure_caller_passrole                                      ,
                                                                                                  ensure_instance_profile                                     ,
                                                                                                  get_creator                  as _get_creator               ,
                                                                                                  instance_deploy_name         as _instance_deploy_name      ,
                                                                                                  instance_tag                 as _instance_tag              ,
                                                                                                  random_deploy_name           as _random_deploy_name        ,
                                                                                                  uptime_str                   as _uptime_str                )


EC2__INSTANCE_TYPE           = 'm6i.xlarge'                                             # 4 vCPU / 16 GB RAM — fixed CPU (no burst credits), fits full observability stack
# EC2__AMI_NAME_AL2023, EC2__AMI_OWNER_AMAZON, EC2__PLAYWRIGHT_PORT,
# EC2__SIDECAR_ADMIN_PORT, EC2__BROWSER_INTERNAL_PORT moved to Ec2__AWS__Client
# (Phase A step 3d) — imported at top.

# ── Instance-type presets (shown by sg-ec2 create --interactive) ──────────────
EC2__INSTANCE_TYPE_PRESETS = [
    ('m6i.xlarge' , 4, 16 , 0.1920, 'default · fixed CPU · balanced RAM'     ),
    ('c6i.xlarge' , 4, 8  , 0.1700, 'compute-optimised · lower cost'         ),
    ('m6i.2xlarge', 8, 32 , 0.3840, 'double RAM · heavy investigation'        ),
    ('t3.large'   , 2, 8  , 0.0832, 'burstable · dev/test only'              ),
    ('t3.xlarge'  , 4, 16 , 0.1664, 'burstable · dev/test only'              ),
]
EC2__MITMWEB_TUNNEL_PORT    = 18080                                                    # mitmweb proxy UI — loopback only; reach via: sgpl forward 18080

WATCHDOG_MAX_REQUEST_MS      = 120_000                                                  # 120s — covers Firefox + long upstream-proxy round-trips

# IAM__ROLE_NAME, IAM__ECR_READONLY_POLICY_ARN, IAM__SSM_CORE_POLICY_ARN,
# IAM__POLICY_ARNS, IAM__PROMETHEUS_RW_POLICY_ARN, IAM__OBSERVABILITY_POLICY_ARNS,
# IAM__ASSUME_ROLE_SERVICE moved to Ec2__AWS__Client (Phase A step 3c) —
# imported at the top of this file under the same names.

EC2__PROMETHEUS_PORT      = 9090
EC2__BROWSER_IMAGE         = 'lscr.io/linuxserver/chromium:latest'                     # public image — pulled explicitly before compose up
EC2__DOCKGE_PORT           = 5001                                                      # Dockge — SSM-forward only; first login sets admin password
EC2__DOCKGE_IMAGE          = 'louislam/dockge:1'                                       # public image — pulled explicitly before compose up

# SG__NAME, SG__DESCRIPTION moved to Ec2__AWS__Client (Phase A step 3d) —
# imported at top.

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

# _ADJECTIVES + _SCIENTISTS pools moved to Ec2__AWS__Client (Phase A step 3a).
# Helpers (_random_deploy_name, _get_creator, _uptime_str, _instance_tag,
# _instance_deploy_name) imported at the top of this file under the original
# underscored names for callsite stability.

COMPOSE_PROJECT   = 'sg-playwright'
COMPOSE_FILE_PATH            = '/opt/sg-playwright/docker-compose.yml'
DOCKER__PLAYWRIGHT_CONTAINER = 'sg-playwright-playwright-1'

SMOKE_URLS = ['https://www.google.com'   ,
              'https://sgraph.ai'         ,
              'https://send.sgraph.ai'    ,
              'https://news.bbc.co.uk'    ]

# TAG__AMI_STATUS_KEY moved to Ec2__AWS__Client (Phase A step 3d) — imported at top.

DASHBOARDS_DIR = Path(__file__).parent.parent / 'library' / 'docs' / 'ops' / 'dashboards'

# Short user_data for AMI-based launches: Docker + images already baked in,
# just write the compose file (fresh API key) and start containers.
AMI_USER_DATA_TEMPLATE = """\
#!/bin/bash
set -euxo pipefail
exec > >(tee /var/log/sg-playwright-start.log | logger -t sg-playwright) 2>&1

BOOT_STATUS_FILE=/var/log/sg-playwright-boot-status
echo "PENDING $(date --iso-8601=seconds)" > "$BOOT_STATUS_FILE"
trap 'echo "FAILED at $(date --iso-8601=seconds) — exit $?" > "$BOOT_STATUS_FILE"' EXIT

echo "=== SG Playwright AMI boot at $(date) ==="

mkdir -p /opt/sg-playwright/config /opt/dockge/data

cat > /opt/sg-playwright/docker-compose.yml << 'SG_COMPOSE_EOF'
{compose_content}
SG_COMPOSE_EOF

{observability_configs_section}
{browser_proxy_section}
{browser_image_pull}
docker pull {dockge_image} || true
docker compose -f /opt/sg-playwright/docker-compose.yml up -d

# Write container ID → service name map for fluent-bit log enrichment
sleep 5
docker ps --format '{{{{.ID}}}} {{{{.Names}}}}' \
  | sed 's/ sg-playwright-/ /; s/-[0-9]*$//' \
  > /opt/sg-playwright/config/container-names.txt || true

echo "=== SG Playwright AMI start complete at $(date) ==="
echo "OK $(date --iso-8601=seconds)" > "$BOOT_STATUS_FILE"
trap - EXIT
"""


# _random_deploy_name / _get_creator / _uptime_str moved to Ec2__AWS__Client
# (Phase A step 3a) — imported as aliases at the top of this file.


COMPOSE_SVC_PLAYWRIGHT = """\
  playwright:
    image: {playwright_image_uri}
    ports:
      - "{playwright_port}:{playwright_port}"
    environment:
      FAST_API__AUTH__API_KEY__NAME:          '{api_key_name}'
      FAST_API__AUTH__API_KEY__VALUE:         '{api_key_value}'
      SG_PLAYWRIGHT__DEPLOYMENT_TARGET:       container
      SG_PLAYWRIGHT__DEFAULT_PROXY_URL:       "http://agent-mitmproxy:8080"
      SG_PLAYWRIGHT__IGNORE_HTTPS_ERRORS:     'true'
      SG_PLAYWRIGHT__WATCHDOG_MAX_REQUEST_MS: {watchdog_max_request_ms}
    networks:
      - sg-net
    depends_on:
      - agent-mitmproxy
    restart: always
"""

COMPOSE_SVC_MITMPROXY = """\
  agent-mitmproxy:
    image: {sidecar_image_uri}
    ports:
      - "{sidecar_admin_port}:8000"
      - "127.0.0.1:18080:8080"
    environment:
      FAST_API__AUTH__API_KEY__NAME:  '{api_key_name}'
      FAST_API__AUTH__API_KEY__VALUE: '{api_key_value}'
      AGENT_MITMPROXY__UPSTREAM_URL:  '{upstream_url}'
      AGENT_MITMPROXY__UPSTREAM_USER: '{upstream_user}'
      AGENT_MITMPROXY__UPSTREAM_PASS: '{upstream_pass}'
      AGENT_MITMPROXY__HTTP2:         '{http2}'
    networks:
      - sg-net
    restart: always
"""

# browser + browser-proxy: only when upstream proxy is configured
COMPOSE_SVC_BROWSER = """\
  browser:
    image: {browser_image_uri}
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
"""

COMPOSE_SVC_BROWSER_PROXY = """\
  browser-proxy:
    image: nginx:alpine
    ports:
      - "{browser_port}:{browser_port}"
    volumes:
      - /opt/sg-playwright/config/nginx-browser.conf:/etc/nginx/conf.d/default.conf:ro
      - /opt/sg-playwright/config/browser-certs:/etc/nginx/certs:ro
    networks:
      - sg-net
    depends_on:
      - browser
    restart: unless-stopped
"""

# cadvisor + node-exporter + prometheus: only when AMP_REMOTE_WRITE_URL is configured
COMPOSE_SVC_CADVISOR = """\
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
"""

COMPOSE_SVC_NODE_EXPORTER = """\
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
"""

COMPOSE_SVC_PROMETHEUS = """\
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
"""

# fluent-bit: only when OPENSEARCH_ENDPOINT is configured
COMPOSE_SVC_FLUENT_BIT = """\
  fluent-bit:
    image: amazon/aws-for-fluent-bit:stable
    command: /fluent-bit/bin/fluent-bit -c /opt/sg-playwright/config/fluent-bit.conf
    volumes:
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /opt/sg-playwright/config:/opt/sg-playwright/config:ro
    networks:
      - sg-net
    restart: always
"""

COMPOSE_SVC_DOCKGE = """\
  dockge:
    image: {dockge_image}
    ports:
      - "127.0.0.1:{dockge_port}:{dockge_port}"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - /opt/dockge/data:/app/data
    environment:
      DOCKGE_STACKS_DIR: /opt
    networks:
      - sg-net
    restart: always
"""

COMPOSE_FOOTER = """\
networks:
  sg-net:
    driver: bridge

volumes:
{volume_lines}
"""


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

FLUENT_BIT_PARSERS_CUSTOM = """\
# uvicorn/FastAPI access log: INFO:     <ip>:<port> - "<METHOD> <path> HTTP/<ver>" <status> <text>
[PARSER]
    Name        uvicorn_access
    Format      regex
    Regex       ^INFO:\\s+(?<client_ip>[^:]+):\\d+ - "(?<http_method>[A-Z]+) (?<http_path>[^ ]+) HTTP/[^"]*" (?<http_status>\\d+)
    Types       http_status:integer
"""

# Lua filter: maps 12-char container ID → service name by reading container-names.txt
# The names file is written by the host after `docker compose up -d` so it's always fresh.
# Short-ID lookup matches the 12-char prefix that `docker ps` shows.
FLUENT_BIT_LUA_CONTAINER_NAME = """\
local cache    = {}
local map_file = "/opt/sg-playwright/config/container-names.txt"

local function load_map()
    local f = io.open(map_file, "r")
    if not f then return end
    for line in f:lines() do
        local id, name = line:match("^(%S+)%s+(.+)$")
        if id and name then cache[id] = name end
    end
    f:close()
end

load_map()

function add_container_name(tag, timestamp, record)
    local path = record["container_path"]
    if not path then return 0, timestamp, record end
    local cid = path:match("/containers/([0-9a-f]+)/")
    if not cid then return 0, timestamp, record end
    local short = cid:sub(1, 12)
    if not cache[short] then load_map() end         -- reload if container started after fluent-bit
    record["container_name"] = cache[short] or short
    return 1, timestamp, record
end
"""

FLUENT_BIT_CONF_TEMPLATE = """\
[SERVICE]
    Flush         1
    Daemon        Off
    Log_Level     info
    Parsers_File  /fluent-bit/etc/parsers.conf
    Parsers_File  /opt/sg-playwright/config/parsers_custom.conf

[INPUT]
    Name              tail
    Path              /var/lib/docker/containers/*/*.log
    Parser            docker
    Tag               docker.*
    Refresh_Interval  5
    Mem_Buf_Limit     5MB
    Skip_Long_Lines   On
    Path_Key          container_path

[FILTER]
    Name    record_modifier
    Match   *
    Record  stack        sg-playwright
    Record  environment  {stage}

# Add container_name field by looking up the short container ID in container-names.txt
[FILTER]
    Name    lua
    Match   docker.*
    script  /opt/sg-playwright/config/container_name.lua
    call    add_container_name

# Parse FastAPI/uvicorn access log lines into structured fields
[FILTER]
    Name         parser
    Match        docker.*
    Key_Name     log
    Parser       uvicorn_access
    Reserve_Data On
    Preserve_Key On

# Drop /health/ polling — high-volume noise with no signal value
[FILTER]
    Name    grep
    Match   docker.*
    Exclude http_path  ^/health/

# Drop blank / whitespace-only log lines
[FILTER]
    Name   grep
    Match  docker.*
    Regex  log  \\S

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

NGINX_BROWSER_CONF_TEMPLATE = """\
server {{
    listen {browser_port} ssl;
    ssl_certificate     /etc/nginx/certs/cert.pem;
    ssl_certificate_key /etc/nginx/certs/key.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    location / {{
        auth_basic           "VNC Viewer";
        auth_basic_user_file /etc/nginx/certs/.htpasswd;
        proxy_pass         http://browser:3000;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade    $http_upgrade;
        proxy_set_header   Connection upgrade;
        proxy_set_header   Host       $host;
        proxy_read_timeout 86400;
    }}
}}
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
        opensearch_host = opensearch_endpoint.removeprefix('https://').removeprefix('http://')
        output_section = FLUENT_BIT_OUTPUT_OPENSEARCH.format(
            opensearch_endpoint = opensearch_host,
            region              = region)
    else:
        output_section = FLUENT_BIT_OUTPUT_STDOUT
    fluent_bit_conf = FLUENT_BIT_CONF_TEMPLATE.format(output_section=output_section, stage=stage)

    parts = [
        f"cat > /opt/sg-playwright/config/prometheus.yml << 'SG_PROM_EOF'\n{prometheus_yml}SG_PROM_EOF",
        f"cat > /opt/sg-playwright/config/parsers_custom.conf << 'SG_FB_PARSERS_EOF'\n{FLUENT_BIT_PARSERS_CUSTOM}SG_FB_PARSERS_EOF",
        f"cat > /opt/sg-playwright/config/container_name.lua << 'SG_FB_LUA_EOF'\n{FLUENT_BIT_LUA_CONTAINER_NAME}SG_FB_LUA_EOF",
        f"cat > /opt/sg-playwright/config/fluent-bit.conf << 'SG_FB_EOF'\n{fluent_bit_conf}SG_FB_EOF",
    ]
    return '\n\n'.join(parts) + '\n'


def render_browser_proxy_section(api_key_value: str = '') -> str:
    nginx_conf = NGINX_BROWSER_CONF_TEMPLATE.format(browser_port=EC2__BROWSER_INTERNAL_PORT)
    # token_urlsafe keys are base64url (A-Za-z0-9_-) — safe to embed in single-quoted shell string
    # Capture hash into a variable first so redirect only runs if openssl succeeded
    htpasswd_line = (
        f"_htpw=$(openssl passwd -apr1 '{api_key_value}')\n"
        f"echo \"viewer:$_htpw\" > /opt/sg-playwright/config/browser-certs/.htpasswd\n"
        f"[ -s /opt/sg-playwright/config/browser-certs/.htpasswd ] "
        f"|| {{ echo 'ERROR: .htpasswd is empty — openssl passwd -apr1 failed' >&2; exit 1; }}\n"
        f"chmod 644 /opt/sg-playwright/config/browser-certs/.htpasswd\n"
    )
    return (
        'mkdir -p /opt/sg-playwright/config /opt/dockge/data/browser-certs\n'
        'openssl req -x509 -nodes -days 3650 -newkey rsa:2048'
        ' -keyout /opt/sg-playwright/config/browser-certs/key.pem'
        ' -out    /opt/sg-playwright/config/browser-certs/cert.pem'
        " -subj   '/CN=sg-playwright-browser'\n\n"
        f"{htpasswd_line}\n"
        f"cat > /opt/sg-playwright/config/nginx-browser.conf << 'SG_NGINX_EOF'\n"
        f"{nginx_conf}"
        f"SG_NGINX_EOF\n"
    )


USER_DATA_TEMPLATE = """\
#!/bin/bash
set -euxo pipefail
exec > >(tee /var/log/sg-playwright-setup.log | logger -t sg-playwright) 2>&1

BOOT_STATUS_FILE=/var/log/sg-playwright-boot-status
echo "PENDING $(date --iso-8601=seconds)" > "$BOOT_STATUS_FILE"
trap 'echo "FAILED at $(date --iso-8601=seconds) — exit $?" > "$BOOT_STATUS_FILE"' EXIT

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
{browser_image_pull}
docker pull {dockge_image}

# Revoke the stored Docker credential immediately after pull — the instance
# profile (AmazonEC2ContainerRegistryReadOnly) provides fresh tokens on demand
# so nothing needs to persist.  This also keeps AMI snapshots credential-free.
docker logout {registry}
rm -f /root/.docker/config.json

mkdir -p /opt/sg-playwright/config /opt/dockge/data

cat > /opt/sg-playwright/docker-compose.yml << 'SG_COMPOSE_EOF'
{compose_content}
SG_COMPOSE_EOF

{observability_configs_section}
{browser_proxy_section}
docker compose -f /opt/sg-playwright/docker-compose.yml up -d

# Write container ID → service name map for fluent-bit log enrichment
sleep 5
docker ps --format '{{{{.ID}}}} {{{{.Names}}}}' \
  | sed 's/ sg-playwright-/ /; s/-[0-9]*$//' \
  > /opt/sg-playwright/config/container-names.txt || true

{shutdown_section}
echo "=== SG Playwright setup complete at $(date) ==="
echo "OK $(date --iso-8601=seconds)" > "$BOOT_STATUS_FILE"
trap - EXIT
"""


# aws_account_id / aws_region / ecr_registry_host / default_playwright_image_uri /
# default_sidecar_image_uri moved to Ec2__AWS__Client (Phase A step 3b) — imported
# at the top of this file under their original names.


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

    # ── iam:PassRole check ────────────────────────────────────────────────────
    passrole = ensure_caller_passrole(account)
    if not passrole['ok'] or passrole['action'] == 'skipped':
        warnings.append(f"iam:PassRole not verified ({passrole['detail']}) — run 'sp ensure-passrole' if sp create fails with UnauthorizedOperation.")
    elif passrole['action'] == 'created':
        warnings.append(f"iam:PassRole policy was missing — attached automatically ({passrole['detail']}).")

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
    port_rows = [
        (f':{EC2__PLAYWRIGHT_PORT}',    'playwright API         (public, API-key gated)'),
        (f':{EC2__SIDECAR_ADMIN_PORT}', 'sidecar admin API      (public, API-key gated)'),
        (':8080',                        'mitmproxy proxy        (Docker-network-only)'  ),
    ]
    if upstream_url:
        port_rows.insert(2, (f':{EC2__BROWSER_INTERNAL_PORT}',
                             'streaming browser      (public, KasmVNC password = API key)'))
    c.print(_kv_table(*port_rows))
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


# IAM__PASSROLE_POLICY_NAME moved to Ec2__AWS__Client (Phase A step 3c) —
# imported at the top of this file under the same name.


# _decode_aws_auth_error moved to Ec2__AWS__Client.decode_aws_auth_error
# (Phase A step 3c) — aliased at the top of this file. The Console-formatted
# print helper below is Tier 2A (CLI rendering) and stays here.


def _print_auth_error(exc: Exception) -> None:
    """Print a clear UnauthorizedOperation block, auto-decoding the encoded message."""
    c       = Console(highlight=False)
    decoded = _decode_aws_auth_error(exc)
    c.print(f'\n  [bold red]✗  UnauthorizedOperation[/]\n  {exc}\n')
    if decoded:
        try:
            detail = json.loads(decoded)
            action = detail.get('context', {}).get('action', '?')
            c.print(f'  [bold]Decoded:[/] the caller lacks permission for [bold]{action}[/]')
            for stmt in detail.get('policies', []):
                c.print(f'    [dim]{stmt}[/]')
        except Exception:
            c.print(f'  [bold]Decoded message:[/]\n{decoded}')
    else:
        c.print('  [dim](Run: aws sts decode-authorization-message --encoded-message <blob> to decode manually)[/]')


# ensure_caller_passrole + ensure_instance_profile moved to Ec2__AWS__Client
# (Phase A step 3c) — imported at the top of this file under the same names.


# ensure_security_group + latest_al2023_ami_id moved to Ec2__AWS__Client
# (Phase A step 3d). The wrappers below preserve the old (ec2: EC2) signatures
# so the typer commands keep working unchanged; they ignore the param and
# delegate to the module-level _AWS instance defined in step 3a.


def ensure_security_group(ec2: EC2 = None) -> str:
    return _AWS.ensure_security_group()


def latest_al2023_ami_id(ec2: EC2 = None) -> str:
    return _AWS.latest_al2023_ami_id()


def render_compose_yaml(playwright_image_uri    : str,
                         sidecar_image_uri      : str,
                         api_key_name           : str,
                         api_key_value          : str,
                         upstream_url           : str = '',
                         upstream_user          : str = '',
                         upstream_pass          : str = '',
                         http2                  : str = '',
                         amp_remote_write_url   : str = '',
                         opensearch_endpoint    : str = '',
                         watchdog_max_request_ms: int = WATCHDOG_MAX_REQUEST_MS) -> str:
    fmt = dict(playwright_image_uri    = playwright_image_uri,
               sidecar_image_uri       = sidecar_image_uri,
               playwright_port         = EC2__PLAYWRIGHT_PORT,
               sidecar_admin_port      = EC2__SIDECAR_ADMIN_PORT,
               browser_port            = EC2__BROWSER_INTERNAL_PORT,
               browser_image_uri       = EC2__BROWSER_IMAGE,
               dockge_port             = EC2__DOCKGE_PORT,
               dockge_image            = EC2__DOCKGE_IMAGE,
               api_key_name            = api_key_name,
               api_key_value           = api_key_value,
               upstream_url            = upstream_url,
               upstream_user           = upstream_user,
               upstream_pass           = upstream_pass,
               http2                   = http2,
               watchdog_max_request_ms = watchdog_max_request_ms)

    services  = ['services:\n']
    services += [COMPOSE_SVC_PLAYWRIGHT.format(**fmt)]
    services += [COMPOSE_SVC_MITMPROXY.format(**fmt)]

    if upstream_url:                                    # browser VNC + nginx only with upstream proxy
        services += [COMPOSE_SVC_BROWSER.format(**fmt)]
        services += [COMPOSE_SVC_BROWSER_PROXY.format(**fmt)]

    if amp_remote_write_url:                            # metrics stack only with AMP
        services += [COMPOSE_SVC_CADVISOR]
        services += [COMPOSE_SVC_NODE_EXPORTER]
        services += [COMPOSE_SVC_PROMETHEUS]

    if opensearch_endpoint:                             # log shipper only with OpenSearch
        services += [COMPOSE_SVC_FLUENT_BIT]

    services += [COMPOSE_SVC_DOCKGE.format(**fmt)]

    volumes = []
    if amp_remote_write_url:
        volumes.append('  prometheus_data:')

    if volumes:
        footer = COMPOSE_FOOTER.format(volume_lines='\n'.join(volumes))
    else:
        footer = 'networks:\n  sg-net:\n    driver: bridge\n'
    return '\n'.join(services) + '\n' + footer


def render_user_data(playwright_image_uri  : str,
                      sidecar_image_uri     : str,
                      compose_content       : str,
                      api_key_value         : str          = '',
                      max_hours             : int          = 1,
                      amp_remote_write_url  : str          = '',
                      opensearch_endpoint   : str          = '',
                      stage                 : str          = DEFAULT_STAGE,
                      upstream_url          : str          = '') -> str:
    if max_hours:
        shutdown_section = (f'\n# Auto-terminate after {max_hours}h\n'
                             f'systemd-run --on-active={max_hours}h /sbin/shutdown -h now\n'
                             f'echo "Auto-terminate timer started: {max_hours}h from now"\n')
    else:
        shutdown_section = ''
    obs_section          = render_observability_configs_section(region               = aws_region()       ,
                                                                 amp_remote_write_url = amp_remote_write_url,
                                                                 opensearch_endpoint  = opensearch_endpoint ,
                                                                 stage                = stage               )
    browser_image_pull   = (f'docker pull {EC2__BROWSER_IMAGE}' if upstream_url
                             else '# browser image skipped — no upstream proxy configured')
    return USER_DATA_TEMPLATE.format(region                        = aws_region()           ,
                                     registry                      = ecr_registry_host()    ,
                                     playwright_image_uri          = playwright_image_uri   ,
                                     sidecar_image_uri             = sidecar_image_uri      ,
                                     browser_image_pull            = browser_image_pull     ,
                                     dockge_image                  = EC2__DOCKGE_IMAGE      ,
                                     compose_content               = compose_content        ,
                                     observability_configs_section = obs_section            ,
                                     browser_proxy_section         = render_browser_proxy_section(api_key_value=api_key_value),
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
              'BlockDeviceMappings'              : [{'DeviceName': '/dev/xvda',
                                                     'Ebs'       : {'VolumeSize'          : 30,
                                                                    'VolumeType'          : 'gp3',
                                                                    'DeleteOnTermination' : True}}],
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
            if 'UnauthorizedOperation' in str(exc):
                _print_auth_error(exc)
                raise typer.Exit(1)
            raise


# find_instances / find_instance_ids / _resolve_instance_id /
# terminate_instances logic moved to Ec2__AWS__Client (Phase A step 3a).
# These wrappers preserve the old signatures (which take an explicit `ec2`
# parameter) so the typer commands below don't need editing in this slice;
# the wrappers ignore the parameter because Ec2__AWS__Client creates its
# own EC2 instance internally — equivalent for our use, since osbot-aws
# EC2() construction is cheap.
_AWS = Ec2__AWS__Client()                                                               # Module-level instance shared by the wrappers below


def find_instances(ec2: EC2 = None) -> dict:
    return _AWS.find_instances()


def find_instance_ids(ec2: EC2 = None) -> list:
    return _AWS.find_instance_ids()


def _resolve_instance_id(ec2: EC2, target: str) -> str:
    return _AWS.resolve_instance_id(target)


def terminate_instances(ec2: EC2 = None, nickname: str = '') -> list:
    return _AWS.terminate_instances(nickname=nickname)


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


# create_ami / wait_ami_available / tag_ami / latest_healthy_ami moved to
# Ec2__AWS__Client (Phase A step 3d). Wrappers preserve old signatures.


def create_ami(ec2: EC2, instance_id: str, name: str) -> str:
    return _AWS.create_ami(instance_id, name)


def wait_ami_available(ec2: EC2, ami_id: str, timeout: int = 900) -> bool:
    return _AWS.wait_ami_available(ami_id, timeout=timeout)


def tag_ami(ec2: EC2, ami_id: str, status: str) -> None:
    _AWS.tag_ami(ami_id, status)


def latest_healthy_ami(ec2: EC2 = None) -> str:
    return _AWS.latest_healthy_ami()


def provision(stage                  : str          = DEFAULT_STAGE    ,
               playwright_image_uri  : str          = None             ,
               sidecar_image_uri     : str          = None             ,
               deploy_name           : str          = ''               ,
               from_ami              : str          = None             ,    # use pre-baked AMI; skips install+pull
               instance_type         : str          = EC2__INSTANCE_TYPE,
               max_hours             : int           = 1               ,
               terminate             : bool         = False            ,
               upstream_url          : str          = ''               ,    # CLI-supplied proxy; falls back to env var
               upstream_user         : str          = ''               ,
               upstream_pass         : str          = ''               ,
               http2                 : str          = ''               ) -> dict:    # 'false' → --set http2=false; fixes InvalidBodyLengthError
    ec2 = EC2()

    if terminate:
        terminated = terminate_instances(ec2)
        return {'action': 'terminate', 'instance_ids': terminated}

    preflight             = preflight_check(playwright_image_uri=playwright_image_uri,
                                             sidecar_image_uri=sidecar_image_uri,
                                             instance_type=instance_type)
    api_key_name          = get_env('FAST_API__AUTH__API_KEY__NAME' ) or 'X-API-Key'
    api_key_value         = get_env('FAST_API__AUTH__API_KEY__VALUE') or preflight['api_key_value']
    upstream_url          = upstream_url  or get_env('AGENT_MITMPROXY__UPSTREAM_URL' ) or ''
    upstream_user         = upstream_user or get_env('AGENT_MITMPROXY__UPSTREAM_USER') or ''
    upstream_pass         = upstream_pass or get_env('AGENT_MITMPROXY__UPSTREAM_PASS') or ''
    http2                 = http2         or get_env('AGENT_MITMPROXY__HTTP2'         ) or ''
    if upstream_url and not http2:                                              # upstream proxies trigger InvalidBodyLengthError with HTTP/2; disable unless explicitly overridden
        http2 = 'false'
    playwright_image_uri  = playwright_image_uri or default_playwright_image_uri()
    sidecar_image_uri     = sidecar_image_uri    or default_sidecar_image_uri()
    resolved_deploy_name  = deploy_name or _random_deploy_name()
    creator               = _get_creator()

    amp_remote_write_url  = get_env('AMP_REMOTE_WRITE_URL' ) or ''
    opensearch_endpoint   = get_env('OPENSEARCH_ENDPOINT'  ) or ''

    compose_content       = render_compose_yaml(playwright_image_uri  = playwright_image_uri ,
                                                 sidecar_image_uri     = sidecar_image_uri    ,
                                                 api_key_name          = api_key_name         ,
                                                 api_key_value         = api_key_value        ,
                                                 upstream_url          = upstream_url         ,
                                                 upstream_user         = upstream_user        ,
                                                 upstream_pass         = upstream_pass        ,
                                                 http2                 = http2                ,
                                                 amp_remote_write_url  = amp_remote_write_url ,
                                                 opensearch_endpoint   = opensearch_endpoint  )
    obs_section = render_observability_configs_section(region               = aws_region()       ,
                                                        amp_remote_write_url = amp_remote_write_url,
                                                        opensearch_endpoint  = opensearch_endpoint ,
                                                        stage                = stage               )
    browser_image_pull_ami = (f'docker pull {EC2__BROWSER_IMAGE} || true'
                               if upstream_url else '')
    if from_ami:
        user_data = AMI_USER_DATA_TEMPLATE.format(compose_content               = compose_content                 ,
                                                   observability_configs_section = obs_section                      ,
                                                   browser_proxy_section         = render_browser_proxy_section(api_key_value=api_key_value),
                                                   browser_image_pull            = browser_image_pull_ami           ,
                                                   dockge_image                  = EC2__DOCKGE_IMAGE               )
    else:
        user_data = render_user_data(playwright_image_uri  = playwright_image_uri ,
                                     sidecar_image_uri     = sidecar_image_uri    ,
                                     compose_content       = compose_content      ,
                                     api_key_value         = api_key_value        ,
                                     max_hours             = max_hours            ,
                                     amp_remote_write_url  = amp_remote_write_url ,
                                     opensearch_endpoint   = opensearch_endpoint  ,
                                     stage                 = stage                ,
                                     upstream_url          = upstream_url         )

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
    playwright_url = f'http://{public_ip}:{EC2__PLAYWRIGHT_PORT}'         if public_ip else None
    sidecar_url    = f'http://{public_ip}:{EC2__SIDECAR_ADMIN_PORT}'     if public_ip else None
    browser_url    = (f'https://{public_ip}:{EC2__BROWSER_INTERNAL_PORT}'
                      if public_ip and upstream_url else None)

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
            'api_key_value'      : api_key_value           ,
            'max_hours'          : max_hours               }


# ── Typer CLI ─────────────────────────────────────────────────────────────────

app = typer.Typer(name           = 'provision_ec2'                                     ,
                   help           = 'Manage the Playwright + agent_mitmproxy EC2 stack.',
                   no_args_is_help = True                                              ,
                   add_completion  = False                                             )

from scripts.observability import app as _observability_app, _check_os_dashboards, _os_endpoint, _list_stacks  # noqa: E402
app.add_typer(_observability_app, name='observability', hidden=True)
app.add_typer(_observability_app, name='ob',            hidden=True)

from scripts.elastic import app as _elastic_app  # noqa: E402
app.add_typer(_elastic_app, name='elastic'        )                                  # ephemeral Elastic+Kibana EC2 stacks
app.add_typer(_elastic_app, name='el',     hidden=True)                              # short alias

from scripts.opensearch import app as _opensearch_app  # noqa: E402
app.add_typer(_opensearch_app, name='opensearch'        )                            # ephemeral OpenSearch+Dashboards EC2 stacks
app.add_typer(_opensearch_app, name='os',         hidden=True)                       # short alias


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
                                   TimeoutSeconds   = max(30, timeout)       )  # SSM minimum is 30
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
    c     = Console(highlight=False, width=200)
    max_h         = r.get('max_hours', 0)
    timeout_label = (f'[bold yellow]{max_h}h[/]  (sp delete {r["deploy_name"]} to cancel early)'
                     if max_h else '[dim]none — delete manually[/]')
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
    left.add_row('auto-delete', timeout_label     )

    right = Table(box=None, show_header=False, padding=(0, 2), expand=False)
    right.add_column(style='bold',    min_width=14, no_wrap=True)
    right.add_column(style='default')
    right.add_row('public-ip',    r['public_ip']                               )
    right.add_row('playwright',   r['playwright_url'] or '—'                   )
    right.add_row('sidecar-admin',r['sidecar_admin_url'] or '—'                )
    if r.get('browser_url'):
        right.add_row('browser',  r['browser_url']                             )
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
    all_connection_errors = all('error' in v for v in results.values())
    if not all_ok:
        c.print()
        if all_connection_errors:
            c.print('  [dim]💡  Service not reachable — containers may not have started.[/]')
            c.print('  [dim]    Run:[/]  [bold]sp diagnose[/]  [dim]to see boot log, docker state, and port listeners[/]')
        else:
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
           max_hours            : int           = typer.Option(1,    '--max-hours',        help='Auto-terminate after N hours. Default: 1. Pass 0 to disable.'),
           interactive          : bool          = typer.Option(False, '--interactive', '-i', help='Ask questions before launching (instance type, smoke workflow).')  ,
           smoke                : bool          = typer.Option(False, '--smoke',            help='After instance is up: run smoke test then delete (implies --wait).')  ,
           wait                 : bool          = typer.Option(False, '--wait',             help='Poll health until up.')                                     ,
           timeout              : int           = typer.Option(600,  '--timeout',           help='Max seconds to wait when --wait or --smoke is set.')        ,
           upstream_url         : Optional[str] = typer.Option(None,  '--upstream-url',    help='Upstream proxy URL for agent_mitmproxy, e.g. http://proxy.example.com:8080.')  ,
           upstream_user        : Optional[str] = typer.Option(None,  '--upstream-user',   help='Username for upstream proxy authentication.')                                  ,
           upstream_pass        : Optional[str] = typer.Option(None,  '--upstream-pass',   help='Password for upstream proxy authentication.')                                  ,
           disable_http2        : bool          = typer.Option(False, '--disable-http2',   help='Force http2=false on the sidecar. Auto-applied when --upstream-url is set.'),
           env_file             : Optional[str] = typer.Option(None,  '--env-file',        help='Path to a .env file; values are merged under CLI flags (CLI wins on conflict).')):
    """Provision an EC2 instance running the Playwright + agent_mitmproxy stack."""
    c = Console(highlight=False, width=200)

    # ── Load .env file (CLI flags take precedence) ────────────────────────────
    if env_file:
        import dotenv                                                            # python-dotenv; already a dev dep
        env_values   = dotenv.dotenv_values(env_file)
        upstream_url  = upstream_url  or env_values.get('AGENT_MITMPROXY__UPSTREAM_URL' ) or ''
        upstream_user = upstream_user or env_values.get('AGENT_MITMPROXY__UPSTREAM_USER') or ''
        upstream_pass = upstream_pass or env_values.get('AGENT_MITMPROXY__UPSTREAM_PASS') or ''
        if not disable_http2:
            disable_http2 = (env_values.get('AGENT_MITMPROXY__HTTP2', '').lower() == 'false')

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
                                  max_hours=max_hours,
                                  upstream_url=upstream_url or '', upstream_user=upstream_user or '',
                                  upstream_pass=upstream_pass or '',
                                  http2='false' if disable_http2 else '')
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
    from sgraph_ai_service_playwright__cli.ec2.service.Ec2__Service                  import Ec2__Service

    c       = Console(highlight=False, width=200)
    listing = Ec2__Service().list_instances()
    if not listing.instances:
        c.print('  [dim]No instances found.[/]')
        return

    ec2          = EC2()                                                             # Display enrichments — kept inline since they're presentation-only and need raw boto3 (osbot_aws has 'LauchTime' typo on launch-time)
    resp         = ec2.client().describe_images(
        Filters  = [{'Name': f'tag:{TAG__SERVICE_KEY}', 'Values': [TAG__SERVICE_VALUE]}],
        Owners   = ['self'])
    project_amis = {img['ImageId']: img.get('Name', '') for img in resp.get('Images', [])}
    instance_ids = [str(info.instance_id) for info in listing.instances]
    raw_resp     = ec2.client().describe_instances(InstanceIds=instance_ids)
    launch_map   = {}
    for r in raw_resp.get('Reservations', []):
        for inst in r.get('Instances', []):
            launch_map[inst['InstanceId']] = inst.get('LaunchTime')

    t = Table(show_header=True, header_style='bold blue', box=None, padding=(0, 2))
    t.add_column('deploy-name',   style='bold')
    t.add_column('instance-id',   style='dim')
    t.add_column('state')
    t.add_column('uptime',        style='yellow', no_wrap=True)
    t.add_column('launch',        style='cyan', no_wrap=True)
    t.add_column('instance-type', style='cyan')
    t.add_column('public-ip',     style='green')
    t.add_column('creator',       style='dim')
    for info in listing.instances:
        state_value = info.state.value if hasattr(info.state, 'value') else str(info.state)
        colour      = 'green' if state_value == 'running' else 'yellow' if state_value == 'pending' else 'red'
        uptime      = _uptime_str(launch_map.get(str(info.instance_id))) if state_value == 'running' else '[dim]—[/]'
        launch      = '[magenta]ami[/]' if str(info.ami_id) in project_amis else '[blue]docker[/]'
        t.add_row(str(info.deploy_name)         ,
                  str(info.instance_id)         ,
                  f'[{colour}]{state_value}[/]' ,
                  uptime                        ,
                  launch                        ,
                  str(info.instance_type) or '?',
                  str(info.public_ip)           ,
                  str(info.creator)             )
    c.print(t)


@app.command(name='info')
def cmd_info(target   : Optional[str] = typer.Argument(None,  help='Deploy-name or instance-id (auto if only one).'),
             json_flag: bool           = typer.Option(False, '--json', help='Output raw JSON instead of rich table.')):
    """Show full details for an instance, reading metadata from its tags."""
    from sgraph_ai_service_playwright__cli.ec2.service.Ec2__Service                  import Ec2__Service

    info = Ec2__Service().get_instance_info(_resolve_typer_target(target))           # service handles dict → schema mapping; raise ValueError on miss
    if info is None:
        Console(highlight=False, width=200).print('  [red]✗  Instance not found.[/]')
        raise typer.Exit(1)

    if json_flag:
        print(info.json_str())
        return
    _render_info(info)


def _resolve_typer_target(target: Optional[str]) -> str:                             # Helper: handle "auto-pick when only one instance" UX that the typer commands all share
    if target:
        return target
    ec2       = EC2()
    instances = find_instances(ec2)
    if len(instances) == 1:
        return next(iter(instances.keys()))
    if not instances:
        Console(highlight=False, width=200).print('  [dim]No instances found.[/]')
        raise typer.Exit(0)
    Console(highlight=False, width=200).print('  [red]✗  Multiple instances — specify a deploy-name or instance-id.[/]')
    raise typer.Exit(1)


def _render_info(info) -> None:                                                      # Tier 2A — Rich rendering of Schema__Ec2__Instance__Info
    state_value = info.state.value if hasattr(info.state, 'value') else str(info.state)
    colour      = 'green' if state_value == 'running' else 'yellow' if state_value == 'pending' else 'red'
    c           = Console(highlight=False, width=200)
    c.print()
    c.print(Panel(
        f'[bold]ℹ️   Instance info[/]  ·  {info.deploy_name}  [dim]{info.instance_id}[/]  [{colour}]{state_value}[/]',
        border_style=colour, expand=False))
    c.print()

    left = Table(box=None, show_header=False, padding=(0, 2), expand=False)
    left.add_column(style='bold',    min_width=14, no_wrap=True)
    left.add_column(style='default')
    left.add_row('deploy-name', str(info.deploy_name))
    left.add_row('stage',       str(info.stage)      )
    left.add_row('creator',     str(info.creator)    )
    left.add_row('ami',         str(info.ami_id) or '—')
    left.add_row('instance-id', str(info.instance_id))

    right = Table(box=None, show_header=False, padding=(0, 2), expand=False)
    right.add_column(style='bold',    min_width=14, no_wrap=True)
    right.add_column(style='default')
    right.add_row('public-ip',     str(info.public_ip)         or '—')
    right.add_row('playwright',    str(info.playwright_url)    or '—')
    right.add_row('sidecar-admin', str(info.sidecar_admin_url) or '—')
    right.add_row('browser',       str(info.browser_url)       or '—')
    right.add_row('api-key-name',  str(info.api_key_name))
    right.add_row('api-key-value', f'[bold green]{info.api_key_value}[/]')

    cols = Table(box=None, show_header=False, padding=(0, 3), expand=False)
    cols.add_column()
    cols.add_column()
    cols.add_row(left, right)
    c.print(cols)
    c.print()
    c.print(f'  sg-ec2 forward 8000 --target {info.deploy_name}   ·   '
            f'sg-ec2 health {info.deploy_name}   ·   sg-ec2 logs --target {info.deploy_name}')
    c.print()


@app.command(name='delete')
def cmd_delete(name    : Optional[str] = typer.Argument(None,  help='Deploy-name or instance-id.'),
               all_flag: bool          = typer.Option(False, '--all', help='Delete ALL playwright-ec2 instances.')):
    """Delete one instance by name/id, or all with --all."""
    from sgraph_ai_service_playwright__cli.ec2.service.Ec2__Service                  import Ec2__Service

    c       = Console(highlight=False, width=200)
    service = Ec2__Service()
    if all_flag:
        instances = service.list_instances().instances
        if not instances:
            c.print('  [dim]No instances found.[/]')
            return
        c.print()
        for info in instances:
            deploy = str(info.deploy_name) or str(info.instance_id)
            c.print(f'  🗑️   [bold]{deploy}[/]  [dim]{info.instance_id}[/]')
        c.print()
        confirm = c.input(f'  [bold red]Delete all {len(instances)} instance(s)?[/] [dim][y/N][/] › ').strip().lower()
        if confirm not in ('y', 'yes'):
            c.print('  Aborted.')
            return
        result  = service.delete_all_instances()
        deleted = [str(iid) for iid in result.terminated_instance_ids]
    else:
        target = _resolve_typer_target(name)
        result = service.delete_instance(target)
        if not str(result.target):
            c.print('  [red]✗  Instance not found.[/]')
            raise typer.Exit(1)
        deploy = str(result.deploy_name) or str(result.target)
        c.print(f'  🗑️   Deleted [bold]{deploy}[/]  [dim]{result.target}[/]...')
        deleted = [str(iid) for iid in result.terminated_instance_ids]
    c.print(f'  ✅  Deleted {len(deleted)} instance(s): [dim]{", ".join(deleted) or "none"}[/]')


@app.command(name='connect')
def cmd_connect(target: Optional[str] = typer.Argument(None, help='Deploy-name or instance-id; auto-selects if only one instance.')):
    """Open an interactive SSM shell session (no SSH/key-pair needed)."""
    import shutil, subprocess
    c           = Console(highlight=False, width=200)
    ec2         = EC2()
    instance_id, _ = _resolve_target(ec2, target)

    # Check plugin is discoverable before attempting the session
    plugin_path = (shutil.which('session-manager-plugin') or
                   '/usr/local/sessionmanagerplugin/bin/session-manager-plugin')
    import os
    if not os.path.isfile(plugin_path):
        c.print()
        c.print('  [red]✗  session-manager-plugin not found in PATH.[/]')
        c.print('  Fix with one of:')
        c.print()
        c.print('    [bold]sudo ln -s /usr/local/sessionmanagerplugin/bin/session-manager-plugin /usr/local/bin/session-manager-plugin[/]')
        c.print('    [bold]brew install --cask session-manager-plugin[/]')
        c.print()
        raise typer.Exit(1)

    def _do_connect():
        typer.echo(f'  🔌  Opening SSM session → {instance_id}  (plugin: {plugin_path})')
        return subprocess.run(['aws', 'ssm', 'start-session', '--target', instance_id],
                              check=False, capture_output=False)

    result = _do_connect()
    if result.returncode != 0:
        c.print()
        c.print('  [yellow]⚠  Session failed — restarting SSM agent on instance and retrying...[/]')
        _ssm_run(instance_id, ['sudo systemctl restart amazon-ssm-agent'], timeout=30)
        c.print('  [dim]waiting 5s for agent to come back...[/]')
        time.sleep(5)
        c.print()
        result = _do_connect()

    if result.returncode != 0:
        c.print()
        c.print('  [red]✗  Session failed after SSM agent restart.[/]')
        c.print(f'  Plugin path: {plugin_path}')
        c.print('  If you see "Standard_Stream not found", try:')
        c.print('    [bold]brew reinstall --cask session-manager-plugin[/]')
        c.print()


@app.command(name='shell')
def cmd_shell(target   : Optional[str] = typer.Argument(None, help='Deploy-name or instance-id (auto if only one).'),
              container: str           = typer.Option(DOCKER__PLAYWRIGHT_CONTAINER, '--container', '-c',
                                                      help='Container to shell into (default: playwright).')):
    """Open an interactive bash shell inside the specified container via SSM (no SSH needed)."""
    ec2             = EC2()
    instance_id, _  = _resolve_target(ec2, target)
    c               = Console(highlight=False, width=200)
    c.print(f'\n  🐚  Connecting to [bold]{container}[/] on [dim]{instance_id}[/] …\n')
    rc = _vault_shell(instance_id, 'bash', container=container)
    if rc != 0:
        c.print(f'\n  [red]✗  Shell exited with code {rc}[/]')


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
    sys.stderr.write(f'\n  # env — {deploy_name}  {instance_id}\n\n')
    for line in [f'export DEPLOY_NAME={deploy_name!r}'              ,
                 f'export API_KEY_NAME={api_key_name!r}'            ,
                 f'export API_KEY_VALUE={api_key_value!r}'          ,
                 f'export EC2_IP={ip!r}'                            ,
                 f'export INSTANCE_ID={instance_id!r}'              ,
                 f"export SG_PLAYWRIGHT_URL='http://{ip}:{EC2__PLAYWRIGHT_PORT}'"]:
        print(line)
    sys.stderr.write('\n')


@app.command(name='vault-clone')
def cmd_vault_clone(target   : Optional[str] = typer.Argument(None, help='Deploy-name or instance-id; auto-selects if only one instance.'),
                    key      : str           = typer.Argument(...,  help='Vault key (id:secret format from sgit).'),
                    container: Optional[str] = typer.Option('playwright', '--container', '-c',
                                                            help='Install sgit-ai and clone vault inside this Compose service (pass "" for EC2 host).'),
                    work_dir : str           = typer.Option('/root/sg-investigation', '--work-dir',
                                                           help='Exact vault root path (inside container when --container is set).')):
    """Install sgit-ai and clone a vault — defaults to running inside the playwright container.

    Usage:
      sg-play vault-clone fierce-hubble bql3zl0ky2lhvmhofrj33815:qp0flfte
      sg-play vault-clone fierce-hubble bql3zl0ky2lhvmhofrj33815:qp0flfte --container ""  # EC2 host
    """
    ec2             = EC2()
    instance_id, d  = _resolve_target(ec2, target)
    deploy_name     = _instance_deploy_name(d)
    c               = Console(highlight=False, width=200)
    ctr             = container or None
    c.print()
    c.print(Panel(f'[bold]📦  Vault clone → {deploy_name}[/]  [dim]{instance_id}[/]  '
                  f'[blue]{("container: " + container) if container else "EC2 host"}[/]',
                  border_style='blue', expand=False))
    c.print()
    c.print('  [dim]disk space check...[/]')
    _vault_ssm(instance_id, 'df -h / 2>/dev/null | tail -1', container=ctr)
    c.print()
    steps = [('Installing sgit-ai', 'pip install sgit-ai --break-system-packages -q'),
             ('Cloning vault',      _vault_clone_sh(key, work_dir))]
    for label, command in steps:
        c.print(f'  ⏳  {label}...')
        _vault_ssm(instance_id, command, timeout=120, container=ctr)
        c.print(f'  ✅  {label} done')
    c.print()
    c.print(f'  [bold green]Vault root: {work_dir}[/]  {"(in container: " + container + ")" if container else "(on EC2 host)"}')
    c.print(f'  Use [bold]--work-dir {work_dir}[/] with vault-run / vault-list / vault-commit / vault-push')
    c.print()


def _vault_clone_sh(vault_key: str, work_dir: str) -> str:
    """Return a shell fragment that clones vault_key to the exact work_dir path.

    sgit creates a subdirectory named after the key's secret part (the part
    after ':').  We clone into the parent, then rename the subdirectory to
    match the requested work_dir basename so all subsequent commands see a
    consistent path.
    """
    secret   = vault_key.split(':')[-1]
    wq       = shlex.quote(work_dir)
    sq       = shlex.quote(secret)
    parent_q = shlex.quote(work_dir.rstrip('/').rsplit('/', 1)[0] or '/')
    name_q   = shlex.quote(work_dir.rstrip('/').rsplit('/', 1)[-1])
    return f'''\
rm -rf {wq}
mkdir -p {parent_q}
cd {parent_q}
sgit clone {shlex.quote(vault_key)} 2>&1
if [ -d {sq} ] && [ {sq} != {name_q} ]; then
    mv {sq} {name_q}
fi
echo "vault root: {work_dir}"'''


def _vault_ssm(instance_id: str, shell: str, timeout: int = 60, container: Optional[str] = None) -> None:
    """Run a vault shell command via SSM; wraps with docker compose exec when container is set."""
    if container:
        inner = shlex.quote(f'set -uo pipefail; {shell}')
        shell = f'docker compose -f {COMPOSE_FILE_PATH} exec -T {shlex.quote(container)} bash -c {inner}'
    stdout, stderr = _ssm_run(instance_id, [shell], timeout=timeout)
    if stdout.strip():
        print(stdout.rstrip())
    if stderr.strip():
        print(stderr.rstrip(), file=sys.stderr)
    if not stdout.strip() and not stderr.strip():
        Console(highlight=False).print('  [dim](no output)[/]')


def _vault_shell(instance_id: str, shell: str, container: Optional[str] = None) -> int:
    """Run a command via SSM start-session (streams output in real time, requires session-manager-plugin).

    When container is set, wraps the command with docker exec so it runs inside the container.
    Returns the process exit code.
    """
    import json, os, shutil, subprocess
    plugin = shutil.which('session-manager-plugin') or '/usr/local/sessionmanagerplugin/bin/session-manager-plugin'
    if not os.path.isfile(plugin):
        Console(highlight=False).print('  [red]✗  session-manager-plugin not found — streaming requires the plugin.[/]')
        Console(highlight=False).print('  Install: [bold]brew install --cask session-manager-plugin[/]')
        return 1
    if container:
        shell = f'sudo docker exec -it {shlex.quote(container)} bash -c {shlex.quote(shell)}'
    params = json.dumps({'command': [shell]})
    result = subprocess.run(
        ['aws', 'ssm', 'start-session',
         '--target', instance_id,
         '--document-name', 'AWS-StartInteractiveCommand',
         '--parameters', params],
        check=False)
    return result.returncode


@app.command(name='vault-list')
def cmd_vault_list(target   : Optional[str] = typer.Argument(None, help='Deploy-name or instance-id (auto if only one).'),
                   path     : str           = typer.Option('.',          '--path',      '-p', help='Sub-path within --work-dir to list.'),
                   container: Optional[str] = typer.Option('playwright', '--container', '-c', help='Run inside this Compose service (pass "" to run on EC2 host).'),
                   work_dir : str           = typer.Option('/root/sg-investigation', '--work-dir', help='Vault root (inside container when --container is set).')):
    """List files in the vault working directory."""
    ec2             = EC2()
    instance_id, _  = _resolve_target(ec2, target)
    full_path       = f'{work_dir}/{path}'.rstrip('/')
    _vault_ssm(instance_id, f'find {shlex.quote(full_path)} -type f 2>/dev/null | sort',
               container=container or None)


@app.command(name='vault-run')
def cmd_vault_run(script   : str           = typer.Argument(...,  help='Script path relative to --work-dir (e.g. scenarios/00__pre-flight/scripts/01__health.sh).'),
                  target   : Optional[str] = typer.Option(None,          '--target',    '-t', help='Deploy-name or instance-id (auto if only one).'),
                  container: Optional[str] = typer.Option('playwright',  '--container', '-c', help='Run inside this Compose service (pass "" to run on EC2 host).'),
                  work_dir : str           = typer.Option('/root/sg-investigation', '--work-dir', help='Vault root (inside container when --container is set).'),
                  save     : Optional[str] = typer.Option(None,  '--save', '-o', help='Save output to this path within --work-dir.'),
                  timeout  : int           = typer.Option(120,   '--timeout', help='Script timeout in seconds.'),
                  stream   : bool          = typer.Option(True,  '--stream/--no-stream',
                                                          help='Stream output in real time via SSM start-session (requires session-manager-plugin). Use --no-stream to collect and return output after completion.')):
    """Run a single bash or python script from the vault.

    Interpreter is chosen by extension: .py → python3, anything else → bash.
    Instance env vars (DEPLOY_NAME, API_KEY_VALUE, EC2_IP, etc.) are always
    exported so scripts can reference them without extra setup.
    """
    ec2             = EC2()
    instance_id, d  = _resolve_target(ec2, target)
    full_script     = f'{work_dir}/{script}'
    ext             = script.rsplit('.', 1)[-1] if '.' in script else ''
    interpreter     = 'python3' if ext == 'py' else 'bash'
    env_prefix      = _env_export_prefix(instance_id, d)
    run_cmd         = f'timeout {timeout} {interpreter} {shlex.quote(full_script)}'
    if save:
        save_path = f'{work_dir}/{save}'
        shell = f'mkdir -p $(dirname {shlex.quote(save_path)}) && {run_cmd} | tee {shlex.quote(save_path)}'
    else:
        shell = run_cmd
    full_shell = f'{env_prefix}chmod +x {shlex.quote(full_script)} 2>/dev/null; {shell}'
    if stream:
        _vault_shell(instance_id, full_shell, container=container or None)
    else:
        _vault_ssm(instance_id, full_shell, timeout=timeout + 10, container=container or None)


@app.command(name='vault-commit')
def cmd_vault_commit(target   : Optional[str] = typer.Argument(None, help='Deploy-name or instance-id (auto if only one).'),
                     message  : str           = typer.Option('investigation outputs', '--message', '-m', help='Commit message.'),
                     container: Optional[str] = typer.Option('playwright', '--container', '-c', help='Run inside this Compose service (pass "" for EC2 host).'),
                     work_dir : str           = typer.Option('/root/sg-investigation', '--work-dir', help='Vault root.')):
    """Stage all changes in the vault and commit."""
    ec2             = EC2()
    instance_id, _  = _resolve_target(ec2, target)
    _vault_ssm(instance_id,
               f'cd {shlex.quote(work_dir)} && sgit add -A && sgit commit -m {shlex.quote(message)} 2>&1 || echo "(nothing to commit)"',
               container=container or None)


@app.command(name='vault-push')
def cmd_vault_push(target      : Optional[str] = typer.Argument(None, help='Deploy-name or instance-id (auto if only one).'),
                   access_token: Optional[str] = typer.Option(None, '--access-token', envvar='SGIT_WRITE_TOKEN',
                                                               help='Write token; also read from $SGIT_WRITE_TOKEN.'),
                   container   : Optional[str] = typer.Option('playwright', '--container', '-c', help='Run inside this Compose service (pass "" for EC2 host).'),
                   work_dir    : str           = typer.Option('/root/sg-investigation', '--work-dir', help='Vault root.')):
    """Push the vault back to origin."""
    if not access_token:
        typer.echo('Error: provide --access-token or set $SGIT_WRITE_TOKEN', err=True)
        raise typer.Exit(1)
    ec2             = EC2()
    instance_id, _  = _resolve_target(ec2, target)
    tok             = shlex.quote(access_token)
    _vault_ssm(instance_id,
               f'cd {shlex.quote(work_dir)} && SGIT_WRITE_TOKEN={tok} sgit push 2>&1; unset SGIT_WRITE_TOKEN',
               container=container or None)


@app.command(name='vault-pull')
def cmd_vault_pull(target   : Optional[str] = typer.Argument(None, help='Deploy-name or instance-id (auto if only one).'),
                   container: Optional[str] = typer.Option('playwright', '--container', '-c', help='Run inside this Compose service (pass "" for EC2 host).'),
                   work_dir : str           = typer.Option('/root/sg-investigation', '--work-dir', help='Vault root.')):
    """Pull latest changes into the vault."""
    ec2             = EC2()
    instance_id, _  = _resolve_target(ec2, target)
    _vault_ssm(instance_id, f'cd {shlex.quote(work_dir)} && sgit pull 2>&1', container=container or None)


@app.command(name='vault-status')
def cmd_vault_status(target   : Optional[str] = typer.Argument(None, help='Deploy-name or instance-id (auto if only one).'),
                     container: Optional[str] = typer.Option('playwright', '--container', '-c', help='Run inside this Compose service (pass "" for EC2 host).'),
                     work_dir : str           = typer.Option('/root/sg-investigation', '--work-dir', help='Vault root.')):
    """Show vault status: working-tree changes, recent commits, and output files."""
    ec2             = EC2()
    instance_id, _  = _resolve_target(ec2, target)
    shell = f'''\
cd {shlex.quote(work_dir)} 2>/dev/null || {{ echo "vault not found at {work_dir}"; exit 1; }}
echo "=== status ==="
sgit status 2>&1
echo ""
echo "=== recent commits ==="
sgit log --oneline -5 2>&1 || true
echo ""
echo "=== outputs ==="
find . -path "*/outputs/*" -type f 2>/dev/null | sort | while read f; do
    echo "  $(wc -l < "$f" 2>/dev/null || echo 0)L  $f"
done
'''
    _vault_ssm(instance_id, shell, container=container or None)


@app.command(name='run')
def cmd_run(vault_key          : str           = typer.Argument(...,  help='Vault key (id:secret from sgit).'),
            scenario           : Optional[str] = typer.Argument(None, help='Scenario folder in vault (e.g. scenarios/00__pre-flight).'),
            access_token       : Optional[str] = typer.Option(None,  '--access-token', envvar='SGIT_WRITE_TOKEN',
                                                              help='Write token for sgit push; also read from $SGIT_WRITE_TOKEN.'),
            target             : Optional[str] = typer.Option(None,  '--target', '-t', help='Deploy-name or instance-id (auto if only one).'),
            container          : Optional[str] = typer.Option('playwright', '--container', '-c',
                                                              help='Run scripts inside this Compose service (pass "" to run on EC2 host).'),
            read_only          : bool          = typer.Option(False, '--read-only',     help='Clone + run but skip vault push.'),
            work_dir           : str           = typer.Option('/home/ssm-user/sg-investigation',  '--work-dir',
                                                              help='Working directory on the EC2 instance.'),
            per_script_timeout : int           = typer.Option(120,  '--timeout',        help='Per-script timeout in seconds.'),
            total_timeout      : int           = typer.Option(1800, '--total-timeout',   help='Overall SSM command timeout in seconds.')):
    """Clone a vault onto an EC2 instance, run its scenario scripts, push outputs back.

    Usage:
      sgpl run bql3zl0ky2lhvmhofrj33815:qp0flfte scenarios/00__pre-flight \\
               --access-token $SGIT_WRITE_TOKEN --target cool-dirac
      sgpl run bql3zl0ky2lhvmhofrj33815:qp0flfte --read-only  # inspect without push
      sgpl run bql3zl0ky2lhvmhofrj33815:qp0flfte scenarios/00__pre-flight \\
               --container playwright --target cool-dirac
    """
    if not read_only and not access_token:
        typer.echo('Error: provide --access-token (or $SGIT_WRITE_TOKEN), or pass --read-only to skip push.', err=True)
        raise typer.Exit(1)

    ec2             = EC2()
    instance_id, d  = _resolve_target(ec2, target)
    deploy_name     = _instance_deploy_name(d)
    c               = Console(highlight=False, width=200)

    script_dir = f'{work_dir}/{scenario}/scripts' if scenario else f'{work_dir}/scripts'
    output_dir = f'{work_dir}/{scenario}/outputs' if scenario else f'{work_dir}/outputs'

    if container:
        run_cmd = f'cat "$script" | docker compose -f {COMPOSE_FILE_PATH} exec -T {shlex.quote(container)} bash'
    else:
        run_cmd = 'bash "$script"'

    push_block = ''
    if not read_only:
        tok = shlex.quote(access_token)
        scen_q = shlex.quote(scenario or '.')
        push_block = f'''\
echo "=== push outputs ==="
cd {shlex.quote(work_dir)}
SGIT_WRITE_TOKEN={tok} sgit add {scen_q}/outputs/
SGIT_WRITE_TOKEN={tok} sgit commit -m "run: {scenario or 'all'} outputs $(date -u +%Y-%m-%dT%H:%M:%SZ)" 2>&1 || true
SGIT_WRITE_TOKEN={tok} sgit push 2>&1
unset SGIT_WRITE_TOKEN
echo "pushed"
'''

    remote_script = f'''\
#!/bin/bash
set -uo pipefail

echo "=== install sgit-ai ==="
pip install -q sgit-ai --break-system-packages 2>&1 | tail -2

echo "=== clone vault ==="
{_vault_clone_sh(vault_key, work_dir)}

mkdir -p {shlex.quote(output_dir)}

echo "=== run scripts ==="
for script in $(find {shlex.quote(script_dir)} -maxdepth 1 -name "*.sh" 2>/dev/null | sort); do
    name=$(basename "$script" .sh)
    echo "--- $name"
    chmod +x "$script"
    timeout {per_script_timeout} {run_cmd} > {shlex.quote(output_dir)}/"${{name}}__out.txt" 2>&1
    rc=$?
    lines=$(wc -l < {shlex.quote(output_dir)}/"${{name}}__out.txt" 2>/dev/null || echo 0)
    echo "  exit=$rc  ${{lines}}L  outputs/${{name}}__out.txt"
done

{push_block}
echo "=== outputs ==="
find {shlex.quote(output_dir)} -type f 2>/dev/null | sort | while read f; do
    echo "  $(wc -l < "$f")L  $f"
done
echo "=== done ==="
'''

    c.print()
    c.print(Panel(f'[bold]▶  vault run[/]  ·  {deploy_name}  [dim]{instance_id}[/]', border_style='blue', expand=False))
    c.print(f'  vault    : {vault_key.split(":")[0]}:***')
    if scenario:
        c.print(f'  scenario : {scenario}')
    if container:
        c.print(f'  container: {container}')
    c.print(f'  work-dir : {work_dir}')
    c.print(f'  push     : {"no (--read-only)" if read_only else "yes"}')
    c.print()

    stdout, stderr = _ssm_run(instance_id, [remote_script], timeout=total_timeout)
    if stdout.strip():
        print(stdout.rstrip())
    if stderr.strip():
        print(stderr.rstrip(), file=sys.stderr)
    if not stdout.strip() and not stderr.strip():
        c.print('  [yellow](no output — check SSM agent status with: sgpl exec "sudo systemctl status amazon-ssm-agent")[/]')


@app.command(name='exec', context_settings={'allow_extra_args': True, 'ignore_unknown_options': True})
def cmd_exec(ctx        : typer.Context,
             first      : str           = typer.Argument(...,  help='Deploy-name/instance-id, or start of shell command when only one instance exists.'),
             cmd        : Optional[str] = typer.Option(None, '--cmd',         help='Shell command (alternative to positional).'),
             target     : Optional[str] = typer.Option(None, '--target', '-t',help='Force target; first positional arg then becomes the command.'),
             container  : Optional[str] = typer.Option(None, '--container', '-c',
                                                        help='Run inside this container (full name or compose service name, e.g. sg-playwright-playwright-1 or playwright).'),
             inject_env : bool          = typer.Option(False, '--inject-env', help='Prepend DEPLOY_NAME/API_KEY_VALUE/EC2_IP/INSTANCE_ID from tags.') ):
    """Execute a shell command on the EC2 host or inside a Docker container via SSM.

    Usage patterns:
      sgpl exec "docker ps"                                         # host, auto-select target
      sgpl exec deep-tesla docker ps -a                            # host, explicit target, unquoted
      sgpl exec fierce-hubble "docker ps"                          # host, explicit target, quoted
      sgpl exec "ls /" --container sg-playwright-playwright-1      # inside container (full name)
      sgpl exec "ls /" --container playwright                      # inside container (service name)
    """
    # ctx.args holds any extra positional words after `first` (e.g. "docker ps -a" → ['ps', '-a'])
    extra    = ctx.args or []
    ec2      = EC2()
    instances = find_instances(ec2)
    # Determine whether `first` is a target name or the start of the command
    if target:
        resolved_target = target
        shell_cmd       = shlex.join([first] + extra) if not cmd else cmd
    elif cmd:
        resolved_target = first
        shell_cmd       = cmd
    elif extra:
        # If first matches a known instance name/id it is the target; extra is the command.
        # Otherwise treat first+extra as the full command with auto-select target.
        if first in instances or any(_instance_deploy_name(d) == first for d in instances.values()):
            resolved_target = first
            shell_cmd       = shlex.join(extra)
        else:
            resolved_target = None
            shell_cmd       = shlex.join([first] + extra)
    elif first in instances or any(_instance_deploy_name(d) == first for d in instances.values()):
        # first matches a known instance — but no command given; error
        raise typer.BadParameter('Provide a shell command after the target name.')
    else:
        resolved_target = None
        shell_cmd       = first

    if not shell_cmd:
        raise typer.BadParameter('Provide a shell command.')
    ec2             = EC2()
    instance_id, d  = _resolve_target(ec2, resolved_target)
    if inject_env:
        shell_cmd = _env_export_prefix(instance_id, d) + shell_cmd
    if container:
        shell_cmd = f'docker exec {shlex.quote(container)} bash -c {shlex.quote(shell_cmd)}'
    c = Console(highlight=False, width=200)
    ctr_tag = f'[{container}]' if container else ''
    c.print(f'  💻  [dim]{instance_id}{ctr_tag}[/]  {shell_cmd}')
    stdout, stderr = _ssm_run(instance_id, [shell_cmd])
    if stdout.strip():
        print(stdout.rstrip())
    if stderr.strip():
        print(stderr.rstrip(), file=sys.stderr)
    if not stdout.strip() and not stderr.strip():
        c.print('  [dim](no output)[/]')


@app.command(name='exec-c')
def cmd_exec_c(shell_cmd: str           = typer.Argument(...,  help='Shell command to run inside the playwright container.'),
               target   : Optional[str] = typer.Option(None, '--target', '-t', help='Deploy-name or instance-id (auto if only one).'),
               container: str           = typer.Option(DOCKER__PLAYWRIGHT_CONTAINER, '--container', '-c',
                                                        help='Container name (defaults to sg-playwright-playwright-1).')):
    """Run a command inside the playwright container — shorthand for exec --container sg-playwright-playwright-1."""
    ec2             = EC2()
    instance_id, _  = _resolve_target(ec2, target)
    wrapped         = f'docker exec {shlex.quote(container)} bash -c {shlex.quote(shell_cmd)}'
    c               = Console(highlight=False, width=200)
    c.print(f'  💻  [dim]{instance_id}[{container}][/]  {shell_cmd}')
    stdout, stderr  = _ssm_run(instance_id, [wrapped])
    if stdout.strip():
        print(stdout.rstrip())
    if stderr.strip():
        print(stderr.rstrip(), file=sys.stderr)
    if not stdout.strip() and not stderr.strip():
        c.print('  [dim](no output)[/]')


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


# ── diagnose ───────────────────────────────────────────────────────────────────

_DIAGNOSE_CHECKS = [
    ('Boot status',
     'cat /var/log/sg-playwright-boot-status 2>/dev/null || echo "(no boot-status file — pre-diagnose image)"'),
    ('Setup log (last 60 lines)',
     'tail -n 60 /var/log/sg-playwright-setup.log 2>/dev/null'
     ' || tail -n 60 /var/log/sg-playwright-start.log 2>/dev/null'
     ' || echo "(no setup log found)"'),
    ('Cloud-init status',
     'cloud-init status --long 2>/dev/null || echo "(cloud-init not available)"'),
    ('Docker daemon',
     'systemctl is-active docker && echo "docker: active" || echo "docker: NOT active"'),
    ('Docker images',
     'docker images --format "table {{.Repository}}\\t{{.Tag}}\\t{{.Size}}\\t{{.CreatedSince}}" 2>/dev/null || echo "(docker not running)"'),
    ('All containers (running + stopped)',
     'docker ps -a --format "table {{.Names}}\\t{{.Image}}\\t{{.Status}}\\t{{.Ports}}" 2>/dev/null || echo "(docker not running)"'),
    ('Compose file',
     f'ls -la {COMPOSE_FILE_PATH} 2>/dev/null && echo "--- content ---" && cat {COMPOSE_FILE_PATH} 2>/dev/null || echo "(compose file missing)"'),
    ('Compose service status',
     f'docker compose -f {COMPOSE_FILE_PATH} ps 2>&1 || echo "(compose status failed)"'),
    ('Listening ports',
     'ss -tlnp 2>/dev/null | grep -E "8000|8001|5001|9090|3000|5601" || echo "(none of the expected ports are listening)"'),
    ('Disk',
     'df -h / /var/lib/docker 2>/dev/null | tail -n +1'),
    ('Memory',
     'free -h'),
    ('Recent kernel / OOM errors',
     'journalctl -k --since "1 hour ago" --no-pager -q 2>/dev/null | grep -iE "oom|kill|error|fail" | tail -20 || echo "(no kernel errors)"'),
]


@app.command(name='diagnose')
def cmd_diagnose(
    target : Optional[str] = typer.Argument(None, help='Deploy-name or instance-id; auto-selects if only one instance.'),
    quick  : bool          = typer.Option(False, '--quick', '-q', help='Skip setup log and cloud-init; just show containers + ports.'),
):
    """Deep system diagnosis via SSM — boot log, docker state, ports, disk, OOM. Use when sp health fails."""
    ec2             = EC2()
    instance_id, d  = _resolve_target(ec2, target)
    deploy_name     = _instance_deploy_name(d) or instance_id
    public_ip       = d.get('public_ip', '?')
    c               = Console(highlight=False, width=200)
    c.print()
    c.print(Panel(
        f'[bold]🔬  Diagnose[/]  [dim]{deploy_name}[/]  {instance_id}  {public_ip}',
        border_style='cyan', expand=False))
    c.print()

    skip_slow = {'Setup log (last 60 lines)', 'Cloud-init status', 'Recent kernel / OOM errors'}
    for label, cmd in _DIAGNOSE_CHECKS:
        if quick and label in skip_slow:
            continue
        c.print(f'  [bold cyan]── {label}[/]')
        stdout, stderr = _ssm_run(instance_id, [cmd], timeout=45)
        output = (stdout or stderr or '(no output)').rstrip()
        for line in output.splitlines():
            # Highlight failure signals
            colour = 'red' if any(k in line.lower() for k in ('fail', 'error', 'oom', 'killed', 'exit')) \
                     else 'yellow' if 'warn' in line.lower() \
                     else 'green' if any(k in line.lower() for k in ('ok', 'active', 'running', 'up')) \
                     else ''
            if colour:
                c.print(f'  [{colour}]{line}[/]')
            else:
                c.print(f'  {line}')
        c.print()

    # API reachability (HTTP, no SSM needed)
    c.print('  [bold cyan]── API health endpoints[/]')
    tag_key_name  = _instance_tag(d, TAG__API_KEY_NAME_KEY)
    tag_key_value = _instance_tag(d, TAG__API_KEY_VALUE_KEY)
    base_url = f'http://{public_ip}:{EC2__PLAYWRIGHT_PORT}'
    results  = _health_check_once(base_url, tag_key_name or 'X-API-Key', tag_key_value)
    _render_health(results, base_url)
    c.print()

    # OpenSearch Dashboards check (if the stack has an OpenSearch endpoint)
    opensearch_ep = get_env('OPENSEARCH_ENDPOINT') or ''
    if not opensearch_ep:
        stacks = {s['name']: s for s in _list_stacks(aws_region())}
        for s in stacks.values():
            if s.get('opensearch'):
                opensearch_ep = _os_endpoint(s['opensearch'])
                break
    if opensearch_ep:
        c.print('  [bold cyan]── OpenSearch Dashboards objects[/]')
        _check_os_dashboards(opensearch_ep, aws_region(), c)

    c.print('  [dim]Tip: sp logs --target {target} — see docker compose stdout[/]')
    c.print()


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
    c   = Console(highlight=False, width=200)
    # Resolve target — also grab stored api key from tags when not supplied via option/env
    instance_id = None
    if ip and ip.replace('.', '').isdigit():
        actual_ip = ip
        tag_key_name, tag_key_value = '', ''
    else:
        instance_id, details = _resolve_target(ec2, ip)
        actual_ip     = details.get('public_ip', '')
        tag_key_name  = _instance_tag(details, TAG__API_KEY_NAME_KEY)
        tag_key_value = _instance_tag(details, TAG__API_KEY_VALUE_KEY)

    base_url  = f'http://{actual_ip}:{port}'
    key_name  = api_key_name  or get_env('FAST_API__AUTH__API_KEY__NAME' ) or tag_key_name  or 'X-API-Key'
    key_value = api_key_value or get_env('FAST_API__AUTH__API_KEY__VALUE') or tag_key_value or ''
    deadline  = time.time() + timeout
    c.print(f'\n  ⏳  Waiting for {base_url} (timeout {timeout}s)...\n')

    def _print_instance_status() -> None:
        if not instance_id:
            return
        c.print(f'  [dim]── instance status ({instance_id}) ──[/]')
        try:
            stdout, _ = _ssm_run(instance_id, [
                'echo "~~containers~~" && '
                'docker ps -a --format "  {{.Names}}\\t{{.Status}}\\t{{.Image}}" 2>/dev/null || echo "  (docker not ready yet)"',
                'echo "~~start-log~~" && '
                'tail -20 /var/log/sg-playwright-start.log 2>/dev/null || echo "  (log not yet available)"',
            ], timeout=15)
        except Exception as e:
            c.print(f'  [dim]  SSM not reachable yet: {str(e)[:60]}[/]')
            return
        if not stdout.strip():
            c.print('  [dim]  SSM agent not ready yet[/]')
            return
        section = None
        for raw in stdout.splitlines():
            line = raw.rstrip()
            if line == '~~containers~~':
                section = 'containers'
                c.print('  [bold blue]containers:[/]')
                continue
            if line == '~~start-log~~':
                section = 'log'
                c.print('  [bold blue]start log:[/]')
                continue
            if section == 'containers':
                colour = 'green' if 'Up' in line else ('red' if 'Exited' in line else 'yellow')
                c.print(f'  [{colour}]{line}[/]')
            else:
                if any(kw in line for kw in ('error', 'Error', 'ERROR', 'failed', 'FAILED')):
                    c.print(f'  [red]{line}[/]')
                elif any(kw in line for kw in ('===', 'docker pull', 'docker compose', 'Pulling', 'Pull complete', 'Started')):
                    c.print(f'  [bold]{line}[/]')
                else:
                    c.print(f'  [dim]{line}[/]')
        c.print()

    attempt       = 0
    status_every  = 3                                      # SSM status check every N HTTP attempts
    while time.time() < deadline:
        attempt += 1
        try:
            r = requests.get(f'{base_url}/health/status', headers={key_name: key_value}, timeout=8)
            if r.status_code in (200, 401):              # 401 = service up, auth required
                c.print(f'  ✅  service up after {attempt} attempt(s)  (HTTP {r.status_code})')
                _render_health(_health_check_once(base_url, key_name, key_value), base_url)
                return
            c.print(f'  🔄  attempt {attempt}: HTTP {r.status_code} — retrying in {interval}s...')
        except Exception as exc:
            c.print(f'  🔄  attempt {attempt}: [dim]{str(exc)[:100]}[/] — retrying in {interval}s...')
        if attempt % status_every == 0:
            _print_instance_status()
        time.sleep(interval)
    c.print(f'\n  ❌  timed out after {timeout}s', err=True)
    # Final status dump on timeout so you can see exactly what failed
    _print_instance_status()
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
    ec2             = EC2()
    instance_id, d  = _resolve_target(ec2, target)
    deploy_name     = _instance_deploy_name(d)
    name            = ami_name or f'sg-playwright-{datetime.utcnow().strftime("%Y%m%d-%H%M%S")}'
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


@app.command(name='list-amis')
def cmd_list_amis():
    """List all sg-playwright AMIs in the current region with their status, age, and running instances."""
    c         = Console(highlight=False, width=200)
    ec2       = EC2()
    resp      = ec2.client().describe_images(
        Filters = [{'Name': f'tag:{TAG__SERVICE_KEY}', 'Values': [TAG__SERVICE_VALUE]}],
        Owners  = ['self'])
    images    = sorted(resp.get('Images', []), key=lambda x: x['CreationDate'], reverse=True)
    if not images:
        c.print('  [dim]No sg-playwright AMIs found.[/]')
        return
    instances     = find_instances(ec2)                                        # {iid: details}
    ami_instances : dict = {}                                                  # ami_id → list of deploy-names
    for iid, d in instances.items():
        img_id = d.get('image_id', '')
        if img_id:
            ami_instances.setdefault(img_id, []).append(_instance_deploy_name(d) or iid)
    t = Table(show_header=True, header_style='bold blue', box=None, padding=(0, 2))
    t.add_column('#',          style='dim',     no_wrap=True)
    t.add_column('ami-id',     style='bold',    no_wrap=True)
    t.add_column('name',       style='default')
    t.add_column('status',     style='default', no_wrap=True)
    t.add_column('state',      style='default', no_wrap=True)
    t.add_column('created',    style='dim',     no_wrap=True)
    t.add_column('instances',  style='cyan')
    for idx, img in enumerate(images, 1):
        ami_id   = img['ImageId']
        name     = img.get('Name', '—')
        state    = img.get('State', '?')
        created  = img.get('CreationDate', '?')[:19].replace('T', ' ')
        status   = next((tg['Value'] for tg in img.get('Tags', []) if tg['Key'] == TAG__AMI_STATUS_KEY), '—')
        running  = ami_instances.get(ami_id, [])
        s_colour = 'green' if status == 'healthy' else 'red' if status == 'unhealthy' else 'yellow'
        d_colour = 'green' if state   == 'available' else 'yellow'
        inst_str = ', '.join(running) if running else '[dim]—[/]'
        t.add_row(str(idx), ami_id, name, f'[{s_colour}]{status}[/]', f'[{d_colour}]{state}[/]', created, inst_str)
    c.print(t)


@app.command(name='create-from-ami')
def cmd_create_from_ami(
        ami_id         : Optional[str] = typer.Argument(None,                  help='AMI ID to launch from. Omit to pick interactively.'),
        name           : Optional[str] = typer.Option(None,  '--name',         help='Deploy name (default: random two-word).'),
        instance_type  : Optional[str] = typer.Option(None,  '--instance-type',help=f'Instance type or preset 1–5 (default: {EC2__INSTANCE_TYPE}).'),
        max_hours      : int           = typer.Option(1,     '--max-hours',    help='Auto-terminate after N hours. Default: 1. Pass 0 to disable.'),
        wait           : bool          = typer.Option(False, '--wait',         help='Poll health until up.'),
        smoke          : bool          = typer.Option(False, '--smoke',        help='After instance is up: run smoke test then delete.')):
    """Launch an EC2 instance from a pre-baked sg-playwright AMI (fast boot — no docker install or image pull)."""
    c   = Console(highlight=False, width=200)
    ec2 = EC2()

    if ami_id is None:
        resp   = ec2.client().describe_images(
            Filters = [{'Name': f'tag:{TAG__SERVICE_KEY}', 'Values': [TAG__SERVICE_VALUE]},
                       {'Name': 'state',                   'Values': ['available']        }],
            Owners  = ['self'])
        images = sorted(resp.get('Images', []), key=lambda x: x['CreationDate'], reverse=True)
        if not images:
            c.print('  [red]✗  No sg-playwright AMIs found. Run [bold]sgpl bake-ami[/] first.[/]')
            raise typer.Exit(1)
        healthy = [img for img in images
                   if next((tg['Value'] for tg in img.get('Tags', []) if tg['Key'] == TAG__AMI_STATUS_KEY), '') == 'healthy']
        chosen = (healthy or images)[0]                                        # prefer healthy, fall back to latest
        ami_id = chosen['ImageId']
        status = next((tg['Value'] for tg in chosen.get('Tags', []) if tg['Key'] == TAG__AMI_STATUS_KEY), '—')
        c.print(f'\n  → using latest: [bold]{ami_id}[/]  {chosen.get("Name", "?")}  [dim]({status})[/]\n')

    resolved_type = _resolve_instance_type(instance_type)
    result        = provision(stage=DEFAULT_STAGE, deploy_name=name or '', from_ami=ami_id,
                               instance_type=resolved_type, max_hours=max_hours)
    _render_create_result(result)
    resolved_name = result['deploy_name']

    if wait or smoke:
        _cmd_wait(ip=result['public_ip'], port=EC2__PLAYWRIGHT_PORT,
                  api_key_name=result['api_key_name'], api_key_value=result['api_key_value'],
                  timeout=600, interval=10)

    if smoke:
        smoke_ok = True
        try:
            cmd_smoke(target=resolved_name, url=(), port=EC2__PLAYWRIGHT_PORT,
                      no_screenshot=False, req_timeout=120)
        except SystemExit as e:
            smoke_ok = (e.code == 0 or e.code is None)
        c.print()
        c.print(Panel(f'[bold]🗑️  Deleting {resolved_name}[/]', border_style='dim', expand=False))
        cmd_delete(resolved_name)
        if not smoke_ok:
            raise typer.Exit(code=1)


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
    c.print(f'  Mitmproxy UI  →  sg-ec2 forward {EC2__MITMWEB_TUNNEL_PORT}   then  http://localhost:{EC2__MITMWEB_TUNNEL_PORT}/')
    c.print(f'  Browser       →  sg-ec2 forward-browser        then  http://localhost:{EC2__BROWSER_INTERNAL_PORT}/')
    c.print(f'  Dockge        →  sg-ec2 forward-dockge         then  http://localhost:{EC2__DOCKGE_PORT}/')
    c.print(f'  Prometheus    →  sg-ec2 forward-prometheus      then  http://localhost:{EC2__PROMETHEUS_PORT}/')
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


@app.command(name='forward-dockge')
def cmd_forward_dockge(target: Optional[str] = typer.Argument(None, help='Deploy-name or instance-id; auto-selects if only one instance.')):
    """Forward Dockge (port 5001) to localhost via SSM — Docker Compose management UI."""
    import subprocess
    ec2                  = EC2()
    instance_id, details = _resolve_target(ec2, target)
    deploy_name          = _instance_deploy_name(details) or instance_id
    c = Console(highlight=False, width=200)
    c.print()
    c.print(Panel(
        f'[bold]🐳  Dockge Forward[/]\n\n'
        f'  instance   [bold]{deploy_name}[/]  [dim]{instance_id}[/]\n'
        f'  tunnel     [bold]localhost:{EC2__DOCKGE_PORT}[/]\n\n'
        f'  [green]Access:[/]  [bold]http://localhost:{EC2__DOCKGE_PORT}/[/]\n'
        f'  [dim]First visit sets the admin password.[/]\n'
        f'  [dim]Press Ctrl-C to close the tunnel.[/]',
        border_style='bright_blue', expand=False))
    c.print()
    subprocess.run(['aws', 'ssm', 'start-session',
                    '--target'       , instance_id,
                    '--document-name', 'AWS-StartPortForwardingSession',
                    '--parameters'   , json.dumps({'portNumber'     : [str(EC2__DOCKGE_PORT)],
                                                   'localPortNumber': [str(EC2__DOCKGE_PORT)]})],
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


@app.command(name='ensure-passrole')
def cmd_ensure_passrole():
    """Attach a minimal iam:PassRole inline policy to the current IAM user.

    Required for sp create to succeed when calling RunInstances with an IAM
    instance profile. The policy is scoped to the playwright-ec2 role only,
    with a condition restricting PassRole to ec2.amazonaws.com — it cannot
    be used to pass the role to Lambda, ECS, or any other service.

    Policy attached: sg-playwright-passrole-ec2 (inline, on the IAM user)
    """
    c       = Console(highlight=False)
    account = aws_account_id()
    c.print()
    result  = ensure_caller_passrole(account)
    if result['ok']:
        action = result['action']
        if action == 'already_exists':
            c.print(f"  [green]✓[/]  {result['detail']}")
        else:
            c.print(f"  [green]✓  Policy created.[/]  {result['detail']}")
            c.print()
            c.print('  [dim]Policy document:[/]')
            role_arn = f'arn:aws:iam::{account}:role/{IAM__ROLE_NAME}'
            c.print(f'  [dim]  Action:    iam:PassRole[/]')
            c.print(f'  [dim]  Resource:  {role_arn}[/]')
            c.print(f'  [dim]  Condition: iam:PassedToService = ec2.amazonaws.com[/]')
    else:
        c.print(f"  [yellow]⚠  Skipped.[/]  {result['detail']}")
        c.print()
        c.print('  Attach this inline policy manually to your IAM user in the AWS console:')
        role_arn = f'arn:aws:iam::{account}:role/{IAM__ROLE_NAME}'
        c.print(f'    Action:    iam:PassRole')
        c.print(f'    Resource:  {role_arn}')
        c.print(f'    Condition: iam:PassedToService = ec2.amazonaws.com')
    c.print()


if __name__ == '__main__':
    app()

# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Playwright__User_Data__Builder
# Renders the EC2 UserData bash that boots sg-playwright (+ optional mitmproxy)
# on a fresh AL2023 instance via docker-compose, then starts the host-control
# container as a sidecar. Mirrors Vnc__User_Data__Builder + provision_ec2.py.
#
# Layout (everything under /opt/sg-playwright):
#   interceptors/active.py     ← resolved interceptor source (mitmproxy only)
#   docker-compose.yml         ← rendered upstream by Playwright__Compose__Template
#
# Boot sections (in order):
#   1. header          — set -euo pipefail, log
#   2. docker install  — dnf + compose plugin
#   3. layout          — mkdir -p
#   4. intercept script— only when with_mitmproxy; no-op default when intercept_script=''
#   5. compose         — heredoc → docker-compose.yml; compose up -d
#   6. host control    — docker run host-control container (provision_ec2.py:288-310)
#   7. shutdown        — systemd-run auto-terminate timer (Section__Shutdown)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe

from sg_compute.platforms.ec2.user_data.Section__Shutdown                       import Section__Shutdown


COMPOSE_DIR      = '/opt/sg-playwright'
COMPOSE_FILE     = '/opt/sg-playwright/docker-compose.yml'
INTERCEPTOR_DIR  = '/opt/sg-playwright/interceptors'
INTERCEPTOR_FILE = '/opt/sg-playwright/interceptors/active.py'
LOG_FILE         = '/var/log/sg-playwright-boot.log'


NOOP_INTERCEPTOR = '''\
# no-op mitmproxy interceptor — pass all traffic through unchanged
def request(flow):
    pass

def response(flow):
    pass
'''


USER_DATA_TEMPLATE = """\
#!/usr/bin/env bash
set -euo pipefail
exec > >(tee -a {log_file}) 2>&1
echo "[sg-playwright] boot starting at $(date -u +%FT%TZ)"

STACK_NAME='{stack_name}'
REGION='{region}'

echo "[sg-playwright] installing Docker on AL2023..."
dnf install -y docker
systemctl enable --now docker

echo "[sg-playwright] installing docker compose plugin..."
mkdir -p /usr/local/lib/docker/cli-plugins
curl -fsSL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" \\
    -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

echo "[sg-playwright] preparing /opt/sg-playwright layout..."
mkdir -p {interceptor_dir}

{interceptor_section}
echo "[sg-playwright] writing compose to {compose_file}..."
cat > {compose_file} <<'SG_PLAYWRIGHT_COMPOSE_EOF'
{compose_yaml}
SG_PLAYWRIGHT_COMPOSE_EOF

echo "[sg-playwright] starting compose stack..."
cd {compose_dir}
docker compose up -d

{host_control_section}
{shutdown_section}
echo "[sg-playwright] boot complete at $(date -u +%FT%TZ)"
"""


INTERCEPTOR_SECTION_TEMPLATE = """\
echo "[sg-playwright] writing interceptor to {interceptor_file}..."
cat > {interceptor_file} <<'SG_PLAYWRIGHT_INTERCEPTOR_EOF'
{interceptor_source}
SG_PLAYWRIGHT_INTERCEPTOR_EOF
"""


HOST_CONTROL_SECTION_TEMPLATE = """\
echo "[sg-playwright] starting host control plane..."
HOST_API_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
mkdir -p /opt/host-api
echo "$HOST_API_KEY" > /opt/host-api/api-key.txt
chmod 600 /opt/host-api/api-key.txt

aws ecr get-login-password --region {region} | \\
  docker login --username AWS --password-stdin {registry}

docker run -d \\
  --name sp-host-control \\
  --restart=unless-stopped \\
  --privileged \\
  -v /var/run/docker.sock:/var/run/docker.sock \\
  -e FAST_API__AUTH__API_KEY__VALUE="$HOST_API_KEY" \\
  -p 19009:8000 \\
  {registry}/sgraph_ai_service_playwright_host:latest || true

rm -f /root/.docker/config.json
"""


PLACEHOLDERS = ('stack_name', 'region', 'log_file',
                'compose_dir', 'compose_file', 'compose_yaml',
                'interceptor_dir', 'interceptor_section',
                'host_control_section', 'shutdown_section')                      # Locked by test


class Playwright__User_Data__Builder(Type_Safe):

    def render(self, stack_name      : str,
                     region          : str,
                     compose_yaml    : str,
                     api_key         : str  = '',
                     with_mitmproxy  : bool = False,
                     intercept_script: str  = '',
                     registry        : str  = '',
                     max_hours       : int  = 1   ) -> str:

        interceptor_section = ''
        if with_mitmproxy:
            source = str(intercept_script) if intercept_script else NOOP_INTERCEPTOR
            interceptor_section = INTERCEPTOR_SECTION_TEMPLATE.format(
                interceptor_file   = INTERCEPTOR_FILE ,
                interceptor_source = source           )

        host_control_section = HOST_CONTROL_SECTION_TEMPLATE.format(
            region   = str(region)   ,
            registry = str(registry) )

        shutdown_section = ''
        if max_hours and max_hours > 0:
            shutdown_section = Section__Shutdown().render(max_hours)

        return USER_DATA_TEMPLATE.format(
            stack_name           = str(stack_name)        ,
            region               = str(region)            ,
            log_file             = LOG_FILE               ,
            compose_dir          = COMPOSE_DIR            ,
            compose_file         = COMPOSE_FILE           ,
            compose_yaml         = str(compose_yaml)      ,
            interceptor_dir      = INTERCEPTOR_DIR        ,
            interceptor_section  = interceptor_section    ,
            host_control_section = host_control_section   ,
            shutdown_section     = shutdown_section       )

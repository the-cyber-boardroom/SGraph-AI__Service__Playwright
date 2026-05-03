# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Docker__User_Data__Builder
# cloud-init for a bare AL2023 instance with Docker CE installed. Installs
# Docker Engine + Compose plugin so `docker run` and `docker compose` work
# out of the box. SSM agent is already present on AL2023.
# Also starts the host control plane sidecar (port 9000) from ECR.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


LOG_FILE              = '/var/log/sg-docker-boot.log'
HOST_CONTROL_IMAGE    = 'sgraph_ai_service_playwright_host'


USER_DATA_TEMPLATE = """\
#!/usr/bin/env bash
set -euo pipefail
exec > >(tee -a {log_file}) 2>&1
echo "[sg-docker] boot starting at $(date -u +%FT%TZ)"

STACK_NAME='{stack_name}'
REGION='{region}'
REGISTRY='{registry}'

echo "[sg-docker] installing Docker on AL2023..."
dnf install -y docker
systemctl enable --now docker

echo "[sg-docker] installing docker compose plugin..."
mkdir -p /usr/local/lib/docker/cli-plugins
curl -fsSL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" \\
    -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

echo "[sg-docker] verifying docker..."
docker version
docker compose version

# AL2023 ships with SSM agent; ensure it is active
systemctl enable --now amazon-ssm-agent || true

# ── host control plane ────────────────────────────────────────────────────────
echo "[sg-docker] starting host control plane (port 9000)..."

aws ecr get-login-password --region "$REGION" | \\
  docker login --username AWS --password-stdin "$REGISTRY"

docker run -d \\
  --name sp-host-control \\
  --restart=unless-stopped \\
  --privileged \\
  -v /var/run/docker.sock:/var/run/docker.sock \\
  -e FAST_API__AUTH__API_KEY__NAME="{api_key_name}" \\
  -e FAST_API__AUTH__API_KEY__VALUE="{api_key_value}" \\
  -p 9000:8000 \\
  "$REGISTRY"/{host_control_image}:latest || true

echo "[sg-docker] host control plane started"

{shutdown_line}

echo "[sg-docker] boot complete at $(date -u +%FT%TZ)"
"""

SHUTDOWN_TEMPLATE = 'shutdown -h +{minutes}  # auto-terminate after {hours}h'
SHUTDOWN_DISABLED = '# max_hours=0 — no auto-terminate'

PLACEHOLDERS = ('stack_name', 'region', 'registry', 'host_control_image',
                'api_key_name', 'api_key_value',
                'log_file', 'shutdown_line')                                         # Locked by test


class Docker__User_Data__Builder(Type_Safe):

    def render(self, stack_name: str, region: str, registry: str = '',
               api_key_name: str = 'X-API-Key', api_key_value: str = '',
               max_hours: int = 1) -> str:
        if max_hours > 0:
            shutdown_line = SHUTDOWN_TEMPLATE.format(minutes=max_hours * 60, hours=max_hours)
        else:
            shutdown_line = SHUTDOWN_DISABLED
        return USER_DATA_TEMPLATE.format(stack_name         = str(stack_name)    ,
                                         region             = str(region)        ,
                                         registry           = str(registry)      ,
                                         host_control_image = HOST_CONTROL_IMAGE ,
                                         api_key_name       = str(api_key_name)  ,
                                         api_key_value      = str(api_key_value) ,
                                         log_file           = LOG_FILE           ,
                                         shutdown_line      = shutdown_line      )

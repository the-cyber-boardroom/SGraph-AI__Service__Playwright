# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Docker__User_Data__Builder
# cloud-init for a bare AL2023 instance with Docker CE installed. Installs
# Docker Engine + Compose plugin so `docker run` and `docker compose` work
# out of the box. SSM agent is already present on AL2023.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


LOG_FILE = '/var/log/sg-docker-boot.log'


USER_DATA_TEMPLATE = """\
#!/usr/bin/env bash
set -euo pipefail
exec > >(tee -a {log_file}) 2>&1
echo "[sg-docker] boot starting at $(date -u +%FT%TZ)"

STACK_NAME='{stack_name}'
REGION='{region}'

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

echo "[sg-docker] boot complete at $(date -u +%FT%TZ)"
"""


PLACEHOLDERS = ('stack_name', 'region', 'log_file')                                 # Locked by test


class Docker__User_Data__Builder(Type_Safe):

    def render(self, stack_name: str, region: str) -> str:
        return USER_DATA_TEMPLATE.format(stack_name = str(stack_name),
                                         region     = str(region)    ,
                                         log_file   = LOG_FILE       )

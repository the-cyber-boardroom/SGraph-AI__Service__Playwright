# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — OpenSearch__User_Data__Builder
# Renders the EC2 UserData bash that installs OpenSearch + Dashboards on a
# fresh AL2023 instance. Single responsibility: string templating with safe
# substitutions. The compose YAML is rendered upstream (by
# OpenSearch__Compose__Template) and embedded here as a heredoc so this
# class never touches admin_password directly — secrets stay in one place.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


COMPOSE_DIR  = '/opt/sg-opensearch'
COMPOSE_FILE = '/opt/sg-opensearch/docker-compose.yml'
LOG_FILE     = '/var/log/sg-opensearch-boot.log'


# Bash template — every {placeholder} must appear in PLACEHOLDERS below.
USER_DATA_TEMPLATE = """\
#!/usr/bin/env bash
set -euo pipefail
exec > >(tee -a {log_file}) 2>&1
echo "[sg-opensearch] boot starting at $(date -u +%FT%TZ)"

STACK_NAME='{stack_name}'
REGION='{region}'

echo "[sg-opensearch] installing Docker on AL2023..."
dnf install -y docker
systemctl enable --now docker

echo "[sg-opensearch] installing docker compose plugin..."
mkdir -p /usr/local/lib/docker/cli-plugins
curl -fsSL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" \\
    -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

echo "[sg-opensearch] writing compose to {compose_file}..."
mkdir -p {compose_dir}
cat > {compose_file} <<'SG_OS_COMPOSE_EOF'
{compose_yaml}
SG_OS_COMPOSE_EOF

echo "[sg-opensearch] required for OS 2.x: increase vm.max_map_count..."
sysctl -w vm.max_map_count=262144
echo "vm.max_map_count=262144" >> /etc/sysctl.d/99-sg-opensearch.conf

echo "[sg-opensearch] starting compose..."
cd {compose_dir}
docker compose up -d

echo "[sg-opensearch] boot complete at $(date -u +%FT%TZ)"
"""


PLACEHOLDERS = ('stack_name', 'region', 'log_file', 'compose_dir', 'compose_file', 'compose_yaml')   # Locked by test


class OpenSearch__User_Data__Builder(Type_Safe):

    def render(self, stack_name: str, region: str, compose_yaml: str) -> str:      # admin_password lives inside compose_yaml — secrets in one place
        return USER_DATA_TEMPLATE.format(stack_name   = str(stack_name)   ,
                                         region       = str(region)       ,
                                         log_file     = LOG_FILE           ,
                                         compose_dir  = COMPOSE_DIR        ,
                                         compose_file = COMPOSE_FILE       ,
                                         compose_yaml = str(compose_yaml)  )

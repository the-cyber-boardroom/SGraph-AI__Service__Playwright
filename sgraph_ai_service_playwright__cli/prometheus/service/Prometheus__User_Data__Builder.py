# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Prometheus__User_Data__Builder
# Renders the EC2 UserData bash that installs Prometheus + cAdvisor +
# node-exporter on a fresh AL2023 instance. Single responsibility: string
# templating. Mirrors OpenSearch__User_Data__Builder minus the
# `vm.max_map_count` bump (Prometheus doesn't need it).
#
# Both the compose YAML and the prometheus.yml are rendered upstream and
# passed in as input — this class never substitutes secrets directly
# (Prometheus has no built-in auth per P1, so there are no secrets in
# practice; the seam stays consistent with the OS pattern).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


COMPOSE_DIR        = '/opt/sg-prometheus'
COMPOSE_FILE       = '/opt/sg-prometheus/docker-compose.yml'
PROM_CONFIG_FILE   = '/opt/sg-prometheus/prometheus.yml'
LOG_FILE           = '/var/log/sg-prometheus-boot.log'


# Bash template — every {placeholder} must appear in PLACEHOLDERS below.
USER_DATA_TEMPLATE = """\
#!/usr/bin/env bash
set -euo pipefail
exec > >(tee -a {log_file}) 2>&1
echo "[sg-prometheus] boot starting at $(date -u +%FT%TZ)"

STACK_NAME='{stack_name}'
REGION='{region}'

echo "[sg-prometheus] installing Docker on AL2023..."
dnf install -y docker
systemctl enable --now docker

echo "[sg-prometheus] installing docker compose plugin..."
mkdir -p /usr/local/lib/docker/cli-plugins
curl -fsSL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" \\
    -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

echo "[sg-prometheus] writing prometheus.yml to {prom_config_file}..."
mkdir -p {compose_dir}
cat > {prom_config_file} <<'SG_PROM_CONFIG_EOF'
{prom_config_yaml}
SG_PROM_CONFIG_EOF

echo "[sg-prometheus] writing compose to {compose_file}..."
cat > {compose_file} <<'SG_PROM_COMPOSE_EOF'
{compose_yaml}
SG_PROM_COMPOSE_EOF

echo "[sg-prometheus] starting compose..."
cd {compose_dir}
docker compose up -d

echo "[sg-prometheus] boot complete at $(date -u +%FT%TZ)"
"""


PLACEHOLDERS = ('stack_name', 'region', 'log_file',
                'compose_dir', 'compose_file', 'compose_yaml',
                'prom_config_file', 'prom_config_yaml')                             # Locked by test


class Prometheus__User_Data__Builder(Type_Safe):

    def render(self, stack_name: str, region: str, compose_yaml: str, prom_config_yaml: str) -> str:
        return USER_DATA_TEMPLATE.format(stack_name       = str(stack_name)        ,
                                         region           = str(region)            ,
                                         log_file         = LOG_FILE                ,
                                         compose_dir      = COMPOSE_DIR             ,
                                         compose_file     = COMPOSE_FILE            ,
                                         compose_yaml     = str(compose_yaml)       ,
                                         prom_config_file = PROM_CONFIG_FILE        ,
                                         prom_config_yaml = str(prom_config_yaml)   )

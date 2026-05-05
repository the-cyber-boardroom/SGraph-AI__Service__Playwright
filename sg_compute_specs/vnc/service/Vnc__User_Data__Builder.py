# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — VNC: Vnc__User_Data__Builder
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute.platforms.ec2.user_data.Section__Sidecar                            import Section__Sidecar
from sg_compute_specs.vnc.service.Vnc__Caddy__Template                              import Vnc__Caddy__Template


COMPOSE_DIR        = '/opt/sg-vnc'
COMPOSE_FILE       = '/opt/sg-vnc/docker-compose.yml'
INTERCEPTOR_FILE   = '/opt/sg-vnc/interceptors/runtime/active.py'
CADDY_DIR          = '/opt/sg-vnc/caddy'
CADDY_DOCKERFILE   = '/opt/sg-vnc/caddy/Dockerfile'
CADDY_FILE         = '/opt/sg-vnc/caddy/Caddyfile'
CADDY_USERS_JSON   = '/opt/sg-vnc/caddy/users.json'
CADDY_JWT_SECRET   = '/opt/sg-vnc/caddy/jwt-secret'
LOG_FILE           = '/var/log/sg-vnc-boot.log'


USER_DATA_TEMPLATE = """\
#!/usr/bin/env bash
set -euo pipefail
exec > >(tee -a {log_file}) 2>&1
echo "[sg-vnc] boot starting at $(date -u +%FT%TZ)"

STACK_NAME='{stack_name}'
REGION='{region}'
SG_VNC_OPERATOR_PASSWORD='{operator_password}'

echo "[sg-vnc] installing Docker on AL2023..."
dnf install -y docker httpd-tools
systemctl enable --now docker

echo "[sg-vnc] installing docker compose plugin..."
mkdir -p /usr/local/lib/docker/cli-plugins
curl -fsSL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" \\
    -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

echo "[sg-vnc] preparing /opt/sg-vnc layout..."
mkdir -p {compose_dir}/caddy/data {compose_dir}/caddy/config \\
         {compose_dir}/interceptors/runtime {compose_dir}/interceptors/examples

echo "[sg-vnc] writing Caddy Dockerfile..."
cat > {caddy_dockerfile} <<'SG_VNC_CADDY_DOCKERFILE_EOF'
{caddy_dockerfile_body}
SG_VNC_CADDY_DOCKERFILE_EOF

echo "[sg-vnc] writing Caddyfile..."
cat > {caddy_file} <<'SG_VNC_CADDYFILE_EOF'
{caddyfile_body}
SG_VNC_CADDYFILE_EOF

echo "[sg-vnc] generating bcrypt hash for operator password..."
BCRYPT_HASH=$(htpasswd -bnBC 10 operator "${{SG_VNC_OPERATOR_PASSWORD}}" | cut -d: -f2-)

echo "[sg-vnc] writing caddy-security users.json..."
cat > {caddy_users_json} <<SG_VNC_USERS_JSON_EOF
{users_json_body}
SG_VNC_USERS_JSON_EOF

echo "[sg-vnc] generating JWT signing secret (32 bytes from /dev/urandom)..."
head -c 32 /dev/urandom | base64 > {caddy_jwt_secret}

chmod 644 {caddy_users_json} {caddy_jwt_secret}

echo "[sg-vnc] writing interceptor (kind={interceptor_kind}) to {interceptor_file}..."
cat > {interceptor_file} <<'SG_VNC_INTERCEPTOR_EOF'
{interceptor_source}
SG_VNC_INTERCEPTOR_EOF

echo "[sg-vnc] writing compose to {compose_file}..."
cat > {compose_file} <<'SG_VNC_COMPOSE_EOF'
{compose_yaml}
SG_VNC_COMPOSE_EOF

echo "[sg-vnc] building caddy image (caddy:2-builder + caddy-security via xcaddy)..."
cd {compose_dir}
docker compose build caddy

echo "[sg-vnc] starting compose..."
docker compose up -d

{sidecar_section}
echo "[sg-vnc] boot complete at $(date -u +%FT%TZ)"
"""


PLACEHOLDERS = ('stack_name', 'region', 'log_file', 'operator_password',
                'compose_dir', 'compose_file', 'compose_yaml',
                'interceptor_file', 'interceptor_source', 'interceptor_kind',
                'caddy_dockerfile', 'caddy_dockerfile_body',
                'caddy_file', 'caddyfile_body',
                'caddy_users_json', 'users_json_body',
                'caddy_jwt_secret', 'sidecar_section')                              # Locked by test


class Vnc__User_Data__Builder(Type_Safe):

    def render(self, stack_name        : str,
                     region            : str,
                     compose_yaml      : str,
                     interceptor_source: str,
                     operator_password : str,
                     interceptor_kind  : str = 'none',
                     registry          : str = ''    ,
                     api_key_name      : str = 'X-API-Key',
                     api_key_ssm_path     : str = ''    ) -> str:
        caddy_template   = Vnc__Caddy__Template()
        caddy_dockerfile = caddy_template.render_dockerfile()
        caddyfile_body   = caddy_template.render_caddyfile()
        users_json_body  = caddy_template.render_users_json(bcrypt_hash='${BCRYPT_HASH}')
        sidecar_section  = Section__Sidecar().render(registry      = registry      ,
                                                     api_key_name  = api_key_name  ,
                                                     api_key_ssm_path = api_key_ssm_path )

        return USER_DATA_TEMPLATE.format(stack_name            = str(stack_name)        ,
                                         region                = str(region)            ,
                                         log_file              = LOG_FILE               ,
                                         operator_password     = str(operator_password) ,
                                         compose_dir           = COMPOSE_DIR            ,
                                         compose_file          = COMPOSE_FILE           ,
                                         compose_yaml          = str(compose_yaml)      ,
                                         interceptor_file      = INTERCEPTOR_FILE       ,
                                         interceptor_source    = str(interceptor_source),
                                         interceptor_kind      = str(interceptor_kind)  ,
                                         caddy_dockerfile      = CADDY_DOCKERFILE       ,
                                         caddy_dockerfile_body = caddy_dockerfile       ,
                                         caddy_file            = CADDY_FILE             ,
                                         caddyfile_body        = caddyfile_body         ,
                                         caddy_users_json      = CADDY_USERS_JSON       ,
                                         users_json_body       = users_json_body        ,
                                         caddy_jwt_secret      = CADDY_JWT_SECRET       ,
                                         sidecar_section       = sidecar_section        )

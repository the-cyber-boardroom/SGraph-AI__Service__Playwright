# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Vnc__User_Data__Builder
# Renders the EC2 UserData bash that installs chromium + nginx + mitmproxy
# on a fresh AL2023 instance. Mirrors OS / Prom user-data shape.
#
# Layout (everything under /opt/sg-vnc):
#   nginx/conf.d/default.conf        ← TLS terminator + Basic auth + reverse-proxy
#   nginx/htpasswd                   ← bcrypt hash from operator_password
#   nginx/tls/{cert.pem,key.pem}     ← self-signed cert generated at boot
#   mitm/proxyauth                   ← `operator:<password>` (file format mitmproxy expects)
#   interceptors/runtime/active.py   ← resolved interceptor source (no-op / example / inline)
#   docker-compose.yml               ← rendered upstream by Vnc__Compose__Template
#
# operator_password is treated as a single secret used in two places (htpasswd
# + mitmproxy proxyauth file). It does NOT appear in compose YAML.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


COMPOSE_DIR        = '/opt/sg-vnc'
COMPOSE_FILE       = '/opt/sg-vnc/docker-compose.yml'
INTERCEPTOR_FILE   = '/opt/sg-vnc/interceptors/runtime/active.py'
NGINX_CONF_FILE    = '/opt/sg-vnc/nginx/conf.d/default.conf'
NGINX_HTPASSWD     = '/opt/sg-vnc/nginx/htpasswd'
NGINX_TLS_DIR      = '/opt/sg-vnc/nginx/tls'
MITM_PROXYAUTH     = '/opt/sg-vnc/mitm/proxyauth'
LOG_FILE           = '/var/log/sg-vnc-boot.log'


# nginx default.conf — TLS terminator on 443; Basic auth; reverse-proxy /
# to the chromium-VNC noVNC endpoint and /mitmweb/ to mitmweb on 8081.
NGINX_DEFAULT_CONF = """\
server {
    listen 443 ssl;
    server_name _;

    ssl_certificate     /etc/nginx/tls/cert.pem;
    ssl_certificate_key /etc/nginx/tls/key.pem;

    auth_basic           "sg-vnc";
    auth_basic_user_file /etc/nginx/htpasswd;

    location / {
        proxy_pass         http://chromium:3000/;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade           $http_upgrade;
        proxy_set_header   Connection        "upgrade";
        proxy_set_header   Host              $host;
        proxy_read_timeout 1800s;
    }

    location /mitmweb/ {
        proxy_pass         http://mitmproxy:8081/;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade           $http_upgrade;
        proxy_set_header   Connection        "upgrade";
        proxy_set_header   Host              $host;
    }
}
"""


# Bash template — every {placeholder} must appear in PLACEHOLDERS below.
USER_DATA_TEMPLATE = """\
#!/usr/bin/env bash
set -euo pipefail
exec > >(tee -a {log_file}) 2>&1
echo "[sg-vnc] boot starting at $(date -u +%FT%TZ)"

STACK_NAME='{stack_name}'
REGION='{region}'
SG_VNC_OPERATOR_PASSWORD='{operator_password}'

echo "[sg-vnc] installing Docker on AL2023..."
dnf install -y docker httpd-tools openssl
systemctl enable --now docker

echo "[sg-vnc] installing docker compose plugin..."
mkdir -p /usr/local/lib/docker/cli-plugins
curl -fsSL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" \\
    -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

echo "[sg-vnc] preparing /opt/sg-vnc layout..."
mkdir -p {compose_dir}/nginx/conf.d {compose_dir}/nginx/tls {compose_dir}/mitm \\
         {compose_dir}/interceptors/runtime {compose_dir}/interceptors/examples

echo "[sg-vnc] writing nginx default.conf..."
cat > {nginx_conf_file} <<'SG_VNC_NGINX_CONF_EOF'
{nginx_conf}
SG_VNC_NGINX_CONF_EOF

echo "[sg-vnc] writing operator htpasswd (bcrypt)..."
htpasswd -bcB {nginx_htpasswd} operator "${{SG_VNC_OPERATOR_PASSWORD}}"

echo "[sg-vnc] generating self-signed TLS cert..."
openssl req -x509 -nodes -newkey rsa:2048 -days 365 \\
    -keyout {nginx_tls_dir}/key.pem -out {nginx_tls_dir}/cert.pem \\
    -subj '/CN=sg-vnc/O=sg-vnc/OU=ephemeral'

echo "[sg-vnc] writing mitmproxy proxyauth htpasswd file..."
htpasswd -bcB {mitm_proxyauth} operator "${{SG_VNC_OPERATOR_PASSWORD}}"              # mitmproxy's --set proxyauth=@FILE uses passlib HtpasswdFile and rejects plaintext; needs proper bcrypt entry, same shape as the nginx htpasswd above
chmod 644 {mitm_proxyauth} {nginx_htpasswd}                                          # 0644 — both files are bind-mounted into containers that run as non-root (mitmproxy + nginx). At 0600 the container user can't open them; mitmweb crash-loops with "Could not open htpasswd file". The host SG already limits exposure; the htpasswd is bcrypt-hashed.

echo "[sg-vnc] writing interceptor (kind={interceptor_kind}) to {interceptor_file}..."
cat > {interceptor_file} <<'SG_VNC_INTERCEPTOR_EOF'
{interceptor_source}
SG_VNC_INTERCEPTOR_EOF

echo "[sg-vnc] writing compose to {compose_file}..."
cat > {compose_file} <<'SG_VNC_COMPOSE_EOF'
{compose_yaml}
SG_VNC_COMPOSE_EOF

echo "[sg-vnc] starting compose..."
cd {compose_dir}
docker compose up -d

echo "[sg-vnc] boot complete at $(date -u +%FT%TZ)"
"""


PLACEHOLDERS = ('stack_name', 'region', 'log_file', 'operator_password',
                'compose_dir', 'compose_file', 'compose_yaml',
                'interceptor_file', 'interceptor_source', 'interceptor_kind',
                'nginx_conf_file', 'nginx_conf', 'nginx_htpasswd', 'nginx_tls_dir',
                'mitm_proxyauth')                                                   # Locked by test


class Vnc__User_Data__Builder(Type_Safe):

    def render(self, stack_name        : str,
                     region            : str,
                     compose_yaml      : str,
                     interceptor_source: str,
                     operator_password : str,
                     interceptor_kind  : str = 'none') -> str:                      # operator_password is URL-safe base64 (no quotes) — fits inside single quotes safely
        return USER_DATA_TEMPLATE.format(stack_name         = str(stack_name)         ,
                                         region             = str(region)             ,
                                         log_file           = LOG_FILE                 ,
                                         operator_password  = str(operator_password)   ,
                                         compose_dir        = COMPOSE_DIR              ,
                                         compose_file       = COMPOSE_FILE             ,
                                         compose_yaml       = str(compose_yaml)        ,
                                         interceptor_file   = INTERCEPTOR_FILE         ,
                                         interceptor_source = str(interceptor_source)  ,
                                         interceptor_kind   = str(interceptor_kind)    ,
                                         nginx_conf_file    = NGINX_CONF_FILE          ,
                                         nginx_conf         = NGINX_DEFAULT_CONF       ,
                                         nginx_htpasswd     = NGINX_HTPASSWD           ,
                                         nginx_tls_dir      = NGINX_TLS_DIR            ,
                                         mitm_proxyauth     = MITM_PROXYAUTH           )

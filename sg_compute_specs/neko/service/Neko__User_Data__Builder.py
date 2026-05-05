# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Neko: Neko__User_Data__Builder
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute.platforms.ec2.user_data.Section__Sidecar                           import Section__Sidecar


NEKO_DIR         = '/opt/sg-neko'
COMPOSE_FILE     = '/opt/sg-neko/docker-compose.yml'
CADDY_DIR        = '/opt/sg-neko/caddy'
CADDY_FILE       = '/opt/sg-neko/caddy/Caddyfile'
CERTS_DIR        = '/opt/sg-neko/caddy/certs'
LOG_FILE         = '/var/log/sg-neko-boot.log'
NEKO_IMAGE       = 'ghcr.io/m1k1o/neko/chromium:latest'
WEBRTC_PORT_FROM = 52000
WEBRTC_PORT_TO   = 52100


CADDYFILE_TEMPLATE = """\
:443 {{
  tls {caddy_certs_dir}/neko.crt {caddy_certs_dir}/neko.key
  reverse_proxy neko:8080
}}
"""

COMPOSE_TEMPLATE = """\
services:
  neko:
    image: {neko_image}
    restart: unless-stopped
    shm_size: "2gb"
    environment:
      NEKO_SCREEN:          "1920x1080@30"
      NEKO_PASSWORD:        "{member_password}"
      NEKO_PASSWORD_ADMIN:  "{admin_password}"
      NEKO_BIND:            ":8080"
      NEKO_EPR:             "{webrtc_from}-{webrtc_to}"
      NEKO_NAT1TO1:         "${{PUBLIC_IP}}"
      NEKO_ICELITE:         "1"
    ports:
      - "{webrtc_from}-{webrtc_to}:{webrtc_from}-{webrtc_to}/udp"
    cap_add:
      - SYS_ADMIN

  caddy:
    image: caddy:2
    restart: unless-stopped
    ports:
      - "443:443"
    volumes:
      - {caddy_dir}/Caddyfile:/etc/caddy/Caddyfile:ro
      - {caddy_dir}/certs:/etc/caddy/certs:ro
      - {caddy_dir}/data:/data
      - {caddy_dir}/config:/config
    depends_on:
      - neko
"""

USER_DATA_TEMPLATE = """\
#!/usr/bin/env bash
set -euo pipefail
exec > >(tee -a {log_file}) 2>&1
echo "[sg-neko] boot starting at $(date -u +%FT%TZ)"

STACK_NAME='{stack_name}'
REGION='{region}'

echo "[sg-neko] fetching public IP from EC2 metadata..."
TOKEN=$(curl -sf -X PUT "http://169.254.169.254/latest/api/token" \\
    -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
PUBLIC_IP=$(curl -sf -H "X-aws-ec2-metadata-token: $TOKEN" \\
    http://169.254.169.254/latest/meta-data/public-ipv4)
echo "[sg-neko] public IP: $PUBLIC_IP"

echo "[sg-neko] installing Docker and openssl on AL2023..."
dnf install -y docker openssl
systemctl enable --now docker

echo "[sg-neko] installing docker compose plugin..."
mkdir -p /usr/local/lib/docker/cli-plugins
curl -fsSL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" \\
    -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

echo "[sg-neko] preparing layout..."
mkdir -p {caddy_dir}/data {caddy_dir}/config {certs_dir}

echo "[sg-neko] generating self-signed TLS cert for $PUBLIC_IP..."
openssl req -x509 -newkey rsa:4096 \\
    -keyout {certs_dir}/neko.key \\
    -out    {certs_dir}/neko.crt \\
    -days 3650 -nodes \\
    -subj "/CN=$PUBLIC_IP" \\
    -addext "subjectAltName=IP:$PUBLIC_IP"
chmod 644 {certs_dir}/neko.crt {certs_dir}/neko.key

echo "[sg-neko] writing Caddyfile..."
cat > {caddy_file} <<NEKO_CADDY_EOF
{caddyfile}
NEKO_CADDY_EOF

echo "[sg-neko] writing docker-compose.yml (PUBLIC_IP=$PUBLIC_IP)..."
PUBLIC_IP="$PUBLIC_IP" envsubst < /dev/stdin > {compose_file} <<'NEKO_COMPOSE_EOF'
{compose_yaml}
NEKO_COMPOSE_EOF

echo "[sg-neko] pulling images..."
cd {neko_dir}
docker compose pull

echo "[sg-neko] starting stack..."
docker compose up -d

{sidecar_section}
echo "[sg-neko] boot complete at $(date -u +%FT%TZ)"
"""


PLACEHOLDERS = ('stack_name', 'region', 'log_file',
                'neko_dir', 'caddy_dir', 'caddy_file', 'certs_dir',
                'caddyfile', 'compose_file', 'compose_yaml',
                'sidecar_section')                                                   # Locked by test


class Neko__User_Data__Builder(Type_Safe):

    def render(self, stack_name      : str,
                     region          : str,
                     admin_password  : str,
                     member_password : str,
                     registry        : str = '',
                     api_key_name    : str = 'X-API-Key',
                     api_key_ssm_path   : str = '') -> str:
        caddyfile       = CADDYFILE_TEMPLATE.format(caddy_certs_dir='/etc/caddy/certs')
        compose_yaml    = COMPOSE_TEMPLATE.format(neko_image       = NEKO_IMAGE      ,
                                                  member_password  = member_password ,
                                                  admin_password   = admin_password  ,
                                                  webrtc_from      = WEBRTC_PORT_FROM,
                                                  webrtc_to        = WEBRTC_PORT_TO  ,
                                                  caddy_dir        = CADDY_DIR       )
        sidecar_section = Section__Sidecar().render(registry      = registry      ,
                                                    api_key_name  = api_key_name  ,
                                                    api_key_ssm_path = api_key_ssm_path )
        return USER_DATA_TEMPLATE.format(stack_name      = stack_name      ,
                                          region          = region          ,
                                          log_file        = LOG_FILE        ,
                                          neko_dir        = NEKO_DIR        ,
                                          caddy_dir       = CADDY_DIR       ,
                                          caddy_file      = CADDY_FILE      ,
                                          certs_dir       = CERTS_DIR       ,
                                          caddyfile       = caddyfile       ,
                                          compose_file    = COMPOSE_FILE    ,
                                          compose_yaml    = compose_yaml    ,
                                          sidecar_section = sidecar_section )

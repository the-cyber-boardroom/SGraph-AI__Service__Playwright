# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Firefox__User_Data__Builder
# Renders the EC2 UserData bash that provisions a jlesage/firefox stack on a
# fresh AL2023 instance.
#
# Stack layout (/opt/sg-firefox):
#   docker-compose.yml          — firefox service
#   /docker/appdata/firefox     — persistent Firefox config volume
#
# jlesage/firefox key env vars:
#   WEB_AUTHENTICATION          — 1 = require password to access the web UI
#   WEB_AUTHENTICATION_USERNAME — login username (default: user)
#   WEB_AUTHENTICATION_PASSWORD — login password
#   DISPLAY_WIDTH / DISPLAY_HEIGHT — resolution (default 1920x1080)
#   KEEP_APP_RUNNING            — 1 = restart Firefox if it crashes
#
# Access: http://<public-ip>:5800/ in a browser. No TLS — plain HTTP.
# Port 5800 is open from caller /32 only (set in Firefox__SG__Helper).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


FIREFOX_DIR    = '/opt/sg-firefox'
COMPOSE_FILE   = '/opt/sg-firefox/docker-compose.yml'
APP_DATA_DIR   = '/docker/appdata/firefox'
LOG_FILE       = '/var/log/sg-firefox-boot.log'
FIREFOX_IMAGE  = 'jlesage/firefox'
VIEWER_PORT    = 5800


COMPOSE_TEMPLATE = """\
services:
  firefox:
    image: {firefox_image}
    restart: unless-stopped
    ports:
      - "{viewer_port}:{viewer_port}"
    volumes:
      - {app_data_dir}:/config:rw
    environment:
      SECURE_CONNECTION:           "1"
      WEB_AUTHENTICATION:          "1"
      WEB_AUTHENTICATION_USERNAME: "user"
      WEB_AUTHENTICATION_PASSWORD: "{password}"
      DISPLAY_WIDTH:               "1920"
      DISPLAY_HEIGHT:              "1080"
      KEEP_APP_RUNNING:            "1"
    shm_size: "1gb"
"""


USER_DATA_TEMPLATE = """\
#!/usr/bin/env bash
set -euo pipefail
exec > >(tee -a {log_file}) 2>&1
echo "[sg-firefox] boot starting at $(date -u +%FT%TZ)"

STACK_NAME='{stack_name}'
REGION='{region}'

echo "[sg-firefox] installing Docker on AL2023..."
dnf install -y docker
systemctl enable --now docker

echo "[sg-firefox] installing docker compose plugin..."
mkdir -p /usr/local/lib/docker/cli-plugins
curl -fsSL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" \\
    -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

echo "[sg-firefox] preparing layout..."
mkdir -p {firefox_dir} {app_data_dir}

echo "[sg-firefox] writing docker-compose.yml..."
cat > {compose_file} <<'FIREFOX_COMPOSE_EOF'
{compose_yaml}
FIREFOX_COMPOSE_EOF

echo "[sg-firefox] pulling image..."
cd {firefox_dir}
docker compose pull

echo "[sg-firefox] starting stack..."
docker compose up -d

echo "[sg-firefox] boot complete at $(date -u +%FT%TZ)"
"""


class Firefox__User_Data__Builder(Type_Safe):

    def render(self, stack_name : str,
                     region     : str,
                     password   : str) -> str:
        compose_yaml = COMPOSE_TEMPLATE.format(
            firefox_image = FIREFOX_IMAGE ,
            viewer_port   = VIEWER_PORT   ,
            app_data_dir  = APP_DATA_DIR  ,
            password      = password      )

        return USER_DATA_TEMPLATE.format(
            stack_name   = stack_name  ,
            region       = region      ,
            log_file     = LOG_FILE    ,
            firefox_dir  = FIREFOX_DIR ,
            app_data_dir = APP_DATA_DIR,
            compose_file = COMPOSE_FILE,
            compose_yaml = compose_yaml)

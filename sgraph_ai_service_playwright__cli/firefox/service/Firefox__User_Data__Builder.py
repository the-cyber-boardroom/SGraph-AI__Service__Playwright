# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Firefox__User_Data__Builder
# Renders the EC2 UserData bash that provisions a jlesage/firefox + mitmproxy
# stack on a fresh AL2023 instance.
#
# Stack layout (/opt/sg-firefox):
#   docker-compose.yml          — firefox + mitmproxy services
#   interceptors/active.py      — resolved interceptor source (mitmproxy script)
#   mitmproxy-data/             — mitmproxy CA cert + state (bind-mounted)
#   /docker/appdata/firefox     — persistent Firefox config volume
#
# mitmproxy acts as Firefox's HTTP/HTTPS proxy (via user.js).
# The mitmproxy CA cert is installed into the OS trust store at boot so
# Firefox trusts it when security.enterprise_roots.enabled = true.
# mitmweb is exposed on port 8081 (no auth; gated by SG to caller IP only).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


FIREFOX_DIR      = '/opt/sg-firefox'
COMPOSE_FILE     = '/opt/sg-firefox/docker-compose.yml'
INTERCEPTOR_FILE = '/opt/sg-firefox/interceptors/active.py'
MITM_DATA_DIR    = '/opt/sg-firefox/mitmproxy-data'
APP_DATA_DIR     = '/docker/appdata/firefox'
PROFILE_DIR      = '/docker/appdata/firefox/profile'
USER_JS_FILE     = '/docker/appdata/firefox/profile/user.js'
LOG_FILE         = '/var/log/sg-firefox-boot.log'
ENV_FILE         = '/run/sg-firefox/env'                                            # tmpfs (RAM-only); not baked into AMI
FIREFOX_IMAGE    = 'jlesage/firefox'
MITM_IMAGE       = 'mitmproxy/mitmproxy'
VIEWER_PORT      = 5800
MITMWEB_PORT     = 8081
MITM_PROXY_PORT  = 8080                                                             # internal docker network port


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
    depends_on:
      - mitmproxy

  mitmproxy:
    image: {mitm_image}
    restart: unless-stopped
    ports:
      - "{mitmweb_port}:{mitmweb_port}"
    volumes:
      - {mitm_data_dir}:/home/mitmproxy/.mitmproxy
      - {firefox_dir}/interceptors:/interceptors:ro
    env_file:
      - /run/sg-firefox/env
    command: >
      mitmweb
      --web-host 0.0.0.0
      --web-port {mitmweb_port}
      --listen-host 0.0.0.0
      --listen-port {mitm_proxy_port}
      --scripts /interceptors/active.py
"""

USER_JS_TEMPLATE = """\
// proxy: mitmproxy (docker-compose internal network)
user_pref("network.proxy.type",          1);
user_pref("network.proxy.http",          "mitmproxy");
user_pref("network.proxy.http_port",     {mitm_proxy_port});
user_pref("network.proxy.ssl",           "mitmproxy");
user_pref("network.proxy.ssl_port",      {mitm_proxy_port});
user_pref("network.proxy.no_proxies_on", "localhost,127.0.0.1");
// disable update checks — avoids 10-30s startup delay on every launch
user_pref("app.update.auto",             false);
user_pref("app.update.enabled",          false);
user_pref("extensions.update.enabled",   false);
"""

USER_DATA_TEMPLATE = """\
#!/usr/bin/env bash
set -euo pipefail
exec > >(tee -a {log_file}) 2>&1
echo "[sg-firefox] boot starting at $(date -u +%FT%TZ)"

STACK_NAME='{stack_name}'
REGION='{region}'

echo "[sg-firefox] installing Docker + certutil (nss-tools) on AL2023..."
dnf install -y docker nss-tools
systemctl enable --now docker

echo "[sg-firefox] installing docker compose plugin..."
mkdir -p /usr/local/lib/docker/cli-plugins
curl -fsSL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" \\
    -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

echo "[sg-firefox] preparing layout..."
mkdir -p {firefox_dir}/interceptors {mitm_data_dir} {app_data_dir} {profile_dir}

echo "[sg-firefox] writing interceptor (kind={interceptor_kind}) to {interceptor_file}..."
cat > {interceptor_file} <<'SG_FIREFOX_INTERCEPTOR_EOF'
{interceptor_source}
SG_FIREFOX_INTERCEPTOR_EOF

echo "[sg-firefox] writing docker-compose.yml..."
cat > {compose_file} <<'FIREFOX_COMPOSE_EOF'
{compose_yaml}
FIREFOX_COMPOSE_EOF

echo "[sg-firefox] pulling images..."
cd {firefox_dir}
docker compose pull

echo "[sg-firefox] starting mitmproxy first (generates CA cert)..."
docker compose up -d mitmproxy

echo "[sg-firefox] waiting for mitmproxy CA cert to appear..."
for i in $(seq 1 30); do
    if [ -f {mitm_data_dir}/mitmproxy-ca-cert.pem ]; then
        echo "[sg-firefox] CA cert ready after ${{i}} × 2s"
        break
    fi
    sleep 2
done

echo "[sg-firefox] installing mitmproxy CA cert into Firefox NSS database..."
if [ -f {mitm_data_dir}/mitmproxy-ca-cert.pem ]; then
    # Firefox has its own cert store (NSS) separate from the OS trust store.
    # certutil writes directly to the profile's cert9.db so Firefox trusts the
    # mitmproxy CA without any manual step or cert warning.
    certutil -N --empty-password -d sql:{profile_dir} 2>/dev/null || true
    certutil -A -n "mitmproxy CA" -t "TCu,," \
        -i {mitm_data_dir}/mitmproxy-ca-cert.pem \
        -d sql:{profile_dir}
    echo "[sg-firefox] mitmproxy CA trusted in Firefox NSS database."
else
    echo "[sg-firefox] WARNING: CA cert not found after 60s; HTTPS will show cert errors."
fi

echo "[sg-firefox] writing Firefox proxy user.js..."
cat > {user_js_file} <<'FIREFOX_USERJS_EOF'
{user_js}
FIREFOX_USERJS_EOF

echo "[sg-firefox] writing env vars to tmpfs (/run/sg-firefox/env)..."
mkdir -p /run/sg-firefox
cat > {env_file} <<'SG_FIREFOX_ENV_EOF'
{env_source}
SG_FIREFOX_ENV_EOF

echo "[sg-firefox] starting Firefox..."
docker compose up -d firefox

echo "[sg-firefox] boot complete at $(date -u +%FT%TZ)"
"""


FAST_USER_DATA_TEMPLATE = """\
#!/usr/bin/env bash
set -euo pipefail
exec > >(tee -a {log_file}) 2>&1
echo "[sg-firefox] fast-boot from AMI starting at $(date -u +%FT%TZ)"

STACK_NAME='{stack_name}'

systemctl enable --now docker

echo "[sg-firefox] writing updated docker-compose.yml..."
cat > {compose_file} <<'FIREFOX_COMPOSE_EOF'
{compose_yaml}
FIREFOX_COMPOSE_EOF

if [ "{interceptor_kind}" != "none" ]; then
    echo "[sg-firefox] writing interceptor (kind={interceptor_kind})..."
    cat > {interceptor_file} <<'SG_FIREFOX_INTERCEPTOR_EOF'
{interceptor_source}
SG_FIREFOX_INTERCEPTOR_EOF
else
    echo "[sg-firefox] interceptor_kind=none — keeping AMI baked interceptor in place"
fi

echo "[sg-firefox] writing env vars to tmpfs (/run/sg-firefox/env)..."
mkdir -p /run/sg-firefox
cat > {env_file} <<'SG_FIREFOX_ENV_EOF'
{env_source}
SG_FIREFOX_ENV_EOF

echo "[sg-firefox] starting stack (mitmproxy CA already trusted from AMI)..."
cd {firefox_dir}
docker compose up -d

echo "[sg-firefox] fast-boot complete at $(date -u +%FT%TZ)"
"""


class Firefox__User_Data__Builder(Type_Safe):

    def render(self, stack_name        : str,
                     region            : str,
                     password          : str,
                     interceptor_source: str,
                     interceptor_kind  : str = 'none',
                     env_source        : str = ''    ) -> str:

        compose_yaml = COMPOSE_TEMPLATE.format(
            firefox_image    = FIREFOX_IMAGE   ,
            mitm_image       = MITM_IMAGE      ,
            viewer_port      = VIEWER_PORT     ,
            mitmweb_port     = MITMWEB_PORT    ,
            mitm_proxy_port  = MITM_PROXY_PORT ,
            app_data_dir     = APP_DATA_DIR    ,
            firefox_dir      = FIREFOX_DIR     ,
            mitm_data_dir    = MITM_DATA_DIR   ,
            password         = password        )

        user_js = USER_JS_TEMPLATE.format(mitm_proxy_port=MITM_PROXY_PORT)

        return USER_DATA_TEMPLATE.format(
            stack_name         = stack_name         ,
            region             = region             ,
            log_file           = LOG_FILE           ,
            firefox_dir        = FIREFOX_DIR        ,
            mitm_data_dir      = MITM_DATA_DIR      ,
            app_data_dir       = APP_DATA_DIR       ,
            profile_dir        = PROFILE_DIR        ,
            compose_file       = COMPOSE_FILE       ,
            compose_yaml       = compose_yaml       ,
            interceptor_file   = INTERCEPTOR_FILE   ,
            interceptor_source = interceptor_source ,
            interceptor_kind   = interceptor_kind   ,
            user_js_file       = USER_JS_FILE       ,
            user_js            = user_js            ,
            env_file           = ENV_FILE           ,
            env_source         = env_source         )

    def render_fast(self, stack_name        : str,
                          region            : str,
                          password          : str,
                          interceptor_source: str,
                          interceptor_kind  : str = 'none',
                          env_source        : str = ''    ) -> str:
        compose_yaml = COMPOSE_TEMPLATE.format(
            firefox_image    = FIREFOX_IMAGE   ,
            mitm_image       = MITM_IMAGE      ,
            viewer_port      = VIEWER_PORT     ,
            mitmweb_port     = MITMWEB_PORT    ,
            mitm_proxy_port  = MITM_PROXY_PORT ,
            app_data_dir     = APP_DATA_DIR    ,
            firefox_dir      = FIREFOX_DIR     ,
            mitm_data_dir    = MITM_DATA_DIR   ,
            password         = password        )
        return FAST_USER_DATA_TEMPLATE.format(
            stack_name         = stack_name         ,
            log_file           = LOG_FILE           ,
            firefox_dir        = FIREFOX_DIR        ,
            compose_file       = COMPOSE_FILE       ,
            compose_yaml       = compose_yaml       ,
            interceptor_file   = INTERCEPTOR_FILE   ,
            interceptor_source = interceptor_source ,
            interceptor_kind   = interceptor_kind   ,
            env_file           = ENV_FILE           ,
            env_source         = env_source         )

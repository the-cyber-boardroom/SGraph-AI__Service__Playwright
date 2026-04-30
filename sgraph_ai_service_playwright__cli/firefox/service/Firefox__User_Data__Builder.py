# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Firefox__User_Data__Builder
# Renders the EC2 UserData bash that provisions a jlesage/firefox stack on a
# fresh AL2023 instance.
#
# Stack layout (/opt/sg-firefox):
#   docker-compose.yml          — firefox service
#   proxy-relay.py              — optional: auth relay (when --proxy-user given)
#   /docker/appdata/firefox     — persistent Firefox config volume
#
# Proxy support (--proxy host:port):
#   Without --proxy-user: user.js points Firefox directly at the upstream proxy.
#   Firefox prompts once for credentials, saves them in the profile volume.
#
#   With --proxy-user/--proxy-pass: a tiny Python relay runs as a systemd
#   service on the host, injects Proxy-Authorization, and tunnels CONNECT
#   transparently (no TLS interception). Firefox user.js points to
#   host.docker.internal:8118 — zero auth prompts, works for HTTP + HTTPS.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


FIREFOX_DIR      = '/opt/sg-firefox'
COMPOSE_FILE     = '/opt/sg-firefox/docker-compose.yml'
RELAY_SCRIPT     = '/opt/sg-firefox/proxy-relay.py'
APP_DATA_DIR     = '/docker/appdata/firefox'
PROFILE_DIR      = '/docker/appdata/firefox/profile'
USER_JS_FILE     = '/docker/appdata/firefox/profile/user.js'
LOG_FILE         = '/var/log/sg-firefox-boot.log'
FIREFOX_IMAGE    = 'jlesage/firefox'
VIEWER_PORT      = 5800
RELAY_PORT       = 8118


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
    shm_size: "1gb"{extra_hosts_block}
"""

EXTRA_HOSTS_BLOCK = """
    extra_hosts:
      - "host.docker.internal:host-gateway"
"""

# ── proxy relay (Python, runs as systemd service on host) ────────────────────
# Listens on 0.0.0.0:8118. Injects Proxy-Authorization into every request and
# tunnels CONNECT transparently — no TLS interception, no cert warnings.

RELAY_SCRIPT_TEMPLATE = """\
#!/usr/bin/env python3
import base64, select, socket, threading

UPSTREAM_HOST = '{proxy_host}'
UPSTREAM_PORT = {proxy_port}
AUTH_HEADER   = (b'Proxy-Authorization: Basic ' +
                 base64.b64encode(b'{proxy_user}:{proxy_pass}'))


def _pipe(src, dst):
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            dst.sendall(data)
    except Exception:
        pass
    finally:
        for s in (src, dst):
            try:
                s.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass


def _handle(client):
    try:
        buf = b''
        while b'\\r\\n\\r\\n' not in buf:
            chunk = client.recv(4096)
            if not chunk:
                return
            buf += chunk
        header_end  = buf.index(b'\\r\\n\\r\\n')
        headers_raw = buf[:header_end]
        body_tail   = buf[header_end + 4:]

        lines          = headers_raw.split(b'\\r\\n')
        request_line   = lines[0]
        method         = request_line.split(b' ', 1)[0]
        out_lines      = [request_line]
        for line in lines[1:]:
            if not line.lower().startswith(b'proxy-authorization'):
                out_lines.append(line)
        out_lines.append(AUTH_HEADER)

        upstream = socket.create_connection((UPSTREAM_HOST, UPSTREAM_PORT), timeout=30)
        upstream.sendall(b'\\r\\n'.join(out_lines) + b'\\r\\n\\r\\n')
        if body_tail:
            upstream.sendall(body_tail)

        if method == b'CONNECT':
            resp = b''
            while b'\\r\\n\\r\\n' not in resp:
                chunk = upstream.recv(4096)
                if not chunk:
                    return
                resp += chunk
            client.sendall(b'HTTP/1.1 200 Connection established\\r\\n\\r\\n')

        t = threading.Thread(target=_pipe, args=(upstream, client), daemon=True)
        t.start()
        _pipe(client, upstream)
        t.join()
    except Exception:
        pass
    finally:
        try:
            client.close()
        except Exception:
            pass


server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(('0.0.0.0', {relay_port}))
server.listen(128)
print(f'proxy-relay: {proxy_host}:{proxy_port} via 0.0.0.0:{relay_port}', flush=True)
while True:
    conn, _ = server.accept()
    threading.Thread(target=_handle, args=(conn,), daemon=True).start()
"""

RELAY_SYSTEMD_UNIT = """\
[Unit]
Description=Firefox proxy relay ({proxy_host}:{proxy_port})
After=network.target

[Service]
ExecStart=/usr/bin/python3 {relay_script}
Restart=always
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""

RELAY_SETUP_BLOCK = """\
echo "[sg-firefox] writing proxy-relay.py ({proxy_host}:{proxy_port} → relay port {relay_port})..."
cat > {relay_script} << 'RELAY_PY_EOF'
{relay_py}
RELAY_PY_EOF
chmod +x {relay_script}

echo "[sg-firefox] installing proxy-relay systemd service..."
cat > /etc/systemd/system/sg-firefox-proxy-relay.service << 'RELAY_UNIT_EOF'
{relay_unit}
RELAY_UNIT_EOF
systemctl daemon-reload
systemctl enable --now sg-firefox-proxy-relay
"""

USER_JS_BLOCK = """\
echo "[sg-firefox] writing proxy user.js ({proxy_js_host}:{proxy_js_port})..."
cat > {user_js_file} << 'FIREFOX_USERJS_EOF'
// proxy pre-configured by sp firefox create --proxy
user_pref("network.proxy.type",          1);
user_pref("network.proxy.http",          "{proxy_js_host}");
user_pref("network.proxy.http_port",     {proxy_js_port});
user_pref("network.proxy.ssl",           "{proxy_js_host}");
user_pref("network.proxy.ssl_port",      {proxy_js_port});
user_pref("network.proxy.no_proxies_on", "localhost,127.0.0.1");
user_pref("signon.rememberSignons",      true);
FIREFOX_USERJS_EOF
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
mkdir -p {firefox_dir} {app_data_dir} {profile_dir}

echo "[sg-firefox] writing docker-compose.yml..."
cat > {compose_file} <<'FIREFOX_COMPOSE_EOF'
{compose_yaml}
FIREFOX_COMPOSE_EOF
{proxy_blocks}
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
                     password   : str,
                     proxy_host : str = '',
                     proxy_port : int = 0,
                     proxy_user : str = '',
                     proxy_pass : str = '') -> str:

        use_relay      = bool(proxy_host and proxy_port and proxy_user and proxy_pass)
        use_direct     = bool(proxy_host and proxy_port and not use_relay)
        extra_hosts    = EXTRA_HOSTS_BLOCK if use_relay else ''

        compose_yaml   = COMPOSE_TEMPLATE.format(
            firefox_image     = FIREFOX_IMAGE ,
            viewer_port       = VIEWER_PORT   ,
            app_data_dir      = APP_DATA_DIR  ,
            password          = password      ,
            extra_hosts_block = extra_hosts   )

        proxy_blocks = ''

        if use_relay:
            relay_py   = RELAY_SCRIPT_TEMPLATE.format(
                proxy_host = proxy_host ,
                proxy_port = proxy_port ,
                proxy_user = proxy_user ,
                proxy_pass = proxy_pass ,
                relay_port = RELAY_PORT )
            relay_unit = RELAY_SYSTEMD_UNIT.format(
                proxy_host   = proxy_host  ,
                proxy_port   = proxy_port  ,
                relay_script = RELAY_SCRIPT)
            proxy_blocks += RELAY_SETUP_BLOCK.format(
                proxy_host   = proxy_host  ,
                proxy_port   = proxy_port  ,
                relay_port   = RELAY_PORT  ,
                relay_script = RELAY_SCRIPT,
                relay_py     = relay_py    ,
                relay_unit   = relay_unit  )
            proxy_blocks += USER_JS_BLOCK.format(
                proxy_js_host = 'host.docker.internal',
                proxy_js_port = RELAY_PORT             ,
                user_js_file  = USER_JS_FILE           )

        elif use_direct:
            proxy_blocks += USER_JS_BLOCK.format(
                proxy_js_host = proxy_host  ,
                proxy_js_port = proxy_port  ,
                user_js_file  = USER_JS_FILE)

        return USER_DATA_TEMPLATE.format(
            stack_name   = stack_name  ,
            region       = region      ,
            log_file     = LOG_FILE    ,
            firefox_dir  = FIREFOX_DIR ,
            app_data_dir = APP_DATA_DIR,
            profile_dir  = PROFILE_DIR ,
            compose_file = COMPOSE_FILE,
            compose_yaml = compose_yaml,
            proxy_blocks = proxy_blocks)

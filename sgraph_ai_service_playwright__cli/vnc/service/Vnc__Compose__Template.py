# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Vnc__Compose__Template
# Renders the docker-compose.yml that boots chromium + caddy + mitmproxy on
# the EC2 host. Pure templating; no secrets in the YAML itself —
# operator credentials live in /opt/sg-vnc/caddy/users.json (bcrypt) and
# the JWT signing secret in /opt/sg-vnc/caddy/jwt-secret.
#
# Per plan doc 6 + v0.1.118 caddy slice:
#   N1 — section is sp vnc.
#   N2 — chromium-only at runtime (linuxserver/chromium image).
#   N3 — profile + state wiped at termination (no host volumes for state).
#   P4 — moving 'latest' tags; tests pin known versions.
#
# Caddy replaces nginx. It builds locally from a small Dockerfile rendered
# by Vnc__User_Data__Builder (caddy:2-builder + caddy-security plugin via
# xcaddy) so we never depend on a third-party registry image.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


CHROMIUM_IMAGE  = 'lscr.io/linuxserver/chromium:latest'                             # Tests pin a known version
MITMPROXY_IMAGE = 'mitmproxy/mitmproxy:10.4.2'                                      # Pinned: mitmproxy 11+ added CSRF/host-rebind protection on the mitmweb UI which 403s every cross-origin request (including reverse-proxy via Caddy). 10.4.2 is the last 10.x release and exposes the documented /flows REST API without that block.


# docker-compose.yml template — 3 services on the sg-net bridge.
# - caddy: built locally from /opt/sg-vnc/caddy/Dockerfile (caddy + caddy-security plugin)
# - chromium: noVNC + chromium browser
# - mitmproxy: --proxyauth dropped — :8080 (proxy) is docker-network-only;
#   :8081 (mitmweb UI) is now gated by Caddy at /mitmweb/.
COMPOSE_TEMPLATE = """\
services:
  chromium:
    image: {chromium_image}
    container_name: sg-chromium
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
      - CHROME_CLI=--browser=chromium
      - HTTPS_PROXY=http://mitmproxy:8080
      - HTTP_PROXY=http://mitmproxy:8080
    shm_size: '2gb'
    networks:
      - sg-net
    restart: unless-stopped

  caddy:
    build:
      context: /opt/sg-vnc/caddy                                                  # Dockerfile rendered by Vnc__User_Data__Builder
    image: sg-vnc/caddy:local                                                      # Tag the locally-built image so docker compose can find it on restart
    container_name: sg-caddy
    ports:
      - "443:443"
    volumes:                                                                       # `,z` SELinux relabel — required on AL2023 even with selinux=permissive (defensive)
      - /opt/sg-vnc/caddy/Caddyfile:/etc/caddy/Caddyfile:ro,z
      - /opt/sg-vnc/caddy/users.json:/etc/caddy/users.json:ro,z
      - /opt/sg-vnc/caddy/jwt-secret:/etc/caddy/jwt-secret:ro,z
      - /opt/sg-vnc/caddy/data:/data:z                                            # Caddy persists its internal CA + acme state here
      - /opt/sg-vnc/caddy/config:/config:z
    networks:
      - sg-net
    restart: unless-stopped
    depends_on:
      - chromium
      - mitmproxy

  mitmproxy:
    image: {mitmproxy_image}
    container_name: sg-mitmproxy
    command:
      - mitmweb
      - --web-host=0.0.0.0
      - --web-port=8081
      - --listen-host=0.0.0.0
      - --listen-port=8080
      - --scripts=/opt/sg-vnc/interceptors/runtime/active.py
    volumes:
      - /opt/sg-vnc/interceptors:/opt/sg-vnc/interceptors:ro,z
    networks:
      - sg-net
    restart: unless-stopped

networks:
  sg-net:
    driver: bridge
"""


PLACEHOLDERS = ('chromium_image', 'mitmproxy_image')                                # Locked by test


class Vnc__Compose__Template(Type_Safe):

    def render(self, chromium_image : str = CHROMIUM_IMAGE ,
                     mitmproxy_image: str = MITMPROXY_IMAGE) -> str:
        return COMPOSE_TEMPLATE.format(chromium_image  = str(chromium_image)  ,
                                       mitmproxy_image = str(mitmproxy_image) )

# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Vnc__Compose__Template
# Renders the docker-compose.yml that boots chromium + nginx + mitmproxy on
# the EC2 host. Pure templating; no secrets in the YAML itself —
# MITM_PROXYAUTH is read from /opt/sg-vnc/mitm/proxyauth (file written by
# user-data so the compose template stays static + reviewable).
#
# Per plan doc 6:
#   N1 — section is sp vnc.
#   N2 — chromium-only at runtime (linuxserver/chromium image).
#   N3 — profile + state wiped at termination (no host volumes for state).
#   P4 — moving 'latest' tags; tests pin known versions.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


CHROMIUM_IMAGE  = 'lscr.io/linuxserver/chromium:latest'                             # Tests pin a known version
NGINX_IMAGE     = 'nginx:latest'
MITMPROXY_IMAGE = 'mitmproxy/mitmproxy:latest'


# docker-compose.yml template — 3 services on the sg-net bridge
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

  nginx:
    image: {nginx_image}
    container_name: sg-nginx
    ports:
      - "443:443"
    volumes:                                                                     # `:z` relabels the host path with a shared SELinux label so the container can read it. AL2023 has SELinux enforcing — without :z the bind mount is denied even at chmod 0644.
      - /opt/sg-vnc/nginx/conf.d:/etc/nginx/conf.d:ro,z
      - /opt/sg-vnc/nginx/htpasswd:/etc/nginx/htpasswd:ro,z
      - /opt/sg-vnc/nginx/tls:/etc/nginx/tls:ro,z
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
      - --set=proxyauth=@/opt/sg-vnc/mitm/proxyauth
      - --scripts=/opt/sg-vnc/interceptors/runtime/active.py
    volumes:
      - /opt/sg-vnc/interceptors:/opt/sg-vnc/interceptors:ro,z
      - /opt/sg-vnc/mitm:/opt/sg-vnc/mitm:ro,z
    networks:
      - sg-net
    restart: unless-stopped

networks:
  sg-net:
    driver: bridge
"""


PLACEHOLDERS = ('chromium_image', 'nginx_image', 'mitmproxy_image')                 # Locked by test


class Vnc__Compose__Template(Type_Safe):

    def render(self, chromium_image : str = CHROMIUM_IMAGE ,
                     nginx_image    : str = NGINX_IMAGE    ,
                     mitmproxy_image: str = MITMPROXY_IMAGE) -> str:
        return COMPOSE_TEMPLATE.format(chromium_image  = str(chromium_image)  ,
                                       nginx_image     = str(nginx_image)     ,
                                       mitmproxy_image = str(mitmproxy_image) )

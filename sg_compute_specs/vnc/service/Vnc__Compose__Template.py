# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — VNC: Vnc__Compose__Template
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


CHROMIUM_IMAGE  = 'lscr.io/linuxserver/chromium:latest'
MITMPROXY_IMAGE = 'mitmproxy/mitmproxy:10.4.2'                                      # Pinned: mitmproxy 11+ blocks cross-origin mitmweb UI requests via CSRF protection


COMPOSE_TEMPLATE = '''\
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
      context: /opt/sg-vnc/caddy
    image: sg-vnc/caddy:local
    container_name: sg-caddy
    ports:
      - "443:443"
    volumes:
      - /opt/sg-vnc/caddy/Caddyfile:/etc/caddy/Caddyfile:ro,z
      - /opt/sg-vnc/caddy/users.json:/etc/caddy/users.json:ro,z
      - /opt/sg-vnc/caddy/jwt-secret:/etc/caddy/jwt-secret:ro,z
      - /opt/sg-vnc/caddy/data:/data:z
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
'''


PLACEHOLDERS = ('chromium_image', 'mitmproxy_image')                                # Locked by test


class Vnc__Compose__Template(Type_Safe):

    def render(self, chromium_image : str = CHROMIUM_IMAGE ,
                     mitmproxy_image: str = MITMPROXY_IMAGE) -> str:
        return COMPOSE_TEMPLATE.format(chromium_image  = str(chromium_image)  ,
                                       mitmproxy_image = str(mitmproxy_image) )

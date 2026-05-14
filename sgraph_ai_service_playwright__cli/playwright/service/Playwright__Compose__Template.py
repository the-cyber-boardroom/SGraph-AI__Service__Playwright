# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Playwright__Compose__Template
# Renders the docker-compose.yml for the APP containers on the EC2 host:
#   - sg-playwright (always)          : Playwright FastAPI on :8000
#   - mitmproxy (only --with-mitmproxy): transparent HTTP proxy on :8080
#
# The host-control container is started separately by Playwright__User_Data__Builder
# (mirrors provision_ec2.py pattern — compose owns the app stack, docker run
# owns the sidecar).
#
# `api_key` is baked into the compose env at render time —
# FAST_API__AUTH__API_KEY__VALUE never appears on disk except inside this file.
# Pure templating; no AWS calls.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe


SG_PLAYWRIGHT_IMAGE = 'diniscruz/sg-playwright'                                  # Docker Hub — always tagged at render time
MITMPROXY_IMAGE     = 'mitmproxy/mitmproxy:10.4.2'                               # Pinned: 10.4.2 is last 10.x before CSRF/host-rebind protection in 11+


COMPOSE_BASE = """\
services:
  sg-playwright:
    image: {sg_playwright_image}:{image_tag}
    container_name: sg-playwright
    ports:
      - "8000:8000"
    environment:
      - FAST_API__AUTH__API_KEY__VALUE={api_key}{proxy_env}
    networks: [sg-net]
    restart: unless-stopped{depends_on}
"""

COMPOSE_MITMPROXY_BLOCK = """
  mitmproxy:
    image: {mitmproxy_image}
    container_name: sg-mitmproxy
    command:
      - mitmdump
      - --listen-host=0.0.0.0
      - --listen-port=8080
      - --scripts=/opt/sg-playwright/interceptors/active.py
    volumes:
      - /opt/sg-playwright/interceptors:/opt/sg-playwright/interceptors:ro,z
    networks: [sg-net]
    restart: unless-stopped
"""

COMPOSE_FOOTER = """
networks:
  sg-net:
    driver: bridge
"""

PROXY_ENV_LINES = """
      - SG_PLAYWRIGHT__DEFAULT_PROXY_URL=http://mitmproxy:8080
      - SG_PLAYWRIGHT__IGNORE_HTTPS_ERRORS=1"""

DEPENDS_ON_MITMPROXY = """
    depends_on: [mitmproxy]"""


PLACEHOLDERS = ('sg_playwright_image', 'image_tag', 'api_key',
                'mitmproxy_image')                                               # Locked by test


class Playwright__Compose__Template(Type_Safe):

    def render(self, image_tag     : str = 'latest'        ,
                     api_key       : str = ''              ,
                     with_mitmproxy: bool = False          ,
                     mitmproxy_image: str = MITMPROXY_IMAGE) -> str:
        proxy_env  = PROXY_ENV_LINES        if with_mitmproxy else ''
        depends_on = DEPENDS_ON_MITMPROXY   if with_mitmproxy else ''
        base = COMPOSE_BASE.format(sg_playwright_image = SG_PLAYWRIGHT_IMAGE  ,
                                   image_tag           = str(image_tag)        ,
                                   api_key             = str(api_key)          ,
                                   proxy_env           = proxy_env             ,
                                   depends_on          = depends_on            )
        if with_mitmproxy:
            base += COMPOSE_MITMPROXY_BLOCK.format(mitmproxy_image=str(mitmproxy_image))
        base += COMPOSE_FOOTER
        return base

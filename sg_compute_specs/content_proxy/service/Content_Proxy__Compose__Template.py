# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Content_Proxy__Compose__Template
# Renders the docker-compose.yml for the 5-service content-transformation stack.
# Pure templating. Secrets are NEVER in the YAML — they are `${...}` references
# interpolated by docker-compose from the .env file (written by the user-data
# builder on EC2, or supplied locally). Image refs are the only .format fields.
#
# Two mitmproxy instances run the SAME interceptor into the SAME FastAPI workflow:
#   mitmproxy-ext  :8080  basic auth (--proxyauth)  — for a human browser
#   mitmproxy-int  :8080  no auth, net-local         — for the sg-playwright browser
# Both run mitmweb so the TUI can read /flows. The 10.4.2 VNC pin does NOT apply:
# we never reverse-proxy the mitmweb UI; the TUI reads /flows from localhost/SSM.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


MITMPROXY_IMAGE    = 'mitmproxy/mitmproxy:12.2.3'                                   # latest
MITM_SERVICE_IMAGE = 'diniscruz/mgraph-ai-service-mitmproxy'
PLAYWRIGHT_IMAGE   = 'diniscruz/sg-playwright'
VAULT_APP_IMAGE    = 'diniscruz/sg-send-vault'

PLACEHOLDERS = ('mitmproxy_image', 'mitm_service_image', 'playwright_image', 'vault_app_image')   # locked by test


# `${{...}}` survives .format() as `${...}` for docker-compose env interpolation.
COMPOSE_TEMPLATE = """\
services:
  mitm-service:
    image: {mitm_service_image}
    container_name: cp-mitm-service
    environment:
      - FAST_API__AUTH__API_KEY__NAME=${{FASTAPI_API_KEY_NAME}}
      - FAST_API__AUTH__API_KEY__VALUE=${{FASTAPI_API_KEY_VALUE}}
    networks:
      - cp-net
    restart: unless-stopped

  mitmproxy-int:
    image: {mitmproxy_image}
    container_name: cp-mitmproxy-int
    command:
      - mitmweb
      - --web-host=0.0.0.0
      - --web-port=8081
      - --listen-host=0.0.0.0
      - --listen-port=8080
      - --scripts=/interceptors/active.py
    environment:
      - FASTAPI_BASE_URL=http://mitm-service:10011
      - FASTAPI_API_KEY_NAME=${{FASTAPI_API_KEY_NAME}}
      - FASTAPI_API_KEY_VALUE=${{FASTAPI_API_KEY_VALUE}}
    volumes:
      - ./interceptors:/interceptors:ro
      - ${{CONTENT_PROXY__CA_DIR:-./certs}}:/home/mitmproxy/.mitmproxy:ro
    networks:
      - cp-net
    restart: unless-stopped
    depends_on:
      - mitm-service

  mitmproxy-ext:
    image: {mitmproxy_image}
    container_name: cp-mitmproxy-ext
    command:
      - mitmweb
      - --web-host=0.0.0.0
      - --web-port=8081
      - --listen-host=0.0.0.0
      - --listen-port=8080
      - --scripts=/interceptors/active.py
      - --set
      - proxyauth=${{CONTENT_PROXY__PROXYAUTH_USER}}:${{CONTENT_PROXY__PROXYAUTH_PASS}}
    environment:
      - FASTAPI_BASE_URL=http://mitm-service:10011
      - FASTAPI_API_KEY_NAME=${{FASTAPI_API_KEY_NAME}}
      - FASTAPI_API_KEY_VALUE=${{FASTAPI_API_KEY_VALUE}}
    volumes:
      - ./interceptors:/interceptors:ro
      - ${{CONTENT_PROXY__CA_DIR:-./certs}}:/home/mitmproxy/.mitmproxy:ro
    ports:
      - "8080:8080"
      - "8081:8081"
    networks:
      - cp-net
    restart: unless-stopped
    depends_on:
      - mitm-service

  sg-playwright:
    image: {playwright_image}
    container_name: cp-sg-playwright
    environment:
      - SG_PLAYWRIGHT__DEFAULT_PROXY_URL=http://mitmproxy-int:8080
      - IGNORE_HTTPS_ERRORS=true
      - FAST_API__AUTH__API_KEY__NAME=X-API-Key
      - FAST_API__AUTH__API_KEY__VALUE=${{SG_PLAYWRIGHT__API_KEY}}
    networks:
      - cp-net
    restart: unless-stopped
    depends_on:
      - mitmproxy-int

  vault-app:
    image: {vault_app_image}
    container_name: cp-vault-app
    environment:
      - FAST_API__REVERSE_PROXY__ROUTES=pw=http://sg-playwright:8000
      - SEND__STORAGE_MODE=${{SEND__STORAGE_MODE:-memory}}
    ports:
      - "443:443"
    networks:
      - cp-net
    restart: unless-stopped
    depends_on:
      - sg-playwright

networks:
  cp-net:
    driver: bridge
"""


class Content_Proxy__Compose__Template(Type_Safe):

    def render(self, mitmproxy_image    : str = MITMPROXY_IMAGE    ,
                     mitm_service_image : str = MITM_SERVICE_IMAGE ,
                     playwright_image   : str = PLAYWRIGHT_IMAGE   ,
                     vault_app_image    : str = VAULT_APP_IMAGE    ) -> str:
        return COMPOSE_TEMPLATE.format(mitmproxy_image    = str(mitmproxy_image)   ,
                                       mitm_service_image = str(mitm_service_image),
                                       playwright_image   = str(playwright_image)  ,
                                       vault_app_image    = str(vault_app_image)   )

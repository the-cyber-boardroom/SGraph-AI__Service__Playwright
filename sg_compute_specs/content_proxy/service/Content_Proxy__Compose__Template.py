# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Content_Proxy__Compose__Template
# Renders the docker-compose.yml for the 5-service content-transformation stack.
# Pure templating. Secrets are NEVER in the YAML — they are `${...}` references
# interpolated by docker-compose from the .env file. Image refs + the per-proxy
# command blocks are the only injected fields.
#
# Two mitmproxy instances run the SAME interceptor into the SAME FastAPI workflow:
#   mitmproxy-ext  :8080  basic auth (--proxyauth)  — for a human browser
#   mitmproxy-int  :8080  no auth, net-local         — for the sg-playwright browser
# The proxy tool is configurable (Enum__Content_Proxy__Proxy__Tool):
#   MITMWEB  — dev/QA: exposes /flows for the TUI; accumulates flows in memory.
#   MITMDUMP — prod : headless; no accumulation (no TUI flows).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Proxy__Tool           import Enum__Content_Proxy__Proxy__Tool


MITMPROXY_IMAGE    = 'mitmproxy/mitmproxy:12.2.3'                                   # latest
MITM_SERVICE_IMAGE = 'diniscruz/mgraph-ai-service-mitmproxy'
PLAYWRIGHT_IMAGE   = 'diniscruz/sg-playwright'
VAULT_APP_IMAGE    = 'diniscruz/sg-send-vault'

PLACEHOLDERS = ('mitmproxy_image', 'mitm_service_image', 'playwright_image', 'vault_app_image',
                'int_command', 'ext_command', 'interceptors_mount')                 # locked by test

# Where the interceptor dir lives, RELATIVE TO THE COMPOSE FILE:
#   local committed compose sits in content_proxy/docker/compose/ → ../../interceptors
#   EC2 user-data writes the compose to /opt/content-proxy/ → ./interceptors
INTERCEPTORS_MOUNT__LOCAL = '../../interceptors'
INTERCEPTORS_MOUNT__EC2   = './interceptors'


def proxy_command(tool: Enum__Content_Proxy__Proxy__Tool, with_proxyauth: bool, indent: str = '      ') -> str:
    lines = [str(tool.value)]                                                       # 'mitmweb' | 'mitmdump'
    if tool == Enum__Content_Proxy__Proxy__Tool.MITMWEB:
        lines += ['--web-host=0.0.0.0', '--web-port=8081']
    lines += ['--listen-host=0.0.0.0', '--listen-port=8080',
              '--scripts=/interceptors/active.py']
    if with_proxyauth:
        lines += ['--set',
                  'proxyauth=${CONTENT_PROXY__PROXYAUTH_USER}:${CONTENT_PROXY__PROXYAUTH_PASS}']
    return '\n'.join(f'{indent}- {ln}' for ln in lines)


# `${{...}}` survives .format() as `${...}`. The command blocks are injected verbatim.
COMPOSE_TEMPLATE = """\
services:
  mitm-service:
    image: {mitm_service_image}
    container_name: cp-mitm-service
    environment:
      - FAST_API__AUTH__API_KEY__NAME=${{FASTAPI_API_KEY_NAME}}
      - FAST_API__AUTH__API_KEY__VALUE=${{FASTAPI_API_KEY_VALUE}}
      # AWS creds to read the scripts S3 bucket. LOCAL: set them in .env (passthrough
      # below). EC2/prod: leave them UNSET and use the instance role instead.
      - AWS_ACCOUNT_ID
      - AWS_DEFAULT_REGION
      - AWS_ACCESS_KEY_ID
      - AWS_SECRET_ACCESS_KEY
      - CACHE__SERVICE__BUCKET_NAME
    networks:
      - cp-net
    restart: unless-stopped

  mitmproxy-int:
    image: {mitmproxy_image}
    container_name: cp-mitmproxy-int
    command:
{int_command}
    environment:
      - FASTAPI_BASE_URL=http://mitm-service:10011
      - FASTAPI_API_KEY_NAME=${{FASTAPI_API_KEY_NAME}}
      - FASTAPI_API_KEY_VALUE=${{FASTAPI_API_KEY_VALUE}}
    volumes:
      - {interceptors_mount}:/interceptors:ro
      - ${{CONTENT_PROXY__CA_DIR:-./certs}}:/home/mitmproxy/.mitmproxy
    networks:
      - cp-net
    restart: unless-stopped
    depends_on:
      - mitm-service

  mitmproxy-ext:
    image: {mitmproxy_image}
    container_name: cp-mitmproxy-ext
    command:
{ext_command}
    environment:
      - FASTAPI_BASE_URL=http://mitm-service:10011
      - FASTAPI_API_KEY_NAME=${{FASTAPI_API_KEY_NAME}}
      - FASTAPI_API_KEY_VALUE=${{FASTAPI_API_KEY_VALUE}}
    volumes:
      - {interceptors_mount}:/interceptors:ro
      - ${{CONTENT_PROXY__CA_DIR:-./certs}}:/home/mitmproxy/.mitmproxy
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
                     vault_app_image    : str = VAULT_APP_IMAGE    ,
                     proxy_tool         : Enum__Content_Proxy__Proxy__Tool = Enum__Content_Proxy__Proxy__Tool.MITMWEB,
                     interceptors_mount : str = INTERCEPTORS_MOUNT__LOCAL
               ) -> str:
        return COMPOSE_TEMPLATE.format(mitmproxy_image    = str(mitmproxy_image)            ,
                                       mitm_service_image = str(mitm_service_image)         ,
                                       playwright_image   = str(playwright_image)           ,
                                       vault_app_image    = str(vault_app_image)            ,
                                       int_command        = proxy_command(proxy_tool, False),
                                       ext_command        = proxy_command(proxy_tool, True ),
                                       interceptors_mount = str(interceptors_mount)         )

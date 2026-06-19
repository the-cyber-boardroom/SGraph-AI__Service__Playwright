# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Content_Proxy__Compose__Template
# Renders the docker-compose.yml for the content-transformation stack. Pure
# templating. Secrets are NEVER in the YAML — `${...}` refs from the .env.
#
# Proxies: two mitmproxy instances (ext basic-auth / int no-auth) run the SAME
# interceptor into the SAME FastAPI workflow. Proxy tool is configurable
# (mitmweb dev / mitmdump prod).
#
# Vault TLS (mirrors `sg va`): NONE → vault plain HTTP on :8080 (host 443→8080).
# SELF_SIGNED / LETSENCRYPT → a one-shot cert-init sidecar
# (diniscruz/sg-host-control) writes /certs to a shared volume; the vault
# terminates TLS on :443 via FAST_API__TLS__*. letsencrypt-ip also publishes :80
# for the ACME http-01 challenge.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Proxy__Tool           import Enum__Content_Proxy__Proxy__Tool
from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Tls                   import Enum__Content_Proxy__Tls


MITMPROXY_IMAGE    = 'mitmproxy/mitmproxy:12.2.3'                                   # latest
MITM_SERVICE_IMAGE = 'diniscruz/mgraph-ai-service-mitmproxy'
PLAYWRIGHT_IMAGE   = 'diniscruz/sg-playwright'
VAULT_APP_IMAGE    = 'diniscruz/sg-send-vault'
CERT_INIT_IMAGE    = 'diniscruz/sg-host-control'                                    # carries sg_compute.platforms.tls.cert_init

PLACEHOLDERS = ('mitmproxy_image', 'mitm_service_image', 'playwright_image',
                'int_command', 'ext_command', 'interceptors_mount',
                'vault_block', 'cert_init_block', 'volumes_block')                  # locked by test

INTERCEPTORS_MOUNT__LOCAL = '../../interceptors'                                    # committed local compose sits in docker/compose/
INTERCEPTORS_MOUNT__EC2   = './interceptors'                                        # EC2 user-data writes compose to /opt/content-proxy/


def _cert_init_mode(tls: Enum__Content_Proxy__Tls) -> str:                          # → SG__CERT_INIT__MODE
    if tls == Enum__Content_Proxy__Tls.LETSENCRYPT:
        return 'letsencrypt-ip'
    return 'self-signed'                                                            # SELF_SIGNED + ACM-fallback


def proxy_command(tool: Enum__Content_Proxy__Proxy__Tool, with_proxyauth: bool, indent: str = '      ') -> str:
    lines = [str(tool.value)]                                                       # 'mitmweb' | 'mitmdump'
    if tool == Enum__Content_Proxy__Proxy__Tool.MITMWEB:
        lines += ['--web-host=0.0.0.0', '--web-port=8081']
    lines += ['--listen-host=0.0.0.0', '--listen-port=8080', '--scripts=/interceptors/active.py']
    if with_proxyauth:
        lines += ['--set', 'proxyauth=${CONTENT_PROXY__PROXYAUTH_USER}:${CONTENT_PROXY__PROXYAUTH_PASS}']
    return '\n'.join(f'{indent}- {ln}' for ln in lines)


# ── vault-app blocks (HTTP vs TLS) ──────────────────────────────────────────────
_VAULT_HTTP = """\
  vault-app:
    image: {vault_app_image}
    container_name: cp-vault-app
    environment:
      - FAST_API__REVERSE_PROXY__ROUTES=pw=http://sg-playwright:8000
      - SEND__STORAGE_MODE=${SEND__STORAGE_MODE:-memory}
    ports:
      - "443:8080"
    networks:
      - cp-net
    restart: unless-stopped
    depends_on:
      - sg-playwright
"""

_VAULT_TLS = """\
  vault-app:
    image: {vault_app_image}
    container_name: cp-vault-app
    environment:
      - FAST_API__REVERSE_PROXY__ROUTES=pw=http://sg-playwright:8000
      - SEND__STORAGE_MODE=${SEND__STORAGE_MODE:-memory}
      - FAST_API__TLS__ENABLED=true
      - FAST_API__TLS__CERT_FILE=/certs/cert.pem
      - FAST_API__TLS__KEY_FILE=/certs/key.pem
      - FAST_API__TLS__PORT=443
    volumes:
      - vault_certs:/certs:ro
    ports:
      - "443:443"
    networks:
      - cp-net
    restart: unless-stopped
    depends_on:
      sg-playwright:
        condition: service_started
      cert-init:
        condition: service_completed_successfully
"""

_CERT_INIT = """\

  cert-init:
    image: {cert_init_image}
    container_name: cp-cert-init
    command: ["python3", "-m", "sg_compute.platforms.tls.cert_init"]
    environment:
      - SG__CERT_INIT__MODE={mode}
      - SG__CERT_INIT__ACME_PROD=${SG__CERT_INIT__ACME_PROD:-false}
      - SG__CERT_INIT__ACME_EMAIL=${SG__CERT_INIT__ACME_EMAIL:-}
      - FAST_API__TLS__CERT_FILE=/certs/cert.pem
      - FAST_API__TLS__KEY_FILE=/certs/key.pem
    volumes:
      - vault_certs:/certs
{acme_ports}    networks:
      - cp-net
    restart: "no"
"""

_ACME_PORTS = '    ports:\n      - "80:80"\n'                                        # letsencrypt-ip http-01 challenge


def vault_block(vault_app_image: str, tls: Enum__Content_Proxy__Tls) -> str:
    tpl = _VAULT_HTTP if tls == Enum__Content_Proxy__Tls.NONE else _VAULT_TLS
    return tpl.replace('{vault_app_image}', str(vault_app_image))


def cert_init_block(tls: Enum__Content_Proxy__Tls) -> str:
    if tls == Enum__Content_Proxy__Tls.NONE:
        return ''
    mode  = _cert_init_mode(tls)
    ports = _ACME_PORTS if mode == 'letsencrypt-ip' else ''
    return (_CERT_INIT.replace('{cert_init_image}', CERT_INIT_IMAGE)
                      .replace('{mode}', mode)
                      .replace('{acme_ports}', ports))


def volumes_block(tls: Enum__Content_Proxy__Tls) -> str:
    return '' if tls == Enum__Content_Proxy__Tls.NONE else '\nvolumes:\n  vault_certs:\n'


# `${{...}}` survives .format() as `${...}`. vault/cert/volumes blocks are injected verbatim.
COMPOSE_TEMPLATE = """\
services:
  mitm-service:
    image: {mitm_service_image}
    container_name: cp-mitm-service
    environment:
      - FAST_API__AUTH__API_KEY__NAME=${{FASTAPI_API_KEY_NAME}}
      - FAST_API__AUTH__API_KEY__VALUE=${{FASTAPI_API_KEY_VALUE}}
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

{vault_block}{cert_init_block}
networks:
  cp-net:
    driver: bridge
{volumes_block}"""


class Content_Proxy__Compose__Template(Type_Safe):

    def render(self, mitmproxy_image    : str = MITMPROXY_IMAGE    ,
                     mitm_service_image : str = MITM_SERVICE_IMAGE ,
                     playwright_image   : str = PLAYWRIGHT_IMAGE   ,
                     vault_app_image    : str = VAULT_APP_IMAGE    ,
                     proxy_tool         : Enum__Content_Proxy__Proxy__Tool = Enum__Content_Proxy__Proxy__Tool.MITMWEB,
                     interceptors_mount : str = INTERCEPTORS_MOUNT__LOCAL,
                     tls                : Enum__Content_Proxy__Tls = Enum__Content_Proxy__Tls.NONE
               ) -> str:
        return COMPOSE_TEMPLATE.format(mitmproxy_image    = str(mitmproxy_image)            ,
                                       mitm_service_image = str(mitm_service_image)         ,
                                       playwright_image   = str(playwright_image)           ,
                                       int_command        = proxy_command(proxy_tool, False),
                                       ext_command        = proxy_command(proxy_tool, True ),
                                       interceptors_mount = str(interceptors_mount)         ,
                                       vault_block        = vault_block(vault_app_image, tls),
                                       cert_init_block    = cert_init_block(tls)            ,
                                       volumes_block      = volumes_block(tls)              )

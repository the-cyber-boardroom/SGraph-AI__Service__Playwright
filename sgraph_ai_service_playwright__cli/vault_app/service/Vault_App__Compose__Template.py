# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Vault_App__Compose__Template
# Renders the docker-compose.yml that boots the 4-container vault-app stack
# on an EC2 host. Pure templating — no secrets in the YAML itself.
#
# Containers:
#   host-plane     — control-plane FastAPI; manages Docker via socket
#   sg-send-vault  — vault storage + UI; only external port (8080)
#   sg-playwright  — browser automation; internal only
#   agent-mitmproxy — passive traffic capture; internal only, no admin ports
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


SG_SEND_VAULT_IMAGE = 'diniscruz/sg-send-vault:latest'                             # public image; no ECR pull needed

COMPOSE_TEMPLATE = """\
services:

  host-plane:
    image: {host_plane_image}
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      FAST_API__AUTH__API_KEY__NAME:  {api_key_name}
      FAST_API__AUTH__API_KEY__VALUE: {api_key_value}
    networks:
      - vault-net
    restart: unless-stopped

  sg-send-vault:
    image: {sg_send_vault_image}
    ports:
      - "8080:8080"
    volumes:
      - /opt/vault-app/data:/data
    environment:
      SGRAPH_SEND__ACCESS_TOKEN: {access_token}
      SEND__STORAGE_MODE:        disk
    networks:
      - vault-net
    restart: unless-stopped

  sg-playwright:
    image: {playwright_image}
    environment:
      FAST_API__AUTH__API_KEY__NAME:          {api_key_name}
      FAST_API__AUTH__API_KEY__VALUE:         {api_key_value}
      SG_PLAYWRIGHT__DEPLOYMENT_TARGET:       container
      SG_PLAYWRIGHT__DEFAULT_PROXY_URL:       http://agent-mitmproxy:8080
      SG_PLAYWRIGHT__IGNORE_HTTPS_ERRORS:     'true'
      SG_VAULT_APP__SEED_VAULT_KEYS:          {seed_vault_keys}
    networks:
      - vault-net
    depends_on:
      - agent-mitmproxy
    restart: unless-stopped

  agent-mitmproxy:
    image: {mitmproxy_image}
    environment:
      FAST_API__AUTH__API_KEY__NAME:  {api_key_name}
      FAST_API__AUTH__API_KEY__VALUE: {api_key_value}
    networks:
      - vault-net
    restart: unless-stopped

networks:
  vault-net:
    driver: bridge
"""

PLACEHOLDERS = ('host_plane_image', 'sg_send_vault_image', 'playwright_image',
                'mitmproxy_image', 'api_key_name', 'api_key_value',
                'access_token', 'seed_vault_keys')                                  # Locked by test


class Vault_App__Compose__Template(Type_Safe):

    def render(self,
               host_plane_image    : str = '',
               sg_send_vault_image : str = SG_SEND_VAULT_IMAGE,
               playwright_image    : str = '',
               mitmproxy_image     : str = '',
               api_key_name        : str = 'X-API-Key',
               api_key_value       : str = '',
               access_token        : str = '',
               seed_vault_keys     : str = '') -> str:
        return COMPOSE_TEMPLATE.format(
            host_plane_image    = host_plane_image    ,
            sg_send_vault_image = sg_send_vault_image ,
            playwright_image    = playwright_image    ,
            mitmproxy_image     = mitmproxy_image     ,
            api_key_name        = api_key_name        ,
            api_key_value       = api_key_value       ,
            access_token        = access_token        ,
            seed_vault_keys     = seed_vault_keys     ,
        )

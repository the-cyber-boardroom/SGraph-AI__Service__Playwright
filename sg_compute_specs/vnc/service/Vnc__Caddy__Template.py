# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — VNC: Vnc__Caddy__Template
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


CADDY_BUILDER_IMAGE     = 'caddy:2.7-builder-alpine'
CADDY_RUNTIME_IMAGE     = 'caddy:2.7-alpine'
CADDY_SECURITY_VERSION  = 'v1.1.30'
CADDY_LOCAL_IMAGE_TAG   = 'sg-vnc/caddy:local'


CADDY_DOCKERFILE = '''\
FROM {builder_image} AS builder
RUN xcaddy build \\
    --with github.com/greenpau/caddy-security@{caddy_security_version}

FROM {runtime_image}
COPY --from=builder /usr/bin/caddy /usr/bin/caddy
'''


CADDYFILE_TEMPLATE = '''\
{{
    order authenticate before respond
    order authorize    before basicauth
}}

:443 {{
    tls internal

    log {{
        output stdout
        format console
    }}

    security {{
        local identity store local_users {{
            realm sg-vnc
            path  /etc/caddy/users.json
        }}

        authentication portal sg_portal {{
            crypto default token name sg_vnc_token
            crypto default token lifetime 28800
            crypto key sign-verify from file /etc/caddy/jwt-secret
            backend local local_users local
            cookie domain *
            cookie httponly true
            cookie secure   true
            cookie samesite lax
            ui {{
                title "sp vnc · sign in"
            }}
            transform user {{
                match origin local
                action add role authp/user
            }}
        }}

        authorization policy operator_policy {{
            set auth url /login
            crypto key verify from file /etc/caddy/jwt-secret
            allow roles authp/user
        }}
    }}

    route /healthz {{
        respond "ok" 200
    }}

    route /login* {{
        authenticate with sg_portal
    }}

    route /mitmweb/* {{
        authorize with operator_policy
        uri strip_prefix /mitmweb
        reverse_proxy mitmproxy:8081
    }}

    route /* {{
        authorize with operator_policy
        reverse_proxy chromium:3000
    }}
}}
'''


USERS_JSON_TEMPLATE = '''\
{{
  "users": [
    {{
      "id"             : "sg-vnc-operator-001",
      "username"       : "operator",
      "name"           : "Operator",
      "email_addresses": [
        {{ "address": "operator@sg-vnc.local", "domain": "sg-vnc.local" }}
      ],
      "passwords"      : [
        {{ "purpose": "generic", "type": "bcrypt", "hash": "{bcrypt_hash}" }}
      ],
      "roles"          : [
        {{ "name": "user", "organization": "authp" }}
      ]
    }}
  ],
  "revision": 1
}}
'''


class Vnc__Caddy__Template(Type_Safe):

    def render_dockerfile(self, builder_image         : str = CADDY_BUILDER_IMAGE   ,
                                runtime_image         : str = CADDY_RUNTIME_IMAGE   ,
                                caddy_security_version: str = CADDY_SECURITY_VERSION) -> str:
        return CADDY_DOCKERFILE.format(builder_image          = str(builder_image)         ,
                                       runtime_image          = str(runtime_image)         ,
                                       caddy_security_version = str(caddy_security_version))

    def render_caddyfile(self) -> str:
        return CADDYFILE_TEMPLATE

    def render_users_json(self, bcrypt_hash: str) -> str:
        return USERS_JSON_TEMPLATE.format(bcrypt_hash=str(bcrypt_hash))

# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Vnc__Caddy__Template
# Renders the Caddy artefacts that replace the nginx setup:
#
#   Caddyfile     ← TLS terminator (`tls internal`) + caddy-security login
#                   portal (/login) + authorization gate on /  and /mitmweb/
#   users.json    ← caddy-security local identity store with the bcrypt hash
#                   of the operator password (same hash htpasswd would emit)
#   Dockerfile    ← builds caddy:2-builder + caddy-security plugin via xcaddy
#
# Why a new file (not folded into Vnc__User_Data__Builder): the artefacts are
# Caddy-specific and likely to evolve independently (theming, OIDC backend,
# MFA). Keeping them isolated means the user-data builder stays a thin
# orchestrator that knows file paths, not config syntax.
#
# Pinned versions live in this module so a single grep finds them:
#   - caddy 2-builder + 2-alpine: project standard moving-tag pin
#   - caddy-security: see CADDY_SECURITY_VERSION below
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


CADDY_BUILDER_IMAGE     = 'caddy:2.7-builder-alpine'                                # xcaddy lives in the builder image; pinned to a stable 2.7 line
CADDY_RUNTIME_IMAGE     = 'caddy:2.7-alpine'                                        # Final runtime — copies the custom binary
CADDY_SECURITY_VERSION  = 'v1.1.30'                                                 # github.com/greenpau/caddy-security tag — pinned so user-data renders the same image hash on every boot
CADDY_LOCAL_IMAGE_TAG   = 'sg-vnc/caddy:local'                                      # `docker compose build` tags the produced image with this label


# ── Dockerfile ───────────────────────────────────────────────────────────────
#
# Two-stage build. Stage 1 uses caddy:2-builder which ships xcaddy; we add
# the caddy-security plugin and emit a static caddy binary. Stage 2 copies
# only the binary into a slim alpine runtime.
CADDY_DOCKERFILE = """\
FROM {builder_image} AS builder
RUN xcaddy build \\
    --with github.com/greenpau/caddy-security@{caddy_security_version}

FROM {runtime_image}
COPY --from=builder /usr/bin/caddy /usr/bin/caddy
"""


# ── Caddyfile ───────────────────────────────────────────────────────────────
#
# `:443` site label binds without a host — the operator hits the EC2 by IP,
# so there's no DNS to anchor TLS to. `tls internal` lets Caddy mint a cert
# from its own internal CA (same browser UX as our previous self-signed:
# untrusted CA, one-time "Visit Site" prompt — but no openssl step in
# user-data and Caddy handles renewal automatically).
#
# Routes evaluated top-down:
#   /healthz   → 200 unauth'd (probe target — see Vnc__HTTP__Probe)
#   /login*    → caddy-security authentication portal (branded form)
#   /mitmweb/* → require valid JWT cookie → reverse-proxy to mitmweb
#   /*         → require valid JWT cookie → reverse-proxy to chromium
CADDYFILE_TEMPLATE = """\
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
"""


# ── users.json ──────────────────────────────────────────────────────────────
#
# caddy-security `local` identity store schema. Single user named 'operator'
# with the bcrypt hash injected at user-data render time.
USERS_JSON_TEMPLATE = """\
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
"""


class Vnc__Caddy__Template(Type_Safe):

    def render_dockerfile(self, builder_image         : str = CADDY_BUILDER_IMAGE   ,
                                runtime_image         : str = CADDY_RUNTIME_IMAGE   ,
                                caddy_security_version: str = CADDY_SECURITY_VERSION) -> str:
        return CADDY_DOCKERFILE.format(builder_image          = str(builder_image)         ,
                                       runtime_image          = str(runtime_image)         ,
                                       caddy_security_version = str(caddy_security_version))

    def render_caddyfile(self) -> str:
        return CADDYFILE_TEMPLATE                                                   # No placeholders today; method exists so future branding/theming knobs can land without changing callers

    def render_users_json(self, bcrypt_hash: str) -> str:                           # bcrypt_hash is the `$2y$10$...` portion (no `operator:` prefix) emitted by `htpasswd -bnBC 10 operator <pwd>`
        return USERS_JSON_TEMPLATE.format(bcrypt_hash=str(bcrypt_hash))

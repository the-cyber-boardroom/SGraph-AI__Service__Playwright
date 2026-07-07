# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Content_Proxy__Edge__Template
# Renders the Caddyfile for the dedicated front-door edge. The edge owns :443
# (TLS) and routes paths to plain-origin backends — replacing the vault /pw
# runtime injection: /pw is a Caddy route, not an app patch.
#
# Two site-address modes:
#   - local       → `localhost, 127.0.0.1` + `tls internal`. A *named* site (not
#                   bare `:443`) is required: with `:443` Caddy has no subject to
#                   mint an internal cert for and aborts the handshake with
#                   `tlsv1 alert internal error`. Naming the host makes Caddy
#                   provision the internal cert at startup. curl -k / browser
#                   click-through to https://localhost/ works.
#   - hostname    → `<fqdn>` site block; Caddy does auto-ACME (http-01 on :80,
#                   tls-alpn on :443) for a publicly-trusted cert — what external
#                   callers (Claude) need to reach `https://<slug>.sg-compute.sgraph.ai/`.
#                   Requires :80 + :443 reachable and DNS pointing at the box.
#
# Shared route body for both modes:
#   - /pw/*  → sg-playwright (strip prefix, inject X-API-Key + X-Forwarded-Prefix).
#   - /      → vault-app (plain HTTP origin).
# `{$SGRAPH_SEND__ACCESS_TOKEN}` is read by Caddy from its own env (compose sets it).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


# the route body shared by both site-address modes (one tab of indent under the block)
# The injected header NAME is env-driven ({$FAST_API__AUTH__API_KEY__NAME}) so it
# always matches what sg-playwright expects — never hardcode it. Caddy reads both
# {$...} placeholders from its own env (compose sets them from the .env).
# split into the fixed /pw head, the generated /browser fleet routes, and the
# catch-all tail so the browser routes land ABOVE the catch-all handle. With
# firefox_count=0 the fleet block is empty and route_body() == the original body,
# keeping the committed Caddyfile drift-free.
ROUTE_BODY__PW = """\
	# sg-playwright, same-origin under /pw — strip the prefix, inject the API key
	handle_path /pw/* {
		reverse_proxy sg-playwright:8000 {
			header_up {$FAST_API__AUTH__API_KEY__NAME:x-api-key} {$SGRAPH_SEND__ACCESS_TOKEN}
			header_up X-Forwarded-Prefix /pw
		}
	}

	# bare /pw → /pw/ so the handle_path matcher catches it
	redir /pw /pw/ 308
"""

ROUTE_BODY__CATCHALL = """\
	# everything else → the vault app (plain origin)
	handle {
		reverse_proxy vault-app:8080
	}"""

# one generated block per interactive Firefox. handle_path strips the /browser/
# firefox/{i} prefix so the container receives /; X-Forwarded-Prefix lets jlesage's
# baseimage-gui (noVNC) emit correct sub-path asset + websocket URLs. Same
# access-token gate as /pw (the whole site is behind it). {{ }} → single Caddy brace.
BROWSER_ROUTE = """\
	# interactive Firefox {i} — noVNC under a sub-path (jlesage baseimage-gui honours X-Forwarded-*)
	handle_path /browser/firefox/{i}/* {{
		reverse_proxy cp-firefox-{i}:5800 {{
			header_up X-Forwarded-Prefix /browser/firefox/{i}
		}}
	}}

	# bare /browser/firefox/{i} → trailing slash so the handle_path matcher catches it
	redir /browser/firefox/{i} /browser/firefox/{i}/ 308

"""


# ── token-gated variants (--edge-auth) ─────────────────────────────────────────
# Without this the edge is open: /pw injects the key downstream and /browser just
# reverse-proxies, so anyone who reaches the box can drive them. With --edge-auth
# each gated block 401s unless the access token is presented as an X-API-Key header
# (programmatic) OR a cp_access cookie (browser, set once via /edge/auth?token=…).
# Nested `handle @noauth {…}` / `handle {…}` blocks are mutually exclusive and force
# guard-before-proxy regardless of Caddy's global directive order. Built with
# explicit \t/\n so the Caddyfile indentation is exact. `{{` survives .format() as
# `{` for the /browser routes; the /pw + bootstrap strings are not .format()ed.
_AUTH_GUARD = (
    "\t\t@noauth {\n"
    "\t\t\tnot header X-API-Key {$SGRAPH_SEND__ACCESS_TOKEN}\n"
    "\t\t\tnot header Cookie *cp_access={$SGRAPH_SEND__ACCESS_TOKEN}*\n"
    "\t\t}\n"
    "\t\thandle @noauth {\n"
    '\t\t\trespond "unauthorized — send X-API-Key or set cp_access via /edge/auth?token=…" 401\n'
    "\t\t}\n")

ROUTE_BODY__PW__AUTH = (
    "\t# sg-playwright, same-origin under /pw — token-gated at the edge\n"
    "\thandle_path /pw/* {\n"
    + _AUTH_GUARD +
    "\t\thandle {\n"
    "\t\t\treverse_proxy sg-playwright:8000 {\n"
    "\t\t\t\theader_up {$FAST_API__AUTH__API_KEY__NAME:x-api-key} {$SGRAPH_SEND__ACCESS_TOKEN}\n"
    "\t\t\t\theader_up X-Forwarded-Prefix /pw\n"
    "\t\t\t}\n"
    "\t\t}\n"
    "\t}\n"
    "\n"
    "\tredir /pw /pw/ 308\n")

BROWSER_ROUTE__AUTH = (
    "\t# interactive Firefox {i} — token-gated at the edge\n"
    "\thandle_path /browser/firefox/{i}/* {{\n"
    "\t\t@noauth {{\n"
    "\t\t\tnot header X-API-Key {{$SGRAPH_SEND__ACCESS_TOKEN}}\n"
    "\t\t\tnot header Cookie *cp_access={{$SGRAPH_SEND__ACCESS_TOKEN}}*\n"
    "\t\t}}\n"
    "\t\thandle @noauth {{\n"
    '\t\t\trespond "unauthorized" 401\n'
    "\t\t}}\n"
    "\t\thandle {{\n"
    "\t\t\treverse_proxy cp-firefox-{i}:5800 {{\n"
    "\t\t\t\theader_up X-Forwarded-Prefix /browser/firefox/{i}\n"
    "\t\t\t}}\n"
    "\t\t}}\n"
    "\t}}\n"
    "\n"
    "\tredir /browser/firefox/{i} /browser/firefox/{i}/ 308\n"
    "\n")

# ungated bootstrap: promote ?token=… to the cp_access cookie so a human can auth
# once in the browser, then open the gated /browser or /pw URLs. A wrong token still
# 401s at the gate (the gate compares the cookie to the real token).
EDGE_AUTH_BOOTSTRAP = (
    "\t# bootstrap: set the cp_access cookie from ?token=… (browser one-time auth)\n"
    "\thandle /edge/auth {\n"
    '\t\theader Set-Cookie "cp_access={http.request.uri.query.token}; Path=/; Secure; HttpOnly; SameSite=Lax"\n'
    '\t\trespond "cp_access cookie set — now open /pw/ or /browser/firefox/N/" 200\n'
    "\t}\n"
    "\n")


def browser_routes(firefox_count: int, edge_auth: bool = False) -> str:             # → N handle_path /browser/firefox/{i} blocks ('' when count<=0)
    tmpl = BROWSER_ROUTE__AUTH if edge_auth else BROWSER_ROUTE
    return ''.join(tmpl.format(i=i) for i in range(1, int(firefox_count) + 1))


def route_body(firefox_count: int = 0, edge_auth: bool = False) -> str:             # /pw + fleet + catch-all; count=0 & no auth → identical to the original single body
    pw        = ROUTE_BODY__PW__AUTH if edge_auth else ROUTE_BODY__PW
    bootstrap = EDGE_AUTH_BOOTSTRAP  if edge_auth else ''
    return pw + '\n' + browser_routes(firefox_count, edge_auth) + bootstrap + ROUTE_BODY__CATCHALL


ROUTE_BODY = route_body()                                                           # back-compat: the count=0 body (imported by tests / callers)


# local: Caddy's internal CA, no public ACME. Named site (localhost + loopback IP)
# so the internal cert is provisioned — a bare `:443` has no subject and fails the
# handshake with `tlsv1 alert internal error`.
CADDYFILE__INTERNAL = """\
{{
	auto_https disable_redirects
}}

localhost, 127.0.0.1 {{
	tls internal

{route_body}
}}
"""


# hostname: public auto-ACME. `email` feeds the global block when supplied.
CADDYFILE__HOSTNAME = """\
{{
{global_email}}}

{hostname} {{
{route_body}
}}
"""


class Content_Proxy__Edge__Template(Type_Safe):

    def render(self, hostname     : str = '',                                       # <fqdn> → public auto-ACME; blank → :443 tls internal
                     acme_email   : str = '',                                       # LE registration email (optional)
                     firefox_count: int = 0,                                        # N → adds /browser/firefox/{i} routes above the catch-all
                     edge_auth    : bool = False                                    # True → 401-gate /pw + /browser on the access token
              ) -> str:
        body = route_body(firefox_count, edge_auth)
        if hostname:
            global_email = f'\temail {acme_email}\n' if acme_email else ''
            return CADDYFILE__HOSTNAME.format(global_email = global_email,
                                              hostname     = hostname,
                                              route_body   = body)
        return CADDYFILE__INTERNAL.format(route_body = body)

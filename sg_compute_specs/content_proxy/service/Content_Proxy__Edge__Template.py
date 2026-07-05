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


def browser_routes(firefox_count: int) -> str:                                      # → N handle_path /browser/firefox/{i} blocks ('' when count<=0)
    return ''.join(BROWSER_ROUTE.format(i=i) for i in range(1, int(firefox_count) + 1))


def route_body(firefox_count: int = 0) -> str:                                      # /pw + fleet + catch-all; count=0 → identical to the original single body
    return ROUTE_BODY__PW + '\n' + browser_routes(firefox_count) + ROUTE_BODY__CATCHALL


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
                     firefox_count: int = 0                                         # N → adds /browser/firefox/{i} routes above the catch-all
              ) -> str:
        body = route_body(firefox_count)
        if hostname:
            global_email = f'\temail {acme_email}\n' if acme_email else ''
            return CADDYFILE__HOSTNAME.format(global_email = global_email,
                                              hostname     = hostname,
                                              route_body   = body)
        return CADDYFILE__INTERNAL.format(route_body = body)

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
ROUTE_BODY = """\
	# sg-playwright, same-origin under /pw — strip the prefix, inject the API key
	handle_path /pw/* {
		reverse_proxy sg-playwright:8000 {
			header_up X-API-Key {$SGRAPH_SEND__ACCESS_TOKEN}
			header_up X-Forwarded-Prefix /pw
		}
	}

	# bare /pw → /pw/ so the handle_path matcher catches it
	redir /pw /pw/ 308

	# everything else → the vault app (plain origin)
	handle {
		reverse_proxy vault-app:8080
	}"""


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

    def render(self, hostname  : str = '',                                          # <fqdn> → public auto-ACME; blank → :443 tls internal
                     acme_email: str = ''                                           # LE registration email (optional)
              ) -> str:
        if hostname:
            global_email = f'\temail {acme_email}\n' if acme_email else ''
            return CADDYFILE__HOSTNAME.format(global_email = global_email,
                                              hostname     = hostname,
                                              route_body   = ROUTE_BODY)
        return CADDYFILE__INTERNAL.format(route_body = ROUTE_BODY)

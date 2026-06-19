# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Content_Proxy__Edge__Template
# Renders the Caddyfile for the dedicated front-door edge (PoC). The edge owns
# :443 (TLS) and routes paths to plain-origin backends — replacing the vault /pw
# runtime injection: /pw is a Caddy route, not an app patch.
#
# - `tls internal`  → Caddy's own CA for local/IP (curl -k, or trust /data root).
#   Swap to a hostname block (auto ACME / caddy-dns route53) for *.sgraph.ai.
# - /pw/*  → sg-playwright (strip prefix, inject X-API-Key + X-Forwarded-Prefix).
# - /      → vault-app (plain HTTP origin).
# `{$SGRAPH_SEND__ACCESS_TOKEN}` is read by Caddy from its own env (compose sets it).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


CADDYFILE = """\
{
	auto_https disable_redirects
}

:443 {
	tls internal

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
	}
}
"""


class Content_Proxy__Edge__Template(Type_Safe):

    def render(self) -> str:
        return CADDYFILE

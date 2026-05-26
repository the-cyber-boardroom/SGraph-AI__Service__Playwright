# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vscode: Vscode__Caddy__Template
# PUBLIC_HTTPS mode only. Plain caddy:2-alpine terminates TLS on :443 and
# reverse-proxies to the code-server container. No caddy-security auth portal —
# code-server's own PASSWORD gates access. With a real domain Caddy obtains a
# Let's Encrypt cert automatically (Slice 4 + Auto-DNS); without one it uses
# `tls internal` (a self-signed cert; the browser warns once).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

CADDY_IMAGE  = 'caddy:2-alpine'

_CADDYFILE_INTERNAL = ''':443 {{
    tls internal
    reverse_proxy code-server:8080
}}
'''

_CADDYFILE_DOMAIN = '''{domain} {{
    reverse_proxy code-server:8080
}}
'''

_BOOT_BLOCK = '''
# ── Caddy (TLS terminator + reverse proxy on :443) ──────────────────────────────
echo "[ephemeral-ec2] starting Caddy..."
mkdir -p /opt/vscode/caddy/data /opt/vscode/caddy/config
cat > /opt/vscode/caddy/Caddyfile <<'VSCODE_CADDYFILE_EOF'
{caddyfile}
VSCODE_CADDYFILE_EOF
docker run -d --name caddy --restart unless-stopped --network {network} \\
  -p 443:443 -p 80:80 \\
  -v /opt/vscode/caddy/Caddyfile:/etc/caddy/Caddyfile:ro \\
  -v /opt/vscode/caddy/data:/data \\
  -v /opt/vscode/caddy/config:/config \\
  {image}
echo "[ephemeral-ec2] Caddy started on :443"
'''


class Vscode__Caddy__Template(Type_Safe):

    def render_caddyfile(self, domain: str = '') -> str:
        if domain:
            return _CADDYFILE_DOMAIN.format(domain=domain)
        return _CADDYFILE_INTERNAL.format()

    def render_boot_block(self, network: str, domain: str = '') -> str:
        return _BOOT_BLOCK.format(caddyfile=self.render_caddyfile(domain),
                                  network=network,
                                  image=CADDY_IMAGE)

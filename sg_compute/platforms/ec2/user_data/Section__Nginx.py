# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Section__Nginx
# Runs nginx as a Docker container that reverse-proxies to the app process on
# the host. Uses --network=host so nginx can reach localhost:<app_port>.
# SSE-safe: proxy_buffering off, gzip off, long read timeout.
# Self-signed TLS cert generated at runtime (no domain required).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

NGINX_CONF = '''\
server {{
    listen 443 ssl;
    server_name _;

    ssl_certificate     /etc/nginx/certs/self.crt;
    ssl_certificate_key /etc/nginx/certs/self.key;
    ssl_protocols       TLSv1.2 TLSv1.3;

    location / {{
        proxy_pass         http://localhost:{app_port};
        proxy_http_version 1.1;
        proxy_set_header   Connection      '';
        proxy_set_header   Host            $host;
        proxy_set_header   X-Real-IP       $remote_addr;
        proxy_buffering    off;
        proxy_cache        off;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
        chunked_transfer_encoding on;
        gzip               off;
    }}
}}
'''

TEMPLATE = '''
# ── nginx reverse proxy (docker, --network=host) ──────────────────────────────
echo "[ephemeral-ec2] configuring nginx..."
mkdir -p /etc/nginx-proxy/certs /etc/nginx-proxy/conf.d

cat > /etc/nginx-proxy/conf.d/app.conf <<'NGINXEOF'
{nginx_conf}
NGINXEOF

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \\
    -keyout /etc/nginx-proxy/certs/self.key \\
    -out    /etc/nginx-proxy/certs/self.crt \\
    -subj   '/CN=ephemeral-ec2' 2>/dev/null

docker run -d --name nginx-proxy \\
    --network=host \\
    --restart=always \\
    -v /etc/nginx-proxy/conf.d:/etc/nginx/conf.d:ro \\
    -v /etc/nginx-proxy/certs:/etc/nginx/certs:ro \\
    nginx:alpine

echo "[ephemeral-ec2] nginx ready on port 443"
'''


class Section__Nginx(Type_Safe):
    app_port : int = 7456

    def render(self, app_port: int = 0) -> str:
        port = app_port or self.app_port
        conf = NGINX_CONF.format(app_port=port)
        return TEMPLATE.format(nginx_conf=conf)

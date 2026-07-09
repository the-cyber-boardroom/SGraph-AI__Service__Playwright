# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Content_Proxy__User_Data__Builder
# Renders the EC2 cloud-init bash: install docker + compose, write the .env, the
# rendered docker-compose.yml, and the interceptor files to /opt/content-proxy,
# then `docker compose up -d`. MVP writes NO vaults. Pure templating — testable.
#
# Secrets are written into /opt/content-proxy/.env from the create request (the
# standard user-data pattern; user-data is operator-controlled). Quoted heredocs
# ('EOF') prevent shell interpolation of embedded file bodies.
# ═══════════════════════════════════════════════════════════════════════════════

from pathlib                                                                        import Path

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

import sg_compute_specs.content_proxy.interceptors                                   as interceptors_pkg
from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Edge                   import Enum__Content_Proxy__Edge
from sg_compute_specs.content_proxy.service.Content_Proxy__Compose__Template         import (Content_Proxy__Compose__Template,
                                                                                             INTERCEPTORS_MOUNT__EC2)
from sg_compute_specs.content_proxy.service.Content_Proxy__Edge__Template            import Content_Proxy__Edge__Template
from sg_compute_specs.vault_app.service.Vault_App__Reverse_Proxy__Override           import Vault_App__Reverse_Proxy__Override


APP_DIR       = '/opt/content-proxy'
OVERRIDES_DIR = '/opt/content-proxy/overrides'                                       # /pw runtime injection (same sg-send-vault image as sg va)
LOG_FILE      = '/var/log/sg-content-proxy-boot.log'
CA_CERT_FILE  = '/opt/content-proxy/certs/mitmproxy-ca-cert.pem'                     # mitmproxy self-generates its CA here (bind-mounted from certs/)

TEMPLATE = '''\
#!/usr/bin/env bash
set -euo pipefail
exec > >(tee -a {log_file}) 2>&1
echo "[content-proxy] boot starting at $(date -u +%FT%TZ)"

# Arm the auto-terminate deadman switch FIRST — before docker install and the
# image pulls, any of which can fail or hang under `set -e`. If it were scheduled
# at the end (as it once was), a stuck boot would leave the instance running
# forever. Armed here, the box always self-terminates.
{shutdown_line}

dnf install -y docker
systemctl enable --now docker
mkdir -p /usr/local/lib/docker/cli-plugins
curl -fsSL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" \\
    -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
systemctl enable --now amazon-ssm-agent || true

mkdir -p {app_dir}/interceptors {app_dir}/certs
chmod 777 {app_dir}/certs                                                           # mitmproxy (uid 1000) self-generates its CA here

cat > {app_dir}/.env <<'CP_ENV_EOF'
{env_body}
CP_ENV_EOF

cat > {app_dir}/docker-compose.yml <<'CP_COMPOSE_EOF'
{compose_body}
CP_COMPOSE_EOF

cat > {app_dir}/interceptors/active.py <<'CP_ACTIVE_EOF'
{active_body}
CP_ACTIVE_EOF

cat > {app_dir}/interceptors/Content_Proxy__Interceptor__Logic.py <<'CP_LOGIC_EOF'
{logic_body}
CP_LOGIC_EOF

{ca_block}

{overrides_block}

{caddy_block}

cd {app_dir}
docker compose --env-file {app_dir}/.env up -d

echo "[content-proxy] boot complete at $(date -u +%FT%TZ)"
'''

SHUTDOWN_TEMPLATE = 'shutdown -h +{minutes}  # auto-terminate after {hours}h'
SHUTDOWN_DISABLED = '# max_hours=0 — no auto-terminate'

PLACEHOLDERS = ('log_file', 'app_dir', 'env_body', 'compose_body',
                'active_body', 'logic_body', 'ca_block', 'overrides_block',
                'caddy_block', 'shutdown_line')   # locked by test

# `tls internal` only mints a cert for the names in the site address. The internal
# Caddyfile names its site `localhost, 127.0.0.1`, so a browser hitting https://<ip>
# sends an SNI (the public IP) Caddy has no cert for → it aborts the handshake with
# ERR_SSL_PROTOCOL_ERROR (not a trust warning — no cert at all). Fetch this box's
# public IP from IMDSv2 at boot and splice it into the site address so the internal
# cert carries it as a SAN (browser then shows the normal click-through CA warning).
CADDY_IP_INJECT = f'''\
CP_IMDS_TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 300" || true)
CP_PUBLIC_IP=$(curl -s -H "X-aws-ec2-metadata-token: $CP_IMDS_TOKEN" http://169.254.169.254/latest/meta-data/public-ipv4 || true)
if [ -n "$CP_PUBLIC_IP" ]; then
    sed -i "s|^localhost, 127.0.0.1 {{|localhost, 127.0.0.1, $CP_PUBLIC_IP {{|" {APP_DIR}/Caddyfile
    echo "[content-proxy] added public IP $CP_PUBLIC_IP to the Caddy internal-CA site"
fi'''


class Content_Proxy__User_Data__Builder(Type_Safe):

    def render_env(self, request, fastapi_api_key: str = '', access_token: str = '',
                   region: str = '', account_id: str = '', aws_creds: dict = None) -> str:
        lines = [
            'FASTAPI_API_KEY_NAME=x-api-key',
            f'FASTAPI_API_KEY_VALUE={fastapi_api_key}',                              # generated per-stack; interceptor ↔ mitm-service
            # the access token — vault + sg-playwright key (/pw) + set-cookie token (one value, like sg va)
            'FAST_API__AUTH__API_KEY__NAME=X-API-Key',
            f'FAST_API__AUTH__API_KEY__VALUE={access_token}',
            f'SGRAPH_SEND__ACCESS_TOKEN={access_token}',
            f'CONTENT_PROXY__PROXYAUTH_USER={str(request.proxyauth_user)}',
            f'CONTENT_PROXY__PROXYAUTH_PASS={str(request.proxyauth_pass)}',
            f'CONTENT_PROXY__CA_DIR={APP_DIR}/certs',
            'SEND__STORAGE_MODE=memory',
            f'AWS_DEFAULT_REGION={region}',
        ]
        if account_id:                                                              # deploying account — set on BOTH the instance-role and forwarded-creds paths (the app reads AWS_ACCOUNT_ID even when creds come from IMDS)
            lines.append(f'AWS_ACCOUNT_ID={account_id}')
        if str(request.scripts_bucket):
            lines.append(f'CACHE__SERVICE__BUCKET_NAME={str(request.scripts_bucket)}')
        for k, v in (aws_creds or {}).items():                                      # only when --forward-aws-creds (else instance role)
            if v and k != 'AWS_ACCOUNT_ID':                                         # account id already written above — don't duplicate
                lines.append(f'{k}={v}')
        return '\n'.join(lines)

    def _interceptor_body(self, filename: str) -> str:
        return (Path(interceptors_pkg.__file__).parent / filename).read_text()

    def _shutdown_line(self, max_hours: float) -> str:
        minutes = int(round(float(max_hours) * 60))
        if minutes > 0:
            return SHUTDOWN_TEMPLATE.format(minutes=minutes, hours=max_hours)
        return SHUTDOWN_DISABLED

    def _ca_block(self, request) -> str:
        pem = str(getattr(request, 'proxy_ca_pem', '') or '')
        if pem:                                                                      # ship the (already-trusted) CA so the EC2 proxy reuses it
            return ('echo "[content-proxy] installing supplied proxy CA"\n'
                    f"cat > {APP_DIR}/certs/mitmproxy-ca.pem <<'CP_CA_EOF'\n{pem}\nCP_CA_EOF\n"
                    f'chmod 644 {APP_DIR}/certs/mitmproxy-ca.pem')
        cert = str(getattr(request, 'proxy_ca_cert', '') or '')
        if cert:
            return f'# proxy CA path {cert} supplied — copy into {APP_DIR}/certs before boot'
        return '# no proxy CA supplied — mitmproxy will self-generate one'

    def _caddy_block(self, request, hostname: str, browser_count: int = 0) -> str:
        # edge=caddy → write the Caddyfile the cp-caddy service bind-mounts. hostname
        # (when set) makes Caddy do public auto-ACME; blank → `tls internal` (IP/local).
        # browser_count adds the /browser/{i} routes above the catch-all.
        if getattr(request, 'edge', None) != Enum__Content_Proxy__Edge.CADDY:
            return '# edge=none — vault is the front door (no Caddyfile)'
        caddyfile  = Content_Proxy__Edge__Template().render(hostname=hostname, acme_email='',   # acme_email not wired yet (no --acme-email flag)
                                                            browser_count=browser_count,
                                                            edge_auth=bool(getattr(request, 'edge_auth', False)))
        block = ('echo "[content-proxy] writing Caddyfile (edge=caddy)"\n'
                 f"cat > {APP_DIR}/Caddyfile <<'CP_CADDY_EOF'\n{caddyfile}\nCP_CADDY_EOF")
        if not hostname:                                                              # internal-CA site (no FQDN) → add the box's public IP so https://<ip> works
            block += '\n' + CADDY_IP_INJECT
        return block

    def render(self, request, fastapi_api_key: str = '', access_token: str = '',
               region: str = '', account_id: str = '', aws_creds: dict = None, env_override: str = '',
               hostname: str = '', browser_count: int = 0, browser_engine: str = 'chromium') -> str:
        # MVP: if the operator supplied a full .env, ship it verbatim; else build one.
        env_body = env_override if env_override else self.render_env(
            request, fastapi_api_key, access_token, region, account_id, aws_creds)
        edge     = getattr(request, 'edge', Enum__Content_Proxy__Edge.NONE)
        is_caddy = edge == Enum__Content_Proxy__Edge.CADDY
        compose = Content_Proxy__Compose__Template().render(
            mitmproxy_image    = str(request.mitmproxy_image)   ,
            mitm_service_image = str(request.mitm_service_image),
            playwright_image   = str(request.playwright_image)  ,
            vault_app_image    = str(request.vault_app_image)   ,
            proxy_tool         = request.proxy_tool             ,                    # MITMDUMP default on EC2 (prod-safe)
            interceptors_mount = INTERCEPTORS_MOUNT__EC2        ,                    # /opt/content-proxy/interceptors
            tls                = request.tls                    ,                    # vault port: 8080 (NONE) vs 443 (TLS)
            edge               = edge                           ,                    # caddy → vault plain origin, edge owns :443
            hostname           = hostname                       ,                    # caddy hostname → publish :80 for ACME
            browser_count      = browser_count                  ,                    # N interactive sg-playwright-vnc browsers (cp-browser-{i})
            browser_engine     = browser_engine                 )                    # the fleet's autostarted engine
        # caddy fronts /pw at the edge → vault uses its default entrypoint (no override package needed)
        overrides_block = ('# edge=caddy — /pw routed at the edge, no vault entrypoint patch'
                           if is_caddy else
                           Vault_App__Reverse_Proxy__Override().render_write_block(OVERRIDES_DIR))
        return TEMPLATE.format(log_file      = LOG_FILE                                  ,
                               app_dir       = APP_DIR                                   ,
                               env_body      = env_body                                  ,
                               compose_body  = compose                                   ,
                               active_body   = self._interceptor_body('active.py')       ,
                               logic_body    = self._interceptor_body('Content_Proxy__Interceptor__Logic.py'),
                               ca_block      = self._ca_block(request)                   ,
                               overrides_block = overrides_block                         ,
                               caddy_block   = self._caddy_block(request, hostname, browser_count),
                               shutdown_line = self._shutdown_line(float(request.max_hours)))

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
from sg_compute_specs.content_proxy.service.Content_Proxy__Compose__Template         import (Content_Proxy__Compose__Template,
                                                                                             INTERCEPTORS_MOUNT__EC2)


APP_DIR  = '/opt/content-proxy'
LOG_FILE = '/var/log/sg-content-proxy-boot.log'

TEMPLATE = '''\
#!/usr/bin/env bash
set -euo pipefail
exec > >(tee -a {log_file}) 2>&1
echo "[content-proxy] boot starting at $(date -u +%FT%TZ)"

dnf install -y docker
systemctl enable --now docker
mkdir -p /usr/local/lib/docker/cli-plugins
curl -fsSL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" \\
    -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
systemctl enable --now amazon-ssm-agent || true

mkdir -p {app_dir}/interceptors {app_dir}/certs

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

cd {app_dir}
docker compose --env-file {app_dir}/.env up -d

{shutdown_line}
echo "[content-proxy] boot complete at $(date -u +%FT%TZ)"
'''

SHUTDOWN_TEMPLATE = 'shutdown -h +{minutes}  # auto-terminate after {hours}h'
SHUTDOWN_DISABLED = '# max_hours=0 — no auto-terminate'

PLACEHOLDERS = ('log_file', 'app_dir', 'env_body', 'compose_body',
                'active_body', 'logic_body', 'ca_block', 'shutdown_line')           # locked by test


class Content_Proxy__User_Data__Builder(Type_Safe):

    def render_env(self, request) -> str:
        return '\n'.join([
            f'FASTAPI_API_KEY_NAME={str(request.api_key_name) if hasattr(request, "api_key_name") else "x-api-key"}',
            'FASTAPI_API_KEY_VALUE=${FASTAPI_API_KEY_VALUE:-}',                      # injected via SSM/secret at deploy
            f'CONTENT_PROXY__PROXYAUTH_USER={str(request.proxyauth_user)}',
            f'CONTENT_PROXY__PROXYAUTH_PASS={str(request.proxyauth_pass)}',
            f'CONTENT_PROXY__CA_DIR={APP_DIR}/certs',
            'SEND__STORAGE_MODE=memory',
        ])

    def _interceptor_body(self, filename: str) -> str:
        return (Path(interceptors_pkg.__file__).parent / filename).read_text()

    def _shutdown_line(self, max_hours: int) -> str:
        if max_hours and int(max_hours) > 0:
            return SHUTDOWN_TEMPLATE.format(minutes=int(max_hours) * 60, hours=int(max_hours))
        return SHUTDOWN_DISABLED

    def _ca_block(self, request) -> str:
        cert = str(getattr(request, 'proxy_ca_cert', '') or '')
        if not cert:
            return '# no proxy CA supplied — mitmproxy will self-generate one'
        return (f'echo "[content-proxy] proxy CA supplied at {cert}; '
                f'copy it into {APP_DIR}/certs before first boot"')

    def render(self, request) -> str:
        compose = Content_Proxy__Compose__Template().render(
            mitmproxy_image    = str(request.mitmproxy_image)   ,
            mitm_service_image = str(request.mitm_service_image),
            playwright_image   = str(request.playwright_image)  ,
            vault_app_image    = str(request.vault_app_image)   ,
            proxy_tool         = request.proxy_tool             ,                    # MITMDUMP default on EC2 (prod-safe)
            interceptors_mount = INTERCEPTORS_MOUNT__EC2        )                    # /opt/content-proxy/interceptors
        return TEMPLATE.format(log_file      = LOG_FILE                                  ,
                               app_dir       = APP_DIR                                   ,
                               env_body      = self.render_env(request)                  ,
                               compose_body  = compose                                   ,
                               active_body   = self._interceptor_body('active.py')       ,
                               logic_body    = self._interceptor_body('Content_Proxy__Interceptor__Logic.py'),
                               ca_block      = self._ca_block(request)                   ,
                               shutdown_line = self._shutdown_line(int(request.max_hours)))

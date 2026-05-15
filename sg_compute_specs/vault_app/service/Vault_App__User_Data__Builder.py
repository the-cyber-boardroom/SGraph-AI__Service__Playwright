# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-app: Vault_App__User_Data__Builder
# Composes the cloud-init bash script for a vault-app EC2 host.
#
# Order: Section__Base (incl. auto-terminate timer) → container-engine install
#      → write .env + docker-compose.yml → ECR login → compose up → footer
#
# The auto-terminate timer is inside Section__Base and fires even if a later
# dnf install or image pull aborts the script (L9 lesson).
#
# Boot-time note: the slow steps are the engine install (including GitHub compose
# download) and the ECR image pull. Bake an AMI from a warm stack so a re-launch
# skips both — see the AMI__Helper header. When booting from a baked AMI the
# engine is already present and `compose up` re-uses the local image layers.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute.platforms.ec2.user_data.Section__Base                import Section__Base
from sg_compute_specs.vault_app.service.Vault_App__Compose__Template import Vault_App__Compose__Template

FOOTER = ('\ntouch /var/lib/sg-compute-boot-ok\n'
          'echo "[vault-app] boot complete at $(date -u +%FT%TZ)"\n')

# ── container-engine install fragments ───────────────────────────────────────
# docker: docker-compose-plugin is NOT in standard AL2023 repos — the compose V2
#         CLI plugin binary is downloaded from Docker's GitHub releases instead.
# podman: daemonless; podman-compose drives the same compose file.

_ENGINE_DOCKER = '''
# ── Docker CE + compose plugin ───────────────────────────────────────────────
echo "[vault-app] installing Docker CE..."
dnf install -y docker
# docker-compose-plugin is not in standard AL2023 repos — download the CLI plugin.
COMPOSE_VER="v2.27.0"
mkdir -p /usr/local/lib/docker/cli-plugins
curl -fsSL "https://github.com/docker/compose/releases/download/${COMPOSE_VER}/docker-compose-linux-x86_64" \\
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
systemctl enable --now docker
docker --version
docker compose version
echo "[vault-app] Docker ready"
'''

_ENGINE_PODMAN = '''
# ── Podman + podman-compose ──────────────────────────────────────────────────
echo "[vault-app] installing Podman..."
dnf install -y podman podman-compose
# host-plane needs a docker-API socket — podman exposes a compatible one.
systemctl enable --now podman.socket
podman --version
echo "[vault-app] Podman ready"
'''

_STACK_TEMPLATE = '''
# ── vault-app stack ({mode}, engine={engine}) ───────────────────────────────
mkdir -p /opt/vault-app/data

cat > /opt/vault-app/.env <<'ENVEOF'
ECR_REGISTRY={ecr_registry}
IMAGE_TAG={image_tag}
FAST_API__AUTH__API_KEY__NAME=X-API-Key
FAST_API__AUTH__API_KEY__VALUE={access_token}
SGRAPH_SEND__ACCESS_TOKEN={access_token}
SEND__STORAGE_MODE={storage_mode}
VAULT_DATA_PATH=/opt/vault-app/data
SG_VAULT_APP__SEED_VAULT_KEYS={seed_vault_keys}
{tls_env_lines}ENVEOF
chmod 600 /opt/vault-app/.env

cat > /opt/vault-app/docker-compose.yml <<'COMPOSEEOF'
{compose_yaml}
COMPOSEEOF

cd /opt/vault-app
aws ecr get-login-password --region "{region}" | \\
  {engine} login --username AWS --password-stdin "{ecr_registry}"
{compose_cmd} --env-file /opt/vault-app/.env up -d
{engine} logout "{ecr_registry}" 2>/dev/null || true
echo "[vault-app] stack started ({mode}, engine={engine})"
'''


class Vault_App__User_Data__Builder(Type_Safe):

    def render(self, stack_name       : str   ,
                     region           : str   ,
                     ecr_registry     : str   ,
                     access_token     : str   ,
                     with_playwright  : bool  = False        ,
                     container_engine : str   = 'docker'     ,
                     image_tag        : str   = 'latest'     ,
                     storage_mode     : str   = 'disk'       ,
                     seed_vault_keys  : str   = ''           ,
                     max_hours        : float = 1.0          ,
                     with_tls_check   : bool  = False        ,
                     tls_mode         : str   = 'self-signed',
                     acme_prod        : bool  = False        ,
                     tls_hostname     : str   = ''            ) -> str:
        engine        = container_engine if container_engine in ('docker', 'podman') else 'docker'
        is_podman     = engine == 'podman'
        docker_socket = '/run/podman/podman.sock' if is_podman else '/var/run/docker.sock'
        compose_cmd   = 'podman-compose' if is_podman else 'docker compose'
        engine_block  = _ENGINE_PODMAN  if is_podman else _ENGINE_DOCKER
        mode          = 'with-playwright' if with_playwright else 'just-vault'

        # cert-init reads these from .env; only emitted when TLS is on.
        tls_env_lines = ''
        if with_tls_check:
            tls_mode      = tls_mode if tls_mode in ('self-signed', 'letsencrypt-ip', 'letsencrypt-hostname') else 'self-signed'
            tls_env_lines = (f'SG__CERT_INIT__MODE={tls_mode}\n'
                             f'SG__CERT_INIT__ACME_PROD={"true" if acme_prod else "false"}\n')
            if tls_mode == 'letsencrypt-hostname':                           # FQDN is mandatory for this mode; service layer validates non-empty
                tls_env_lines += f'SG__CERT_INIT__TLS_HOSTNAME={tls_hostname}\n'

        compose_yaml  = Vault_App__Compose__Template().render(
            ecr_registry    = ecr_registry    ,
            with_playwright = with_playwright ,
            image_tag       = image_tag       ,
            docker_socket   = docker_socket   ,
            with_tls_check  = with_tls_check  )

        stack_block = _STACK_TEMPLATE.format(
            mode            = mode            ,
            engine          = engine          ,
            compose_cmd     = compose_cmd     ,
            ecr_registry    = ecr_registry    ,
            image_tag       = image_tag       ,
            access_token    = access_token    ,
            storage_mode    = storage_mode    ,
            seed_vault_keys = seed_vault_keys ,
            region          = region          ,
            tls_env_lines   = tls_env_lines   ,
            compose_yaml    = compose_yaml    )

        parts = [
            Section__Base().render(stack_name=stack_name, max_hours=max_hours),
            engine_block ,
            stack_block  ,
            FOOTER       ,
        ]
        return '\n'.join(p for p in parts if p)

# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — playwright: Playwright__User_Data__Builder
# Composes the cloud-init bash script for a playwright EC2 host.
#
# Order: Section__Base (incl. auto-terminate timer) → Docker CE install →
#        write .env + (optional) interceptor + docker-compose.yml → ECR login →
#        compose up → footer
#
# The auto-terminate timer is inside Section__Base and fires even if a later
# dnf install or image pull aborts the script.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute.platforms.ec2.user_data.Section__Base                  import Section__Base
from sg_compute_specs.playwright.service.Playwright__Compose__Template import Playwright__Compose__Template

FOOTER = ('\ntouch /var/lib/sg-compute-boot-ok\n'
          'echo "[playwright] boot complete at $(date -u +%FT%TZ)"\n')

# docker-compose-plugin is NOT in standard AL2023 repos — the compose V2 CLI
# plugin binary is downloaded from Docker's GitHub releases instead.
_ENGINE_DOCKER = '''
# ── Docker CE + compose plugin ───────────────────────────────────────────────
echo "[playwright] installing Docker CE..."
dnf install -y docker
COMPOSE_VER="v2.27.0"
mkdir -p /usr/local/lib/docker/cli-plugins
curl -fsSL "https://github.com/docker/compose/releases/download/${COMPOSE_VER}/docker-compose-linux-x86_64" \\
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
systemctl enable --now docker
docker --version
docker compose version
echo "[playwright] Docker ready"
'''

_INTERCEPTOR_BLOCK = '''
# ── mitmproxy interceptor (--intercept-script) ───────────────────────────────
mkdir -p /opt/sg-playwright/interceptors
cat > /opt/sg-playwright/interceptors/active.py <<'INTERCEPTOREOF'
{intercept_script}
INTERCEPTOREOF
echo "[playwright] interceptor script written"
'''

_STACK_TEMPLATE = '''
# ── playwright stack ({mode}) ────────────────────────────────────────────────
mkdir -p /opt/sg-playwright
{interceptor_block}
cat > /opt/sg-playwright/.env <<'ENVEOF'
ECR_REGISTRY={ecr_registry}
IMAGE_TAG={image_tag}
FAST_API__AUTH__API_KEY__NAME=X-API-Key
FAST_API__AUTH__API_KEY__VALUE={api_key}
ENVEOF
chmod 600 /opt/sg-playwright/.env

cat > /opt/sg-playwright/docker-compose.yml <<'COMPOSEEOF'
{compose_yaml}
COMPOSEEOF

cd /opt/sg-playwright
aws ecr get-login-password --region "{region}" | \\
  docker login --username AWS --password-stdin "{ecr_registry}"
docker compose --env-file /opt/sg-playwright/.env up -d
docker logout "{ecr_registry}" 2>/dev/null || true
echo "[playwright] stack started ({mode})"
'''


class Playwright__User_Data__Builder(Type_Safe):

    def render(self, stack_name       : str   ,
                     region           : str   ,
                     ecr_registry     : str   ,
                     api_key          : str   ,
                     with_mitmproxy   : bool  = False        ,
                     intercept_script : str   = ''           ,
                     image_tag        : str   = 'latest'     ,
                     max_hours        : float = 1.0           ) -> str:
        with_intercept = bool(with_mitmproxy and intercept_script)
        mode           = 'with-mitmproxy' if with_mitmproxy else 'default'

        compose_yaml = Playwright__Compose__Template().render(
            ecr_registry   = ecr_registry   ,
            with_mitmproxy = with_mitmproxy ,
            with_intercept = with_intercept ,
            image_tag      = image_tag      )

        interceptor_block = ''
        if with_intercept:
            interceptor_block = _INTERCEPTOR_BLOCK.format(intercept_script=intercept_script)

        stack_block = _STACK_TEMPLATE.format(
            mode              = mode              ,
            interceptor_block = interceptor_block ,
            ecr_registry      = ecr_registry      ,
            image_tag         = image_tag         ,
            api_key           = api_key           ,
            region            = region            ,
            compose_yaml      = compose_yaml      )

        parts = [
            Section__Base().render(stack_name=stack_name, max_hours=max_hours),
            _ENGINE_DOCKER ,
            stack_block    ,
            FOOTER         ,
        ]
        return '\n'.join(p for p in parts if p)

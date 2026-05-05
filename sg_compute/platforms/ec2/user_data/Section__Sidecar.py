# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Section__Sidecar
# Bash fragment that pulls and starts the host-control sidecar container.
# Injected by every spec's User_Data__Builder when a registry is provided.
# Container listens on :19009 (internal 8000) with docker.sock mounted.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

IMAGE_NAME     = 'sgraph_ai_service_playwright_host'
CONTAINER_NAME = 'sg-sidecar'
DEFAULT_PORT   = 19009

TEMPLATE = """\
# ── sidecar (host control plane) ─────────────────────────────────────────────
echo "[sg-compute] starting sidecar on port {port}..."

aws ecr get-login-password --region "$REGION" | \\
  docker login --username AWS --password-stdin "{registry}"

docker run -d \\
  --name {container_name} \\
  --restart=unless-stopped \\
  --privileged \\
  -v /var/run/docker.sock:/var/run/docker.sock \\
  -e FAST_API__AUTH__API_KEY__NAME="{api_key_name}" \\
  -e FAST_API__AUTH__API_KEY__VALUE="{api_key_value}" \\
  -p {port}:8000 \\
  "{registry}/{image}:{image_tag}" || true

echo "[sg-compute] sidecar started"
rm -f /root/.docker/config.json
"""


class Section__Sidecar(Type_Safe):

    def render(self, registry     : str = '',
                     image_tag    : str = 'latest',
                     api_key_name : str = 'X-API-Key',
                     api_key_value: str = '',
                     port         : int = DEFAULT_PORT) -> str:
        if not registry:
            return ''
        return TEMPLATE.format(registry      = registry      ,
                               image         = IMAGE_NAME    ,
                               image_tag     = image_tag     ,
                               api_key_name  = api_key_name  ,
                               api_key_value = api_key_value ,
                               port          = port          ,
                               container_name= CONTAINER_NAME)

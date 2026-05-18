# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Section__Sidecar
# Bash fragment that pulls and starts the host-control sidecar container.
# Injected by every spec's User_Data__Builder when an SSM key path is provided.
# Container listens on :19009 (internal 8000) with docker.sock mounted.
#
# Image source: Docker Hub — `diniscruz/sg-host-control` (small dedicated
# python:3.12-alpine image, NOT the 2GB Playwright image). Public pull, so
# no `docker login` is required and no `/root/.docker/config.json` cleanup
# needed. Built + pushed by .github/workflows/build-host-control-dockerhub.yml.
#
# Security boundary: Docker socket mount only — NEVER --privileged.
# Host-kernel access (CAP_SYS_ADMIN, raw devices) is not in the contract.
# Docker socket is sufficient for pod-CRUD; --privileged would allow
# container escape to the host kernel.
#
# API key: fetched from SSM at boot via the Node's IAM role (not baked into
# user-data where IMDS at 169.254.169.254/latest/user-data would expose it).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute.primitives.Safe_Int__Port                                    import Safe_Int__Port
from sg_compute.primitives.Safe_Str__Image__Registry                        import Safe_Str__Image__Registry
from sg_compute.primitives.Safe_Str__Image__Tag                             import Safe_Str__Image__Tag
from sg_compute.primitives.Safe_Str__Message                                import Safe_Str__Message
from sg_compute.primitives.Safe_Str__SSM__Path                              import Safe_Str__SSM__Path

HOST_CONTROL_IMAGE = 'diniscruz/sg-host-control'                                    # Docker Hub — pulled directly, no ECR login required
CONTAINER_NAME     = 'sg-sidecar'
DEFAULT_PORT       = 19009

TEMPLATE = '''\
# ── sidecar (host control plane) ─────────────────────────────────────────────
echo "[sg-compute] starting sidecar on port {port}..."

# Fetch per-node API key from SSM (IAM role auth; key never in user-data)
SIDECAR_API_KEY=$(aws ssm get-parameter \\
  --name "{api_key_ssm_path}" \\
  --with-decryption \\
  --query Parameter.Value \\
  --output text)

docker run -d \\
  --name {container_name} \\
  --restart=unless-stopped \\
  -v /var/run/docker.sock:/var/run/docker.sock \\
  -e FAST_API__AUTH__API_KEY__NAME="{api_key_name}" \\
  -e FAST_API__AUTH__API_KEY__VALUE="$SIDECAR_API_KEY" \\
  {shell_env_flag}-p {port}:8000 \\
  "{image}:{image_tag}" || true

echo "[sg-compute] sidecar started"
'''


class Section__Sidecar(Type_Safe):

    def render(self, registry        : Safe_Str__Image__Registry = Safe_Str__Image__Registry(),  # legacy/unused — kept for caller compatibility
                     image_tag       : Safe_Str__Image__Tag      = Safe_Str__Image__Tag('latest'),
                     api_key_name    : Safe_Str__Message         = Safe_Str__Message('X-API-Key'),
                     api_key_ssm_path: Safe_Str__SSM__Path       = Safe_Str__SSM__Path(),
                     port            : Safe_Int__Port            = Safe_Int__Port(DEFAULT_PORT),
                     enable_shell    : bool                      = False) -> str:
        if not api_key_ssm_path:                                                    # gate on SSM path — the IAM-fetched key is required for the sidecar to be useful
            return ''
        _ = registry                                                                # explicitly unused — Docker Hub image needs no registry
        shell_env_flag = '-e SG_SHELL_UNRESTRICTED=1 \\\n  ' if enable_shell else ''
        return TEMPLATE.format(image            = HOST_CONTROL_IMAGE,
                               image_tag        = image_tag         ,
                               api_key_name     = api_key_name      ,
                               api_key_ssm_path = api_key_ssm_path  ,
                               port             = port              ,
                               container_name   = CONTAINER_NAME    ,
                               shell_env_flag   = shell_env_flag    )

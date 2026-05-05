# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Docker: Docker__User_Data__Builder
# cloud-init for AL2023 + Docker CE + host control plane sidecar (port 19009).
# When registry is empty the sidecar section is omitted (bare docker only).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute.platforms.ec2.user_data.Section__Sidecar                           import Section__Sidecar
from sg_compute.primitives.Safe_Int__Max__Hours                                    import Safe_Int__Max__Hours
from sg_compute.primitives.Safe_Str__AWS__Region                                   import Safe_Str__AWS__Region
from sg_compute.primitives.Safe_Str__Image__Registry                               import Safe_Str__Image__Registry
from sg_compute.primitives.Safe_Str__Message                                       import Safe_Str__Message
from sg_compute.primitives.Safe_Str__SSM__Path                                     import Safe_Str__SSM__Path
from sg_compute.primitives.Safe_Str__Stack__Name                                   import Safe_Str__Stack__Name


LOG_FILE = '/var/log/sg-docker-boot.log'

BASE_TEMPLATE = '''\
#!/usr/bin/env bash
set -euo pipefail
exec > >(tee -a {log_file}) 2>&1
echo "[sg-docker] boot starting at $(date -u +%FT%TZ)"

STACK_NAME='{stack_name}'
REGION='{region}'

echo "[sg-docker] installing Docker on AL2023..."
dnf install -y docker
systemctl enable --now docker

echo "[sg-docker] installing docker compose plugin..."
mkdir -p /usr/local/lib/docker/cli-plugins
curl -fsSL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" \\
    -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

echo "[sg-docker] verifying docker..."
docker version
docker compose version

# AL2023 ships with SSM agent; ensure it is active
systemctl enable --now amazon-ssm-agent || true
'''

FOOTER_TEMPLATE = '''\
{shutdown_line}

echo "[sg-docker] boot complete at $(date -u +%FT%TZ)"
'''

SHUTDOWN_TEMPLATE = 'shutdown -h +{minutes}  # auto-terminate after {hours}h'
SHUTDOWN_DISABLED = '# max_hours=0 — no auto-terminate'

PLACEHOLDERS = ('stack_name', 'region', 'log_file', 'shutdown_line')               # Locked by test


class Docker__User_Data__Builder(Type_Safe):

    def render(self, stack_name     : Safe_Str__Stack__Name    ,
                     region         : Safe_Str__AWS__Region     ,
                     registry       : Safe_Str__Image__Registry = Safe_Str__Image__Registry()        ,
                     api_key_name   : Safe_Str__Message         = Safe_Str__Message('X-API-Key')     ,
                     api_key_ssm_path: Safe_Str__SSM__Path      = Safe_Str__SSM__Path()              ,
                     max_hours      : Safe_Int__Max__Hours       = Safe_Int__Max__Hours(1)            ,
                     enable_shell   : bool                      = False                              ) -> str:
        shutdown_line = (SHUTDOWN_TEMPLATE.format(minutes=max_hours * 60, hours=max_hours)
                         if max_hours > 0 else SHUTDOWN_DISABLED)
        script = BASE_TEMPLATE.format(stack_name=str(stack_name),
                                      region    =str(region)    ,
                                      log_file  =LOG_FILE       )
        script += Section__Sidecar().render(registry         = registry         ,
                                            api_key_name     = api_key_name     ,
                                            api_key_ssm_path = api_key_ssm_path ,
                                            enable_shell     = enable_shell     )
        script += FOOTER_TEMPLATE.format(shutdown_line=shutdown_line)
        return script

# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Podman: Podman__User_Data__Builder
# cloud-init for a bare AL2023 instance with Podman installed. Daemonless —
# no Docker daemon required. SSM agent is already present on AL2023.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute.platforms.ec2.user_data.Section__Sidecar                           import Section__Sidecar
from sg_compute.primitives.Safe_Int__Max__Hours                                    import Safe_Int__Max__Hours
from sg_compute.primitives.Safe_Str__AWS__Region                                   import Safe_Str__AWS__Region
from sg_compute.primitives.Safe_Str__Image__Registry                               import Safe_Str__Image__Registry
from sg_compute.primitives.Safe_Str__Message                                       import Safe_Str__Message
from sg_compute.primitives.Safe_Str__SSM__Path                                     import Safe_Str__SSM__Path
from sg_compute.primitives.Safe_Str__Stack__Name                                   import Safe_Str__Stack__Name


LOG_FILE = '/var/log/sg-podman-boot.log'


USER_DATA_TEMPLATE = """\
#!/usr/bin/env bash
set -euo pipefail
exec > >(tee -a {log_file}) 2>&1
echo "[sg-podman] boot starting at $(date -u +%FT%TZ)"

STACK_NAME='{stack_name}'
REGION='{region}'

echo "[sg-podman] installing Podman on AL2023..."
dnf install -y podman
# No daemon — podman is daemonless

echo "[sg-podman] enabling podman socket (Docker-compatible API)..."
systemctl enable --now podman.socket || true

echo "[sg-podman] verifying podman..."
podman version

# AL2023 ships with SSM agent; ensure it is active
systemctl enable --now amazon-ssm-agent || true

{sidecar_section}
{shutdown_line}

echo "[sg-podman] boot complete at $(date -u +%FT%TZ)"
"""

SHUTDOWN_TEMPLATE = 'shutdown -h +{minutes}  # auto-terminate after {hours}h'
SHUTDOWN_DISABLED = '# max_hours=0 — no auto-terminate'

PLACEHOLDERS = ('stack_name', 'region', 'log_file', 'sidecar_section', 'shutdown_line')  # Locked by test


class Podman__User_Data__Builder(Type_Safe):

    def render(self, stack_name     : Safe_Str__Stack__Name    ,
                     region         : Safe_Str__AWS__Region     ,
                     max_hours      : Safe_Int__Max__Hours       = Safe_Int__Max__Hours(1)            ,
                     registry       : Safe_Str__Image__Registry  = Safe_Str__Image__Registry()        ,
                     api_key_name   : Safe_Str__Message          = Safe_Str__Message('X-API-Key')     ,
                     api_key_ssm_path: Safe_Str__SSM__Path       = Safe_Str__SSM__Path()              ) -> str:
        shutdown_line   = (SHUTDOWN_TEMPLATE.format(minutes=max_hours * 60, hours=max_hours)
                           if max_hours > 0 else SHUTDOWN_DISABLED)
        sidecar_section = Section__Sidecar().render(registry      = registry      ,
                                                    api_key_name  = api_key_name  ,
                                                    api_key_ssm_path = api_key_ssm_path )
        return USER_DATA_TEMPLATE.format(stack_name      = str(stack_name)  ,
                                         region          = str(region)      ,
                                         log_file        = LOG_FILE         ,
                                         sidecar_section = sidecar_section  ,
                                         shutdown_line   = shutdown_line    )

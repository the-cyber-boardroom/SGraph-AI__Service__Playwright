# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Linux__User_Data__Builder
# Minimal cloud-init for a bare AL2023 instance with SSM pre-installed.
# AL2023 ships with the SSM agent — this script just ensures it is running
# and tags completion so health checks can detect readiness via SSM.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


LOG_FILE = '/var/log/sg-linux-boot.log'


USER_DATA_TEMPLATE = """\
#!/usr/bin/env bash
set -euo pipefail
exec > >(tee -a {log_file}) 2>&1
echo "[sg-linux] boot starting at $(date -u +%FT%TZ)"

STACK_NAME='{stack_name}'
REGION='{region}'

# AL2023 ships with SSM agent; ensure it is active
systemctl enable --now amazon-ssm-agent || true

echo "[sg-linux] boot complete at $(date -u +%FT%TZ)"
"""


PLACEHOLDERS = ('stack_name', 'region', 'log_file')                                 # Locked by test


class Linux__User_Data__Builder(Type_Safe):

    def render(self, stack_name: str, region: str) -> str:
        return USER_DATA_TEMPLATE.format(stack_name = str(stack_name),
                                         region     = str(region)    ,
                                         log_file   = LOG_FILE       )

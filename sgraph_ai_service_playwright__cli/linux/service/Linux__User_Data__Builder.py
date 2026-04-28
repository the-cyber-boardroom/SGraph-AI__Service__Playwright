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

{shutdown_line}

echo "[sg-linux] boot complete at $(date -u +%FT%TZ)"
"""

SHUTDOWN_TEMPLATE = 'shutdown -h +{minutes}  # auto-terminate after {hours}h'      # Runs at boot via cloud-init; works even without at/cron
SHUTDOWN_DISABLED = '# max_hours=0 — no auto-terminate'

PLACEHOLDERS = ('stack_name', 'region', 'log_file', 'shutdown_line')                # Locked by test


class Linux__User_Data__Builder(Type_Safe):

    def render(self, stack_name: str, region: str, max_hours: int = 1) -> str:
        if max_hours > 0:
            shutdown_line = SHUTDOWN_TEMPLATE.format(minutes=max_hours * 60, hours=max_hours)
        else:
            shutdown_line = SHUTDOWN_DISABLED
        return USER_DATA_TEMPLATE.format(stack_name    = str(stack_name) ,
                                         region        = str(region)     ,
                                         log_file      = LOG_FILE        ,
                                         shutdown_line = shutdown_line   )

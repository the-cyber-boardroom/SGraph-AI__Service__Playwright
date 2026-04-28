# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — OpenSearch__User_Data__Builder
# Renders the EC2 UserData (cloud-init #cloud-config or bash) that installs
# OpenSearch + Dashboards on a fresh AL2023 instance. Single responsibility:
# string templating with safe substitutions.
#
# This slice (Phase B step 5f.1) ships the shape only — a small bash
# scaffold with substitution placeholders. The actual Docker / compose /
# OpenSearch install commands grow incrementally in subsequent slices so
# each addition is reviewable on its own. The renderer's contract (inputs,
# placeholder set, escaping) is locked by tests now.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


# Bash template — every {placeholder} must appear in PLACEHOLDERS below
USER_DATA_TEMPLATE = """\
#!/usr/bin/env bash
set -euo pipefail
exec > >(tee -a /var/log/sg-opensearch-boot.log) 2>&1
echo "[sg-opensearch] boot starting at $(date -u +%FT%TZ)"

STACK_NAME='{stack_name}'
ADMIN_PASSWORD='{admin_password}'
REGION='{region}'

echo "[sg-opensearch] stack=$STACK_NAME region=$REGION"
# OpenSearch + Dashboards install commands land in subsequent slices.
echo "[sg-opensearch] boot script placeholder — install logic deferred"
"""


PLACEHOLDERS = ('stack_name', 'admin_password', 'region')                           # Locked by test — drift caught on PLACEHOLDER add/remove


class OpenSearch__User_Data__Builder(Type_Safe):

    def render(self, stack_name: str, admin_password: str, region: str) -> str:
        return USER_DATA_TEMPLATE.format(stack_name     = str(stack_name)    ,
                                         admin_password = str(admin_password),
                                         region         = str(region)        )

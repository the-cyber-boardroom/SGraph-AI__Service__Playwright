# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Section__Env__File
# Writes KEY=VALUE pairs to /run/<stack_name>/env on a tmpfs mount.
# Secrets exist only in RAM — never on EBS / AMI / disk.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

TEMPLATE = """
# ── Environment file on tmpfs (RAM only) ─────────────────────────────────────
mkdir -p /run/{stack_name}
mount -t tmpfs tmpfs /run/{stack_name} 2>/dev/null || true
cat > /run/{stack_name}/env <<'ENVEOF'
{env_content}
ENVEOF
chmod 600 /run/{stack_name}/env
echo "[ephemeral-ec2] env file written to /run/{stack_name}/env"
"""


class Section__Env__File(Type_Safe):

    def render(self, stack_name: str, env_content: str) -> str:
        return TEMPLATE.format(stack_name=stack_name, env_content=env_content)

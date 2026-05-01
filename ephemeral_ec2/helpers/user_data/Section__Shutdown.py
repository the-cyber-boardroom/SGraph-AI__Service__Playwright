# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Section__Shutdown
# Schedules auto-termination via systemd-run. Paired with
# InstanceInitiatedShutdownBehavior=terminate in EC2__Launch__Helper so that
# halt causes termination, not stop.
# max_hours=0 emits a no-op comment (caller omits this section instead).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

TEMPLATE = """
# ── Auto-terminate after {max_hours}h ────────────────────────────────────────
systemd-run --on-active={max_hours}h /sbin/shutdown -h now
echo "[ephemeral-ec2] auto-terminate timer set: {max_hours}h from now"
"""


class Section__Shutdown(Type_Safe):

    def render(self, max_hours: int = 1) -> str:
        return TEMPLATE.format(max_hours=max_hours)

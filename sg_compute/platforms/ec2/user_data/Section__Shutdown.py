# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Section__Shutdown
# Schedules auto-termination via systemd-run. Paired with
# InstanceInitiatedShutdownBehavior=terminate in EC2__Launch__Helper so that
# halt causes termination, not stop.
# max_hours=0 emits a no-op comment (caller omits this section instead).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

TEMPLATE = '''
# ── Auto-terminate after {max_hours}h ({seconds}s) ───────────────────────────
systemd-run --on-active={seconds}s /sbin/shutdown -h now
echo "[ephemeral-ec2] auto-terminate timer set: {max_hours}h ({seconds}s) from now"
'''


class Section__Shutdown(Type_Safe):

    def render(self, max_hours: float = 1.0) -> str:
        seconds = max(1, int(round(max_hours * 3600)))
        return TEMPLATE.format(max_hours=max_hours, seconds=seconds)

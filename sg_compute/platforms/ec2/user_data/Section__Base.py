# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Section__Base
# Bash preamble: strict mode, logging, hostname, essential packages.
# Every stack user-data script starts with this section.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

LOG_FILE = '/var/log/ephemeral-ec2-boot.log'

# The timer block is rendered separately so Section__Base.render() can inject
# it before any failable work (L9: auto-terminate timer must precede all
# failable work — if dnf install aborts the script, the timer still fires).
_TIMER_BLOCK = '''\
# ── Auto-{action} after {max_hours}h ({seconds}s) — set BEFORE any failable work ──
systemd-run --on-active={seconds}s {shutdown_cmd}
echo "[ephemeral-ec2] auto-{action} timer set: {max_hours}h ({seconds}s) from now"
'''

# When InstanceInitiatedShutdownBehavior='stop' (vault-publish stacks), the
# timer calls aws ec2 stop-instances via IMDSv2 instead of halting the OS.
# IMDSv2 token first (required on all new AL2023 instances), then stop.
_STOP_CMD = (
    'bash -c \''
    'TOKEN=$(curl -s -X PUT http://169.254.169.254/latest/api/token '
    '-H "X-aws-ec2-metadata-token-ttl-seconds: 21600") && '
    'IID=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" '
    'http://169.254.169.254/latest/meta-data/instance-id) && '
    'REGION=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" '
    'http://169.254.169.254/latest/meta-data/placement/region) && '
    'aws ec2 stop-instances --instance-ids "$IID" --region "$REGION"\''
)
_HALT_CMD = '/sbin/shutdown -h now'

TEMPLATE = '''\
#!/usr/bin/env bash
set -euo pipefail
mkdir -p /var/lib
trap 'rc=$?; echo "[ephemeral-ec2] boot FAILED at line $LINENO (exit=$rc)"; touch /var/lib/sg-compute-boot-failed' ERR
exec > >(tee -a {log_file}) 2>&1
echo "[ephemeral-ec2] boot starting: {stack_name} at $(date -u +%FT%TZ)"
{timer_block}
hostnamectl set-hostname {stack_name} 2>/dev/null || true
dnf update -y -q
dnf install -y --allowerasing git curl jq unzip

# SSM agent ships on AL2023 — ensure it is running
systemctl enable --now amazon-ssm-agent 2>/dev/null || true

# Pre-create ssm-user so sections that write to /home/ssm-user/ never block.
# SSM Session Manager creates this user on the first interactive session; SSM
# SendCommand (used by `sg lc exec`) does NOT. Pre-creating ensures the boot
# script can install Claude Code config / sgit venv / etc. on any instance,
# regardless of whether anyone ever opens a Session Manager session.
id ssm-user >/dev/null 2>&1 || useradd ssm-user -m -d /home/ssm-user -s /bin/bash
# NOPASSWD sudo for ssm-user. The SSM agent normally writes this file ONLY on
# the first interactive Session Manager session — if ssm-user already exists
# (because we pre-created it above, or because it was baked into the AMI) the
# agent sees "already done" and skips it, leaving connect sessions without
# sudo. Writing it here is idempotent and survives AMI bakes.
cat > /etc/sudoers.d/ssm-agent-users <<'SUDOERS_EOF'
ssm-user ALL=(ALL) NOPASSWD:ALL
SUDOERS_EOF
chmod 440 /etc/sudoers.d/ssm-agent-users
echo "[ephemeral-ec2] ssm-user ensured (uid=$(id -u ssm-user)); NOPASSWD sudo granted"
'''


class Section__Base(Type_Safe):

    def render(self, stack_name: str, max_hours: float = 0.0,
               shutdown_behavior: str = 'terminate') -> str:
        if max_hours > 0:
            seconds      = max(1, int(round(max_hours * 3600)))
            shutdown_cmd = _STOP_CMD if shutdown_behavior == 'stop' else _HALT_CMD
            action       = 'stop' if shutdown_behavior == 'stop' else 'terminate'
            timer_block  = _TIMER_BLOCK.format(max_hours    = max_hours   ,
                                               seconds      = seconds     ,
                                               shutdown_cmd = shutdown_cmd ,
                                               action       = action      )
        else:
            timer_block = ''
        return TEMPLATE.format(stack_name=stack_name, log_file=LOG_FILE,
                               timer_block=timer_block)

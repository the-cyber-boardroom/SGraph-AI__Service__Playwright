# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Section__Claude_Code__Firstboot
# Bakes the Claude Code launcher, settings.json env block, and a vllm-status
# helper into ssm-user's home dir. Claude Code itself is NOT bundled — a systemd
# oneshot installs it from Anthropic's official installer on first boot so each
# user accepts the Anthropic terms directly (license-clean).
#
# Key env vars in settings.json (must live there, not in export — Lesson 4
# from the 2026-05-10 local-claude recipe):
#   CLAUDE_CODE_ATTRIBUTION_HEADER=0    — restores prefix caching (~90% speedup)
#   CLAUDE_CODE_DISABLE_1M_CONTEXT=1    — stops the "1M" badge lie
#   CONTEXT_WINDOW_OVERRIDE             — shows accurate /context percentage
#   CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=70  — fires compact at 70%, leaves room
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

_HEADER = '''\
# ── Claude Code firstboot config ─────────────────────────────────────────────
# ssm-user is pre-created in Section__Base; no wait needed.
dnf install -y tmux
echo '[sg-compute] writing Claude Code launcher and settings...'
mkdir -p /home/ssm-user/.claude /home/ssm-user/bin
'''

_SYSTEMD_UNIT = '''\
[Unit]
Description=Install Claude Code on first boot
ConditionPathExists=!/var/lib/claude-code-installed
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'su - ssm-user -c "curl -fsSL https://claude.ai/install.sh | bash" && touch /var/lib/claude-code-installed'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
'''

_FOOTER = '''\
chown -R ssm-user:ssm-user /home/ssm-user/.claude /home/ssm-user/bin \
  /home/ssm-user/local-llm-claude.sh 2>/dev/null || true
cat > /etc/systemd/system/claude-code-firstboot.service <<'UNIT_EOF'
''' + _SYSTEMD_UNIT + '''\
UNIT_EOF
systemctl daemon-reload
systemctl enable --now claude-code-firstboot.service
echo '[sg-compute] Claude Code firstboot service started'
'''


def _settings_block(max_model_len: int) -> str:
    return (
        "cat > /home/ssm-user/.claude/settings.json <<'SETTINGS_EOF'\n"
        "{\n"
        '  "theme": "auto",\n'
        '  "env": {\n'
        '    "CLAUDE_CODE_ATTRIBUTION_HEADER": "0",\n'
        '    "CLAUDE_CODE_DISABLE_1M_CONTEXT": "1",\n'
        f'    "CONTEXT_WINDOW_OVERRIDE": "{max_model_len}",\n'
        '    "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "70"\n'
        '  }\n'
        '}\n'
        'SETTINGS_EOF\n'
    )


def _launcher_block(served_model_name: str) -> str:
    return (
        "cat > /home/ssm-user/local-llm-claude.sh <<'LAUNCHER_EOF'\n"
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'export ANTHROPIC_BASE_URL="http://127.0.0.1:8000"\n'
        'export ANTHROPIC_API_KEY="dummy"\n'
        'export ANTHROPIC_AUTH_TOKEN="dummy"\n'
        f'export ANTHROPIC_MODEL="{served_model_name}"\n'
        f'export ANTHROPIC_DEFAULT_OPUS_MODEL="{served_model_name}"\n'
        f'export ANTHROPIC_DEFAULT_SONNET_MODEL="{served_model_name}"\n'
        f'export ANTHROPIC_DEFAULT_HAIKU_MODEL="{served_model_name}"\n'
        f'export ANTHROPIC_SMALL_FAST_MODEL="{served_model_name}"\n'
        "export CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1\n"
        "export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1\n"
        "export DISABLE_AUTOUPDATER=1\n"
        "export CLAUDE_CODE_DISABLE_OFFICIAL_MARKETPLACE_AUTOINSTALL=1\n"
        "export CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1\n"
        "export CLAUDE_CODE_MAX_OUTPUT_TOKENS=1024\n"
        'export PATH="$HOME/.local/bin:$HOME/.npm-global/bin:$HOME/bin:$PATH"\n'
        'exec claude "$@"\n'
        "LAUNCHER_EOF\n"
        "chmod +x /home/ssm-user/local-llm-claude.sh\n"
    )


def _status_block() -> str:
    # Regular string (not f-string) — Docker format uses {.Names} which conflicts
    # with Python f-string syntax. The single-quoted heredoc (<<'STATUS_EOF')
    # writes the content literally including the {{.Names}} Go template tokens.
    return (
        "cat > /home/ssm-user/bin/vllm-status.sh <<'STATUS_EOF'\n"
        "#!/usr/bin/env bash\n"
        "echo '=== Container ==='\n"
        "docker ps --filter name=vllm-claude-code"
        " --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}'\n"
        "echo\n"
        "echo '=== GPU ==='\n"
        "nvidia-smi --query-gpu=memory.used,memory.free,memory.total,utilization.gpu"
        " --format=csv,noheader\n"
        "echo\n"
        "echo '=== Model ==='\n"
        "curl -s http://127.0.0.1:8000/v1/models"
        " | jq -r '.data[0].id' 2>/dev/null || echo 'vLLM not responding'\n"
        "STATUS_EOF\n"
        "chmod +x /home/ssm-user/bin/vllm-status.sh\n"
    )


class Section__Claude_Code__Firstboot(Type_Safe):

    def render(self, served_model_name: str = 'local-coder',
                     max_model_len    : int = 65536         ) -> str:
        return (
            _HEADER
            + _settings_block(max_model_len)
            + _launcher_block(served_model_name)
            + _status_block()
            + _FOOTER
        )

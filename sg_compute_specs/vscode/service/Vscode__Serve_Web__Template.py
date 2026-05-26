# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vscode: Vscode__Serve_Web__Template
# The official `code serve-web` distribution (full MS marketplace — the
# feature-equivalent build). No official Docker image exists, so the official
# VS Code CLI is installed on the host and run under systemd, bound to loopback
# and tokenless — reached only via the SSM port-forward, exactly as
# local_claude runs vLLM on loopback (SSM/IAM is the security boundary).
# SSM_FORWARD mode only; the service guards serve-web + PUBLIC_HTTPS.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

VSCODE_CLI_URL = 'https://code.visualstudio.com/sha/download?build=stable&os=cli-linux-x64'

_TEMPLATE = '''
# ── VS Code serve-web (official build, full MS marketplace) ─────────────────────
echo "[ephemeral-ec2] installing the official VS Code CLI..."
mkdir -p /opt/vscode/cli /opt/vscode/serve-web
curl -fsSL "{cli_url}" -o /tmp/vscode-cli.tar.gz
tar -xzf /tmp/vscode-cli.tar.gz -C /opt/vscode/cli
cat > /etc/systemd/system/code-serve-web.service <<'VSCODE_SERVEWEB_UNIT_EOF'
[Unit]
Description=VS Code serve-web
After=network.target

[Service]
ExecStart=/opt/vscode/cli/code serve-web --host 127.0.0.1 --port {port} --without-connection-token --accept-server-license-terms --server-data-dir /opt/vscode/serve-web
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
VSCODE_SERVEWEB_UNIT_EOF
systemctl daemon-reload
systemctl enable --now code-serve-web
echo "[ephemeral-ec2] code serve-web started on 127.0.0.1:{port}"
'''


class Vscode__Serve_Web__Template(Type_Safe):

    def render(self, port: int) -> str:
        return _TEMPLATE.format(cli_url=VSCODE_CLI_URL, port=port)

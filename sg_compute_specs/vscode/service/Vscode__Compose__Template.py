# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vscode: Vscode__Compose__Template
# Renders the boot block that runs the VS Code server container, published on
# the instance loopback (127.0.0.1:{port}) so it is reachable only via the SSM
# port-forward — never exposed on a public interface in SSM_FORWARD mode.
# Slice 2 implements CODE_SERVER; OPENVSCODE_SERVER / SERVE_WEB land in Slice 5.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vscode.enums.Enum__Vscode__Distribution import Enum__Vscode__Distribution

CODE_SERVER_IMAGE = 'codercom/code-server:latest'

_CODE_SERVER_TEMPLATE = '''
# ── code-server (VS Code in the browser) ────────────────────────────────────────
echo "[ephemeral-ec2] starting code-server..."
mkdir -p /opt/vscode/project
chown -R 1000:1000 /opt/vscode/project
cat > /opt/vscode/.env <<'VSCODE_ENV_EOF'
PASSWORD={password}
VSCODE_ENV_EOF
chmod 600 /opt/vscode/.env
docker run -d --name code-server --restart unless-stopped \\
  -p 127.0.0.1:{port}:8080 \\
  --env-file /opt/vscode/.env \\
  -v /opt/vscode/project:/home/coder/project \\
  {image}
echo "[ephemeral-ec2] code-server started on 127.0.0.1:{port}"
'''


class Vscode__Compose__Template(Type_Safe):

    def render(self, distribution: Enum__Vscode__Distribution,
                     password    : str,
                     port        : int) -> str:
        if distribution == Enum__Vscode__Distribution.CODE_SERVER:
            return _CODE_SERVER_TEMPLATE.format(password=password,
                                                port=port,
                                                image=CODE_SERVER_IMAGE)
        raise NotImplementedError(
            f'distribution {distribution.value!r} not implemented yet '
            f'(CODE_SERVER only in Slice 2; serve-web/openvscode in Slice 5)')

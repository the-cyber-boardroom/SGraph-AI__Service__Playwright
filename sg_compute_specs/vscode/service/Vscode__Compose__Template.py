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

# code-server is always published on the instance loopback (127.0.0.1:{port}) so
# the SSM port-forward + health probe work identically in both ingress modes.
# In PUBLIC_HTTPS mode it ALSO joins {network} so the Caddy container can
# reverse-proxy to it by name (code-server:8080) — see Vscode__Caddy__Template.
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
  {network_flag}-p 127.0.0.1:{port}:8080 \\
  --env-file /opt/vscode/.env \\
  -v /opt/vscode/project:/home/coder/project \\
  {image}
echo "[ephemeral-ec2] code-server started on 127.0.0.1:{port}"
'''


class Vscode__Compose__Template(Type_Safe):

    def render(self, distribution: Enum__Vscode__Distribution,
                     password    : str,
                     port        : int,
                     network     : str = '') -> str:
        if distribution == Enum__Vscode__Distribution.CODE_SERVER:
            network_flag = f'--network {network} \\\n  ' if network else ''
            return _CODE_SERVER_TEMPLATE.format(password=password,
                                                port=port,
                                                image=CODE_SERVER_IMAGE,
                                                network_flag=network_flag)
        raise NotImplementedError(
            f'distribution {distribution.value!r} not implemented yet '
            f'(CODE_SERVER only in Slice 2; serve-web/openvscode in Slice 5)')

# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Sentinel__Docker__Runtime
# Manages the CF-environment simulation container (Target C): materialises the L1
# engine (BANNED_IPS inlined — same substitution the CF deployer performs) into a
# build context, builds the image, runs the container, and evaluates a captured
# request by POSTing it at the in-container HTTP listener (which shells the same
# node sentinel_l1.js). The container catches CF-runtime surprises before AWS.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
import shutil
import subprocess
import tempfile
import time

import requests

from osbot_utils.type_safe.Type_Safe                import Type_Safe
from osbot_utils.type_safe.primitives.core.Safe_Str import Safe_Str

from sgraph_ai_service_playwright__cli.sentinel.runtime.layer1.Sentinel__L1__Source import Sentinel__L1__Source


def docker_available() -> bool:                                                     # binary present AND daemon reachable
    if shutil.which('docker') is None:
        return False
    try:
        return subprocess.run(['docker', 'info'], capture_output=True, text=True, timeout=10).returncode == 0
    except Exception:
        return False


class Sentinel__Docker__Runtime(Type_Safe):
    image_tag      : Safe_Str = Safe_Str('sg-sentinel-l1')
    container_name : Safe_Str = Safe_Str('sg-sentinel-l1')
    port           : int      = 8599

    def docker_dir(self) -> str:
        return os.path.join(os.path.dirname(__file__), 'docker')

    def base_url(self) -> str:
        return f'http://127.0.0.1:{self.port}'

    def build_context(self) -> str:                                                 # temp dir: materialised engine + server + Dockerfile
        out = tempfile.mkdtemp(prefix='sg_sentinel_docker_')
        with open(os.path.join(out, 'sentinel_l1.js'), 'w') as fh:
            fh.write(Sentinel__L1__Source().materialised_source())
        for name in ('server.node.js', 'Dockerfile'):
            shutil.copy(os.path.join(self.docker_dir(), name), os.path.join(out, name))
        return out

    def build(self) -> None:
        ctx = self.build_context()
        try:
            self._run(['docker', 'build', '-t', str(self.image_tag), ctx])
        finally:
            shutil.rmtree(ctx, ignore_errors=True)

    def up(self) -> None:
        self.down()                                                                 # clear any stale container
        self.build()
        self._run(['docker', 'run', '-d', '--rm', '--name', str(self.container_name),
                   '-p', f'{self.port}:8080', str(self.image_tag)])
        self.wait_healthy()

    def wait_healthy(self, timeout_sec: int = 30) -> bool:
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            try:
                if requests.get(self.base_url() + '/health', timeout=2).status_code == 200:
                    return True
            except requests.RequestException:
                pass
            time.sleep(1)
        raise RuntimeError('sentinel docker container did not become healthy in time')

    def down(self) -> None:
        self._run(['docker', 'rm', '-f', str(self.container_name)], check=False)

    def evaluate(self, captured: dict) -> dict:                                      # POST captured → signal (via the container)
        resp = requests.post(self.base_url() + '/', data=json.dumps(captured), timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _run(self, cmd: list, check: bool = True) -> subprocess.CompletedProcess:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if check and proc.returncode != 0:
            raise RuntimeError(f'{" ".join(cmd[:3])} failed: {proc.stderr.strip()}')
        return proc

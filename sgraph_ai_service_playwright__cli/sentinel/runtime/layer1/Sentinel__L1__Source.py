# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Sentinel__L1__Source
# Owns the single-source L1 JS engine: reads sentinel_l1.js + rules.embedded.json,
# inlines BANNED_IPS (the same substitution the CloudFront deployer performs), and
# evaluates a captured request dict by shelling `node <materialised>.js '<json>'`.
#
# This is the one place node is invoked for L1; the local harness reuses it so the
# offline targets run the byte-identical engine that ships to CloudFront.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
import shutil
import subprocess
import tempfile

from osbot_utils.type_safe.Type_Safe                import Type_Safe
from osbot_utils.type_safe.primitives.core.Safe_Str import Safe_Str

_BANNED_MARKER = 'var BANNED_IPS = [];'


def node_available() -> bool:                                                        # gate for integration-tier tests
    return shutil.which('node') is not None


class Sentinel__L1__Source(Type_Safe):
    node_bin : Safe_Str = Safe_Str('node')

    def engine_path(self) -> str:
        return os.path.join(os.path.dirname(__file__), 'sentinel_l1.js')

    def rules_path(self) -> str:
        return os.path.join(os.path.dirname(__file__), 'rules.embedded.json')

    def raw_source(self) -> str:
        with open(self.engine_path(), 'r') as fh:
            return fh.read()

    def banned_ips(self) -> list:
        with open(self.rules_path(), 'r') as fh:
            return json.load(fh).get('banned_ips', [])

    def materialised_source(self) -> str:                                            # JS with BANNED_IPS inlined
        inlined = 'var BANNED_IPS = ' + json.dumps(self.banned_ips()) + ';'
        return self.raw_source().replace(_BANNED_MARKER, inlined)

    def materialised_path(self) -> str:                                              # write the runnable engine to a temp file
        out_dir = os.path.join(tempfile.gettempdir(), 'sg_sentinel')
        os.makedirs(out_dir, exist_ok=True)
        out = os.path.join(out_dir, 'sentinel_l1.materialised.js')
        with open(out, 'w') as fh:
            fh.write(self.materialised_source())
        return out

    def evaluate(self, captured: dict) -> dict:                                      # run the engine over one captured request
        proc = subprocess.run([str(self.node_bin), self.materialised_path(), json.dumps(captured)],
                              capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f'node L1 evaluate failed: {proc.stderr.strip()}')
        return json.loads(proc.stdout)

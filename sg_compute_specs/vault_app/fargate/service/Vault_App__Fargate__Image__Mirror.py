# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute_specs vault_app/fargate — Vault_App__Fargate__Image__Mirror
# Shells docker pull / tag / push to mirror a public image into ECR.
# _runner is injectable for tests (no mock/patch needed).
# Signature: (cmd: list) → (exit_code: int, stdout: str, stderr: str)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Vault_App__Fargate__Image__Mirror(Type_Safe):
    _runner : object = None                                                     # override in tests: (cmd) → (rc, stdout, stderr)

    def _run(self, cmd: list) -> tuple:                                         # (exit_code, stdout, stderr)
        if self._runner:
            return self._runner(cmd)
        import subprocess
        r = subprocess.run(cmd, capture_output=True, text=True)
        return r.returncode, r.stdout, r.stderr

    def mirror(self, source_image: str, ecr_uri: str) -> dict:                 # pull → tag → push → inspect → return result dict
        # source_image: e.g. 'diniscruz/sg-send-vault:latest'
        # ecr_uri:      e.g. '123456789012.dkr.ecr.eu-west-2.amazonaws.com/sg-send-vault'
        ecr_tagged = f'{ecr_uri}:latest'
        steps      = []

        def _step(cmd: list) -> bool:                                           # run one step; append to steps; return ok
            rc, stdout, stderr = self._run(cmd)
            steps.append({'cmd': cmd, 'rc': rc, 'stdout': stdout, 'stderr': stderr})
            return rc == 0

        if not _step(['docker', 'pull', source_image]):                        # step 1 — pull
            return {'ok': False, 'sha': '', 'steps': steps}

        if not _step(['docker', 'tag', source_image, ecr_tagged]):             # step 2 — tag
            return {'ok': False, 'sha': '', 'steps': steps}

        if not _step(['docker', 'push', ecr_tagged]):                          # step 3 — push
            return {'ok': False, 'sha': '', 'steps': steps}

        inspect_cmd = ['docker', 'inspect', '--format={{index .RepoDigests 0}}', ecr_tagged]
        if not _step(inspect_cmd):                                             # step 4 — get digest SHA
            return {'ok': False, 'sha': '', 'steps': steps}

        sha = steps[-1]['stdout'].strip()
        return {'ok': True, 'sha': sha, 'steps': steps}

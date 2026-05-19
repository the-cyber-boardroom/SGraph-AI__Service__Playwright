# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute_specs vault_app/fargate — Vault_App__Fargate__Image__Mirror
# Mirror a public image into ECR, with:
#   • idempotency check  — skip push if ECR already has `latest` and the local
#                          source manifest matches what's there
#   • auto docker login  — `aws ecr get-login-password | docker login` step 0
#                          (when region + registry are passed)
#   • streaming progress — fires step_cb(step_name, line) per stdout line so a
#                          live renderer can show docker layer activity
#   • per-step timings   — each step records duration_ms in the returned dict
#
# _runner still works for unit tests (cmd → (rc, stdout, stderr)).  When set,
# the streaming path is bypassed entirely.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import re
import shutil
import subprocess
import time

from osbot_utils.type_safe.Type_Safe import Type_Safe


_PROGRESS_NOISE_RE = re.compile(r'^[\s\d.]+$')                                    # filter pure-numeric progress lines


class Vault_App__Fargate__Image__Mirror(Type_Safe):
    _runner    : object = None                                                    # override in tests: (cmd) → (rc, stdout, stderr)
    step_cb    : object = None                                                    # callable(step_name, line) → None; line-level progress
    region     : str    = ''                                                      # AWS region; required for ecr login
    registry   : str    = ''                                                      # e.g. '123.dkr.ecr.eu-west-2.amazonaws.com'; required for ecr login
    ecr_client : object = None                                                    # if set, used for idempotency check (describe_image latest)
    force      : bool   = False                                                   # bypass idempotency check, always re-push

    # ── public entry point ────────────────────────────────────────────────────

    def mirror(self, source_image: str, ecr_uri: str) -> dict:                   # source_image: 'diniscruz/sg-send-vault:latest'; ecr_uri: '<registry>/<repo>'
        ecr_tagged = f'{ecr_uri}:latest'
        steps      = []

        # ── step 0: docker login (optional) ───────────────────────────────────
        if self.region and self.registry:
            self._emit('login', f'logging in to {self.registry}')
            if not self._ecr_login(steps):
                return {'ok': False, 'sha': '', 'steps': steps, 'skipped': False}

        # ── step 1: docker pull source ────────────────────────────────────────
        if not self._step(steps, 'pull', ['docker', 'pull', source_image]):
            return {'ok': False, 'sha': '', 'steps': steps, 'skipped': False}

        # ── step 1.5: idempotency check ───────────────────────────────────────
        repo_name = ecr_uri.rsplit('/', 1)[-1]
        if (not self.force) and self.ecr_client and self._already_in_ecr(
                steps, source_image, ecr_tagged, repo_name):
            return {'ok': True, 'sha': self._inspected_sha(steps),
                    'steps': steps, 'skipped': True}

        # ── step 2: docker tag ────────────────────────────────────────────────
        if not self._step(steps, 'tag', ['docker', 'tag', source_image, ecr_tagged]):
            return {'ok': False, 'sha': '', 'steps': steps, 'skipped': False}

        # ── step 3: docker push ───────────────────────────────────────────────
        if not self._step(steps, 'push', ['docker', 'push', ecr_tagged]):
            return {'ok': False, 'sha': '', 'steps': steps, 'skipped': False}

        # ── step 4: docker inspect (capture SHA) ──────────────────────────────
        inspect_cmd = ['docker', 'inspect', '--format={{index .RepoDigests 0}}', ecr_tagged]
        if not self._step(steps, 'inspect', inspect_cmd):
            return {'ok': False, 'sha': '', 'steps': steps, 'skipped': False}

        return {'ok': True, 'sha': self._inspected_sha(steps),
                'steps': steps, 'skipped': False}

    # ── idempotency check ─────────────────────────────────────────────────────

    def _already_in_ecr(self, steps: list, source_image: str,
                        ecr_tagged: str, repo_name: str) -> bool:                # True if ECR `latest` matches local source content
        try:
            existing = self.ecr_client.describe_image(repo_name, 'latest')
        except Exception:
            return False
        if not existing:
            return False

        # Compare local source's config digest vs what ECR has by pulling the
        # ECR tag locally — if all layers are already present (we just pulled
        # source), this is near-instant. Then compare image .Id (config digest).
        rc, ecr_local_id, _ = self._run_capture(
            ['docker', 'pull', ecr_tagged]
        )
        if rc != 0:                                                                # ECR pull failed (auth/network) — fall through to push
            return False

        rc1, source_id, _ = self._run_capture(
            ['docker', 'inspect', '--format={{.Id}}', source_image])
        rc2, ecr_id, _    = self._run_capture(
            ['docker', 'inspect', '--format={{.Id}}', ecr_tagged])
        if rc1 != 0 or rc2 != 0:
            return False

        source_id = source_id.strip()
        ecr_id    = ecr_id.strip()
        if source_id and source_id == ecr_id:
            self._emit('skip', f'ECR latest already matches source ({source_id[:19]})')
            steps.append({
                'step'       : 'skip',
                'cmd'        : ['<idempotency-check>'],
                'rc'         : 0,
                'stdout'     : f'source={source_id} ecr={ecr_id}',
                'stderr'     : '',
                'duration_ms': 0,
            })
            # Also record an inspect-style entry so callers find the SHA.
            sha = str(existing.digest or '')
            steps.append({
                'step'       : 'inspect',
                'cmd'        : ['<ecr-describe-image>'],
                'rc'         : 0,
                'stdout'     : sha,
                'stderr'     : '',
                'duration_ms': 0,
            })
            return True
        return False

    # ── ECR login (step 0) ────────────────────────────────────────────────────

    def _ecr_login(self, steps: list) -> bool:
        started = time.monotonic()
        if self._runner is None and shutil.which('aws') is None:                  # production path with no aws CLI → skip with warning
            steps.append({
                'step'       : 'login',
                'cmd'        : ['aws', 'ecr', 'get-login-password'],
                'rc'         : 0,
                'stdout'     : '',
                'stderr'     : 'aws CLI not found — skipping auto docker login',
                'duration_ms': int((time.monotonic() - started) * 1000),
            })
            self._emit('login', 'aws CLI not found — skipping auto login')
            return True                                                            # proceed; subsequent push will fail loudly if not pre-authed
        rc1, token, err1 = self._run_capture(
            ['aws', 'ecr', 'get-login-password', '--region', self.region])
        if rc1 != 0:
            steps.append({'step': 'login', 'cmd': ['aws', 'ecr', 'get-login-password'],
                          'rc': rc1, 'stdout': '', 'stderr': err1,
                          'duration_ms': int((time.monotonic() - started) * 1000)})
            return False

        login_cmd = ['docker', 'login', '--username', 'AWS',
                     '--password-stdin', self.registry]
        if self._runner:                                                          # test path — runner handles login as a plain command
            rc, out, err = self._runner(login_cmd)
        else:
            proc = subprocess.Popen(
                login_cmd,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True,
            )
            out, err = proc.communicate(token, timeout=30)
            rc = proc.returncode
        steps.append({
            'step'       : 'login',
            'cmd'        : login_cmd,
            'rc'         : rc,
            'stdout'     : (out or '').strip(),
            'stderr'     : (err or '').strip(),
            'duration_ms': int((time.monotonic() - started) * 1000),
        })
        if rc == 0:
            self._emit('login', 'login succeeded')
        return rc == 0

    # ── single docker step (streaming when no _runner) ────────────────────────

    def _step(self, steps: list, name: str, cmd: list) -> bool:                   # run + record + emit lines; returns ok
        started = time.monotonic()
        if self._runner:                                                          # test path — capture-only, no streaming
            rc, stdout, stderr = self._runner(cmd)
            for line in (stdout + stderr).splitlines():
                line = line.strip()
                if line:
                    self._emit(name, line)
            elapsed_ms = int((time.monotonic() - started) * 1000)
        else:
            rc, stdout, stderr, elapsed_ms = self._run_streaming(cmd, name)

        steps.append({
            'step'       : name,
            'cmd'        : cmd,
            'rc'         : rc,
            'stdout'     : stdout,
            'stderr'     : stderr,
            'duration_ms': elapsed_ms,
        })
        return rc == 0

    def _run_streaming(self, cmd: list, step_name: str) -> tuple:                 # (rc, stdout, stderr, elapsed_ms)
        started = time.monotonic()
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, bufsize=0)
        buf = b''
        captured = []
        try:
            while True:
                chunk = proc.stdout.read(256)
                if not chunk:
                    break
                buf += chunk
                buf = self._consume_lines(buf, step_name, captured)
        finally:
            proc.wait()
        if buf:                                                                   # flush trailing partial line
            self._consume_lines(buf + b'\n', step_name, captured)
        elapsed_ms = int((time.monotonic() - started) * 1000)
        return proc.returncode, '\n'.join(captured), '', elapsed_ms

    def _consume_lines(self, buf: bytes, step_name: str, captured: list) -> bytes:
        text  = buf.decode('utf-8', errors='replace')
        parts = re.split(r'[\r\n]', text)                                         # docker push uses \r for layer progress
        remainder = parts[-1].encode('utf-8')
        for line in parts[:-1]:
            line = line.strip()
            if not line or _PROGRESS_NOISE_RE.match(line):
                continue
            captured.append(line)
            self._emit(step_name, line)
        return remainder

    def _run_capture(self, cmd: list) -> tuple:                                   # blocking capture — used for fast auxiliary calls
        if self._runner:
            return self._runner(cmd)
        r = subprocess.run(cmd, capture_output=True, text=True)
        return r.returncode, r.stdout, r.stderr

    # ── progress emit ─────────────────────────────────────────────────────────

    def _emit(self, step_name: str, line: str) -> None:
        if self.step_cb:
            try:
                self.step_cb(step_name, line)
            except Exception:                                                     # never let callback errors break the mirror
                pass

    # ── helpers ───────────────────────────────────────────────────────────────

    def _inspected_sha(self, steps: list) -> str:
        for s in reversed(steps):
            if s.get('step') == 'inspect' and s.get('rc') == 0:
                return (s.get('stdout') or '').strip()
        return ''

# ═══════════════════════════════════════════════════════════════════════════════
# tests/unit — test_Vault_App__Fargate__Image__Mirror
# Covers: mirror happy path, pull failure, sha extraction, steps recording.
# All tests use a _runner stub — no real docker calls.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute_specs.vault_app.fargate.service.Vault_App__Fargate__Image__Mirror import Vault_App__Fargate__Image__Mirror

_SOURCE   = 'diniscruz/sg-send-vault:latest'
_ECR_URI  = '123456789012.dkr.ecr.eu-west-2.amazonaws.com/sg-send-vault'
_ECR_TAG  = f'{_ECR_URI}:latest'
_SHA      = 'sha256:abc123def456'


def _success_runner(cmd: list) -> tuple:
    """Stub that succeeds all steps; returns SHA on inspect."""
    last = cmd[-1] if cmd else ''
    if 'inspect' in cmd:
        return 0, _SHA + '\n', ''
    return 0, '', ''


def _fail_on_pull(cmd: list) -> tuple:
    if cmd and cmd[1] == 'pull':
        return 1, '', 'Error: pull access denied'
    return 0, '', ''


def _fail_on_push(cmd: list) -> tuple:
    if cmd and cmd[1] == 'push':
        return 1, '', 'Error: push failed'
    return 0, '', ''


class test_Vault_App__Fargate__Image__Mirror(TestCase):

    def setUp(self):
        self.mirror = Vault_App__Fargate__Image__Mirror(_runner=_success_runner)

    # ── happy path ───────────────────────────────────────────────────────────

    def test_mirror_ok_when_all_steps_succeed(self):
        result = self.mirror.mirror(_SOURCE, _ECR_URI)
        assert result['ok'] is True

    def test_mirror_sha_extracted(self):
        result = self.mirror.mirror(_SOURCE, _ECR_URI)
        assert result['sha'] == _SHA

    def test_mirror_steps_contains_four_entries(self):
        result = self.mirror.mirror(_SOURCE, _ECR_URI)
        assert len(result['steps']) == 4

    def test_mirror_steps_first_is_pull(self):
        result = self.mirror.mirror(_SOURCE, _ECR_URI)
        assert 'pull' in result['steps'][0]['cmd']

    def test_mirror_steps_second_is_tag(self):
        result = self.mirror.mirror(_SOURCE, _ECR_URI)
        assert 'tag' in result['steps'][1]['cmd']

    def test_mirror_steps_third_is_push(self):
        result = self.mirror.mirror(_SOURCE, _ECR_URI)
        assert 'push' in result['steps'][2]['cmd']

    def test_mirror_steps_fourth_is_inspect(self):
        result = self.mirror.mirror(_SOURCE, _ECR_URI)
        assert 'inspect' in result['steps'][3]['cmd']

    def test_mirror_all_steps_rc_zero_on_success(self):
        result = self.mirror.mirror(_SOURCE, _ECR_URI)
        for step in result['steps']:
            assert step['rc'] == 0

    def test_mirror_tag_uses_ecr_uri_latest(self):
        result = self.mirror.mirror(_SOURCE, _ECR_URI)
        tag_step = result['steps'][1]
        assert _ECR_TAG in tag_step['cmd']

    # ── pull failure ─────────────────────────────────────────────────────────

    def test_mirror_not_ok_when_pull_fails(self):
        mirror = Vault_App__Fargate__Image__Mirror(_runner=_fail_on_pull)
        result = mirror.mirror(_SOURCE, _ECR_URI)
        assert result['ok'] is False

    def test_mirror_sha_empty_when_pull_fails(self):
        mirror = Vault_App__Fargate__Image__Mirror(_runner=_fail_on_pull)
        result = mirror.mirror(_SOURCE, _ECR_URI)
        assert result['sha'] == ''

    def test_mirror_stops_after_pull_failure(self):
        mirror = Vault_App__Fargate__Image__Mirror(_runner=_fail_on_pull)
        result = mirror.mirror(_SOURCE, _ECR_URI)
        assert len(result['steps']) == 1                                        # only pull was run

    # ── new fields on result ─────────────────────────────────────────────────

    def test_mirror_result_has_skipped_false_on_normal_push(self):
        result = self.mirror.mirror(_SOURCE, _ECR_URI)
        assert result['skipped'] is False

    def test_mirror_result_includes_per_step_duration(self):
        result = self.mirror.mirror(_SOURCE, _ECR_URI)
        for step in result['steps']:
            assert 'duration_ms' in step
            assert isinstance(step['duration_ms'], int)

    def test_mirror_step_cb_fires_for_each_step(self):                          # step_cb gets (step_name, line) per stdout/stderr line
        events = []
        def cb(step_name, line):
            events.append((step_name, line))
        # _success_runner returns SHA on inspect, empty otherwise → only inspect emits
        mirror = Vault_App__Fargate__Image__Mirror(_runner=_success_runner, step_cb=cb)
        mirror.mirror(_SOURCE, _ECR_URI)
        # The inspect step's stdout is captured; cb should fire at least once
        inspect_events = [e for e in events if e[0] == 'inspect']
        assert len(inspect_events) >= 1

    # ── idempotency (skip when ECR already has matching content) ─────────────

    def test_mirror_skipped_when_ecr_matches_local_source(self):
        from osbot_utils.type_safe.Type_Safe import Type_Safe

        class _FakeImage(Type_Safe):
            digest: str = 'sha256:cached123'

        class _FakeEcrClient:
            def describe_image(self, repo, tag):
                return _FakeImage()

        # runner returns identical image .Id for both `docker inspect .Id`
        # calls (source + ecr_tagged) → idempotency check passes → skipped.
        def runner(cmd):
            if 'inspect' in cmd and '--format={{.Id}}' in cmd:
                return (0, 'sha256:same-id-for-both\n', '')
            if 'inspect' in cmd:                                                 # final inspect for SHA (not reached when skipped)
                return (0, _SHA + '\n', '')
            return (0, '', '')                                                   # pull, push, ecr-pull all OK

        mirror = Vault_App__Fargate__Image__Mirror(
            _runner=runner, ecr_client=_FakeEcrClient())
        result = mirror.mirror(_SOURCE, _ECR_URI)
        assert result['ok']      is True
        assert result['skipped'] is True

    def test_mirror_not_skipped_when_force_true(self):
        from osbot_utils.type_safe.Type_Safe import Type_Safe

        class _FakeImage(Type_Safe):
            digest: str = 'sha256:cached123'

        class _FakeEcrClient:
            def describe_image(self, repo, tag):
                return _FakeImage()

        def runner(cmd):
            if 'inspect' in cmd and '--format={{.Id}}' in cmd:
                return (0, 'sha256:same-id-for-both\n', '')
            if 'inspect' in cmd:
                return (0, _SHA + '\n', '')
            return (0, '', '')

        mirror = Vault_App__Fargate__Image__Mirror(
            _runner=runner, ecr_client=_FakeEcrClient(), force=True)
        result = mirror.mirror(_SOURCE, _ECR_URI)
        assert result['skipped'] is False                                        # forced re-push, not skipped

    # ── push failure ─────────────────────────────────────────────────────────

    def test_mirror_not_ok_when_push_fails(self):
        mirror = Vault_App__Fargate__Image__Mirror(_runner=_fail_on_push)
        result = mirror.mirror(_SOURCE, _ECR_URI)
        assert result['ok'] is False

    def test_mirror_stops_after_push_failure(self):
        mirror = Vault_App__Fargate__Image__Mirror(_runner=_fail_on_push)
        result = mirror.mirror(_SOURCE, _ECR_URI)
        assert len(result['steps']) == 3                                        # pull + tag + push(failed)

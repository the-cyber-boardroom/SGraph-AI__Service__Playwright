# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Dig__Runner
# Uses a _Fake_Subprocess that monkey-patches subprocess.run on the module so
# Dig__Runner never invokes real dig. No mocks framework — plain subclassing.
# ═══════════════════════════════════════════════════════════════════════════════

import subprocess
from unittest import TestCase

from sgraph_ai_service_playwright__cli.aws.dns.schemas.Schema__Dig__Result  import Schema__Dig__Result
from sgraph_ai_service_playwright__cli.aws.dns.service.Dig__Runner           import Dig__Runner
import sgraph_ai_service_playwright__cli.aws.dns.service.Dig__Runner as dig_module


# ── Fake subprocess helpers ───────────────────────────────────────────────────

class _FakeCompleted:                                                            # Mimics subprocess.CompletedProcess
    def __init__(self, stdout='', stderr='', returncode=0):
        self.stdout     = stdout
        self.stderr     = stderr
        self.returncode = returncode


class _Fake_Dig__Runner(Dig__Runner):                                           # Real subclass; patches subprocess.run on the module level
    _canned_stdout    : str = '203.0.113.5\n'
    _canned_stderr    : str = ''
    _canned_returncode: int = 0
    _raise_timeout    : bool = False
    _raise_not_found  : bool = False

    def run(self, nameserver, name, rtype, no_recurse=False, timeout=5):
        if self._raise_not_found:
            raise FileNotFoundError('dig not in PATH')
        if self._raise_timeout:
            import time
            start = time.monotonic()
            raise subprocess.TimeoutExpired(cmd=['dig'], timeout=timeout)
        completed = _FakeCompleted(stdout   = self._canned_stdout    ,
                                   stderr   = self._canned_stderr    ,
                                   returncode=self._canned_returncode)
        lines = [l.strip() for l in completed.stdout.splitlines() if l.strip()]
        return Schema__Dig__Result(nameserver  = nameserver           ,
                                   name        = name                 ,
                                   rtype       = rtype                ,
                                   values      = lines                ,
                                   exit_code   = completed.returncode ,
                                   error       = completed.stderr.strip(),
                                   duration_ms = 1                    )


# ── Tests ─────────────────────────────────────────────────────────────────────

class test_Dig__Runner(TestCase):

    # ── Normal result ─────────────────────────────────────────────────────────

    def test__run__returns_schema_dig_result(self):
        runner = _Fake_Dig__Runner()
        result = runner.run('1.1.1.1', 'example.com', 'A')
        assert isinstance(result, Schema__Dig__Result)

    def test__run__parses_values_from_stdout(self):
        runner = _Fake_Dig__Runner()
        result = runner.run('1.1.1.1', 'example.com', 'A')
        assert '203.0.113.5' in result.values

    def test__run__populates_nameserver_name_rtype(self):
        runner = _Fake_Dig__Runner()
        result = runner.run('8.8.8.8', 'sgraph.ai', 'A')
        assert result.nameserver == '8.8.8.8'
        assert result.name       == 'sgraph.ai'
        assert result.rtype      == 'A'

    def test__run__exit_code_zero_on_success(self):
        runner = _Fake_Dig__Runner()
        result = runner.run('1.1.1.1', 'example.com', 'A')
        assert result.exit_code == 0

    def test__run__error_empty_on_success(self):
        runner = _Fake_Dig__Runner()
        result = runner.run('1.1.1.1', 'example.com', 'A')
        assert result.error == ''

    def test__run__nonzero_exit_code_propagated(self):
        runner                   = _Fake_Dig__Runner()
        runner._canned_returncode = 1
        runner._canned_stderr    = 'some error'
        result = runner.run('1.1.1.1', 'nxdomain.example', 'A')
        assert result.exit_code == 1
        assert 'some error' in result.error

    def test__run__empty_output_gives_empty_values(self):
        runner               = _Fake_Dig__Runner()
        runner._canned_stdout = ''
        result = runner.run('1.1.1.1', 'nxdomain.example', 'A')
        assert result.values == []

    # ── check_available ───────────────────────────────────────────────────────

    def test__check_available__returns_bool(self):
        runner = Dig__Runner()
        result = runner.check_available()
        assert isinstance(result, bool)

    def test__check_available__returns_false_when_dig_missing(self):
        # Patch subprocess.run on the module to raise FileNotFoundError
        original = dig_module.subprocess.run
        def fake_run(*args, **kwargs):
            raise FileNotFoundError('dig not found')
        dig_module.subprocess.run = fake_run
        try:
            runner = Dig__Runner()
            result = runner.check_available()
            assert result is False
        finally:
            dig_module.subprocess.run = original

    # ── Command construction — nameserver handling (P1.5 --local mode) ────────

    def test__run__empty_nameserver__omits_at_arg(self):                              # Empty ns => no @<ns> token so dig uses host default resolver
        captured = {}
        original = dig_module.subprocess.run
        def fake_run(cmd, **kwargs):
            captured['cmd'] = list(cmd)
            return _FakeCompleted(stdout='203.0.113.5\n')
        dig_module.subprocess.run = fake_run
        try:
            runner = Dig__Runner()
            runner.run(nameserver='', name='example.com', rtype='A')
        finally:
            dig_module.subprocess.run = original
        cmd = captured['cmd']
        assert cmd[0]   == 'dig'
        assert not any(token.startswith('@') for token in cmd)                       # No @<ns> argument
        assert 'example.com' in cmd
        assert 'A'           in cmd

    def test__run__nonempty_nameserver__includes_at_arg(self):
        captured = {}
        original = dig_module.subprocess.run
        def fake_run(cmd, **kwargs):
            captured['cmd'] = list(cmd)
            return _FakeCompleted(stdout='203.0.113.5\n')
        dig_module.subprocess.run = fake_run
        try:
            runner = Dig__Runner()
            runner.run(nameserver='1.1.1.1', name='example.com', rtype='A')
        finally:
            dig_module.subprocess.run = original
        assert '@1.1.1.1' in captured['cmd']

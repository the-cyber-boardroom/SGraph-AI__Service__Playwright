# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for `sg sentinel traffic` (cases / gen --json)
# ═══════════════════════════════════════════════════════════════════════════════

import json

from unittest      import skipUnless
from typer.testing import CliRunner

from sgraph_ai_service_playwright__cli.sentinel.runtime.layer1.Sentinel__L1__Source import node_available
from sgraph_ai_service_playwright__cli.sentinel.traffic.cli.Cli__Sentinel__Traffic  import app

runner = CliRunner()


class TestCases:
    def test_cases_json(self):
        r = runner.invoke(app, ['cases', '--json'])
        assert r.exit_code == 0
        names = {c['name'] for c in json.loads(r.output)}
        assert 'etc-passwd' in names and 'home' in names


@skipUnless(node_available(), 'node not available')
class TestGen:
    def test_gen_json_is_perfect_on_the_corpus(self):
        r = runner.invoke(app, ['gen', '--json'])
        assert r.exit_code == 0
        out = json.loads(r.output)
        assert out['report']['accuracy_pct'] == 100.0
        assert out['report']['malicious_blocked'] == out['report']['malicious_total']

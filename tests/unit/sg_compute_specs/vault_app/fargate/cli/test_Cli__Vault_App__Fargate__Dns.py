# ═══════════════════════════════════════════════════════════════════════════════
# Tests — test_Cli__Vault_App__Fargate__Dns
# Covers two related slices:
#   1. `fargate stop` deletes the DNS record stamped by `start` via the
#      VaultApp__DnsFqdn task tag (best-effort, idempotent).
#   2. `fargate dns list` / `fargate dns prune` surface orphan A records that
#      no longer have a matching running task.
# Uses Typer CliRunner + in-memory clients injected via ctx.obj.
# No mocks. No patches.
# ═══════════════════════════════════════════════════════════════════════════════

import json

from typer.testing import CliRunner

from sg_compute_specs.vault_app.fargate.cli.Cli__Vault_App__Fargate import app as fargate_app
from sg_compute_specs.vault_app.fargate.service.Vault_App__Fargate__Health  import Vault_App__Fargate__Health

from tests.unit.sgraph_ai_service_playwright__cli.aws.dns.service.Route53__AWS__Client__In_Memory   import Route53__AWS__Client__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client__In_Memory       import EC2__AWS__Client__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.aws.fargate.service.Fargate__AWS__Client__In_Memory import Fargate__AWS__Client__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.aws.logs.service.Logs__AWS__Client__In_Memory     import Logs__AWS__Client__In_Memory

runner    = CliRunner()
_GATE_ENV = 'SG_VAULT_APP__FARGATE__ALLOW_MUTATIONS'
_ZONE     = 'sg-compute.sgraph.ai'


# ── shared helpers ────────────────────────────────────────────────────────────

def _healthy_http(url, headers):
    return 200, True


def _seeded_fargate(dns_zone_tag: str = _ZONE) -> Fargate__AWS__Client__In_Memory:
    fargate = Fargate__AWS__Client__In_Memory()
    fargate.seed_cluster_with_tags('test-cluster', {
        'Stack'                  : 'sg-vault-app-fargate',
        'VaultApp__Subnets'      : 'subnet-aaa',
        'VaultApp__SecurityGroup': 'sg-xxx',
        'VaultApp__LogGroup'     : '/ecs/vault-app',
        'VaultApp__DnsZone'      : dns_zone_tag,
    })
    fargate.register_task_definition(
        name='vault-app', image='ecr.io/sg-send-vault:latest', cpu='512', memory='1024')
    return fargate


def _seeded_route53(records: dict = None) -> Route53__AWS__Client__In_Memory:       # records: {name: [ip,...]} A records under _ZONE
    r53 = Route53__AWS__Client__In_Memory()
    r53.seed_zone(_ZONE)
    for name, ips in (records or {}).items():
        r53.seed_record(_ZONE, name, values=ips)
    return r53


def _obj(fargate=None, route53=None):
    return {
        'fargate_client': fargate or _seeded_fargate(),
        'route53_client': route53 or _seeded_route53(),
        'logs_client'   : Logs__AWS__Client__In_Memory(),
        'ec2_client'    : EC2__AWS__Client__In_Memory(),
        'health'        : Vault_App__Fargate__Health(_http_get=_healthy_http, timeout_seconds=1),
    }


# ════════════════════════════════════════════════════════════════════════════════
# fargate stop — DNS cleanup behaviour (Deliverable 2)
# ════════════════════════════════════════════════════════════════════════════════

class Test__Stop_DNS_Cleanup:

    def test_1__stop_deletes_dns_record_when_fqdn_tag_present(self, monkeypatch):
        monkeypatch.setenv(_GATE_ENV, '1')
        fargate = _seeded_fargate()
        fqdn    = f'my-vault.{_ZONE}'
        fargate.seed_task_with_tags('test-cluster', {
            'VaultApp__Slug'    : 'my-vault',
            'VaultApp__DnsFqdn' : fqdn,
        })
        r53 = _seeded_route53({fqdn: ['18.130.45.12']})
        assert r53.record_exists(_ZONE, fqdn) is True

        result = runner.invoke(
            fargate_app,
            ['stop', '--slug', 'my-vault', '--cluster', 'test-cluster', '--yes', '--json'],
            obj=_obj(fargate=fargate, route53=r53),
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data['stopped']    is True
        assert data['dns_fqdn']   == fqdn
        assert data['dns_status'] == 'Deleted DNS record'
        # Contract assertion — the record is gone from the route53 store.
        assert r53.record_exists(_ZONE, fqdn) is False

    def test_2__stop_skips_dns_when_no_fqdn_tag(self, monkeypatch):
        monkeypatch.setenv(_GATE_ENV, '1')
        fargate = _seeded_fargate()
        fargate.seed_task_with_tags('test-cluster', {'VaultApp__Slug': 'plain-vault'})

        result = runner.invoke(
            fargate_app,
            ['stop', '--slug', 'plain-vault', '--cluster', 'test-cluster', '--yes', '--json'],
            obj=_obj(fargate=fargate),
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data['dns_fqdn']   == ''
        assert data['dns_status'] == 'no DNS record'

    def test_3__stop_handles_missing_record_gracefully(self, monkeypatch):
        monkeypatch.setenv(_GATE_ENV, '1')
        # Tag is present but the actual A record is already gone — stop must not fail.
        fargate = _seeded_fargate()
        fqdn    = f'gone-vault.{_ZONE}'
        fargate.seed_task_with_tags('test-cluster', {
            'VaultApp__Slug'    : 'gone-vault',
            'VaultApp__DnsFqdn' : fqdn,
        })
        r53 = _seeded_route53()                                                      # zone exists, record absent

        result = runner.invoke(
            fargate_app,
            ['stop', '--slug', 'gone-vault', '--cluster', 'test-cluster', '--yes', '--json'],
            obj=_obj(fargate=fargate, route53=r53),
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data['stopped']    is True
        assert data['dns_status'] == 'DNS record already absent'


# ════════════════════════════════════════════════════════════════════════════════
# fargate dns list — Deliverable 3
# ════════════════════════════════════════════════════════════════════════════════

class Test__Dns_List:

    def test_1__list_returns_only_slug_shaped_records(self):
        fargate = _seeded_fargate()                                                  # no tasks → every record is orphan
        r53     = _seeded_route53({
            f'brave-curie.{_ZONE}'   : ['1.1.1.1'],                                  # slug-shaped → included
            f'random-foo-bar.{_ZONE}': ['2.2.2.2'],                                  # 3 alpha segments → fails pattern → excluded
            f'mail.{_ZONE}'          : ['3.3.3.3'],                                  # single label → excluded
        })
        result = runner.invoke(
            fargate_app,
            ['dns', 'list', '--zone', _ZONE, '--json'],
            obj=_obj(fargate=fargate, route53=r53),
        )
        assert result.exit_code == 0, result.output
        data  = json.loads(result.output)
        slugs = sorted(row['slug'] for row in data)
        assert slugs == ['brave-curie']

    def test_2__list_marks_orphan_when_no_running_task(self):
        fargate = _seeded_fargate()                                                  # no tasks
        r53     = _seeded_route53({f'lonely-bohr.{_ZONE}': ['1.2.3.4']})
        result  = runner.invoke(
            fargate_app,
            ['dns', 'list', '--zone', _ZONE, '--json'],
            obj=_obj(fargate=fargate, route53=r53),
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]['slug']   == 'lonely-bohr'
        assert data[0]['status'] == 'orphan'

    def test_3__list_marks_running_when_task_exists(self):
        fargate = _seeded_fargate()
        fargate.seed_task_with_tags('test-cluster', {'VaultApp__Slug': 'live-curie'})
        r53 = _seeded_route53({f'live-curie.{_ZONE}': ['5.6.7.8']})
        result = runner.invoke(
            fargate_app,
            ['dns', 'list', '--zone', _ZONE, '--json'],
            obj=_obj(fargate=fargate, route53=r53),
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data[0]['slug']   == 'live-curie'
        assert data[0]['status'] == 'RUNNING'

    def test_4__list_resolves_zone_from_cluster_tag(self):
        fargate = _seeded_fargate()                                                  # cluster carries VaultApp__DnsZone tag
        r53     = _seeded_route53({f'tagged-bohr.{_ZONE}': ['9.9.9.9']})
        result  = runner.invoke(
            fargate_app,
            ['dns', 'list', '--json'],                                               # no --zone → must auto-resolve
            obj=_obj(fargate=fargate, route53=r53),
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data[0]['slug'] == 'tagged-bohr'


# ════════════════════════════════════════════════════════════════════════════════
# fargate dns prune — Deliverable 3
# ════════════════════════════════════════════════════════════════════════════════

class Test__Dns_Prune:

    def test_1__prune_deletes_orphans(self, monkeypatch):
        monkeypatch.setenv(_GATE_ENV, '1')
        fargate = _seeded_fargate()                                                  # no tasks → all records are orphan
        fqdn    = f'orphan-bohr.{_ZONE}'
        r53     = _seeded_route53({fqdn: ['1.2.3.4']})
        assert r53.record_exists(_ZONE, fqdn) is True

        result = runner.invoke(
            fargate_app,
            ['dns', 'prune', '--zone', _ZONE, '--yes', '--json'],
            obj=_obj(fargate=fargate, route53=r53),
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data['dry_run'] is False
        assert len(data['deleted']) == 1
        assert data['deleted'][0]['fqdn'] == fqdn
        assert r53.record_exists(_ZONE, fqdn) is False

    def test_2__prune_dry_run_deletes_nothing(self, monkeypatch):
        monkeypatch.delenv(_GATE_ENV, raising=False)                                 # dry-run bypasses the mutation gate
        fargate = _seeded_fargate()
        fqdn    = f'orphan-curie.{_ZONE}'
        r53     = _seeded_route53({fqdn: ['1.2.3.4']})

        result = runner.invoke(
            fargate_app,
            ['dns', 'prune', '--zone', _ZONE, '--dry-run', '--json'],
            obj=_obj(fargate=fargate, route53=r53),
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data['dry_run'] is True
        assert data['deleted'] == []
        assert len(data['orphans']) == 1
        assert r53.record_exists(_ZONE, fqdn) is True                                # untouched

    def test_3__prune_skips_running_records(self, monkeypatch):
        monkeypatch.setenv(_GATE_ENV, '1')
        fargate = _seeded_fargate()
        fargate.seed_task_with_tags('test-cluster', {'VaultApp__Slug': 'alive-curie'})
        fqdn = f'alive-curie.{_ZONE}'
        r53  = _seeded_route53({fqdn: ['1.2.3.4']})

        result = runner.invoke(
            fargate_app,
            ['dns', 'prune', '--zone', _ZONE, '--yes', '--json'],
            obj=_obj(fargate=fargate, route53=r53),
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data['orphans'] == []
        assert data['deleted'] == []
        assert r53.record_exists(_ZONE, fqdn) is True

    def test_4__prune_blocked_without_gate(self, monkeypatch):
        monkeypatch.delenv(_GATE_ENV, raising=False)
        fargate = _seeded_fargate()
        r53     = _seeded_route53({f'orphan-bohr.{_ZONE}': ['1.2.3.4']})
        result  = runner.invoke(
            fargate_app,
            ['dns', 'prune', '--zone', _ZONE, '--yes', '--json'],
            obj=_obj(fargate=fargate, route53=r53),
        )
        assert result.exit_code == 1
        assert _GATE_ENV in result.output


# ════════════════════════════════════════════════════════════════════════════════
# parent app integration
# ════════════════════════════════════════════════════════════════════════════════

class Test__Fargate_App_Has_Dns_Group:

    def test_1__fargate_app_mounts_dns_typer(self):
        names = [g.name for g in getattr(fargate_app, 'registered_groups', [])]
        assert 'dns' in names

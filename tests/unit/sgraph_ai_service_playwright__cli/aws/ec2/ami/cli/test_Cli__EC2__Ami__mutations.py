# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__EC2__Ami mutating commands
# CLI tests for `sg aws ec2 ami delete` via Typer CliRunner. No mocks, no
# patches — the in-memory client is injected via ctx.obj. Each test that
# should reach the command body sets SG_AWS__EC2__ALLOW_MUTATIONS=1 via
# monkeypatch; gate-blocked tests delete the env var.
# ═══════════════════════════════════════════════════════════════════════════════

import json

from typer.testing import CliRunner

from sgraph_ai_service_playwright__cli.aws.ec2.cli.Cli__EC2__Ami import app
from tests.unit.sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client__In_Memory import EC2__AWS__Client__In_Memory


runner = CliRunner()


def _obj(client):
    return {'ec2_client': client}


class Test__Cli__EC2__Ami__Mutations:

    # ── mutation gate ────────────────────────────────────────────────────────

    def test_1__delete_requires_mutation_gate(self, monkeypatch):
        monkeypatch.delenv('SG_AWS__EC2__ALLOW_MUTATIONS', raising=False)
        client = EC2__AWS__Client__In_Memory()
        client.seed_ami(ami_id='ami-aaaaaaaa', name='target', owner='self')
        result = runner.invoke(app, ['delete', 'ami-aaaaaaaa', '--yes'],
                               obj=_obj(client))
        assert result.exit_code == 1
        # AMI still present
        assert client.describe_ami('ami-aaaaaaaa') is not None

    # ── happy path ───────────────────────────────────────────────────────────

    def test_2__delete_with_yes_deregisters(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        client.seed_ami(ami_id='ami-aaaaaaaa', name='target', owner='self',
                        snapshot_ids=['snap-11111111'])
        client.seed_snapshot(snapshot_id='snap-11111111', owner='self')
        result = runner.invoke(app, ['delete', 'ami-aaaaaaaa', '--yes'],
                               obj=_obj(client))
        assert result.exit_code == 0
        assert 'Deregistered' in result.output
        assert client.describe_ami('ami-aaaaaaaa') is None
        # snapshot preserved by default
        assert len(client.list_snapshots(owner='self')) == 1

    def test_3__delete_with_snapshots_deletes_them(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        client.seed_ami(ami_id='ami-aaaaaaaa', name='target', owner='self',
                        snapshot_ids=['snap-11111111', 'snap-22222222'])
        client.seed_snapshot(snapshot_id='snap-11111111', owner='self')
        client.seed_snapshot(snapshot_id='snap-22222222', owner='self')
        result = runner.invoke(app, ['delete', 'ami-aaaaaaaa',
                                     '--with-snapshots', '--yes'],
                               obj=_obj(client))
        assert result.exit_code == 0
        assert client.describe_ami('ami-aaaaaaaa') is None
        assert len(client.list_snapshots(owner='self')) == 0

    def test_4__delete_with_snapshots_in_use_partial_fail(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        client.seed_ami(ami_id='ami-aaaaaaaa', name='target', owner='self',
                        snapshot_ids=['snap-11111111', 'snap-22222222'])
        client.seed_snapshot(snapshot_id='snap-11111111', owner='self')
        client.seed_snapshot(snapshot_id='snap-22222222', owner='self',
                             in_use=True)
        result = runner.invoke(app, ['delete', 'ami-aaaaaaaa',
                                     '--with-snapshots', '--yes', '--json'],
                               obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['deregistered'] is True
        snaps_by_id = {s['id']: s for s in data['snapshots']}
        assert snaps_by_id['snap-11111111']['deleted'] is True
        assert snaps_by_id['snap-22222222']['deleted'] is False
        assert snaps_by_id['snap-22222222']['error']   is not None
        assert 'InUse' in snaps_by_id['snap-22222222']['error']
        # AMI still deregistered, healthy snap deleted, in-use one survives
        assert client.describe_ami('ami-aaaaaaaa') is None
        remaining = {str(s.snapshot_id) for s in client.list_snapshots(owner='self')}
        assert remaining == {'snap-22222222'}

    # ── not-found ────────────────────────────────────────────────────────────

    def test_5__delete_missing_exits_1(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['delete', 'ami-deadbeef', '--yes'],
                               obj=_obj(client))
        assert result.exit_code == 1
        assert 'not found' in result.output.lower()

    # ── confirm-no aborts ────────────────────────────────────────────────────

    def test_6__delete_no_confirm_aborts(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        client.seed_ami(ami_id='ami-aaaaaaaa', name='target', owner='self')
        result = runner.invoke(app, ['delete', 'ami-aaaaaaaa'],
                               input='n\n', obj=_obj(client))
        assert result.exit_code == 0
        assert client.describe_ami('ami-aaaaaaaa') is not None

    # ── JSON output ──────────────────────────────────────────────────────────

    def test_7__delete_json_happy_path(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        client.seed_ami(ami_id='ami-aaaaaaaa', name='target', owner='self',
                        snapshot_ids=['snap-11111111'])
        client.seed_snapshot(snapshot_id='snap-11111111', owner='self')
        result = runner.invoke(app, ['delete', 'ami-aaaaaaaa',
                                     '--with-snapshots', '--yes', '--json'],
                               obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['ami_id']       == 'ami-aaaaaaaa'
        assert data['deregistered'] is True
        assert len(data['snapshots']) == 1
        assert data['snapshots'][0]['id']      == 'snap-11111111'
        assert data['snapshots'][0]['deleted'] is True
        assert data['snapshots'][0]['error']   is None

    def test_8__delete_json_without_snapshots_flag(self, monkeypatch):
        monkeypatch.setenv('SG_AWS__EC2__ALLOW_MUTATIONS', '1')
        client = EC2__AWS__Client__In_Memory()
        client.seed_ami(ami_id='ami-aaaaaaaa', name='target', owner='self',
                        snapshot_ids=['snap-11111111'])
        client.seed_snapshot(snapshot_id='snap-11111111', owner='self')
        result = runner.invoke(app, ['delete', 'ami-aaaaaaaa', '--yes', '--json'],
                               obj=_obj(client))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['ami_id']       == 'ami-aaaaaaaa'
        assert data['deregistered'] is True
        assert data['snapshots']    == []                                       # snapshots untouched without --with-snapshots
        assert len(client.list_snapshots(owner='self')) == 1

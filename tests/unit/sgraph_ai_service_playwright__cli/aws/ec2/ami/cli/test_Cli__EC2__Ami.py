# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__EC2__Ami
# Tests for `sg aws ec2 ami {list,show,orphans}` via Typer CliRunner.
# Covers table + JSON modes, orphan detection scenarios, and --older filter.
# No mocks. In-memory client injected via ctx.obj.
# ═══════════════════════════════════════════════════════════════════════════════

import json
from datetime import datetime, timedelta, timezone

from typer.testing import CliRunner

from sgraph_ai_service_playwright__cli.aws.ec2.cli.Cli__EC2__Ami import app
from tests.unit.sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client__In_Memory import EC2__AWS__Client__In_Memory


runner = CliRunner()


def _iso(dt: datetime) -> str:
    return dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')


# ── list ──────────────────────────────────────────────────────────────────────

class Test__Cli__EC2__Ami__list:

    def test_1__empty(self):
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['list'], obj={'ec2_client': client})
        assert result.exit_code == 0
        assert 'No AMIs found' in result.output

    def test_2__list_json(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_ami(ami_id='ami-aaaaaaaa', name='web', owner='self',
                        snapshot_ids=['snap-12345678'])
        result = runner.invoke(app, ['list', '--json'], obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]['ami_id']       == 'ami-aaaaaaaa'
        assert data[0]['name']         == 'web'
        assert data[0]['snapshot_ids'] == ['snap-12345678']

    def test_3__list_table_renders_id(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_ami(ami_id='ami-aaaaaaaa', name='web', owner='self')
        result = runner.invoke(app, ['list'], obj={'ec2_client': client})
        assert result.exit_code == 0
        assert 'ami-aaaaaaaa' in result.output

    def test_4__owner_filter(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_ami(ami_id='ami-aaaaaaaa', name='mine',   owner='self')
        client.seed_ami(ami_id='ami-bbbbbbbb', name='public', owner='amazon')
        result = runner.invoke(app, ['list', '--owner', 'amazon', '--json'],
                               obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]['ami_id'] == 'ami-bbbbbbbb'

    def test_5__name_substring(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_ami(ami_id='ami-aaaaaaaa', name='ubuntu-22.04', owner='self')
        client.seed_ami(ami_id='ami-bbbbbbbb', name='al2023',       owner='self')
        result = runner.invoke(app, ['list', '--name', 'ubuntu', '--json'],
                               obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]['ami_id'] == 'ami-aaaaaaaa'


# ── show ──────────────────────────────────────────────────────────────────────

class Test__Cli__EC2__Ami__show:

    def test_1__show_by_id_json(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_ami(ami_id='ami-aaaaaaaa', name='target', owner='self',
                        snapshot_ids=['snap-12345678'])
        client.seed_instance(name='runner-1', ami_id='ami-aaaaaaaa', state='running')
        result = runner.invoke(app, ['show', 'ami-aaaaaaaa', '--json'],
                               obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['ami_id']       == 'ami-aaaaaaaa'
        assert data['name']         == 'target'
        assert data['snapshot_ids'] == ['snap-12345678']
        assert len(data['attached_instance_ids']) == 1

    def test_2__show_by_name(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_ami(ami_id='ami-aaaaaaaa', name='by-name', owner='self')
        result = runner.invoke(app, ['show', 'by-name', '--json'],
                               obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['ami_id'] == 'ami-aaaaaaaa'

    def test_3__show_missing_exits_1(self):
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['show', 'ami-deadbeef'],
                               obj={'ec2_client': client})
        assert result.exit_code == 1
        assert 'not found' in result.output.lower()

    def test_4__show_no_attached_when_no_instance(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_ami(ami_id='ami-aaaaaaaa', name='unused', owner='self')
        result = runner.invoke(app, ['show', 'ami-aaaaaaaa', '--json'],
                               obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['attached_instance_ids'] == []


# ── orphans ───────────────────────────────────────────────────────────────────

class Test__Cli__EC2__Ami__orphans:

    def test_1__no_orphans_when_all_in_use(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_ami(ami_id='ami-aaaaaaaa', name='live', owner='self')
        client.seed_instance(name='r1', ami_id='ami-aaaaaaaa', state='running')
        result = runner.invoke(app, ['orphans', '--json'],
                               obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data == []

    def test_2__all_orphans_when_no_instances(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_ami(ami_id='ami-aaaaaaaa', name='unused1', owner='self')
        client.seed_ami(ami_id='ami-bbbbbbbb', name='unused2', owner='self')
        result = runner.invoke(app, ['orphans', '--json'],
                               obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        ids  = {d['ami_id'] for d in data}
        assert ids == {'ami-aaaaaaaa', 'ami-bbbbbbbb'}
        for d in data:
            assert d['attached_instance_ids'] == []

    def test_3__mixed_orphans_and_in_use(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_ami(ami_id='ami-aaaaaaaa', name='used',   owner='self')
        client.seed_ami(ami_id='ami-bbbbbbbb', name='unused', owner='self')
        client.seed_instance(name='r1', ami_id='ami-aaaaaaaa', state='running')
        result = runner.invoke(app, ['orphans', '--json'],
                               obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        ids  = {d['ami_id'] for d in data}
        assert ids == {'ami-bbbbbbbb'}

    def test_4__older_filter_excludes_recent(self):
        client = EC2__AWS__Client__In_Memory()
        # Recent (5 days ago) should be filtered out by --older 30d.
        recent = _iso(datetime.now(timezone.utc) - timedelta(days=5))
        old    = _iso(datetime.now(timezone.utc) - timedelta(days=120))
        client.seed_ami(ami_id='ami-aaaaaaaa', name='recent', owner='self', created=recent)
        client.seed_ami(ami_id='ami-bbbbbbbb', name='old',    owner='self', created=old)
        result = runner.invoke(app, ['orphans', '--older', '30d', '--json'],
                               obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        ids  = {d['ami_id'] for d in data}
        assert ids == {'ami-bbbbbbbb'}

    def test_5__amis_with_unparseable_created_at_are_never_orphans(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_ami(ami_id='ami-aaaaaaaa', name='no-date', owner='self', created='')
        result = runner.invoke(app, ['orphans', '--json'],
                               obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data == []

    def test_6__terminated_instance_still_counts_as_in_use(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_ami(ami_id='ami-aaaaaaaa', name='terminated-host', owner='self')
        client.seed_instance(name='gone', ami_id='ami-aaaaaaaa', state='terminated')
        result = runner.invoke(app, ['orphans', '--json'],
                               obj={'ec2_client': client})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data == []

    def test_7__table_output_when_orphans(self):
        client = EC2__AWS__Client__In_Memory()
        client.seed_ami(ami_id='ami-cccccccc', name='lonely', owner='self')
        result = runner.invoke(app, ['orphans'], obj={'ec2_client': client})
        assert result.exit_code == 0
        assert 'ami-cccccccc' in result.output

    def test_8__bad_older_raises(self):
        client = EC2__AWS__Client__In_Memory()
        result = runner.invoke(app, ['orphans', '--older', 'banana'],
                               obj={'ec2_client': client})
        assert result.exit_code != 0

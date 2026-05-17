# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__CloudTrail
# Tests for sg aws cloudtrail events / trail commands via CliRunner.
# All commands are read-only — no mutation gate.
# ═══════════════════════════════════════════════════════════════════════════════

import json

import pytest
from typer.testing import CliRunner

from sgraph_ai_service_playwright__cli.aws.cloudtrail.cli.Cli__CloudTrail import app
from tests.unit.sgraph_ai_service_playwright__cli.aws.cloudtrail.service.CloudTrail__AWS__Client__In_Memory import CloudTrail__AWS__Client__In_Memory

runner = CliRunner()


def _seed_client() -> CloudTrail__AWS__Client__In_Memory:
    client = CloudTrail__AWS__Client__In_Memory()
    client.seed_event(event_name='PutObject',  username='alice', source_ip='1.2.3.4', aws_region='us-east-1')
    client.seed_event(event_name='GetObject',  username='bob',   source_ip='5.6.7.8', aws_region='eu-west-1')
    client.seed_event(event_name='ListBuckets', username='alice', source_ip='1.2.3.4', aws_region='us-east-1')
    client.seed_trail(name='prod-trail', s3_bucket='prod-logs', home_region='us-east-1',
                      multi_region=True, include_global=True, is_logging=True)
    return client


class Test__Cli__CloudTrail__Events:

    def test_1__events_list_empty(self, monkeypatch):
        client = CloudTrail__AWS__Client__In_Memory()
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.cloudtrail.cli.Cli__CloudTrail._client',
                            lambda: client)
        result = runner.invoke(app, ['events', 'list'])
        assert result.exit_code == 0
        assert 'No events found' in result.output

    def test_2__events_list_json(self, monkeypatch):
        client = _seed_client()
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.cloudtrail.cli.Cli__CloudTrail._client',
                            lambda: client)
        result = runner.invoke(app, ['events', 'list', '--json'])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 3
        names = {e['event_name'] for e in data}
        assert 'PutObject'   in names
        assert 'GetObject'   in names
        assert 'ListBuckets' in names

    def test_3__events_list_filter_action(self, monkeypatch):
        client = _seed_client()
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.cloudtrail.cli.Cli__CloudTrail._client',
                            lambda: client)
        result = runner.invoke(app, ['events', 'list', '--action', 'PutObject', '--json'])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]['event_name'] == 'PutObject'

    def test_4__events_list_filter_user(self, monkeypatch):
        client = _seed_client()
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.cloudtrail.cli.Cli__CloudTrail._client',
                            lambda: client)
        result = runner.invoke(app, ['events', 'list', '--user', 'alice', '--json'])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 2
        assert all(e['username'] == 'alice' for e in data)

    def test_5__events_list_limit(self, monkeypatch):
        client = _seed_client()
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.cloudtrail.cli.Cli__CloudTrail._client',
                            lambda: client)
        result = runner.invoke(app, ['events', 'list', '--limit', '1', '--json'])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1

    def test_6__events_show_json(self, monkeypatch):
        client = CloudTrail__AWS__Client__In_Memory()
        eid    = client.seed_event(event_name='CreateBucket', username='carol')
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.cloudtrail.cli.Cli__CloudTrail._client',
                            lambda: client)
        result = runner.invoke(app, ['events', 'show', eid, '--json'])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['event_id']   == eid
        assert data['event_name'] == 'CreateBucket'
        assert data['username']   == 'carol'
        assert 'request_parameters' in data
        assert 'response_elements'  in data

    def test_7__events_show_missing(self, monkeypatch):
        client = CloudTrail__AWS__Client__In_Memory()
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.cloudtrail.cli.Cli__CloudTrail._client',
                            lambda: client)
        result = runner.invoke(app, ['events', 'show', '00000000-0000-0000-0000-000000000000'])
        assert result.exit_code == 1


class Test__Cli__CloudTrail__Trail:

    def test_1__trail_list_empty(self, monkeypatch):
        client = CloudTrail__AWS__Client__In_Memory()
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.cloudtrail.cli.Cli__CloudTrail._client',
                            lambda: client)
        result = runner.invoke(app, ['trail', 'list'])
        assert result.exit_code == 0
        assert 'No trails found' in result.output

    def test_2__trail_list_json(self, monkeypatch):
        client = _seed_client()
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.cloudtrail.cli.Cli__CloudTrail._client',
                            lambda: client)
        result = runner.invoke(app, ['trail', 'list', '--json'])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]['name']           == 'prod-trail'
        assert data[0]['is_logging']     is True
        assert data[0]['home_region']    == 'us-east-1'
        assert data[0]['s3_bucket_name'] == 'prod-logs'

    def test_3__trail_show_json(self, monkeypatch):
        client = _seed_client()
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.cloudtrail.cli.Cli__CloudTrail._client',
                            lambda: client)
        result = runner.invoke(app, ['trail', 'show', 'prod-trail', '--json'])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['name']                          == 'prod-trail'
        assert data['is_multi_region_trail']         is True
        assert data['include_global_service_events'] is True
        assert data['log_file_validation_enabled']   is True
        assert data['is_logging']                    is True
        assert 'arn:aws:cloudtrail' in data['trail_arn']

    def test_4__trail_show_missing(self, monkeypatch):
        client = CloudTrail__AWS__Client__In_Memory()
        monkeypatch.setattr('sgraph_ai_service_playwright__cli.aws.cloudtrail.cli.Cli__CloudTrail._client',
                            lambda: client)
        result = runner.invoke(app, ['trail', 'show', 'no-such-trail'])
        assert result.exit_code == 1

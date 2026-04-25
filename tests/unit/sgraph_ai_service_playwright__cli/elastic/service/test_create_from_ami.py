# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Elastic__Service.create_from_ami + render_fast user-data
# Pins the contract that the fast-launch path:
#   - Requires a from_ami value
#   - Uses minimal user-data (no docker/openssl/jq install, no compose write)
#   - Still wires the per-instance auto-terminate timer when max_hours > 0
#   - Returns elastic_password='' (it's baked into the AMI)
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name import Safe_Str__Elastic__Stack__Name
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Create__Request import Schema__Elastic__Create__Request
from sgraph_ai_service_playwright__cli.elastic.service.Elastic__Service             import Elastic__Service
from sgraph_ai_service_playwright__cli.elastic.service.Elastic__User__Data__Builder import Elastic__User__Data__Builder
from sgraph_ai_service_playwright__cli.elastic.service.Synthetic__Data__Generator   import Synthetic__Data__Generator

from tests.unit.sgraph_ai_service_playwright__cli.elastic.service.Caller__IP__Detector__In_Memory       import Caller__IP__Detector__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.elastic.service.Elastic__AWS__Client__In_Memory       import Elastic__AWS__Client__In_Memory, DEFAULT_FIXTURE_AMI
from tests.unit.sgraph_ai_service_playwright__cli.elastic.service.Elastic__HTTP__Client__In_Memory      import Elastic__HTTP__Client__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.elastic.service.Kibana__Saved_Objects__Client__In_Memory import Kibana__Saved_Objects__Client__In_Memory


REGION = 'eu-west-2'


def build_service() -> Elastic__Service:
    aws  = Elastic__AWS__Client__In_Memory(fixture_ami=DEFAULT_FIXTURE_AMI, fixture_instances={},
                                           fixture_sg_id='sg-0fixture00000000', terminated_ids=[],
                                           deleted_sg_ids=[], ssm_calls=[])
    http = Elastic__HTTP__Client__In_Memory(fixture_kibana_ready=True, fixture_probe_sequence=[], bulk_calls=[])
    saved = Kibana__Saved_Objects__Client__In_Memory(ensure_calls=[], delete_calls=[], dashboard_calls=[], harden_calls=[])
    return Elastic__Service(aws_client=aws, http_client=http, saved_objects_client=saved,
                            ip_detector=Caller__IP__Detector__In_Memory(),
                            user_data_builder=Elastic__User__Data__Builder(),
                            data_generator=Synthetic__Data__Generator(seed=1))


class test_render_fast_user_data(TestCase):

    def test_does_not_install_docker_or_run_compose_up(self):                       # The whole point: skip the install steps the AMI already carries
        rendered = Elastic__User__Data__Builder().render_fast(
            stack_name=Safe_Str__Elastic__Stack__Name('foo'), max_hours=1)
        # Must NOT install (AMI has these)
        assert 'dnf install' not in rendered
        assert 'openssl req'  not in rendered
        # Must NOT mint a new service token (AMI's token is still valid)
        assert 'elasticsearch-service-tokens create' not in rendered
        # Must NOT write a new docker-compose.yml (AMI has it)
        assert 'cat > /opt/sg-elastic/docker-compose.yml' not in rendered
        # SHOULD nudge compose so containers come back up after launch
        assert 'docker compose'              in rendered
        # SHOULD include the auto-terminate timer when max_hours > 0
        assert 'systemd-run --on-active=1h'  in rendered

    def test_no_shutdown_section_when_max_hours_zero(self):
        rendered = Elastic__User__Data__Builder().render_fast(
            stack_name=Safe_Str__Elastic__Stack__Name('foo'), max_hours=0)
        assert 'systemd-run --on-active' not in rendered


class test_create_from_ami(TestCase):

    def test_uses_supplied_ami_and_minimal_user_data(self):
        service = build_service()
        response = service.create_from_ami(Schema__Elastic__Create__Request(
            stack_name='only', region=REGION, from_ami='ami-0a1b2c3d4e5f6789a', max_hours=2))
        assert str(response.ami_id)            == 'ami-0a1b2c3d4e5f6789a'
        assert str(response.elastic_password)  == ''                                # Bake-time password — caller fetches via SSM
        # The user-data captured by the in-memory client must be the FAST one
        captured_user_data = service.aws_client.last_launch_user_data
        assert 'fast-boot from AMI'                  in captured_user_data
        assert 'dnf install'                         not in captured_user_data
        assert 'docker compose --env-file'           in captured_user_data
        # InstanceInitiatedShutdownBehavior=terminate is set when max_hours > 0
        assert service.aws_client.last_launch_max_hours == 2

    def test_no_from_ami_raises(self):
        service = build_service()
        try:
            service.create_from_ami(Schema__Elastic__Create__Request(stack_name='only', region=REGION))
            assert False, 'expected ValueError'
        except ValueError as exc:
            assert 'from-ami' in str(exc)

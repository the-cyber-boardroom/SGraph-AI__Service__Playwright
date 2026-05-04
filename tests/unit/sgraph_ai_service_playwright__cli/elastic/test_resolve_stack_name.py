# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for the resolve_stack_name helper in scripts/elastic.py
# Pins the auto-pick / prompt-on-multiple UX for info/wait/delete/seed:
#   - provided name   → returned unchanged
#   - zero stacks     → typer.Exit(1)
#   - one  stack      → auto-used
#   - many stacks     → prompt_fn called; valid index returns that name;
#                       invalid index raises typer.Exit(1)
#
# No mocks. The multi-stack branch takes a prompt_fn override so tests drive
# it deterministically without touching stdin.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

import typer

from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Create__Request  import Schema__Elastic__Create__Request
from sgraph_ai_service_playwright__cli.elastic.service.Elastic__Service             import Elastic__Service
from sgraph_ai_service_playwright__cli.elastic.service.Elastic__User__Data__Builder import Elastic__User__Data__Builder
from sgraph_ai_service_playwright__cli.elastic.service.Synthetic__Data__Generator   import Synthetic__Data__Generator

from scripts.elastic                                                                import resolve_stack_name
from tests.unit.sgraph_ai_service_playwright__cli.elastic.service.Caller__IP__Detector__In_Memory  import Caller__IP__Detector__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.elastic.service.Elastic__AWS__Client__In_Memory  import Elastic__AWS__Client__In_Memory, DEFAULT_FIXTURE_AMI
from tests.unit.sgraph_ai_service_playwright__cli.elastic.service.Elastic__HTTP__Client__In_Memory import Elastic__HTTP__Client__In_Memory


def build_service_with_stacks(count: int) -> Elastic__Service:
    aws  = Elastic__AWS__Client__In_Memory(fixture_ami       = DEFAULT_FIXTURE_AMI ,
                                           fixture_instances = {}                  ,
                                           fixture_sg_id     = 'sg-0fixture00000000',
                                           terminated_ids    = []                  ,
                                           deleted_sg_ids    = []                  ,
                                           ssm_calls         = []                  )
    http = Elastic__HTTP__Client__In_Memory(fixture_kibana_ready   = True ,
                                            fixture_probe_sequence = []    ,
                                            bulk_calls             = []    )
    service = Elastic__Service(aws_client        = aws                                  ,
                               http_client       = http                                 ,
                               ip_detector       = Caller__IP__Detector__In_Memory()    ,
                               user_data_builder = Elastic__User__Data__Builder()       ,
                               data_generator    = Synthetic__Data__Generator(seed=1)   )
    for idx in range(count):
        service.create(Schema__Elastic__Create__Request(stack_name = f'stack-{idx + 1}'))
    return service


class test_resolve_stack_name(TestCase):

    def test_provided_name__returned_unchanged(self):                               # Service not even consulted when a name is passed
        service = build_service_with_stacks(0)                                      # Zero stacks; provided short-circuits the lookup
        assert resolve_stack_name(service, 'my-stack', None) == 'my-stack'

    def test_zero_stacks__exits_with_helpful_message(self):
        service = build_service_with_stacks(0)
        try:
            resolve_stack_name(service, None, None)
            assert False, 'expected typer.Exit'
        except typer.Exit as exc:
            assert exc.exit_code == 1

    def test_one_stack__auto_used(self):
        service = build_service_with_stacks(1)
        assert resolve_stack_name(service, None, None) == 'stack-1'

    def test_many_stacks__prompt_valid_pick(self):
        service = build_service_with_stacks(3)
        picked  = resolve_stack_name(service, None, None, prompt_fn=lambda: 2)      # Names are sorted by instance-id order — deterministic in fixture
        assert picked in ('stack-1', 'stack-2', 'stack-3')

    def test_many_stacks__prompt_returns_the_indexed_name(self):                    # The list order comes from list_stacks (sorted by instance_id); "2" picks item #2
        service = build_service_with_stacks(3)
        names   = [str(s.stack_name) for s in service.list_stacks().stacks]
        picked  = resolve_stack_name(service, None, None, prompt_fn=lambda: 2)
        assert picked == names[1]

    def test_many_stacks__prompt_out_of_range__exits(self):
        service = build_service_with_stacks(3)
        try:
            resolve_stack_name(service, None, None, prompt_fn=lambda: 99)
            assert False, 'expected typer.Exit'
        except typer.Exit as exc:
            assert exc.exit_code == 1

    def test_many_stacks__prompt_non_numeric__exits(self):
        service = build_service_with_stacks(2)
        try:
            resolve_stack_name(service, None, None, prompt_fn=lambda: 'abc')
            assert False, 'expected typer.Exit'
        except typer.Exit as exc:
            assert exc.exit_code == 1

    def test_many_stacks__prompt_zero__exits(self):                                 # 0 is one-off-by-one user mistake; helper treats it as invalid
        service = build_service_with_stacks(2)
        try:
            resolve_stack_name(service, None, None, prompt_fn=lambda: 0)
            assert False, 'expected typer.Exit'
        except typer.Exit as exc:
            assert exc.exit_code == 1

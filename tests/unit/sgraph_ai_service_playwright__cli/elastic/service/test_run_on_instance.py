# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Elastic__Service.run_on_instance + Safe_Str__Shell__Output
# Drives `sp elastic exec`'s service path against the in-memory SSM stub.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name import Safe_Str__Elastic__Stack__Name
from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Shell__Output   import Safe_Str__Shell__Output
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Create__Request  import Schema__Elastic__Create__Request
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Exec__Result         import Schema__Exec__Result
from sgraph_ai_service_playwright__cli.elastic.service.Elastic__Service             import Elastic__Service
from sgraph_ai_service_playwright__cli.elastic.service.Elastic__User__Data__Builder import Elastic__User__Data__Builder
from sgraph_ai_service_playwright__cli.elastic.service.Synthetic__Data__Generator   import Synthetic__Data__Generator

from tests.unit.sgraph_ai_service_playwright__cli.elastic.service.Caller__IP__Detector__In_Memory  import Caller__IP__Detector__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.elastic.service.Elastic__AWS__Client__In_Memory  import Elastic__AWS__Client__In_Memory, DEFAULT_FIXTURE_AMI
from tests.unit.sgraph_ai_service_playwright__cli.elastic.service.Elastic__HTTP__Client__In_Memory import Elastic__HTTP__Client__In_Memory


REGION = 'eu-west-2'


def build_service():
    aws  = Elastic__AWS__Client__In_Memory(fixture_ami         = DEFAULT_FIXTURE_AMI  ,
                                           fixture_instances   = {}                   ,
                                           fixture_sg_id       = 'sg-0fixture00000000',
                                           terminated_ids      = []                   ,
                                           deleted_sg_ids      = []                   ,
                                           ssm_calls           = []                   )
    http = Elastic__HTTP__Client__In_Memory(fixture_kibana_ready   = True ,
                                            fixture_probe_sequence = []    ,
                                            bulk_calls             = []    )
    return Elastic__Service(aws_client        = aws                                  ,
                            http_client       = http                                 ,
                            ip_detector       = Caller__IP__Detector__In_Memory()    ,
                            user_data_builder = Elastic__User__Data__Builder()       ,
                            data_generator    = Synthetic__Data__Generator(seed=1)   )


class test_Safe_Str__Shell__Output(TestCase):

    def test_preserves_punctuation_and_newlines(self):                              # The whole reason the primitive exists
        payload = ('line one: /opt/foo\n'
                   'line two: http://example.com\n'
                   'line `three` with =equals and <angles>\n'
                   'tab\there\n')
        out = Safe_Str__Shell__Output(payload)
        assert str(out) == payload

    def test_empty_allowed(self):
        assert str(Safe_Str__Shell__Output('')) == ''


class test_run_on_instance(TestCase):

    def test_run__captures_stdout_stderr_exit_code_status(self):
        service = build_service()
        service.create(Schema__Elastic__Create__Request(stack_name='only', region=REGION))
        service.aws_client.fixture_ssm_stdout    = 'hello world\nline 2\n'
        service.aws_client.fixture_ssm_stderr    = 'just a warning\n'
        service.aws_client.fixture_ssm_exit_code = 0
        service.aws_client.fixture_ssm_status    = 'Success'

        result = service.run_on_instance(stack_name = Safe_Str__Elastic__Stack__Name('only'),
                                         command    = 'echo hello'                          ,
                                         region     = REGION                                )

        assert type(result)               is Schema__Exec__Result
        assert str(result.stack_name)     == 'only'
        assert str(result.instance_id)    .startswith('i-')
        assert str(result.command)        == 'echo hello'
        assert str(result.stdout)         == 'hello world\nline 2\n'                  # Newlines + spaces preserved by permissive primitive
        assert str(result.stderr)         == 'just a warning\n'
        assert result.exit_code           == 0
        assert str(result.status)         == 'Success'
        assert result.duration_ms         >= 0

    def test_run__missing_stack_returns_not_found(self):                            # No instance for the name → exit_code -1, status NotFound
        service = build_service()
        result  = service.run_on_instance(stack_name = Safe_Str__Elastic__Stack__Name('ghost'),
                                          command    = 'true'                                 ,
                                          region     = REGION                                 )
        assert result.exit_code        == -1
        assert str(result.status)      == 'NotFound'
        assert 'ghost'                 in str(result.stderr).lower()

    def test_run__captures_command_in_ssm_calls(self):                              # The in-memory SSM stub records what was sent — pin the wiring
        service = build_service()
        service.create(Schema__Elastic__Create__Request(stack_name='only', region=REGION))
        service.run_on_instance(stack_name = Safe_Str__Elastic__Stack__Name('only'),
                                command    = 'docker ps'                            ,
                                region     = REGION                                  )
        assert len(service.aws_client.ssm_calls) == 1
        instance_id, commands = service.aws_client.ssm_calls[0]
        assert instance_id.startswith('i-')
        assert commands == ['docker ps']

    def test_run__non_zero_exit_code_pass_through(self):                            # Service must not swallow non-zero — caller decides what to do
        service = build_service()
        service.create(Schema__Elastic__Create__Request(stack_name='only', region=REGION))
        service.aws_client.fixture_ssm_stdout    = ''
        service.aws_client.fixture_ssm_stderr    = 'permission denied\n'
        service.aws_client.fixture_ssm_exit_code = 13
        service.aws_client.fixture_ssm_status    = 'Failed'

        result = service.run_on_instance(stack_name = Safe_Str__Elastic__Stack__Name('only'),
                                         command    = 'cat /etc/shadow'                     ,
                                         region     = REGION                                 )
        assert result.exit_code   == 13
        assert str(result.status) == 'Failed'

    def test_run__shell_output_preserves_chars_safe_str_text_would_mangle(self):    # End-to-end: stdout containing /, :, backticks survives
        service = build_service()
        service.create(Schema__Elastic__Create__Request(stack_name='only', region=REGION))
        tricky = '/opt/sg-elastic/.env\nhttps://example.com:443\n`backtick` =eq <ang>\n'
        service.aws_client.fixture_ssm_stdout = tricky

        result = service.run_on_instance(stack_name = Safe_Str__Elastic__Stack__Name('only'),
                                         command    = 'cat'                                 ,
                                         region     = REGION                                 )
        assert str(result.stdout) == tricky                                          # Safe_Str__Text would butcher every special char

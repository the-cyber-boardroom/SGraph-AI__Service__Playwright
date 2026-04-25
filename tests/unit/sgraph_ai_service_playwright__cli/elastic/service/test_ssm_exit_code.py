# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Elastic__AWS__Client.ssm_send_command's exit-code parsing
# Regression for a falsy-zero bug: `int(inv.get('ResponseCode', -1) or -1)`
# collapses ResponseCode=0 (success) to -1 because 0 is falsy in Python. The
# `sp el health` SSM rows then showed FAIL with "exit=-1 status=Success" for
# what was actually a successful command.
#
# Real subclass that overrides ssm_client() to return a stub returning a
# canned get_command_invocation payload — no mocks, just inheritance.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.service.Elastic__AWS__Client         import Elastic__AWS__Client


class Stub__SSM__Exceptions:                                                        # boto3 client.exceptions exposes nested classes — mimic the shape we touch
    class InvocationDoesNotExist(Exception):
        pass


class Stub__SSM:                                                                    # Minimal SSM client returning canned payloads
    def __init__(self, invocation):
        self.invocation = invocation
        self.exceptions = Stub__SSM__Exceptions()
        self.sent       = []

    def send_command(self, **kwargs):
        self.sent.append(kwargs)
        return {'Command': {'CommandId': 'cmd-fixture-1'}}

    def get_command_invocation(self, **kwargs):
        return self.invocation


class Capturing__AWS__Client(Elastic__AWS__Client):                                 # Subclass returning a stub SSM client per call
    fixture_invocation : dict

    def ssm_client(self, region: str):
        return Stub__SSM(self.fixture_invocation)


class test_ssm_send_command__exit_code_parsing(TestCase):

    def test_response_code_zero_returns_zero_not_minus_one(self):                   # The actual regression — Python falsy-0 used to collapse to -1
        client = Capturing__AWS__Client(fixture_invocation={
            'Status'                : 'Success' ,
            'ResponseCode'          : 0          ,
            'StandardOutputContent' : 'OK\n'    ,
            'StandardErrorContent'  : ''         })
        stdout, stderr, code, status = client.ssm_send_command('eu-west-2', 'i-x', ['echo OK'])
        assert code   == 0
        assert status == 'Success'
        assert stdout == 'OK\n'

    def test_response_code_non_zero_passes_through(self):
        client = Capturing__AWS__Client(fixture_invocation={
            'Status'                : 'Failed' ,
            'ResponseCode'          : 7         ,
            'StandardOutputContent' : ''        ,
            'StandardErrorContent'  : 'boom'    })
        _, stderr, code, status = client.ssm_send_command('eu-west-2', 'i-x', ['false'])
        assert code   == 7
        assert status == 'Failed'
        assert stderr == 'boom'

    def test_missing_response_code_returns_minus_one(self):                         # Defensive: when AWS doesn't include ResponseCode at all (e.g. timeout edge cases)
        client = Capturing__AWS__Client(fixture_invocation={
            'Status'                : 'TimedOut',
            'StandardOutputContent' : ''         ,
            'StandardErrorContent'  : ''         })
        _, _, code, status = client.ssm_send_command('eu-west-2', 'i-x', ['echo x'])
        assert code   == -1
        assert status == 'TimedOut'

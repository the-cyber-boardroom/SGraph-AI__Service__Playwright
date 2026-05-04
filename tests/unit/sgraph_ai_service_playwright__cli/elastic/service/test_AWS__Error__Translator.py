# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for AWS__Error__Translator
# Constructs real botocore exceptions (not mocks) and asserts the translator
# returns the right Schema__AWS__Error__Hint shape.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from botocore.exceptions                                                            import (
    ClientError                ,
    EndpointConnectionError    ,
    NoCredentialsError         ,
    NoRegionError              ,
)

from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__AWS__Error__Hint     import Schema__AWS__Error__Hint
from sgraph_ai_service_playwright__cli.elastic.service.AWS__Error__Translator       import AWS__Error__Translator


def make_client_error(code: str, message: str = '') -> ClientError:
    return ClientError(error_response = {'Error': {'Code': code, 'Message': message}},
                       operation_name = 'TestOp'                                      )


class test_AWS__Error__Translator(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.translator = AWS__Error__Translator()

    def test_translate__no_credentials(self):
        hint = self.translator.translate(NoCredentialsError())
        assert type(hint) is Schema__AWS__Error__Hint
        assert hint.recognised        is True
        assert str(hint.category)     == 'no-credentials'
        assert 'AWS credentials not found' in str(hint.headline)
        assert any('aws configure' in h for h in hint.hints)
        assert hint.exit_code         == 2

    def test_translate__no_region(self):
        hint = self.translator.translate(NoRegionError())
        assert hint.recognised    is True
        assert str(hint.category) == 'region'
        assert any('--region' in h for h in hint.hints)

    def test_translate__endpoint_connection(self):
        exc  = EndpointConnectionError(endpoint_url='https://ec2.eu-west-2.amazonaws.com')
        hint = self.translator.translate(exc)
        assert hint.recognised    is True
        assert str(hint.category) == 'network'

    def test_translate__client_error_unauthorized(self):
        hint = self.translator.translate(make_client_error('UnauthorizedOperation',
                                                            'You are not authorized to perform this operation.'))
        assert hint.recognised    is True
        assert str(hint.category) == 'denied'
        assert 'authorized' in str(hint.body).lower() or 'permission' in str(hint.body).lower() or 'allowed' in str(hint.body).lower()

    def test_translate__client_error_expired(self):
        hint = self.translator.translate(make_client_error('ExpiredToken', 'Token expired'))
        assert hint.recognised    is True
        assert str(hint.category) == 'expired'

    def test_translate__client_error_clock_skew(self):
        hint = self.translator.translate(make_client_error('RequestExpired', 'Request has expired'))
        assert hint.recognised    is True
        assert str(hint.category) == 'clock'

    def test_translate__client_error_region_disabled(self):
        hint = self.translator.translate(make_client_error('OptInRequired', 'Region not enabled'))
        assert hint.recognised    is True
        assert str(hint.category) == 'region'

    def test_translate__client_error_unknown_code_falls_through(self):              # ClientError with a code we don't catalog → unrecognised so the CLI re-raises
        hint = self.translator.translate(make_client_error('SomeFutureCode', 'whatever'))
        assert hint.recognised is False

    def test_translate__unknown_exception_returns_unrecognised(self):
        hint = self.translator.translate(RuntimeError('boom'))
        assert hint.recognised    is False
        assert str(hint.category) == 'unknown'

    def test_translate__client_error_body_preserves_arn(self):
        # Regression: Safe_Str__Text turned the slash in arn:aws:iam::...:role/foo
        # into an underscore when displayed, so the user copy-pasted the wrong
        # ARN into their IAM policy. Schema body now uses Safe_Str__Diagnostic;
        # this test pins that the slash and colons survive the round-trip.
        msg  = 'User: arn:aws:iam::745506449035:user/SG-Deploy-User is not authorized to perform: iam:PassRole on resource: arn:aws:iam::745506449035:role/sg-elastic-ec2'
        hint = self.translator.translate(make_client_error('AccessDenied', msg))
        assert hint.recognised        is True
        assert 'arn:aws:iam::745506449035:role/sg-elastic-ec2' in str(hint.body)
        assert 'arn:aws:iam::745506449035:user/SG-Deploy-User' in str(hint.body)
        assert ':role/'                                       in str(hint.body)     # The exact path segment the user needs to copy
        assert ':role_'                                       not in str(hint.body) # And NOT the mangled form

    def test_translate__client_error_body_preserves_punctuation(self):              # Generalises the ARN test — every URL/path/keyvalue char must survive
        msg  = 'POST https://example.com:443/_elastic/_bulk -> 401 (key=value, {a:b})'
        hint = self.translator.translate(make_client_error('AccessDenied', msg))
        assert str(hint.body) == msg                                                # Exact round-trip — any mangling is a regression

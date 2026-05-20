# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI tests — Lambda__Deployer combined-deps + IFD S3 code deploy (Stage 4)
# Exercises the deploy_from_folder additions: combined_dependencies upload,
# IFD-versioned S3 code artifact, and Architectures pin. No mocks, no patches —
# subclass seams + a recording in-memory boto3-alike client.
# ═══════════════════════════════════════════════════════════════════════════════

from botocore.exceptions import ClientError

from sgraph_ai_service_playwright__cli.aws.lambda_.enums.Enum__Lambda__Runtime           import Enum__Lambda__Runtime
from sgraph_ai_service_playwright__cli.aws.lambda_.primitives.Safe_Str__Lambda__Name     import Safe_Str__Lambda__Name
from sgraph_ai_service_playwright__cli.aws.lambda_.schemas.Schema__Lambda__Deploy__Request import Schema__Lambda__Deploy__Request
from sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__Deployer              import Lambda__Deployer, ifd_code_s3_key


class _Recording_Lambda_Client:
    def __init__(self):
        self.created = {}
        self.code_updates = []

    def get_function(self, FunctionName):
        if FunctionName not in self.created:
            raise ClientError({'Error': {'Code': 'ResourceNotFoundException', 'Message': 'nope'}}, 'GetFunction')
        return {'Configuration': self.created[FunctionName]}

    def create_function(self, **kwargs):
        kwargs['FunctionArn'] = f'arn:aws:lambda:eu-west-2:123456789012:function:{kwargs["FunctionName"]}'
        self.created[kwargs['FunctionName']] = kwargs
        return {'FunctionArn': kwargs['FunctionArn']}

    def update_function_code(self, FunctionName, **kwargs):
        self.code_updates.append(kwargs)

    def update_function_configuration(self, **_): pass


class _Deployer(Lambda__Deployer):
    def __init__(self):
        super().__init__()
        self._fake          = _Recording_Lambda_Client()
        self.deps_calls     = []
        self.code_puts      = []

    def client(self):                                                    return self._fake
    def _build_zip(self, folder_path, package_root='', extra_modules=None): return b'CODEZIP'
    def _ensure_dependencies(self, combined_dependencies):               self.deps_calls.append(combined_dependencies); return {'status': 'faked'}
    def _osbot_lambdas_bucket(self):                                     return 'acct--osbot-lambdas--eu-west-2'
    def _ensure_bucket(self, bucket):                                    return None
    def _put_code_object(self, bucket, key, code):                       self.code_puts.append((bucket, key, code))


def _req():
    return Schema__Lambda__Deploy__Request(
        name=Safe_Str__Lambda__Name('sg-compute-vault-publish-waker'),
        folder_path='/x', handler='m.run', role_arn='arn:aws:iam::1:role/r',
        runtime=Enum__Lambda__Runtime.PYTHON_3_12, memory_size=512, timeout=60)


class TestIFDCodeKey:
    def test_nested_layout(self):
        assert ifd_code_s3_key('sg-compute-vault-publish-waker', 'v0.1.0') == \
               'lambdas-code/sg-compute-vault-publish-waker/v0/v0.1/v0.1.0.zip'

    def test_two_component_version(self):
        assert ifd_code_s3_key('foo', 'v1.4') == 'lambdas-code/foo/v1/v1.4.zip'

    def test_tolerates_missing_v_prefix(self):
        assert ifd_code_s3_key('foo', '2.0.1') == 'lambdas-code/foo/v2/v2.0/v2.0.1.zip'


class TestDeployWithCombinedDepsAndS3:
    def _deploy(self):
        dep = _Deployer()
        resp = dep.deploy_from_folder(
            _req(),
            combined_dependencies = ('sg-compute-vault-publish-waker', ['osbot-fast-api-serverless==v1.34.0']),
            code_s3_key           = ifd_code_s3_key('sg-compute-vault-publish-waker', 'v0.1.0'),
            architectures         = ['x86_64'],
        )
        return dep, resp

    def test_dependencies_uploaded_first(self):
        dep, _ = self._deploy()
        assert dep.deps_calls == [('sg-compute-vault-publish-waker', ['osbot-fast-api-serverless==v1.34.0'])]

    def test_code_uploaded_to_ifd_s3_key(self):
        dep, _ = self._deploy()
        assert dep.code_puts == [('acct--osbot-lambdas--eu-west-2',
                                  'lambdas-code/sg-compute-vault-publish-waker/v0/v0.1/v0.1.0.zip', b'CODEZIP')]

    def test_function_created_from_s3_not_inline(self):
        dep, _ = self._deploy()
        code = dep._fake.created['sg-compute-vault-publish-waker']['Code']
        assert code == {'S3Bucket': 'acct--osbot-lambdas--eu-west-2',
                        'S3Key'   : 'lambdas-code/sg-compute-vault-publish-waker/v0/v0.1/v0.1.0.zip'}
        assert 'ZipFile' not in code

    def test_architectures_pinned_on_create(self):
        dep, _ = self._deploy()
        assert dep._fake.created['sg-compute-vault-publish-waker']['Architectures'] == ['x86_64']

    def test_response_created(self):
        _, resp = self._deploy()
        assert resp.created is True and resp.success is True


class TestDeployBackwardCompatInline:
    def test_inline_zipfile_when_no_s3_key(self):
        dep = _Deployer()
        dep.deploy_from_folder(_req())                                               # no combined_dependencies / code_s3_key
        assert dep.deps_calls == []
        assert dep.code_puts  == []
        code = dep._fake.created['sg-compute-vault-publish-waker']['Code']
        assert code == {'ZipFile': b'CODEZIP'}
        assert 'Architectures' not in dep._fake.created['sg-compute-vault-publish-waker']

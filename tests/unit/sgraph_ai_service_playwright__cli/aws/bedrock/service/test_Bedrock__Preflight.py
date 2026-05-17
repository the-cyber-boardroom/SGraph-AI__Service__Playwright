# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Bedrock__Preflight
# Uses in-memory subclasses that override the boto3 seam.
# No mocks, no patches.
# ═══════════════════════════════════════════════════════════════════════════════

from pathlib                                                                     import Path
from unittest                                                                    import TestCase

from sgraph_ai_service_playwright__cli.aws.bedrock.collections.List__Schema__Bedrock__Check__Result import List__Schema__Bedrock__Check__Result
from sgraph_ai_service_playwright__cli.aws.bedrock.collections.List__Schema__Bedrock__Model          import List__Schema__Bedrock__Model
from sgraph_ai_service_playwright__cli.aws.bedrock.enums.Enum__Bedrock__Check__Status                import Enum__Bedrock__Check__Status
from sgraph_ai_service_playwright__cli.aws.bedrock.schemas.Schema__Bedrock__Check__Result            import Schema__Bedrock__Check__Result
from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Capture__Writer                  import Bedrock__Capture__Writer
from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Control__AWS__Client             import Bedrock__Control__AWS__Client, FALLBACK_REGION
from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Preflight                        import Bedrock__Preflight
from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Region__Catalogue               import Bedrock__Region__Catalogue
from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Runtime__AWS__Client             import Bedrock__Runtime__AWS__Client

# ── Canned data ───────────────────────────────────────────────────────────────

_FAKE_MODELS = [
    {'modelId': 'anthropic.claude-haiku-4-5:0', 'modelName': 'Claude Haiku',
     'providerName': 'Anthropic', 'inputModalities': ['TEXT'], 'outputModalities': ['TEXT']},
    {'modelId': 'amazon.nova-lite-v1:0', 'modelName': 'Nova Lite',
     'providerName': 'Amazon', 'inputModalities': ['TEXT'], 'outputModalities': ['TEXT']},
]

# ── In-memory boto3 seams ─────────────────────────────────────────────────────

class _FakeBedrockControlClient:                                                  # Returns canned model list; never calls AWS
    def list_foundation_models(self, **kwargs):
        return {'modelSummaries': _FAKE_MODELS}


class _FakeBedrockControlClient_Empty:                                            # Returns empty model list
    def list_foundation_models(self, **kwargs):
        return {'modelSummaries': []}


class _FakeBedrockControlClient_AccessDenied:                                    # Raises AccessDeniedException
    def list_foundation_models(self, **kwargs):
        raise Exception('AccessDeniedException: User is not authorized')


class _FakeStsClient:                                                             # Returns a canned caller identity
    def get_caller_identity(self):
        return {'Arn': 'arn:aws:iam::123456789012:user/test', 'Account': '123456789012'}


class _FakeBedrockRuntimeClient:                                                  # Returns a canned converse response
    def converse(self, **kwargs):
        return {'output': {'message': {'content': [{'text': 'ok'}]}},
                'usage'  : {'inputTokens': 1, 'outputTokens': 1}}


# ── In-memory client subclasses ────────────────────────────────────────────────

class _Control__WithModels(Bedrock__Control__AWS__Client):                        # Has claude + nova models
    def client(self, region: str = None):
        return _FakeBedrockControlClient()
    def current_region(self) -> str:
        return FALLBACK_REGION


class _Control__EmptyModels(Bedrock__Control__AWS__Client):                       # Has no models
    def client(self, region: str = None):
        return _FakeBedrockControlClient_Empty()
    def current_region(self) -> str:
        return FALLBACK_REGION


class _Control__AccessDenied(Bedrock__Control__AWS__Client):                      # list_foundation_models raises
    def client(self, region: str = None):
        return _FakeBedrockControlClient_AccessDenied()
    def current_region(self) -> str:
        return FALLBACK_REGION


class _Runtime__WithConverse(Bedrock__Runtime__AWS__Client):                      # Returns canned response
    def client(self, region: str = None):
        return _FakeBedrockRuntimeClient()
    def current_region(self) -> str:
        return FALLBACK_REGION


# ── Preflight with overridden check_1 (STS identity is live) ─────────────────

class _Preflight__HappyPath(Bedrock__Preflight):                                  # Check 1 overridden to avoid live STS
    def check_1__sts_identity(self, effective_region):
        return Schema__Bedrock__Check__Result(check_name='sts identity',
                                              status    =Enum__Bedrock__Check__Status.PASS,
                                              message   ='arn:aws:iam::123456789012:user/test',
                                              hint      ='')


# ── Tests ─────────────────────────────────────────────────────────────────────

class test_Bedrock__Preflight(TestCase):

    def _make_preflight(self, control_client, runtime_client=None, tmp_path=None):
        writer = Bedrock__Capture__Writer(root=str(tmp_path or Path('/tmp/.sg_preflight_test')))
        pf     = _Preflight__HappyPath(
            control_client   = control_client,
            runtime_client   = runtime_client or _Runtime__WithConverse(),
            region_catalogue = Bedrock__Region__Catalogue(),
            capture_writer   = writer,
        )
        return pf

    # ── check 2: region supported ─────────────────────────────────────────────

    def test__check_region_supported__ga_region_passes(self):
        pf     = self._make_preflight(_Control__WithModels())
        result = pf.check_2__region_supported('us-east-1')
        assert result.status == Enum__Bedrock__Check__Status.PASS
        assert 'us-east-1' in result.message

    def test__check_region_unsupported__ca_west_1_fails(self):
        pf     = self._make_preflight(_Control__WithModels())
        result = pf.check_2__region_supported('ca-west-1')
        assert result.status == Enum__Bedrock__Check__Status.FAIL
        assert 'ca-west-1' in result.message

    # ── check 3: list-models perm ─────────────────────────────────────────────

    def test__check_list_models_perm__success(self):
        pf     = self._make_preflight(_Control__WithModels())
        result, models = pf.check_3__list_models_perm(FALLBACK_REGION)
        assert result.status == Enum__Bedrock__Check__Status.PASS
        assert isinstance(models, List__Schema__Bedrock__Model)

    def test__check_list_models_perm__access_denied_fails(self):
        pf     = self._make_preflight(_Control__AccessDenied())
        result, models = pf.check_3__list_models_perm(FALLBACK_REGION)
        assert result.status == Enum__Bedrock__Check__Status.FAIL
        assert models is None

    # ── check 4: models in catalogue ──────────────────────────────────────────

    def test__check_models_in_catalogue__count_in_message(self):
        pf     = self._make_preflight(_Control__WithModels())
        _, models = pf.check_3__list_models_perm(FALLBACK_REGION)
        result = pf.check_4__models_in_catalogue(models)
        assert result.status == Enum__Bedrock__Check__Status.PASS
        assert '2' in result.message

    # ── check 5: models with access ───────────────────────────────────────────

    def test__check_models_with_access__nonempty_list_passes(self):
        pf     = self._make_preflight(_Control__WithModels())
        _, models = pf.check_3__list_models_perm(FALLBACK_REGION)
        result, enabled = pf.check_5__models_with_access(models, FALLBACK_REGION)
        assert result.status in (Enum__Bedrock__Check__Status.PASS, Enum__Bedrock__Check__Status.WARN)
        assert isinstance(enabled, list)

    def test__check_models_with_access__empty_catalogue_warns(self):
        pf       = self._make_preflight(_Control__EmptyModels())
        _, models = pf.check_3__list_models_perm(FALLBACK_REGION)
        result, enabled = pf.check_5__models_with_access(models, FALLBACK_REGION)
        assert result.status == Enum__Bedrock__Check__Status.WARN

    # ── check 6: provider available ───────────────────────────────────────────

    def test__check_provider_available__claude_model_passes(self):
        pf     = self._make_preflight(_Control__WithModels())
        _, models = pf.check_3__list_models_perm(FALLBACK_REGION)
        _, enabled = pf.check_5__models_with_access(models, FALLBACK_REGION)
        result = pf.check_6__provider_available(enabled)
        assert result.status in (Enum__Bedrock__Check__Status.PASS, Enum__Bedrock__Check__Status.WARN)

    def test__check_provider_available__no_models_fails(self):
        pf     = self._make_preflight(_Control__WithModels())
        result = pf.check_6__provider_available([])
        assert result.status == Enum__Bedrock__Check__Status.FAIL

    # ── run_all ───────────────────────────────────────────────────────────────

    def test__run_all__returns_typed_list(self):
        pf      = self._make_preflight(_Control__WithModels())
        results = pf.run_all(region=FALLBACK_REGION)
        assert isinstance(results, List__Schema__Bedrock__Check__Result)

    def test__run_all__has_8_results(self):
        pf      = self._make_preflight(_Control__WithModels())
        results = pf.run_all(region=FALLBACK_REGION)
        assert len(results) == 8

    def test__run_all__each_result_is_schema(self):
        pf      = self._make_preflight(_Control__WithModels())
        for r in pf.run_all(region=FALLBACK_REGION):
            assert isinstance(r, Schema__Bedrock__Check__Result)

    def test__run_all__unsupported_region_skips_aws_checks(self):
        pf      = self._make_preflight(_Control__WithModels())
        results = pf.run_all(region='ca-west-1')
        assert len(results) == 8
        # check 2 must be FAIL
        assert results[1].status == Enum__Bedrock__Check__Status.FAIL
        # checks 3–7 must be WARN (skipped)
        for r in results[2:7]:
            assert r.status == Enum__Bedrock__Check__Status.WARN

    def test__run_all__access_denied_skips_dependent_checks(self):
        pf      = self._make_preflight(_Control__AccessDenied())
        results = pf.run_all(region=FALLBACK_REGION)
        assert len(results) == 8
        assert results[2].status == Enum__Bedrock__Check__Status.FAIL   # list-models perm
        for r in results[3:7]:
            assert r.status == Enum__Bedrock__Check__Status.WARN         # skipped

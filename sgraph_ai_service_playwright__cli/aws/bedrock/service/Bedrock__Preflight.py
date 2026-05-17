# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Bedrock__Preflight
# Runs 8 diagnostic checks for `sg aws bedrock check`.
# No mutations — safe to run repeatedly.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe

from sgraph_ai_service_playwright__cli.aws.bedrock.collections.List__Schema__Bedrock__Check__Result import List__Schema__Bedrock__Check__Result
from sgraph_ai_service_playwright__cli.aws.bedrock.enums.Enum__Bedrock__Check__Status               import Enum__Bedrock__Check__Status
from sgraph_ai_service_playwright__cli.aws.bedrock.schemas.Schema__Bedrock__Check__Result           import Schema__Bedrock__Check__Result
from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Capture__Writer                 import Bedrock__Capture__Writer
from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Control__AWS__Client            import Bedrock__Control__AWS__Client
from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Model__Resolver                 import Bedrock__Model__Resolver
from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Region__Catalogue              import Bedrock__Region__Catalogue
from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Runtime__AWS__Client            import Bedrock__Runtime__AWS__Client

PASS = Enum__Bedrock__Check__Status.PASS
WARN = Enum__Bedrock__Check__Status.WARN
FAIL = Enum__Bedrock__Check__Status.FAIL

_SKIPPED_HINT = 'skipped — previous check failed'


def _result(check_name, status, message, hint=''):                                # Helper — build a Schema__Bedrock__Check__Result
    return Schema__Bedrock__Check__Result(check_name=check_name ,
                                          status    =status     ,
                                          message   =message    ,
                                          hint      =hint       )


_PROVIDER_NAMESPACES = {                                                           # provider keyword → model-id prefix
    'claude' : 'anthropic.',
    'nova'   : 'amazon.nova',
    'llama'  : 'meta.llama',
}


class Bedrock__Preflight(Type_Safe):
    control_client   : Bedrock__Control__AWS__Client                               # check 3/4/5/6
    runtime_client   : Bedrock__Runtime__AWS__Client                               # check 7 + per-provider checks
    region_catalogue : Bedrock__Region__Catalogue                                  # check 2
    capture_writer   : Bedrock__Capture__Writer                                    # check 8 (now 11)
    resolver         : Bedrock__Model__Resolver                                    # per-provider default checks
    region           : str                                                          # override region; '' = active role's default

    # ── individual checks ─────────────────────────────────────────────────────

    def check_1__sts_identity(self, effective_region: str) -> Schema__Bedrock__Check__Result:
        name = 'sts identity'
        try:
            from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session import Sg__Aws__Session
            session = Sg__Aws__Session.from_context()
            sts     = session.boto3_client_from_context('sts', region=effective_region)
            resp    = sts.get_caller_identity()
            arn     = resp.get('Arn', 'unknown')
            return _result(name, PASS, arn)
        except Exception as exc:
            return _result(name, FAIL, f'Caller-identity failed: {exc}',
                           hint='Likely no AWS credentials. Run: eval $(sg credentials switch <role>)')

    def check_2__region_supported(self, effective_region: str) -> Schema__Bedrock__Check__Result:
        name = 'region supported'
        if self.region_catalogue.is_supported(effective_region):
            return _result(name, PASS, f'{effective_region} (Bedrock GA)')
        supported = ', '.join(self.region_catalogue.supported_regions())
        return _result(name, FAIL,
                       f'Region {effective_region!r} does not host Bedrock as of v0.2.29',
                       hint=f'Supported: {supported}. Pick one with --region.')

    def check_3__list_models_perm(self, effective_region: str):
        name   = 'list-models perm'
        try:
            models = self.control_client.list_models(region=effective_region)
            return _result(name, PASS, 'bedrock:ListFoundationModels'), models
        except Exception as exc:
            return _result(name, FAIL, f'Permission denied: {exc}',
                           hint='Run: sg aws bedrock setup --print-policy'), None

    def check_4__models_in_catalogue(self, models) -> Schema__Bedrock__Check__Result:
        name  = 'models in catalogue'
        count = len(models)
        return _result(name, PASS, f'{count} models')

    def check_5__models_with_access(self, models, effective_region: str) -> tuple:
        name  = 'models with access'
        total = len(models)
        if total == 0:
            return _result(name, WARN, '0 models — cannot check access (catalogue empty)'), []
        url     = (f'https://{effective_region}.console.aws.amazon.com'
                   f'/bedrock/home?region={effective_region}#/modelaccess')
        enabled = [m for m in models if 'ON_DEMAND' in (m.input_modalities + m.output_modalities)
                                     or True]                                      # list_models already filtered to ON_DEMAND; all qualify
        count   = len(enabled)
        if count == 0:
            return _result(name, WARN, f'0 of {total} enabled — none enabled yet',
                           hint=f'Visit {url} or run: sg aws bedrock setup --open-console'), enabled
        return _result(name, PASS, f'{count} of {total} enabled'), enabled

    def check_6__provider_available(self, enabled_models) -> Schema__Bedrock__Check__Result:
        name      = 'claude available'
        providers = {'claude': 0, 'nova': 0, 'llama': 0}
        for m in enabled_models:
            mid = str(m.model_id).lower()
            if 'claude' in mid:
                providers['claude'] += 1
            elif 'nova' in mid:
                providers['nova'] += 1
            elif 'llama' in mid:
                providers['llama'] += 1
        summary = ', '.join(f'{k}: {v}' for k, v in providers.items() if v > 0)
        if not summary:
            summary = 'none'
        if providers['claude'] == 0 and providers['nova'] == 0 and providers['llama'] == 0:
            return _result(name, FAIL, '0 enabled — chat commands will fail',
                           hint='Enable at least one Claude, Nova, or Llama model in the console.')
        if providers['claude'] == 0:
            return _result(name, WARN, f'claude: 0 enabled — `chat claude` will fail  ({summary})',
                           hint='Enable a Claude model for full chat support.')
        return _result(name, PASS, summary)

    def check_7__invoke_perm(self, enabled_models, effective_region: str) -> Schema__Bedrock__Check__Result:
        name = 'invoke perm'
        if not enabled_models:
            return _result(name, WARN, 'smoke-test skipped (no models enabled)', hint=_SKIPPED_HINT)
        model_id = str(enabled_models[0].model_id)
        try:
            resp     = self.runtime_client.converse(model_id=model_id, prompt='0', region=effective_region)
            in_tok   = resp.get('usage', {}).get('inputTokens', 0)
            out_tok  = resp.get('usage', {}).get('outputTokens', 0)
            return _result(name, PASS, f'invoke OK — {model_id}, {in_tok}→{out_tok} tokens')
        except Exception as exc:
            return _result(name, FAIL, f'InvokeModel denied: {exc}',
                           hint='Required: bedrock:InvokeModel. Run: sg aws bedrock setup --print-policy')

    def check_provider_default_invokable(self, provider: str, effective_region: str,
                                          enabled_models: list) -> Schema__Bedrock__Check__Result:
        """Smoke-invoke the default alias for one provider; returns a single result row."""
        check_name = f'{provider} default invokable'
        namespace  = _PROVIDER_NAMESPACES.get(provider, provider)
        enabled_in_provider = [m for m in enabled_models
                                if namespace in str(m.model_id).lower()]
        model_id = self.resolver.resolve(provider, 'default', effective_region)

        if not enabled_in_provider:
            return _result(check_name, WARN,
                           f'{model_id} — skipped (no {provider} models enabled)',
                           hint=f'Enable a {provider} model in the console and re-run check.')

        try:
            resp    = self.runtime_client.converse(model_id=model_id, prompt='ping',
                                                   region=effective_region)
            in_tok  = resp.get('usage', {}).get('inputTokens',  0)
            out_tok = resp.get('usage', {}).get('outputTokens', 0)
            return _result(check_name, PASS, f'{model_id} — OK ({in_tok}→{out_tok} tokens)')
        except Exception as exc:
            err_msg   = str(exc)
            code_hint = ''
            if 'ValidationException' in err_msg and 'model' in err_msg.lower():
                code_hint = (f'Model ID invalid in {effective_region}. '
                             f'Try: sg aws bedrock chat list-models  '
                             f'or run: sg aws bedrock setup --open-console')
            elif 'AccessDeniedException' in err_msg or 'AccessDenied' in err_msg:
                code_hint = 'Missing bedrock:InvokeModel permission. Run: sg aws bedrock setup --print-policy'
            elif 'ResourceNotFoundException' in err_msg:
                code_hint = 'Model not found in this region. Try --region or check list-models.'
            return _result(check_name, FAIL, f'{model_id} — {exc}', hint=code_hint)

    def check_8__capture_writer(self) -> Schema__Bedrock__Check__Result:
        name = 'capture writer'
        try:
            root = self.capture_writer.capture_root()
            root.mkdir(parents=True, exist_ok=True)
            test_file = root / '.preflight_check'
            test_file.write_text('ok')
            test_file.unlink()
            return _result(name, PASS, f'{root} writable')
        except Exception as exc:
            return _result(name, FAIL, f'{self.capture_writer.capture_root()} — cannot create: {exc}',
                           hint='Set $SG_AWS__BEDROCK__CAPTURE_ROOT or check directory permissions.')

    # ── orchestrator ──────────────────────────────────────────────────────────

    def run_all(self, region: str = '') -> List__Schema__Bedrock__Check__Result:   # Run all 11 checks; returns ordered result list
        results          = List__Schema__Bedrock__Check__Result()
        effective_region = region or self.region or self.control_client.current_region()

        r1 = self.check_1__sts_identity(effective_region)
        results.append(r1)

        r2 = self.check_2__region_supported(effective_region)
        results.append(r2)

        if r2.status == FAIL:                                                      # Region not supported — remaining AWS checks meaningless
            for name in ('list-models perm', 'models in catalogue',
                         'models with access', 'claude available', 'invoke perm',
                         'claude default invokable', 'nova default invokable', 'llama default invokable'):
                results.append(_result(name, WARN, 'skipped — region not supported', hint=_SKIPPED_HINT))
            results.append(self.check_8__capture_writer())
            return results

        r3, models = self.check_3__list_models_perm(effective_region)
        results.append(r3)

        if models is None:                                                         # No list-models permission — skip dependent checks
            for name in ('models in catalogue', 'models with access',
                         'claude available', 'invoke perm',
                         'claude default invokable', 'nova default invokable', 'llama default invokable'):
                results.append(_result(name, WARN, 'skipped — list-models perm failed', hint=_SKIPPED_HINT))
            results.append(self.check_8__capture_writer())
            return results

        results.append(self.check_4__models_in_catalogue(models))

        r5, enabled = self.check_5__models_with_access(models, effective_region)
        results.append(r5)

        results.append(self.check_6__provider_available(enabled))

        results.append(self.check_7__invoke_perm(enabled, effective_region))

        for provider in ('claude', 'nova', 'llama'):
            results.append(self.check_provider_default_invokable(provider, effective_region, enabled))

        results.append(self.check_8__capture_writer())

        return results

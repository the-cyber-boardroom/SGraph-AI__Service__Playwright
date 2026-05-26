# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Journey__Assertion__Evaluator
#
# Stateless pure logic over typed inputs. No page.*, no network, no mocks needed.
# Reads the substrate sequence response (terminal URL via get_url results) and the
# per-run mitmproxy network log (flows). Never raises out — a bad input becomes an
# ERROR result. URL + status + header assertions are fully evaluated here; SELECTOR_*
# assertions return SKIPPED until the worker slice wires synthetic-step correlation.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                         import List

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe

from sg_compute_specs.user_journey.core.dispatcher.assertion_schema_registry                            import parse_assertion
from sg_compute_specs.user_journey.core.schemas.enums.Enum__Assertion__Status                            import Enum__Assertion__Status
from sg_compute_specs.user_journey.core.schemas.enums.Enum__Assertion__Type                              import Enum__Assertion__Type
from sg_compute_specs.user_journey.core.schemas.results.Schema__Journey__Assertion__Result               import Schema__Journey__Assertion__Result


class Journey__Assertion__Evaluator(Type_Safe):                                     # Pure-logic assertion evaluation

    def evaluate(self, assertions     : List[dict],                                 # raw assertion dicts (journey.assertions)
                       sequence_response = None,                                     # Schema__Sequence__Response
                       network_log    : List[dict] = None                           # per-run mitmproxy flows
                  ) -> List[Schema__Journey__Assertion__Result]:
        network_log = network_log or []
        return [self.evaluate_one(raw, sequence_response, network_log) for raw in assertions]

    def evaluate_one(self, raw: dict, sequence_response, network_log: List[dict]) -> Schema__Journey__Assertion__Result:
        try:
            assertion = parse_assertion(raw)
        except Exception as error:                                                  # parse failure → ERROR result, never crash
            return self.result(None, None, Enum__Assertion__Status.ERROR, error_message=str(error))

        kind = assertion.assertion_type
        try:
            if   kind == Enum__Assertion__Type.URL_CONTAINS       : return self.eval_url_contains(assertion, sequence_response)
            elif kind == Enum__Assertion__Type.URL_EQUALS         : return self.eval_url_equals  (assertion, sequence_response)
            elif kind == Enum__Assertion__Type.STATUS_CODE_EQUALS : return self.eval_status_code (assertion, network_log)
            elif kind == Enum__Assertion__Type.HTTP_HEADER_PRESENT: return self.eval_http_header (assertion, network_log)
            else:
                return self.result(assertion.assertion_id, kind, Enum__Assertion__Status.SKIPPED,
                                   error_message='selector assertions are evaluated in the worker slice')
        except Exception as error:
            return self.result(assertion.assertion_id, kind, Enum__Assertion__Status.ERROR, error_message=str(error))

    # ── per-type evaluators ──────────────────────────────────────────────────
    def eval_url_contains(self, assertion, sequence_response) -> Schema__Journey__Assertion__Result:
        url      = self.terminal_url(sequence_response)
        expected = str(assertion.expected)
        if url is None:
            return self.result(assertion.assertion_id, assertion.assertion_type, Enum__Assertion__Status.ERROR,
                               expected=expected, error_message='no get_url step result to read terminal URL')
        status = Enum__Assertion__Status.PASSED if expected in url else Enum__Assertion__Status.FAILED
        return self.result(assertion.assertion_id, assertion.assertion_type, status, expected=expected, actual=url)

    def eval_url_equals(self, assertion, sequence_response) -> Schema__Journey__Assertion__Result:
        url      = self.terminal_url(sequence_response)
        expected = str(assertion.expected)
        if url is None:
            return self.result(assertion.assertion_id, assertion.assertion_type, Enum__Assertion__Status.ERROR,
                               expected=expected, error_message='no get_url step result to read terminal URL')
        status = Enum__Assertion__Status.PASSED if url == expected else Enum__Assertion__Status.FAILED
        return self.result(assertion.assertion_id, assertion.assertion_type, status, expected=expected, actual=url)

    def eval_status_code(self, assertion, network_log: List[dict]) -> Schema__Journey__Assertion__Result:
        url_sub  = str(assertion.url_substring) if assertion.url_substring is not None else None
        expected = str(int(assertion.expected_status))
        flow     = self.find_flow(network_log, url_sub)
        if flow is None:
            return self.result(assertion.assertion_id, assertion.assertion_type, Enum__Assertion__Status.ERROR,
                               expected=expected, error_message='no matching flow in network log')
        actual = str(flow.get('response', {}).get('status_code'))
        status = Enum__Assertion__Status.PASSED if actual == expected else Enum__Assertion__Status.FAILED
        return self.result(assertion.assertion_id, assertion.assertion_type, status, expected=expected, actual=actual)

    def eval_http_header(self, assertion, network_log: List[dict]) -> Schema__Journey__Assertion__Result:
        url_sub = str(assertion.url_substring) if assertion.url_substring is not None else None
        header  = str(assertion.header_name)
        flow    = self.find_flow(network_log, url_sub)
        if flow is None:
            return self.result(assertion.assertion_id, assertion.assertion_type, Enum__Assertion__Status.ERROR,
                               expected=header, error_message='no matching flow in network log')
        headers = flow.get('response', {}).get('headers', {}) or {}
        present = any(str(key).lower() == header.lower() for key in headers.keys())
        status  = Enum__Assertion__Status.PASSED if present else Enum__Assertion__Status.FAILED
        return self.result(assertion.assertion_id, assertion.assertion_type, status,
                           expected=header, actual=('present' if present else 'absent'))

    # ── helpers ────────────────────────────────────────────────────────────────
    def terminal_url(self, sequence_response):                                      # last get_url result's url, or None
        if sequence_response is None:
            return None
        for step_result in reversed(list(sequence_response.step_results)):
            url = getattr(step_result, 'url', None)
            if url:
                return str(url)
        return None

    def find_flow(self, network_log: List[dict], url_substring):                    # first flow whose request URL matches
        for flow in network_log:
            request_url = str(flow.get('request', {}).get('url', ''))
            if url_substring and url_substring not in request_url:
                continue
            return flow
        return None

    def result(self, assertion_id, assertion_type, status,                          # build one typed result
                     expected=None, actual=None, error_message=None) -> Schema__Journey__Assertion__Result:
        built = Schema__Journey__Assertion__Result(status=status)
        if assertion_id   is not None: built.assertion_id   = assertion_id
        if assertion_type is not None: built.assertion_type = assertion_type
        if expected       is not None: built.expected       = str(expected)
        if actual         is not None: built.actual         = str(actual)
        if error_message  is not None: built.error_message  = str(error_message)
        return built

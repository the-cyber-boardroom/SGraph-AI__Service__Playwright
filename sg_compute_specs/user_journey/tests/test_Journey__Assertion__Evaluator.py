# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Journey__Assertion__Evaluator (pure logic, real substrate schemas, no mocks)
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.playwright.core.schemas.results.Schema__Step__Result__Get_Url import Schema__Step__Result__Get_Url
from sg_compute_specs.playwright.core.schemas.sequence.Schema__Sequence__Response    import Schema__Sequence__Response
from sg_compute_specs.user_journey.core.evaluator.Journey__Assertion__Evaluator      import Journey__Assertion__Evaluator
from sg_compute_specs.user_journey.core.schemas.enums.Enum__Assertion__Status        import Enum__Assertion__Status


class TestJourneyAssertionEvaluator:

    def seq(self, url):                                                             # a real sequence response with a get_url result
        response = Schema__Sequence__Response()
        response.step_results.append(Schema__Step__Result__Get_Url(url=url))
        return response

    def network_log(self):
        return [{'request' : {'url': 'https://shop.test/cart', 'method': 'GET' },
                 'response': {'status_code': 200, 'headers': {'content-type': 'text/html'}}},
                {'request' : {'url': 'https://shop.test/pay',  'method': 'POST'},
                 'response': {'status_code': 504, 'headers': {'x-trace': 'abc'}}}]

    def test_url_contains_pass_and_fail(self):
        evaluator = Journey__Assertion__Evaluator()
        response  = self.seq('https://shop.test/confirm?ok=1')
        passed = evaluator.evaluate_one({'assertion_type': 'url_contains', 'expected': '/confirm'}, response, [])
        failed = evaluator.evaluate_one({'assertion_type': 'url_contains', 'expected': '/missing'}, response, [])
        assert passed.status == Enum__Assertion__Status.PASSED
        assert failed.status == Enum__Assertion__Status.FAILED
        assert str(passed.actual) == 'https://shop.test/confirm?ok=1'               # actual preserved, not mangled

    def test_url_equals(self):
        evaluator = Journey__Assertion__Evaluator()
        response  = self.seq('https://shop.test/confirm')
        result    = evaluator.evaluate_one({'assertion_type': 'url_equals', 'expected': 'https://shop.test/confirm'}, response, [])
        assert result.status == Enum__Assertion__Status.PASSED

    def test_url_assertion_without_get_url_is_error(self):
        evaluator = Journey__Assertion__Evaluator()
        result    = evaluator.evaluate_one({'assertion_type': 'url_contains', 'expected': '/x'}, Schema__Sequence__Response(), [])
        assert result.status == Enum__Assertion__Status.ERROR

    def test_status_code_equals(self):
        evaluator = Journey__Assertion__Evaluator()
        log       = self.network_log()
        ok   = evaluator.evaluate_one({'assertion_type': 'status_code_equals', 'expected_status': 504, 'url_substring': '/pay'},  None, log)
        bad  = evaluator.evaluate_one({'assertion_type': 'status_code_equals', 'expected_status': 200, 'url_substring': '/pay'},  None, log)
        miss = evaluator.evaluate_one({'assertion_type': 'status_code_equals', 'expected_status': 200, 'url_substring': '/nope'}, None, log)
        assert ok.status   == Enum__Assertion__Status.PASSED
        assert bad.status  == Enum__Assertion__Status.FAILED
        assert miss.status == Enum__Assertion__Status.ERROR

    def test_http_header_present(self):
        evaluator = Journey__Assertion__Evaluator()
        log       = self.network_log()
        present = evaluator.evaluate_one({'assertion_type': 'http_header_present', 'header_name': 'Content-Type', 'url_substring': '/cart'}, None, log)
        absent  = evaluator.evaluate_one({'assertion_type': 'http_header_present', 'header_name': 'X-Nope',       'url_substring': '/cart'}, None, log)
        assert present.status == Enum__Assertion__Status.PASSED
        assert absent.status  == Enum__Assertion__Status.FAILED

    def test_selector_types_are_skipped(self):
        evaluator = Journey__Assertion__Evaluator()
        result    = evaluator.evaluate_one({'assertion_type': 'selector_visible', 'selector': '#main'}, self.seq('https://x.test/'), [])
        assert result.status == Enum__Assertion__Status.SKIPPED

    def test_unknown_type_is_error_not_crash(self):
        evaluator = Journey__Assertion__Evaluator()
        result    = evaluator.evaluate_one({'assertion_type': 'bogus'}, None, [])
        assert result.status == Enum__Assertion__Status.ERROR

    def test_evaluate_batch(self):
        evaluator = Journey__Assertion__Evaluator()
        response  = self.seq('https://shop.test/confirm')
        results   = evaluator.evaluate([{'assertion_type': 'url_contains', 'expected': '/confirm'},
                                        {'assertion_type': 'url_equals',   'expected': 'https://shop.test/confirm'}],
                                       response, [])
        assert len(results) == 2
        assert all(result.status == Enum__Assertion__Status.PASSED for result in results)

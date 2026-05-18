# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Lab__Phase__Not_Ready__Error
# Minimal: subclass of Exception, message format.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.aws.lab.service.Lab__Phase__Not_Ready__Error import Lab__Phase__Not_Ready__Error


class test_Lab__Phase__Not_Ready__Error(TestCase):

    def test_1__is_exception_subclass(self):
        assert issubclass(Lab__Phase__Not_Ready__Error, Exception)

    def test_2__can_be_raised_and_caught(self):
        with self.assertRaises(Lab__Phase__Not_Ready__Error):
            raise Lab__Phase__Not_Ready__Error('test message')

    def test_3__message_preserved(self):
        try:
            raise Lab__Phase__Not_Ready__Error('phase 2b not ready')
        except Lab__Phase__Not_Ready__Error as ex:
            assert 'phase 2b not ready' in str(ex)

    def test_4__stub_teardowns_raise_it(self):
        from sgraph_ai_service_playwright__cli.aws.lab.service.teardown.Lab__Teardown__CF     import Lab__Teardown__CF
        from sgraph_ai_service_playwright__cli.aws.lab.service.teardown.Lab__Teardown__Lambda import Lab__Teardown__Lambda
        from sgraph_ai_service_playwright__cli.aws.lab.service.teardown.Lab__Teardown__ACM   import Lab__Teardown__ACM

        for cls in (Lab__Teardown__CF, Lab__Teardown__Lambda, Lab__Teardown__ACM):
            with self.assertRaises(Lab__Phase__Not_Ready__Error):
                cls().teardown(None)

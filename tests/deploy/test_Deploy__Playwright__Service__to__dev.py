# ═══════════════════════════════════════════════════════════════════════════════
# Lambda deploy test (dev) — SG Playwright Service
#
# Extends the base flow with stage='dev'. Skipped when AWS creds are absent.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                           import TestCase

from tests.deploy.test_Deploy__Playwright__Service__base                                import test_Deploy__Playwright__Service__base


class test_Deploy__Playwright__Service__to__dev(test_Deploy__Playwright__Service__base, TestCase):
    stage = 'dev'

# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Page__Factory
#
# Three test classes:
#   • test_context_kwargs_from_env  — env var → kwargs translation in isolation
#   • test_get_or_create_page       — factory behaviour against a fake browser
#   • test_no_browser_new_context_callers_outside_factory  — DISCIPLINE GUARD
#     that scans the codebase for raw `browser.new_context(` calls. Any
#     callsite outside Page__Factory.py is a blind spot waiting to drift
#     (the @Content debrief ISSUE-A was exactly this: Session__Registry
#     had its own copy that dropped the ignore_https_errors check).
# ═══════════════════════════════════════════════════════════════════════════════

import os
import re
from pathlib  import Path
from unittest import TestCase

from sg_compute_specs.playwright.core.consts.env_vars             import ENV_VAR__IGNORE_HTTPS_ERRORS
from sg_compute_specs.playwright.core.service.Page__Factory       import (
    context_kwargs_from_env,
    get_or_create_page,
)


# ── Fakes ─────────────────────────────────────────────────────────────────────

class _Fake_Page:
    pass


class _Fake_Context:
    def __init__(self, *, has_existing_page=False):
        self.pages = [_Fake_Page()] if has_existing_page else []

    def new_page(self):
        p = _Fake_Page()
        self.pages.append(p)
        return p


class _Fake_Browser:
    def __init__(self, *, has_existing_context=False, has_existing_page=False):
        self.context_kwargs : list = []
        if has_existing_context:
            self._initial_context = _Fake_Context(has_existing_page=has_existing_page)
            self.contexts         = [self._initial_context]
        else:
            self.contexts         = []

    def new_context(self, **kwargs):
        self.context_kwargs.append(kwargs)
        ctx = _Fake_Context()
        self.contexts.append(ctx)
        return ctx


# ── Tier 1: env-var → kwargs translation in isolation ─────────────────────────

class test_context_kwargs_from_env(TestCase):

    def setUp(self):
        self._old = os.environ.pop(ENV_VAR__IGNORE_HTTPS_ERRORS, None)

    def tearDown(self):
        if self._old is not None:
            os.environ[ENV_VAR__IGNORE_HTTPS_ERRORS] = self._old
        else:
            os.environ.pop(ENV_VAR__IGNORE_HTTPS_ERRORS, None)

    def test__no_env_var_returns_empty_dict(self):
        assert context_kwargs_from_env() == {}

    def test__env_var_set_to_1_returns_ignore_https_errors_true(self):
        os.environ[ENV_VAR__IGNORE_HTTPS_ERRORS] = '1'
        assert context_kwargs_from_env() == {'ignore_https_errors': True}

    def test__env_var_set_to_truthy_string_returns_ignore_https_errors_true(self):       # get_env semantics — any non-empty value is truthy
        os.environ[ENV_VAR__IGNORE_HTTPS_ERRORS] = 'true'
        assert context_kwargs_from_env().get('ignore_https_errors') is True

    def test__env_var_explicitly_unset_omits_the_kwarg(self):                            # Default-secure: when not set we don't pass the kwarg at all (Playwright default = validate certs)
        assert 'ignore_https_errors' not in context_kwargs_from_env()


# ── Tier 2: factory behaviour against a fake Browser ──────────────────────────

class test_get_or_create_page(TestCase):

    def setUp(self):
        self._old = os.environ.pop(ENV_VAR__IGNORE_HTTPS_ERRORS, None)

    def tearDown(self):
        if self._old is not None:
            os.environ[ENV_VAR__IGNORE_HTTPS_ERRORS] = self._old
        else:
            os.environ.pop(ENV_VAR__IGNORE_HTTPS_ERRORS, None)

    def test__fresh_browser_creates_context_and_page(self):                              # Fresh launch: no contexts → new_context + new_page
        browser = _Fake_Browser()
        page    = get_or_create_page(browser)
        assert isinstance(page, _Fake_Page)
        assert len(browser.contexts) == 1
        assert browser.context_kwargs[0] == {}                                           # No env → empty kwargs

    def test__env_var_set_passes_ignore_https_errors_to_new_context(self):               # The ISSUE-A reproducer at the factory level
        os.environ[ENV_VAR__IGNORE_HTTPS_ERRORS] = '1'
        browser = _Fake_Browser()
        get_or_create_page(browser)
        assert browser.context_kwargs[0] == {'ignore_https_errors': True}

    def test__existing_context_no_page_reuses_context_creates_page(self):
        browser = _Fake_Browser(has_existing_context=True, has_existing_page=False)
        page    = get_or_create_page(browser)
        assert isinstance(page, _Fake_Page)
        assert browser.context_kwargs == []                                              # new_context NOT called — existing context reused

    def test__existing_context_and_page_returns_existing_page(self):
        browser = _Fake_Browser(has_existing_context=True, has_existing_page=True)
        expected_page = browser._initial_context.pages[0]
        page = get_or_create_page(browser)
        assert page is expected_page                                                     # Existing page returned, no new objects


# ── Tier 3: DISCIPLINE GUARD — scan the codebase for blind-spot regressions ───

class test_no_browser_new_context_callers_outside_factory(TestCase):

    # Allow-listed file paths (relative to repo root). Page__Factory.py legitimately
    # calls browser.new_context(); anything else that does is a blind spot.
    ALLOWED = {
        'sg_compute_specs/playwright/core/service/Page__Factory.py',
    }

    PATTERN = re.compile(r'\bbrowser\.new_context\s*\(')                                 # `browser.new_context(` — the raw API call we want to centralise

    def test__only_Page__Factory_calls_browser_new_context(self):                        # Regression guard. If this test fails, the new caller MUST delegate to Page__Factory.get_or_create_page instead of calling browser.new_context() directly. See @Content debrief 2026-05-31 ISSUE-A for what happens when this discipline lapses.
        repo_root = Path(__file__).resolve().parents[3]
        offenders = []
        scan_root = repo_root / 'sg_compute_specs' / 'playwright' / 'core'
        for py_file in scan_root.rglob('*.py'):
            try:
                text = py_file.read_text(encoding='utf-8')
            except Exception:
                continue
            if self.PATTERN.search(text):
                rel = py_file.relative_to(repo_root).as_posix()
                if rel not in self.ALLOWED:
                    offenders.append(rel)
        assert not offenders, (
            f'browser.new_context(...) called outside Page__Factory.py in: {offenders}.\n'
            f'Use sg_compute_specs.playwright.core.service.Page__Factory.get_or_create_page '
            f'instead — it centralises the ignore_https_errors env-var policy that drifted '
            f'between Sequence__Runner and Session__Registry (ISSUE-A 2026-05-31).')

# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__SG__Repl._match (v0.2.28 — REPL substring fall-back)
# _match() is a module-level function in Cli__SG__Repl.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute.cli.Cli__SG__Repl import _match


OPTIONS = ['credentials', 'osx', 'compute', 'aws-lambda-waker', 'aws-lambda-playwright']


class test__match__prefix(TestCase):

    def test__exact_prefix_returns_prefix_kind(self):
        hits, kind = _match('cred', OPTIONS)
        assert kind  == 'prefix'
        assert 'credentials' in hits

    def test__full_match_returns_prefix_kind(self):
        hits, kind = _match('credentials', OPTIONS)
        assert kind  == 'prefix'
        assert hits  == ['credentials']

    def test__prefix_hit_returns_sorted_list(self):
        hits, kind = _match('aws', OPTIONS)
        assert kind == 'prefix'
        assert hits == sorted(o for o in OPTIONS if o.startswith('aws'))

    def test__prefix_single_hit(self):
        hits, kind = _match('comp', OPTIONS)
        assert kind == 'prefix'
        assert len(hits) == 1
        assert hits[0] == 'compute'


class test__match__substring(TestCase):

    def test__no_prefix_match_falls_to_substring(self):
        hits, kind = _match('lambda', OPTIONS)              # no option starts with 'lambda'
        assert kind == 'substring'
        assert len(hits) >= 1

    def test__substring_match_returns_both_hits(self):
        hits, kind = _match('lambda', OPTIONS)
        assert 'aws-lambda-waker'       in hits
        assert 'aws-lambda-playwright'  in hits

    def test__substring_returns_sorted_list(self):
        hits, kind = _match('lambda', OPTIONS)
        assert hits == sorted(o for o in OPTIONS if 'lambda' in o)

    def test__no_match_returns_empty_list_and_substring(self):
        hits, kind = _match('zzznomatch', OPTIONS)
        assert hits == []
        assert kind == 'substring'

    def test__substring_waker_resolves_uniquely(self):
        hits, kind = _match('waker', OPTIONS)
        assert len(hits) == 1
        assert hits[0]   == 'aws-lambda-waker'
        assert kind      == 'substring'

    def test__substring_playwright_resolves_uniquely(self):
        hits, kind = _match('playwright', OPTIONS)
        assert len(hits) == 1
        assert hits[0]   == 'aws-lambda-playwright'

    def test__empty_prefix_matches_everything(self):
        hits, kind = _match('', OPTIONS)
        assert kind == 'prefix'
        assert set(hits) == set(OPTIONS)


class test__match__empty_options(TestCase):

    def test__empty_options_returns_empty_prefix(self):
        hits, kind = _match('foo', [])
        assert hits == []
        assert kind == 'substring'

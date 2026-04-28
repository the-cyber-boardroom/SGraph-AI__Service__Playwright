# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Schema__Prom__Stack__Create__Request
# Defaults + round-trip via .json() so route serialisation stays stable.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.prometheus.collections.List__Schema__Prom__Scrape__Target import List__Schema__Prom__Scrape__Target
from sgraph_ai_service_playwright__cli.prometheus.collections.List__Str             import List__Str
from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Scrape__Target import Schema__Prom__Scrape__Target
from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Stack__Create__Request import Schema__Prom__Stack__Create__Request


class test_Schema__Prom__Stack__Create__Request(TestCase):

    def test__defaults(self):
        req = Schema__Prom__Stack__Create__Request()
        assert str(req.stack_name)     == ''
        assert str(req.region)         == ''
        assert str(req.instance_type)  == ''
        assert str(req.from_ami)       == ''
        assert str(req.caller_ip)      == ''
        assert req.max_hours           == 1
        assert list(req.scrape_targets) == []                                       # Empty default — service treats as "no static targets baked"

    def test__never_includes_admin_password(self):                                  # P1: Prometheus has no built-in auth; no admin_password field anywhere
        for field in Schema__Prom__Stack__Create__Request.__annotations__:
            assert 'password' not in field.lower(), f'{field} must not introduce a password field'

    def test__round_trip_via_json(self):
        target_hosts = List__Str()
        target_hosts.append('1.2.3.4:8000')
        targets = List__Schema__Prom__Scrape__Target()
        targets.append(Schema__Prom__Scrape__Target(job_name='playwright', targets=target_hosts))
        original = Schema__Prom__Stack__Create__Request(stack_name     = 'prom-quiet-fermi',
                                                         region         = 'eu-west-2',
                                                         instance_type  = 't3.medium',
                                                         caller_ip      = '5.6.7.8',
                                                         max_hours      = 4,
                                                         scrape_targets = targets)
        again = Schema__Prom__Stack__Create__Request.from_json(original.json())
        assert str(again.stack_name)              == 'prom-quiet-fermi'
        assert str(again.region)                  == 'eu-west-2'
        assert str(again.instance_type)           == 't3.medium'                    # Dot preserved
        assert str(again.caller_ip)               == '5.6.7.8'                      # Dotted-quad preserved
        assert again.max_hours                    == 4
        assert len(again.scrape_targets)          == 1
        assert str(again.scrape_targets[0].job_name) == 'playwright'
        assert list(again.scrape_targets[0].targets) == ['1.2.3.4:8000']

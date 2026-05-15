# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-app: Vault_App__Auto_DNS
# Wraps the dev-branch Route 53 service classes for the --with-aws-dns flow of
# `sp vault-app create`. No new boto3 here — everything goes through
# Route53__AWS__Client, Route53__Zone__Resolver, Route53__Authoritative__Checker.
#
# Contract:
#   - run(fqdn, public_ip, on_progress=None) -> Schema__Vault_App__Auto_DNS__Result
#   - Synchronous (the CLI runs this on a thread for parallelism with the EC2 boot).
#   - Never raises — exceptions are captured into the result.error field so the
#     calling thread can surface them after _wait_healthy returns.
#   - on_progress(stage: str, detail: str) — optional UI callback. Stages:
#       'resolving-zone'  | 'upserting'   | 'waiting-insync'  | 'checking-auth'
#       | 'done'          | 'failed'
# ═══════════════════════════════════════════════════════════════════════════════

import time
from typing import Callable, Optional

from osbot_utils.type_safe.Type_Safe                                                  import Type_Safe

from sg_compute_specs.vault_app.schemas.Schema__Vault_App__Auto_DNS__Result            import Schema__Vault_App__Auto_DNS__Result


AUTO_DNS__INSYNC_TIMEOUT_SEC  = 120                                                   # Route 53 typically reaches INSYNC inside 30s; 120s is the conservative ceiling
AUTO_DNS__INSYNC_POLL_SEC     = 2                                                     # 2s tick matches the `sg aws dns records add --wait` UX
AUTO_DNS__RECORD_TTL_SEC      = 60                                                    # short TTL so future record swaps don't get stuck behind stale caches


class Vault_App__Auto_DNS(Type_Safe):

    # Override seams — test substitutes lightweight fakes; prod resolves to real classes lazily
    # to avoid importing aws-dns at module-load time when this code path is unused.
    _aws_client_factory          : Optional[Callable] = None
    _zone_resolver_factory       : Optional[Callable] = None
    _auth_checker_factory        : Optional[Callable] = None

    def _aws_client(self):
        if self._aws_client_factory is not None:
            return self._aws_client_factory()
        from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__AWS__Client import Route53__AWS__Client
        return Route53__AWS__Client()

    def _zone_resolver(self, client):
        if self._zone_resolver_factory is not None:
            return self._zone_resolver_factory(client)
        from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__Zone__Resolver import Route53__Zone__Resolver
        resolver = Route53__Zone__Resolver()
        resolver.aws_client = client
        return resolver

    def _auth_checker(self, client):
        if self._auth_checker_factory is not None:
            return self._auth_checker_factory(client)
        from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__Authoritative__Checker import Route53__Authoritative__Checker
        checker = Route53__Authoritative__Checker()
        checker.aws_client = client
        return checker

    def run(self, fqdn        : str,
                  public_ip   : str,
                  on_progress : Optional[Callable] = None) -> Schema__Vault_App__Auto_DNS__Result:
        result    = Schema__Vault_App__Auto_DNS__Result(fqdn=fqdn, public_ip=public_ip)
        started   = time.time()
        notify    = on_progress or (lambda stage, detail: None)
        try:
            client = self._aws_client()

            notify('resolving-zone', fqdn)
            zone = self._zone_resolver(client).resolve_zone_for_fqdn(fqdn)
            result.zone_id   = str(zone.zone_id)
            result.zone_name = str(zone.name)

            notify('upserting', f'{fqdn} A → {public_ip} (TTL {AUTO_DNS__RECORD_TTL_SEC}s)')
            change = client.upsert_record(zone.zone_id, fqdn, 'A',
                                          [public_ip], ttl=AUTO_DNS__RECORD_TTL_SEC)
            result.change_id = str(change.change_id)

            notify('waiting-insync', result.change_id)
            insync = client.wait_for_change(result.change_id,
                                            timeout       = AUTO_DNS__INSYNC_TIMEOUT_SEC,
                                            poll_interval = AUTO_DNS__INSYNC_POLL_SEC)
            result.insync = (insync.status == 'INSYNC')
            if not result.insync:                                                     # ran out of budget before Route 53 finished propagating to zone NS
                result.error = f'Route 53 change {result.change_id} did not reach INSYNC inside {AUTO_DNS__INSYNC_TIMEOUT_SEC}s'
                notify('failed', result.error)
                return result

            notify('checking-auth', fqdn)
            auth = self._auth_checker(client).check(zone.zone_id, fqdn, 'A', expected=public_ip)
            result.authoritative_pass = bool(auth.passed)
            if not result.authoritative_pass:
                result.error = (f'Route 53 reported INSYNC but only {auth.agreed_count}/{auth.total_count} '
                                f'authoritative nameservers returned {public_ip!r}')
                notify('failed', result.error)
                return result

            notify('done', f'{fqdn} → {public_ip}  insync+authoritative=ok')
            return result
        except Exception as exc:                                                       # never raise out — the CLI joins this on a thread and surfaces error later
            result.error = f'{type(exc).__name__}: {exc}'
            notify('failed', result.error)
            return result
        finally:
            result.elapsed_ms = int((time.time() - started) * 1000)

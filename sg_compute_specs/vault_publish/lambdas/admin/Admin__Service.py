# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish admin — Admin__Service
# Business logic for the admin surface: slug inventory, per-slug status, and the
# 7-step eval (mirrors `sg vp eval`). Returns plain dicts/lists — the route
# classes wrap them in HTML or JSON. Injected into the route classes via
# add_routes(..., admin_service=...).
#
# Type_Safe service (no request state held) — constructed once at cold start.
# ═══════════════════════════════════════════════════════════════════════════════

import socket
import time

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_publish.lambdas.admin.admin__config import admin_zone


class Admin__Service(Type_Safe):

    def zone(self) -> str:
        return admin_zone()

    def list_entries(self) -> list:
        from sg_compute_specs.vault_publish.service.Slug__Registry              import Slug__Registry
        from sg_compute_specs.vault_publish.lambdas.waker.Endpoint__Resolver__EC2 import Endpoint__Resolver__EC2

        registry = Slug__Registry()
        resolver = Endpoint__Resolver__EC2(_registry_factory=lambda: registry)
        out = []
        for slug in registry.list_all():
            entry = registry.get(slug)
            if entry is None:
                continue
            resolution = resolver.resolve(slug)
            out.append({
                'slug'        : str(entry.slug),
                'fqdn'        : str(entry.fqdn),
                'stack_name'  : str(entry.stack_name),
                'region'      : str(entry.region) or str(resolution.region),
                'instance_id' : str(resolution.instance_id),
                'public_ip'   : str(resolution.public_ip),
                'state'       : str(resolution.state),
            })
        return out

    def status(self, slug: str) -> dict:
        from sg_compute_specs.vault_publish.service.Slug__Registry              import Slug__Registry
        from sg_compute_specs.vault_publish.lambdas.waker.Endpoint__Resolver__EC2 import Endpoint__Resolver__EC2

        entry      = Slug__Registry().get(slug)
        resolution = Endpoint__Resolver__EC2().resolve(slug)
        return {
            'slug'        : slug,
            'fqdn'        : str(entry.fqdn) if entry else '',
            'stack_name'  : str(entry.stack_name) if entry else '',
            'region'      : str(entry.region) if entry else str(resolution.region),
            'instance_id' : str(resolution.instance_id),
            'public_ip'   : str(resolution.public_ip),
            'vault_url'   : str(resolution.vault_url),
            'state'       : str(resolution.state),
        }

    def waker_state(self, slug: str) -> dict:
        # Equivalent of the waker /__waker__/probe payload — used by warming
        # pages cross-origin (the public, auth-free /api/v1/status endpoint).
        from sg_compute_specs.vault_publish.lambdas.waker.Endpoint__Resolver__EC2 import Endpoint__Resolver__EC2
        from sg_compute_specs.vault_publish.lambdas.waker.schemas.Enum__Instance__State import Enum__Instance__State
        from sg_compute_specs.vault_publish.lambdas.waker.Waker__Handler          import health_probe

        resolution = Endpoint__Resolver__EC2().resolve(slug)
        state      = resolution.state
        if state == Enum__Instance__State.UNKNOWN:
            waker_state = 'not_found'
        elif (state == Enum__Instance__State.RUNNING
              and resolution.vault_url
              and health_probe(resolution.vault_url)):
            waker_state = 'proxied'
        else:
            waker_state = 'warming'
        return {
            'slug'        : slug,
            'waker_state' : waker_state,
            'ec2_state'   : str(state),
            'instance_id' : str(resolution.instance_id),
            'public_ip'   : str(resolution.public_ip),
            'region'      : str(resolution.region),
        }

    def eval(self, slug: str) -> list:
        # Mirrors `sg vp eval`'s 7 steps. Each step: {n, label, ok, detail}.
        from sg_compute_specs.vault_publish.service.Slug__Registry              import Slug__Registry
        from sg_compute_specs.vault_publish.lambdas.waker.Endpoint__Resolver__EC2 import Endpoint__Resolver__EC2
        from sg_compute_specs.vault_publish.lambdas.waker.schemas.Enum__Instance__State import Enum__Instance__State
        from sg_compute_specs.vault_publish.lambdas.waker.Waker__Handler          import health_probe

        steps    = []
        fqdn     = f'{slug}.{self.zone()}'
        registry = Slug__Registry()

        entry = registry.get(slug)
        steps.append({'n': 1, 'label': 'slug registered',
                      'ok'    : entry is not None,
                      'detail': f'tag:sg:slug={slug}' if entry else f'no EC2 tagged sg:slug={slug}'})
        if entry is None:
            return steps

        resolution = Endpoint__Resolver__EC2().resolve(slug)
        steps.append({'n': 2, 'label': 'ec2 instance present',
                      'ok'    : resolution.state != Enum__Instance__State.UNKNOWN,
                      'detail': f'{resolution.instance_id} state={resolution.state} ip={resolution.public_ip or "(none)"}'})

        running = (resolution.state == Enum__Instance__State.RUNNING and bool(resolution.public_ip))
        if running and resolution.vault_url:
            ok = health_probe(resolution.vault_url, connect_timeout=2, read_timeout=4)
            steps.append({'n': 3, 'label': 'direct IP reachable', 'ok': ok,
                          'detail': f'{resolution.vault_url}/ui/ → {"healthy" if ok else "failed health probe"}'})
        else:
            steps.append({'n': 3, 'label': 'direct IP reachable', 'ok': False,
                          'detail': 'skipped — instance not RUNNING with public IP'})

        if not self._instance_has_tls_tag(resolution.instance_id, resolution.region):
            steps.append({'n': 4, 'label': 'per-slug DNS record', 'ok': True,
                          'detail': 'skipped — StackTLS=false (record would override CF wildcard)'})
        else:
            try:
                from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__AWS__Client    import Route53__AWS__Client
                from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Route53__Record_Type import Enum__Route53__Record_Type
                r53 = Route53__AWS__Client()
                zone_obj = r53.find_hosted_zone_by_name(self.zone())
                if zone_obj:
                    rec = r53.get_record(str(zone_obj.zone_id), fqdn, Enum__Route53__Record_Type.A)
                    if rec:
                        vals = ', '.join(list(rec.values)) if rec.values else (rec.alias_target or '(alias)')
                        steps.append({'n': 4, 'label': 'per-slug DNS record', 'ok': True, 'detail': f'A {fqdn} → {vals}'})
                    else:
                        steps.append({'n': 4, 'label': 'per-slug DNS record', 'ok': False, 'detail': f'no A record for {fqdn}'})
                else:
                    steps.append({'n': 4, 'label': 'per-slug DNS record', 'ok': False, 'detail': f'hosted zone {self.zone()!r} not found'})
            except Exception as e:
                steps.append({'n': 4, 'label': 'per-slug DNS record', 'ok': False, 'detail': f'lookup failed: {type(e).__name__}'})

        try:
            ips = sorted({a[4][0] for a in socket.getaddrinfo(fqdn, None)})
            steps.append({'n': 5, 'label': 'public DNS resolves', 'ok': True, 'detail': f'{fqdn} → {", ".join(ips[:4])}'})
        except socket.gaierror as e:
            steps.append({'n': 5, 'label': 'public DNS resolves', 'ok': False, 'detail': str(e)})

        https_url = f'https://{fqdn}/'
        try:
            import urllib3
            t0   = time.time()
            resp = urllib3.PoolManager(timeout=urllib3.Timeout(connect=3, read=5)).request(
                'GET', https_url, preload_content=False, retries=False)
            ms   = int((time.time() - t0) * 1000)
            steps.append({'n': 6, 'label': 'HTTPS via CloudFront', 'ok': resp.status < 500,
                          'detail': f'{https_url} → HTTP {resp.status} in {ms}ms'})
            state_h = resp.headers.get('X-Waker-State', '') if resp.headers else ''
            host_h  = resp.headers.get('X-Waker-Host',  '') if resp.headers else ''
            if state_h:
                steps.append({'n': 7, 'label': 'waker headers correct', 'ok': (host_h == fqdn),
                              'detail': f'state={state_h} host={host_h or "(empty)"}'})
            else:
                steps.append({'n': 7, 'label': 'waker headers correct', 'ok': True,
                              'detail': 'no X-Waker-State — request went direct to EC2 (DNS converged)'})
        except Exception as e:
            steps.append({'n': 6, 'label': 'HTTPS via CloudFront', 'ok': False, 'detail': str(e)[:120]})
            steps.append({'n': 7, 'label': 'waker headers correct', 'ok': False, 'detail': 'skipped — HTTPS probe failed'})

        return steps

    def _instance_has_tls_tag(self, instance_id: str, region: str) -> bool:
        if not instance_id or not region:
            return False
        try:
            import boto3
            ec2 = boto3.client('ec2', region_name=region)
            resp = ec2.describe_instances(InstanceIds=[instance_id])
            for res in resp.get('Reservations', []):
                for inst in res.get('Instances', []):
                    for t in inst.get('Tags', []) or []:
                        if t.get('Key') == 'StackTLS':
                            return str(t.get('Value', '')).lower() in ('true', '1', 'yes')
        except Exception:
            return False
        return False

# ═══════════════════════════════════════════════════════════════════════════════
# Waker — Waker__Commands
# Dev-only RPC dispatcher invoked via /__waker__/cmd?name=<cmd>&arg=val…
# Lets the operator ask the running Lambda for state, run diagnostics, and
# (when explicitly gated) trigger small mutations — without rebuilding the
# diagnostic page or shipping a new code path for each ask.
#
# Gates:
#   WAKER_CMD_ENABLED='1' (default '1' — assume dev)         → readable commands
#   WAKER_CMD_MUTATIONS_ENABLED='1' (default unset)          → mutating commands
#
# >>> In prod, set WAKER_CMD_ENABLED='0' on the function config to disable
#     the whole /__waker__/cmd route.
#
# Commands return JSON-serialisable dicts. The dispatcher wraps results with
# the called command name + parsed args so the CLI output is self-describing.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
import sys
from typing import Callable

_REGISTRY = {}                                                                       # name → (handler, description, mutates_bool)


def cmd(name: str, description: str = '', mutates: bool = False) -> Callable:
    """Decorator that registers a command under its short name."""
    def _wrap(fn):
        _REGISTRY[name] = (fn, description, mutates)
        return fn
    return _wrap


def list_commands() -> list:
    return [{'name': n, 'description': d, 'mutates': m}
            for n, (_fn, d, m) in sorted(_REGISTRY.items())]


def dispatch(name: str, args: dict) -> dict:
    if not name:
        return {'error': 'no command name supplied — try ?name=help'}
    if name not in _REGISTRY:
        return {'error': f'unknown command: {name!r}', 'available': [c['name'] for c in list_commands()]}
    fn, _desc, mutates = _REGISTRY[name]
    if mutates and os.environ.get('WAKER_CMD_MUTATIONS_ENABLED', '') not in ('1', 'true', 'yes'):
        return {'error': f'command {name!r} mutates state — set WAKER_CMD_MUTATIONS_ENABLED=1 to enable'}
    try:
        result = fn(args)
        return {'cmd': name, 'args': args, 'result': result}
    except Exception as exc:
        return {'cmd': name, 'args': args, 'error': f'{type(exc).__name__}: {exc}'}


def _safe_tags(raw_tags):
    return {t.get('Key', ''): t.get('Value', '') for t in (raw_tags or [])}


# ── meta ──────────────────────────────────────────────────────────────────────

@cmd('help', 'List every registered command + whether it mutates state.')
def _cmd_help(args):
    return list_commands()


@cmd('health', 'Sanity check that the Lambda is alive (no AWS call).')
def _cmd_health(args):
    from sg_compute_specs.vault_publish.waker.lambda_entry import DEPLOY_INFO, WAKER_VERSION
    return {
        'status'         : 'ok',
        'service'        : 'vault-waker',
        'version'        : WAKER_VERSION,
        'service_version': DEPLOY_INFO.get('service_version', ''),
    }


# ── env + python introspection ────────────────────────────────────────────────

@cmd('env', 'Dump env vars whose key contains <pattern> (default "WAKER_"). Pass pattern="" to dump every env var.')
def _cmd_env(args):
    pattern = args.get('pattern', 'WAKER_')
    return {k: v for k, v in sorted(os.environ.items()) if pattern in k}


@cmd('python-info', 'Python version + executable + first 20 entries of sys.path.')
def _cmd_python_info(args):
    return {
        'version'   : sys.version.splitlines()[0],
        'executable': sys.executable,
        'sys_path'  : sys.path[:20],
        'cwd'       : os.getcwd(),
    }


@cmd('list-files', 'List files (and sizes) under <path> (default: the lambda_entry directory). Truncated at 200 entries.')
def _cmd_list_files(args):
    import sg_compute_specs.vault_publish.waker.lambda_entry as le
    root = args.get('path', '') or os.path.dirname(le.__file__)
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != '__pycache__']
        for f in filenames:
            full = os.path.join(dirpath, f)
            try:
                size = os.path.getsize(full)
            except OSError:
                size = -1
            out.append({'path': os.path.relpath(full, root), 'size': size})
            if len(out) >= 200:
                return {'root': root, 'files': out, 'truncated_at': 200}
    return {'root': root, 'files': out}


@cmd('read-file', 'Read a file from disk (max 64KB). Required arg: path=/abs/path/to/file')
def _cmd_read_file(args):
    path = args.get('path', '')
    if not path:
        return {'error': 'arg "path" required (use list-files to discover paths)'}
    try:
        size = os.path.getsize(path)
        with open(path, 'r', encoding='utf-8', errors='replace') as fh:
            content = fh.read(64 * 1024)
        return {'path': path, 'size': size, 'truncated': size > 64 * 1024, 'content': content}
    except Exception as exc:
        return {'error': str(exc)}


# ── resolver / cache ──────────────────────────────────────────────────────────

@cmd('regions', 'List the regions the resolver currently scans for slug tags.')
def _cmd_regions(args):
    from sg_compute_specs.vault_publish.waker.Endpoint__Resolver__EC2 import _scan_regions
    return {'regions': _scan_regions()}


@cmd('cache', 'Dump the in-process slug → EC2 cache (with TTLs).')
def _cmd_cache(args):
    from sg_compute_specs.vault_publish.waker.Endpoint__Resolver__EC2 import _SLUG_CACHE, _CACHE_TTL
    import time as _t
    now = _t.time()
    entries = {}
    for slug, (inst, region, ts, scan) in _SLUG_CACHE.items():
        entries[slug] = {
            'instance_id'    : inst.get('InstanceId', ''),
            'region'         : region,
            'public_ip'      : inst.get('PublicIpAddress', ''),
            'state'          : inst.get('State', {}).get('Name', ''),
            'cached_at'      : ts,
            'age_sec'        : round(now - ts, 1),
            'ttl_remaining_sec': round(_CACHE_TTL - (now - ts), 1),
            'scan'           : scan,
        }
    return {'entries': entries, 'count': len(entries), 'ttl_sec': _CACHE_TTL}


@cmd('cache-clear', 'Clear the in-process slug cache. Pass slug=<slug> to clear just one entry; omit to clear all.', mutates=True)
def _cmd_cache_clear(args):
    from sg_compute_specs.vault_publish.waker.Endpoint__Resolver__EC2 import _SLUG_CACHE
    slug = args.get('slug', '')
    if slug:
        existed = slug in _SLUG_CACHE
        _SLUG_CACHE.pop(slug, None)
        return {'cleared': 1 if existed else 0, 'slug': slug,
                'note': 'entry not in cache' if not existed else 'cleared'}
    n = len(_SLUG_CACHE)
    _SLUG_CACHE.clear()
    return {'cleared': n, 'scope': 'all'}


# ── EC2 lookups ──────────────────────────────────────────────────────────────

@cmd('find-slug', 'Look for an EC2 with sg:slug=<slug> in all scanned regions, AND also report any matches by StackName=<slug>. Required arg: slug=…')
def _cmd_find_slug(args):
    slug = args.get('slug', '')
    if not slug:
        return {'error': 'arg "slug" required'}
    import boto3
    from sg_compute_specs.vault_publish.waker.Endpoint__Resolver__EC2 import _scan_regions

    states = ['running', 'stopped', 'pending', 'stopping']
    findings = []
    for region in _scan_regions():
        try:
            ec2 = boto3.client('ec2', region_name=region)
            by_slug = ec2.describe_instances(Filters=[
                {'Name': 'tag:sg:slug',            'Values': [slug]},
                {'Name': 'instance-state-name',    'Values': states},
            ])
            by_name = ec2.describe_instances(Filters=[
                {'Name': 'tag:StackName',          'Values': [slug]},
                {'Name': 'instance-state-name',    'Values': states},
            ])
            findings.append({
                'region'       : region,
                'by_sg_slug'   : _flatten_instances(by_slug),
                'by_stack_name': _flatten_instances(by_name),
            })
        except Exception as exc:
            findings.append({'region': region, 'error': str(exc)})
    return {'slug': slug, 'scan': findings}


@cmd('check-slug', 'End-to-end per-slug diagnostic: finds the EC2 (by sg:slug then StackName), reads tags, computes the expected vault URL based on StackTLS, probes it from inside the Lambda, resolves DNS for slug.zone and compares to the EC2 IP. Required arg: slug=…  Optional: zone=aws.sg-labs.app')
def _cmd_check_slug(args):
    slug = args.get('slug', '')
    if not slug:
        return {'error': 'arg "slug" required'}
    zone = args.get('zone', 'aws.sg-labs.app')
    fqdn = f'{slug}.{zone}'
    import boto3, socket, urllib3
    from sg_compute_specs.vault_publish.waker.Endpoint__Resolver__EC2 import (
        _scan_regions, _instance_has_tls, _build_vault_url,
    )

    checks = []
    instance = None
    region   = ''
    # 1. Locate the EC2 — sg:slug first, then StackName fallback
    for r in _scan_regions():
        try:
            ec2 = boto3.client('ec2', region_name=r)
            by_slug = ec2.describe_instances(Filters=[
                {'Name': 'tag:sg:slug',         'Values': [slug]},
                {'Name': 'instance-state-name', 'Values': ['running', 'pending']},
            ])
            for res in by_slug.get('Reservations', []):
                for inst in res.get('Instances', []):
                    instance = inst; region = r
                    checks.append({'step': 'find-ec2', 'pass': True,
                                   'detail': f'matched tag:sg:slug={slug} in {r}',
                                   'iid': inst.get('InstanceId', '')})
                    break
                if instance: break
            if instance: break
            by_name = ec2.describe_instances(Filters=[
                {'Name': 'tag:StackName',       'Values': [slug]},
                {'Name': 'instance-state-name', 'Values': ['running', 'pending']},
            ])
            for res in by_name.get('Reservations', []):
                for inst in res.get('Instances', []):
                    instance = inst; region = r
                    checks.append({'step': 'find-ec2', 'pass': True,
                                   'detail': f'matched tag:StackName={slug} in {r} '
                                              f'(sg:slug tag missing — was this created via `sg va create`? '
                                              f'Run `tag-slug iid={inst.get("InstanceId","")} slug={slug}` to fix)',
                                   'iid': inst.get('InstanceId', '')})
                    break
                if instance: break
            if instance: break
        except Exception as exc:
            checks.append({'step': 'find-ec2', 'pass': False, 'detail': f'{r}: {exc}'})
    if not instance:
        checks.append({'step': 'find-ec2', 'pass': False,
                       'detail': f'no EC2 with sg:slug or StackName = {slug} in any scanned region'})
        return {'slug': slug, 'fqdn': fqdn, 'checks': checks}

    tags = {t.get('Key',''): t.get('Value','') for t in instance.get('Tags', [])}
    pub_ip = instance.get('PublicIpAddress', '')
    state  = instance.get('State', {}).get('Name', '')
    tls    = _instance_has_tls(instance)
    vault_url = _build_vault_url(pub_ip, tls=tls)

    checks.append({'step': 'ec2-state', 'pass': state == 'running',
                   'detail': f'state={state} public_ip={pub_ip or "(none)"}'})
    checks.append({'step': 'ec2-tags', 'pass': bool(tags.get('sg:slug')),
                   'detail': f'sg:slug={tags.get("sg:slug","(missing)")} '
                              f'sg:fqdn={tags.get("sg:fqdn","(missing)")} '
                              f'StackTLS={tags.get("StackTLS","(missing)")}'})
    checks.append({'step': 'expected-vault-url', 'pass': bool(vault_url),
                   'detail': f'{vault_url}   (StackTLS={"on" if tls else "off"})'})

    # 2. Probe vault URL from inside the Lambda
    if vault_url:
        try:
            t0 = __import__('time').time()
            http = urllib3.PoolManager(cert_reqs='CERT_NONE',
                                       assert_hostname=False,
                                       timeout=urllib3.Timeout(connect=2, read=5))
            import warnings; warnings.filterwarnings('ignore')
            resp = http.request('GET', vault_url, preload_content=False, retries=False)
            ms = int((__import__('time').time() - t0) * 1000)
            checks.append({'step': 'probe-vault-url', 'pass': resp.status < 500,
                           'detail': f'HTTP {resp.status} in {ms}ms'})
        except Exception as exc:
            checks.append({'step': 'probe-vault-url', 'pass': False, 'detail': str(exc)[:160]})

    # 3. DNS lookup of slug.zone — compare to EC2 IP
    try:
        infos = socket.getaddrinfo(fqdn, None)
        dns_ips = sorted({a[4][0] for a in infos})
        is_ec2 = pub_ip in dns_ips if pub_ip else False
        is_cf  = any(ip.startswith('18.154.') or ip.startswith('99.86.') or
                     ip.startswith('13.224.') or ip.startswith('52.84.')
                     for ip in dns_ips)
        if is_ec2:
            detail = f'{fqdn} → {dns_ips} — matches EC2 IP ✓'
            ok = True
        elif is_cf:
            detail = (f'{fqdn} → {dns_ips} — resolves to CloudFront wildcard, '
                       f'no per-slug A record pointing at {pub_ip}. '
                       f'For direct HTTPS / Let\'s Encrypt validation, create an A record: '
                       f'`sg vp dns {slug}` to inspect, or re-run `sg vp register {slug}` '
                       f'(which creates the per-slug A record).')
            ok = False
        else:
            detail = f'{fqdn} → {dns_ips} — does NOT match EC2 IP {pub_ip}'
            ok = False
        checks.append({'step': 'dns-resolution', 'pass': ok, 'detail': detail})
    except Exception as exc:
        checks.append({'step': 'dns-resolution', 'pass': False, 'detail': str(exc)})

    all_pass = all(c.get('pass') for c in checks)
    return {
        'slug'        : slug,
        'fqdn'        : fqdn,
        'region'      : region,
        'instance_id' : instance.get('InstanceId', ''),
        'public_ip'   : pub_ip,
        'state'       : state,
        'tls'         : tls,
        'vault_url'   : vault_url,
        'tags'        : tags,
        'all_pass'    : all_pass,
        'checks'      : checks,
    }


@cmd('describe-instance', 'Describe a specific EC2 by InstanceId. Required arg: iid=i-xxxx. Optional: region=eu-west-2 (otherwise scans).')
def _cmd_describe_instance(args):
    iid = args.get('iid', '') or args.get('instance_id', '')
    if not iid:
        return {'error': 'arg "iid" required'}
    import boto3
    from sg_compute_specs.vault_publish.waker.Endpoint__Resolver__EC2 import _scan_regions
    region = args.get('region', '')
    regions = [region] if region else _scan_regions()
    for r in regions:
        try:
            ec2  = boto3.client('ec2', region_name=r)
            resp = ec2.describe_instances(InstanceIds=[iid])
            for res in resp.get('Reservations', []):
                for inst in res.get('Instances', []):
                    return {
                        'region'      : r,
                        'instance_id' : inst.get('InstanceId', ''),
                        'state'       : inst.get('State', {}).get('Name', ''),
                        'instance_type': inst.get('InstanceType', ''),
                        'public_ip'   : inst.get('PublicIpAddress', ''),
                        'private_ip'  : inst.get('PrivateIpAddress', ''),
                        'launch_time' : str(inst.get('LaunchTime', '')),
                        'image_id'    : inst.get('ImageId', ''),
                        'tags'        : _safe_tags(inst.get('Tags')),
                    }
        except Exception:
            continue
    return {'error': f'instance {iid!r} not found in regions {regions}'}


# ── EC2 mutations (gated) ─────────────────────────────────────────────────────

@cmd('tag-slug', 'Add sg:slug + sg:fqdn + sg:zone tags to an existing EC2 instance — recovery path for instances created via `sg va create` (which omits these tags). Required args: iid=i-xxxx, slug=…, zone=aws.sg-labs.app. Optional: region.', mutates=True)
def _cmd_tag_slug(args):
    iid  = args.get('iid', '')
    slug = args.get('slug', '')
    zone = args.get('zone', 'aws.sg-labs.app')
    if not iid or not slug:
        return {'error': 'args "iid" and "slug" both required'}
    fqdn = f'{slug}.{zone}'
    import boto3
    from sg_compute_specs.vault_publish.waker.Endpoint__Resolver__EC2 import _scan_regions
    region = args.get('region', '')
    regions = [region] if region else _scan_regions()
    for r in regions:
        try:
            ec2 = boto3.client('ec2', region_name=r)
            # Confirm the instance exists in this region before tagging
            ec2.describe_instances(InstanceIds=[iid])
            ec2.create_tags(
                Resources=[iid],
                Tags=[
                    {'Key': 'sg:slug', 'Value': slug},
                    {'Key': 'sg:fqdn', 'Value': fqdn},
                    {'Key': 'sg:zone', 'Value': zone},
                ],
            )
            # Invalidate any cached entry for this slug so the next request
            # re-scans and picks up the new tags immediately.
            from sg_compute_specs.vault_publish.waker.Endpoint__Resolver__EC2 import _SLUG_CACHE
            _SLUG_CACHE.pop(slug, None)
            return {'tagged': iid, 'region': r, 'sg:slug': slug, 'sg:fqdn': fqdn,
                    'sg:zone': zone, 'cache_invalidated': True}
        except Exception:
            continue
    return {'error': f'instance {iid!r} not found in regions {regions}'}


@cmd('start-instance', 'Start a stopped EC2. Required: iid=i-xxxx. Optional: region.', mutates=True)
def _cmd_start_instance(args):
    iid = args.get('iid', '')
    if not iid:
        return {'error': 'arg "iid" required'}
    import boto3
    from sg_compute_specs.vault_publish.waker.Endpoint__Resolver__EC2 import _scan_regions
    region = args.get('region', '')
    regions = [region] if region else _scan_regions()
    for r in regions:
        try:
            boto3.client('ec2', region_name=r).start_instances(InstanceIds=[iid])
            return {'started': iid, 'region': r}
        except Exception:
            continue
    return {'error': f'failed to start {iid!r} in regions {regions}'}


# ── network probes from inside the Lambda ────────────────────────────────────

@cmd('dns-query', 'Resolve a hostname from inside the Lambda (uses socket.getaddrinfo). Required arg: host=foo.example.com')
def _cmd_dns_query(args):
    host = args.get('host', '')
    if not host:
        return {'error': 'arg "host" required'}
    import socket
    try:
        infos = socket.getaddrinfo(host, None)
        ips = sorted({a[4][0] for a in infos})
        return {'host': host, 'ips': ips}
    except Exception as exc:
        return {'host': host, 'error': str(exc)}


@cmd('http-get', 'HTTP GET from inside the Lambda (response truncated to 4KB). Required arg: url=https://…')
def _cmd_http_get(args):
    url = args.get('url', '')
    if not url:
        return {'error': 'arg "url" required'}
    import urllib3
    try:
        resp = urllib3.PoolManager(timeout=urllib3.Timeout(connect=2, read=5)).request(
            'GET', url, preload_content=True, retries=False)
        body = resp.data[:4096]
        try:    body_str = body.decode('utf-8')
        except Exception: body_str = repr(body)
        return {
            'url'        : url,
            'status'     : resp.status,
            'headers'    : dict(resp.headers),
            'body_bytes' : len(resp.data),
            'body'       : body_str,
            'truncated'  : len(resp.data) > 4096,
        }
    except Exception as exc:
        return {'url': url, 'error': str(exc)}


# ── internal helpers ──────────────────────────────────────────────────────────

def _flatten_instances(resp: dict) -> list:
    out = []
    for res in (resp or {}).get('Reservations', []):
        for inst in res.get('Instances', []):
            out.append({
                'instance_id': inst.get('InstanceId', ''),
                'state'      : inst.get('State', {}).get('Name', ''),
                'public_ip'  : inst.get('PublicIpAddress', ''),
                'launch_time': str(inst.get('LaunchTime', '')),
                'tags'       : _safe_tags(inst.get('Tags')),
            })
    return out

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


@cmd('cache-clear', 'Clear the in-process slug cache (forces a fresh scan on next request).', mutates=True)
def _cmd_cache_clear(args):
    from sg_compute_specs.vault_publish.waker.Endpoint__Resolver__EC2 import _SLUG_CACHE
    n = len(_SLUG_CACHE)
    _SLUG_CACHE.clear()
    return {'cleared': n}


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
            return {'tagged': iid, 'region': r, 'sg:slug': slug, 'sg:fqdn': fqdn, 'sg:zone': zone}
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

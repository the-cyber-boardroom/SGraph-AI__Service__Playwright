# OpenSearch Index Pattern Creation — Debug Session

**Date:** 2026-04-24  
**Branch:** `claude/secure-nginx-vnc-proxy-FE75Q`  
**Stack:** `sp-observe-1` (AWS OpenSearch Service, eu-west-2)

---

## What We Are Trying to Do

Create an **index pattern** (also called a "Data View") in OpenSearch Dashboards so that the `sg-playwright-logs` index — which is confirmed to contain data — becomes queryable via Discover and the imported dashboards.

The index pattern must have:
- **Title / pattern:** `sg-playwright-logs`
- **Time field:** `@timestamp`

---

## Current State

| What | Status |
|------|--------|
| `sg-playwright-logs` index exists with docs | ✅ confirmed (134 docs at first check, growing) |
| Dashboards + visualizations imported | ✅ 6 objects in **global** tenant |
| Index pattern visible in Dashboards UI | ❌ "No items found" even on Global tenant |

The UI user is **admin**, tenant **Global**. Switching tenants does not help.

---

## What Has Been Tried (all failed silently)

### Strategy 1 — Dashboards REST API (`_DV_TRIES` loop)

`scripts/observability.py` `_do_import_os_saved_objects()` tries these POST endpoints in order, stopping at the first HTTP < 300:

```
POST /_dashboards/api/data_views/data_view
     body: {"data_view": {"title": "sg-playwright-logs", "timeFieldName": "@timestamp",
                          "id": "sg-playwright-logs"}, "override": true}

POST /_dashboards/api/index_patterns/index_pattern
     body: {"index_pattern": {"title": "sg-playwright-logs", "timeFieldName": "@timestamp"},
            "override": true}

POST /_dashboards/api/saved_objects/data-view/sg-playwright-logs?overwrite=true&security_tenant=global
     body: {"attributes": {"title": "sg-playwright-logs", "timeFieldName": "@timestamp"}}

POST /_dashboards/api/saved_objects/index-pattern/sg-playwright-logs?overwrite=true&security_tenant=global
     body: {"attributes": {"title": "sg-playwright-logs", "timeFieldName": "@timestamp",
                           "fields": "[]"}}
```

Headers on all calls:
```
Content-Type: application/json
osd-xsrf: true
securitytenant: global
```

Auth: none (IAM-based caller, no admin_user/pass provided).

**Result:** The first endpoint (`/api/data_views/data_view`) returns HTTP 200. But immediately reading it back via:
```
GET /_dashboards/api/data_views/data_view/sg-playwright-logs
GET /_dashboards/api/saved_objects/index-pattern/sg-playwright-logs
GET /_dashboards/api/saved_objects/_find?type=index-pattern&per_page=100
GET /_dashboards/api/saved_objects/_find?type=data-view&per_page=100
```
…returns nothing. The POST is a **silent no-op** — accepted but not persisted.

### Strategy 2 — Direct system index write via basic auth

```python
for idx in ('.opensearch_dashboards', '.opensearch_dashboards_1', '.kibana', '.kibana_1'):
    PUT https://{endpoint}/{idx}/_doc/index-pattern:sg-playwright-logs?refresh=true
    body: {"type": "index-pattern",
           "index-pattern": {"title": "sg-playwright-logs", "timeFieldName": "@timestamp",
                              "fields": "[]"},
           "references": [], "namespaces": ["default"]}
```

**Not tried yet** — this path requires `--admin-user`/`--admin-pass` (master credentials).  
The import has been run without those flags.

### Strategy 3 — Direct system index write via SigV4 (IAM)

Same PUT as Strategy 2 but signed with the caller's IAM credentials (`SigV4Auth(creds, 'es', region)`).

**Result:** The code attempts this and `_sys_idx_write_sigv4()` reports the status codes via `c.print(f'sigv4 sys-idx {idx}: HTTP {resp.status_code}')` — but these lines are currently printed at `[dim]` level only when the write FAILS. Since the output shows "✓ Data View created", the code path that reaches SigV4 may not be executing (the false-positive 200 from Strategy 1 is stopping it).

**This is the next thing to verify.**

---

## The Key Hypothesis

The `POST /api/data_views/data_view` returns 200 but does not persist. The `_verify_index_pattern_exists()` read-back should catch this and set `dv_ok = False`, which would fall through to the SigV4 write. But the output still says "✓ Data View created" — meaning either:

**a)** `_verify_index_pattern_exists()` itself has a bug (returns `True` when it shouldn't), OR  
**b)** The SigV4 write then runs but also silently succeeds (HTTP 200) yet the index pattern still doesn't appear, OR  
**c)** The code has not been reloaded / old version is running

The most important thing to establish first: **which code path is actually executing and what HTTP status codes are being returned at each step**.

---

## Debug Commands to Run Against the Live Stack

### 0. Get the endpoint

```bash
python3 scripts/provision_ec2.py ob info sp-observe-1 2>&1 | grep -i endpoint
# OR:
export OS_ENDPOINT=$(aws opensearch describe-domain --domain-name sp-observe-1 \
  --query 'DomainStatus.Endpoints.vpc // DomainStatus.Endpoint' \
  --output text --region eu-west-2)
echo $OS_ENDPOINT
```

### 1. Can we reach the cluster at all?

```bash
# SigV4 signed — should return cluster health
python3 -c "
import boto3, requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
endpoint = '$OS_ENDPOINT'   # fill in
url = f'https://{endpoint}/_cluster/health'
session = boto3.Session()
creds = session.get_credentials()
req = AWSRequest(method='GET', url=url, headers={'Content-Type': 'application/json'})
SigV4Auth(creds, 'es', 'eu-west-2').add_auth(req)
r = requests.get(url, headers=dict(req.headers), timeout=15)
print(r.status_code, r.text[:300])
"
```

### 2. Does the system index exist and what's in it?

```bash
# List all system indices
python3 -c "
import boto3, requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
endpoint = '$OS_ENDPOINT'
for idx in ('.opensearch_dashboards', '.opensearch_dashboards_1', '.kibana', '.kibana_1'):
    url = f'https://{endpoint}/{idx}/_count'
    session = boto3.Session()
    creds = session.get_credentials()
    req = AWSRequest(method='GET', url=url, headers={'Content-Type': 'application/json'})
    SigV4Auth(creds, 'es', 'eu-west-2').add_auth(req)
    r = requests.get(url, headers=dict(req.headers), timeout=15)
    print(f'{idx}: HTTP {r.status_code}  {r.text[:200]}')
"
```

### 3. What objects are actually in the system index?

```bash
python3 -c "
import boto3, requests, json
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
endpoint = '$OS_ENDPOINT'
# Search for index-pattern type docs
for idx in ('.opensearch_dashboards', '.opensearch_dashboards_1'):
    url = f'https://{endpoint}/{idx}/_search?q=type:index-pattern'
    session = boto3.Session()
    creds = session.get_credentials()
    req = AWSRequest(method='GET', url=url, headers={'Content-Type': 'application/json'})
    SigV4Auth(creds, 'es', 'eu-west-2').add_auth(req)
    r = requests.get(url, headers=dict(req.headers), timeout=15)
    print(f'{idx}: HTTP {r.status_code}')
    if r.status_code < 300:
        hits = r.json().get('hits', {}).get('hits', [])
        print(f'  {len(hits)} index-pattern docs found')
        for h in hits:
            print(f'  id={h[\"_id\"]}  source_keys={list(h[\"_source\"].keys())}')
    else:
        print(f'  {r.text[:200]}')
"
```

### 4. Can we write an index-pattern doc directly via SigV4?

```bash
python3 -c "
import boto3, requests, json
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
endpoint = '$OS_ENDPOINT'
doc = {
    'type': 'index-pattern',
    'index-pattern': {'title': 'sg-playwright-logs', 'timeFieldName': '@timestamp', 'fields': '[]'},
    'references': [], 'namespaces': ['default']
}
body = json.dumps(doc).encode()
for idx in ('.opensearch_dashboards', '.opensearch_dashboards_1'):
    url = f'https://{endpoint}/{idx}/_doc/index-pattern:sg-playwright-logs?refresh=true'
    session = boto3.Session()
    creds = session.get_credentials()
    req = AWSRequest(method='PUT', url=url, data=body, headers={'Content-Type': 'application/json'})
    SigV4Auth(creds, 'es', 'eu-west-2').add_auth(req)
    r = requests.put(url, data=body, headers=dict(req.headers), timeout=15)
    print(f'{idx}: PUT HTTP {r.status_code}  {r.text[:300]}')
"
```

### 5. Try the Dashboards saved_objects API with admin creds

```bash
# Set these first:
export OB_OS_ADMIN_USER=admin
export OB_OS_ADMIN_PASS='<your-master-password>'

python3 -c "
import os, requests
endpoint = '$OS_ENDPOINT'
base = f'https://{endpoint}/_dashboards'
auth = (os.environ['OB_OS_ADMIN_USER'], os.environ['OB_OS_ADMIN_PASS'])
hdrs = {'Content-Type': 'application/json', 'osd-xsrf': 'true', 'securitytenant': 'global'}

# Try creating
body = {'attributes': {'title': 'sg-playwright-logs', 'timeFieldName': '@timestamp', 'fields': '[]'}}
r = requests.post(f'{base}/api/saved_objects/index-pattern/sg-playwright-logs?overwrite=true',
                  json=body, headers=hdrs, auth=auth, timeout=30)
print(f'POST index-pattern: HTTP {r.status_code}  {r.text[:400]}')

# Read it back
r2 = requests.get(f'{base}/api/saved_objects/index-pattern/sg-playwright-logs',
                  headers=hdrs, auth=auth, timeout=15)
print(f'GET index-pattern: HTTP {r2.status_code}  {r2.text[:400]}')
"
```

### 6. Check what the _find endpoint actually returns

```bash
python3 -c "
import requests
endpoint = '$OS_ENDPOINT'
base = f'https://{endpoint}/_dashboards'
hdrs = {'Content-Type': 'application/json', 'osd-xsrf': 'true', 'securitytenant': 'global'}
for t in ('index-pattern', 'data-view', 'dashboard', 'visualization'):
    r = requests.get(f'{base}/api/saved_objects/_find?type={t}&per_page=100',
                     headers=hdrs, timeout=15)
    print(f'type={t}: HTTP {r.status_code}  total={r.json().get(\"total\") if r.status_code < 300 else \"ERR\"}')
    if r.status_code < 300:
        for o in r.json().get('saved_objects', []):
            print(f'  id={o[\"id\"]}  title={o.get(\"attributes\",{}).get(\"title\")}')
"
```

---

## Relevant Code

| File | Function | What it does |
|------|----------|--------------|
| `scripts/observability.py:849` | `_do_import_os_saved_objects()` | Main import entry point — tries 4 API paths then falls back to system index |
| `scripts/observability.py:770` | `_verify_index_pattern_exists()` | Read-back check after each API POST |
| `scripts/observability.py:801` | `_sys_idx_write()` | Direct PUT to system index with basic auth |
| `scripts/observability.py:827` | `_sys_idx_write_sigv4()` | Direct PUT to system index with SigV4 |
| `scripts/observability.py:1045` | `_check_os_dashboards()` | Health check — queries all three tenants + system index |

---

## Most Likely Root Causes (in order)

1. **`_verify_index_pattern_exists()` returns True incorrectly** — the GET to `/api/data_views/data_view/{id}` may return 200 for any request (e.g. returning an empty object), causing the code to think the creation worked and skip the SigV4 fallback. Add `print(r.status_code, r.text[:200])` after each GET in that function to verify.

2. **SigV4 write to system index is blocked** — AWS OpenSearch may restrict PUT to `.opensearch_dashboards` for the IAM caller role (`playwright-ec2`). The error would be HTTP 403. Strategy 2/3 can be tested directly with command #4 above.

3. **Admin credentials needed** — the system index write with admin/password (Strategy 2) has never been tried. Try command #5 above with `--admin-user admin --admin-pass <pwd>`.

4. **Wrong document structure for this OpenSearch version** — the `index-pattern` key name in the body may need to be `index_pattern` (underscore) or the `namespaces` field may cause a rejection that returns 200 anyway.

---

## To Run the Import With Verbose Debugging

Add temporary print statements to `scripts/observability.py` around the critical paths, then re-run:

```bash
# Quick inline diagnostic (no code change needed):
python3 -c "
from scripts.observability import _do_import_os_saved_objects, _os_endpoint, _list_stacks, _verify_index_pattern_exists, OPENSEARCH_INDEX
import requests
from rich.console import Console

region = 'eu-west-2'
stacks = {s['name']: s for s in _list_stacks(region)}
s = stacks['sp-observe-1']
ep = _os_endpoint(s['opensearch'])
base = f'https://{ep}/_dashboards'
hdrs = {'Content-Type': 'application/json', 'osd-xsrf': 'true', 'securitytenant': 'global'}

print('Endpoint:', ep)
print()

# Test all 4 creation endpoints
urls = [
    (f'{base}/api/data_views/data_view',
     {'data_view': {'title': OPENSEARCH_INDEX, 'timeFieldName': '@timestamp', 'id': OPENSEARCH_INDEX}, 'override': True}),
    (f'{base}/api/index_patterns/index_pattern',
     {'index_pattern': {'title': OPENSEARCH_INDEX, 'timeFieldName': '@timestamp'}, 'override': True}),
    (f'{base}/api/saved_objects/data-view/{OPENSEARCH_INDEX}?overwrite=true&security_tenant=global',
     {'attributes': {'title': OPENSEARCH_INDEX, 'timeFieldName': '@timestamp'}}),
    (f'{base}/api/saved_objects/index-pattern/{OPENSEARCH_INDEX}?overwrite=true&security_tenant=global',
     {'attributes': {'title': OPENSEARCH_INDEX, 'timeFieldName': '@timestamp', 'fields': '[]'}}),
]
for url, body in urls:
    r = requests.post(url, json=body, headers=hdrs, timeout=30)
    print(f'POST {url.split(\"/_dashboards\")[1][:60]}: HTTP {r.status_code}')
    print(f'  body: {r.text[:200]}')
    
    # Read back
    verified = _verify_index_pattern_exists(base, hdrs, None)
    print(f'  verify: {verified}')
    print()
    if r.status_code < 300:
        break
"
```

---

## Expected Fix

Once we know which step is failing and why, the fix will be one of:

- **If verify is a false positive:** fix `_verify_index_pattern_exists()` to check the response body, not just status code
- **If SigV4 system index write is blocked:** either add `es:ESHttpPut` IAM permission on the system index, or require admin creds for dashboard import  
- **If admin creds work:** make `sp ob dashboard-import` prompt for (or document requiring) `--admin-user`/`--admin-pass`
- **If document structure is wrong:** adjust the body format (try without `namespaces`, try `index_pattern` key, etc.)

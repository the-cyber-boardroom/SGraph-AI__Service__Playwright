# `sp vnc` — Tier-1 (code / service)

The pure-logic core. Lives at `sgraph_ai_service_playwright__cli/vnc/`.

## Folder layout

```
cli/vnc/
├── __init__.py
├── primitives/
│   ├── Safe_Str__IP__Address.py                    # Section-local copy
│   ├── Safe_Str__Vnc__Stack__Name.py               # Stack name regex (parity with elastic/os/prom)
│   ├── Safe_Str__Vnc__Password.py                  # URL-safe base64, 16-64 chars
│   └── Safe_Str__Vnc__Interceptor__Source.py       # Permissive 32 KB primitive for inline interceptor source
│
├── enums/
│   ├── Enum__Vnc__Stack__State.py                  # PENDING/RUNNING/READY/TERMINATING/TERMINATED/UNKNOWN
│   └── Enum__Vnc__Interceptor__Kind.py             # NONE / NAME / INLINE  (per N5)
│
├── schemas/
│   ├── Schema__Vnc__Interceptor__Choice.py         # N5 selector — kind + name + inline_source
│   ├── Schema__Vnc__Stack__Create__Request.py      # operator_password + interceptor + region/type/etc
│   ├── Schema__Vnc__Stack__Create__Response.py     # viewer_url, mitmweb_url, operator_password (returned once), interceptor_kind+name
│   ├── Schema__Vnc__Stack__Info.py                 # Public view; defensive no-password test
│   ├── Schema__Vnc__Stack__List.py                 # region + stacks
│   ├── Schema__Vnc__Stack__Delete__Response.py     # Empty fields → caller maps to 404
│   ├── Schema__Vnc__Health.py                      # nginx_ok + mitmweb_ok + flow_count (-1 sentinel)
│   └── Schema__Vnc__Mitm__Flow__Summary.py         # One-line flow summary (per N4 — peek only)
│
├── collections/
│   ├── List__Schema__Vnc__Stack__Info.py
│   └── List__Schema__Vnc__Mitm__Flow__Summary.py
│
├── service/                                        # Tier-1 — pure-logic core
│   ├── Vnc__AWS__Client.py                         # Composition shell + VNC_NAMING + 7 tag constants (incl. sg:interceptor)
│   ├── Vnc__SG__Helper.py                          # SG ingress on port 443 (nginx TLS)
│   ├── Vnc__AMI__Helper.py                         # latest_al2023 + latest_healthy filtered by sg:purpose=vnc
│   ├── Vnc__Instance__Helper.py                    # list/find/terminate
│   ├── Vnc__Tags__Builder.py                       # Pure mapper (7 tags incl. sg:interceptor='none'|'name:{ex}'|'inline')
│   ├── Vnc__Launch__Helper.py                      # run_instance(...); DEFAULT_INSTANCE_TYPE='t3.large'
│   ├── Vnc__HTTP__Base.py                          # requests wrapper (verify=False default; Basic auth seam)
│   ├── Vnc__HTTP__Probe.py                         # 3 probes: nginx_ready / mitmweb_ready / flows_listing
│   ├── Caller__IP__Detector.py                     # checkip.amazonaws.com fetch
│   ├── Random__Stack__Name__Generator.py           # 'vnc-{adj}-{sci}' (vocabulary parity with elastic/os/prom)
│   ├── Vnc__Stack__Mapper.py                       # boto3 detail dict → Schema__Vnc__Stack__Info; decodes sg:interceptor → (kind, name)
│   ├── Vnc__Compose__Template.py                   # 3-service docker-compose.yml — chromium+nginx+mitmproxy
│   ├── Vnc__Interceptor__Resolver.py               # N5 logic — 3 baked example sources inline; resolve() → (source, label)
│   ├── Vnc__User_Data__Builder.py                  # EC2 UserData bash; writes nginx config + htpasswd + TLS cert + interceptor + compose
│   └── Vnc__Service.py                             # Tier-1 orchestrator — composes 8 helpers via setup()
│
├── fast_api/                                       # See doc 03
│   └── routes/
│       ├── Routes__Vnc__Stack.py
│       └── Routes__Vnc__Flows.py
│
└── cli/                                            # See doc 01
    └── Renderers.py
```

## Service composition (Tier-1)

`Vnc__Service.setup()` lazy-wires 8 helpers:

```python
self.aws_client           = Vnc__AWS__Client().setup()        # which itself wires 5 sub-helpers
self.probe                = Vnc__HTTP__Probe(http=Vnc__HTTP__Base())
self.mapper               = Vnc__Stack__Mapper()
self.ip_detector          = Caller__IP__Detector()
self.name_gen             = Random__Stack__Name__Generator()
self.compose_template     = Vnc__Compose__Template()
self.user_data_builder    = Vnc__User_Data__Builder()
self.interceptor_resolver = Vnc__Interceptor__Resolver()
```

Operations exposed:

| Method | Returns |
|---|---|
| `create_stack(request, creator='')` | `Schema__Vnc__Stack__Create__Response` (incl. one-time `operator_password`) |
| `list_stacks(region)` | `Schema__Vnc__Stack__List` |
| `get_stack_info(region, stack_name)` | `Optional[Schema__Vnc__Stack__Info]` (None on miss) |
| `delete_stack(region, stack_name)` | `Schema__Vnc__Stack__Delete__Response` (empty on miss → 404) |
| `health(region, stack_name, username, password)` | `Schema__Vnc__Health` (READY only when both nginx_ok + mitmweb_ok) |
| `flows(region, stack_name, username, password)` | `List__Schema__Vnc__Mitm__Flow__Summary` |

## Compose shape (3 containers on `sg-net`)

- **chromium** (`lscr.io/linuxserver/chromium:latest`) — `CHROME_CLI=--browser=chromium` (per N2); `HTTPS_PROXY=http://mitmproxy:8080`
- **nginx** (`nginx:latest`) — TLS terminator on **port 443**; Basic auth via htpasswd; reverse-proxies `/` → chromium and `/mitmweb/` → mitmproxy
- **mitmproxy** (`mitmproxy/mitmproxy:latest`) — `mitmweb` with `--set=proxyauth=@/opt/sg-vnc/mitm/proxyauth` and `--scripts=/opt/sg-vnc/interceptors/runtime/active.py`

**No secrets in the compose YAML** — locked by test. `MITM_PROXYAUTH` lives in `/opt/sg-vnc/mitm/proxyauth` (host file, mounted ro).

## N5 interceptor wiring

Three baked example sources inline in `Vnc__Interceptor__Resolver`: `header_logger`, `header_injector`, `flow_recorder`. The resolver returns `(source, label)`:

| `Choice.kind` | `source` | `label` (used for tag + response) |
|---|---|---|
| `NONE` (default) | `'# sg-vnc: no interceptor active\n'` | `''` |
| `NAME` | `EXAMPLES[name]` | `name` |
| `INLINE` | operator-provided source verbatim | `'inline'` |

The user-data writes the source to `/opt/sg-vnc/interceptors/runtime/active.py`. Mitmproxy's compose command always loads from that path — selection happens at user-data render time, not at runtime.

## Tests

189 unit tests across `tests/unit/sgraph_ai_service_playwright__cli/vnc/`:
- primitives (10) — including 32 KB Python-source regex
- enums (4) — vocab parity with elastic/os/prom locked
- schemas (24) — round-trip via `.json()` + defensive no-password checks
- collections (6) — type-safety
- AWS helpers (26) — `_Fake_Boto_EC2` subclasses, no mocks
- HTTP base + probe (15) — `_Fake_HTTP` + `_Fake_Response`
- service read paths + flows + create_stack + setup() (38)
- compose template (11) — placeholder contract + secret-hygiene
- interceptor resolver (8) — 3 shapes + defensive on empty inline / unknown name
- user-data builder (15) — placeholder contract + interceptor + nginx config
- launch helper (8)
- routes (15) — see doc 03
- typer + renderers (15) — see doc 01

Pattern reference: every helper has its own focused test file (~80-150 lines), every AWS- and HTTP-touching class is exercised through real `_Fake_*` subclasses (no `unittest.mock`). Mirrors the `sp os` / `sp prom` discipline.

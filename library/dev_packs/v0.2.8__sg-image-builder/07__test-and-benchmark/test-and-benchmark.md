# Test and Benchmark

Tests define what an image must do (P16). Benchmarks measure how fast it does it, at three canonical moments (P17). This doc covers both, since they share infrastructure.

---

## Test architecture

Three layers (mirrors `SGraph-AI__Service__Playwright`):

| Layer | Where | What it tests | Speed |
|---|---|---|---|
| **Unit** | `sg_image_builder__tests/unit/` | One service class with in-memory providers | Fast (hundreds/sec) |
| **Integration** | `sg_image_builder__tests/integration/` | Multiple services with `Storage__Local_Disk` + `Exec_Provider__Twin` | Medium (seconds each) |
| **End-to-end** | `sg_image_builder_specs/<spec>/tests/end_to_end/` | Real AWS, real SSH, real bundle load | Slow (minutes each) |

Plus a fourth implicit layer:

| Layer | Where | What |
|---|---|---|
| **Spec test suite** | `sg_image_builder_specs/<spec>/tests/` | Per-spec test suites (the contract from P16) |

### Unit tests

Pattern lifted from the playwright codebase:

```python
class test_Bundle__Publisher(TestCase):
    def setUp(self):
        self.storage = Storage__In_Memory().setup()
        self.publisher = Bundle__Publisher(storage=self.storage).setup()

    def test__publish__writes_to_ifd_path(self):
        bundle = make_test_bundle(name='example', version='0.1.0', spec='ssh_file_server')
        result = self.publisher.publish(bundle=bundle)

        assert result.bundle_uri.endswith('bundles/ssh_file_server/example/v0/v0.1/v0.1.0/')
        assert self.storage.exists(result.bundle_uri + 'payload.tar.zst')
        assert self.storage.exists(result.bundle_uri + 'manifest.json')
        assert self.storage.exists(result.bundle_uri + 'sidecar.zip')
        assert self.storage.exists(result.bundle_uri + 'publish.json')
```

No mocks, no patches, no `monkeypatch`. Real in-memory implementations. The fast feedback loop is critical for development.

### Integration tests

Wire multiple services together with realistic-but-still-fast providers:

```python
class test__capture_to_publish__round_trip(TestCase):
    def setUp(self):
        self.workspace = Workspace__Init().setup().init(path=temp_dir())
        self.storage = Storage__Local_Disk(uri_root=f'file://{temp_dir()}').setup()
        self.exec = Exec_Provider__Twin().setup()
        self.exec.set_response('uname -a', Schema__Exec__Result(stdout='Linux ...', exit_code=0))
        self.exec.set_response('find /opt/example -newer /tmp/marker',
                                Schema__Exec__Result(stdout='/opt/example/bin/foo\n', exit_code=0))

    def test__full_workflow(self):
        # capture
        diff = Capture__Filesystem(exec_provider=self.exec).setup().capture(...)
        # package
        bundle = Bundle__Packer(...).pack(diff)
        # publish
        result = Bundle__Publisher(storage=self.storage).publish(bundle)
        # resolve
        retrieved = Bundle__Resolver(storage=self.storage).resolve(result.bundle_uri)
        assert retrieved.manifest.payload_sha256 == bundle.manifest.payload_sha256
```

### End-to-end tests

Gated by env var (`SGI_E2E_ENABLED=1`) because they cost money and require AWS creds:

```python
@pytest.mark.skipif(not os.getenv('SGI_E2E_ENABLED'), reason='E2E gated')
class test__ssh_file_server__cold_start(TestCase):
    def test__full_cold_start_under_60s(self):
        # Provision an EC2 from the AL2023 AMI
        # Load the ssh_file_server recipe
        # SSH in, create a file, read it, delete it
        # Assert all 4 steps complete in < 60s total
```

E2E tests are the only ones that touch real AWS. CI runs them on a schedule (nightly) plus on tags, not on every PR.

### Spec test suites

Each spec owns its test suite:

```
sg_image_builder_specs/ssh_file_server/
└── tests/
    ├── unit/                        Tests that run on the host machine
    ├── integration/                 Tests run against a target via Exec_Provider__Twin
    └── end_to_end/                  Tests run against a real instance
```

These suites are what `sgi test run <spec>` invokes. They are also the suites that `sgi strip` uses for verification (P16, P6).

---

## Test conventions

- **One assert per test** where possible. If a test has 10 asserts, it should probably be 10 tests.
- **No mocks of sgi's own classes.** Use real in-memory providers. If a test needs a mock of an sgi class, that's a smell — the class probably has the wrong boundaries.
- **Tests check structured results, not log output.** Asserting on text in stdout is brittle and changes-resistant.
- **Coverage target: 90%+** for the core `sg_image_builder/` package. Spec tests don't have a coverage target — they're a black-box contract.
- **Test names:** `test__<scenario>__<expected_outcome>` for unit; `test__<workflow>` for integration; `test__<requirement>` for E2E.

---

## Benchmark architecture

Three canonical performance moments (P17), measured separately and aggregated:

| Moment | Measures | Typical scale |
|---|---|---|
| **first_load** | Pulling bundles from Storage to a fresh target; extracting | 10s of seconds |
| **boot** | Bundle on disk → service responds to health check | 10s of seconds |
| **execution** | One workload-defined operation, once the service is running | ms to seconds |

Plus the composite:

| Moment | Measures |
|---|---|
| **cold_start** | EC2 provisioning + first_load + boot + first execution |

### Benchmark schemas

```python
class Schema__Benchmark__Run(Type_Safe):
    run_id           : Safe_Str
    spec             : Safe_Str
    bundle_uri       : Optional[Safe_Str]                = None
    workload         : Optional[Safe_Str]                = None               # for execution benchmarks
    target_type      : Safe_Str                          # 'g5.xlarge', 't3.micro', etc.
    purchase         : Safe_Str                          # 'on-demand', 'spot'
    region           : Safe_Str
    az               : Safe_Str
    started_at       : Safe_Str
    completed_at     : Safe_Str
    measurements     : Schema__Benchmark__Measurements

class Schema__Benchmark__Measurements(Type_Safe):
    first_load_ms    : Optional[float]                   = None
    boot_ms          : Optional[float]                   = None
    execution_ms     : Optional[float]                   = None
    cold_start_ms    : Optional[float]                   = None
    sub_timings      : Dict[Safe_Str, float]             = {}                 # named sub-steps
```

`sub_timings` captures the breakdown:

```json
{
  "ec2_run_instances": 540,
  "ec2_to_ssh_ready": 16800,
  "bundle_download_runtime": 3200,
  "bundle_download_model": 22100,
  "bundle_extract": 4800,
  "service_start": 3200,
  "first_inference": 1900
}
```

### Storage of results

```
workspace/benchmarks/
├── 2026-05-11__143202__cold-start__vllm-disk.json     ← one run
├── 2026-05-11__143815__cold-start__vllm-disk.json
└── ...
```

`sgi benchmark report` aggregates across files with filtering (`--spec`, `--since`, `--target-type`).

### Sub-step timing

Inside any operation, the `Timing__Tracker` context manager records named sub-steps:

```python
class Timing__Tracker(Type_Safe):
    timings : Dict[Safe_Str, float] = {}

    @contextmanager
    def step(self, name: Safe_Str):
        t0 = time.perf_counter()
        yield
        self.timings[name] = round((time.perf_counter() - t0) * 1000, 3)
```

Used:

```python
tracker = Timing__Tracker()
with tracker.step('bundle_download_runtime'):
    self.downloader.download(runtime_uri)
with tracker.step('bundle_download_model'):
    self.downloader.download(model_uri)
# tracker.timings goes into the benchmark sub_timings
```

### Why three moments matter

A single "cold start" number hides the trade-offs. Concrete example from the EBS findings work:

- DLAMI's cold start was 37s, AL2023's was 17s
- Both are "cold start", but the cause was different
- DLAMI: 30s boot + 7s post-boot
- AL2023: 15s boot + 2s post-boot
- "boot" is where DLAMI's bigger snapshot costs you (lazy load); post-boot is irrelevant

Three moments expose this. One moment hides it.

### KPI checks

Each spec declares KPIs in `Schema__Recipe__KPIs`. After a benchmark run:

```python
class Schema__Benchmark__KPI__Check(Type_Safe):
    moment           : Safe_Str                          # 'first_load' | 'boot' | etc.
    target_p50_ms    : float
    target_p95_ms    : float
    actual_p50_ms    : float
    actual_p95_ms    : float
    passed           : bool

class Schema__Benchmark__Report(Type_Safe):
    spec             : Safe_Str
    period_start     : Safe_Str
    period_end       : Safe_Str
    run_count        : int
    kpi_checks       : List[Schema__Benchmark__KPI__Check]
    overall_passed   : bool
```

`sgi benchmark report --spec vllm_disk` produces this and exit-codes accordingly. CI uses this to gate releases — a recipe that fails its KPIs doesn't get a release tag.

---

## Visualisation integration

The event bus (`Events__Emitter`) emits structured events during every benchmark run. The `Events__Sink__Elasticsearch` ships them to an existing ES instance (assumed to be the sg-compute Elastic spec):

```python
class Schema__Event(Type_Safe):
    event_id         : Safe_Str
    kind             : Safe_Str                          # 'capture.started', 'bundle.uploaded', 'benchmark.first_load.completed'
    operation_id     : Safe_Str                          # ties events from one workflow together
    spec             : Optional[Safe_Str]                = None
    timestamp        : Safe_Str
    attributes       : Dict[Safe_Str, Any]               = {}                 # event-specific payload
```

Kibana dashboards (delivered as JSON definitions in the repo) visualise:

- Cold-start trend by spec over time
- First-load distribution per spec per region
- Strip mode comparison: full vs debug vs service vs minimal
- Failure-rate by spec

These dashboards are part of the deliverable. They live in `docs/kibana-dashboards/` and are importable via the Kibana API.

---

## v1 simplifications

- E2E tests run only against `eu-west-2`. Multi-region testing is v2.
- The Elasticsearch sink is optional. v1 default is `Events__Sink__JSONL`.
- KPI gates are advisory only in v0.1. Release gating starts at v0.2 once we have baseline data.
- Benchmark reports are CLI-rendered tables; web dashboards are v2.

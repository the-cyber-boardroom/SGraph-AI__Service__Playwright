# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish: Cli__Vault_Publish
# Typer app for `sg vp` / `sg vault-publish` commands.
#   register  : publish a vault-app stack under a slug + FQDN
#   adopt     : take ownership of an existing EC2 — tag it + create DNS A record
#               (recovery path for instances created via `sg va create`)
#   unpublish : remove slug, stack, and DNS record
#   status    : show EC2 state + FQDN for a slug
#   list      : list all registered slugs (vault keys redacted)
#   wake      : do what the Lambda does — resolve slug, start EC2 if stopped,
#               wait until running + healthy
#   dns       : DNS diagnostics for a slug (Route 53 record + dig-equivalent)
#   eval      : end-to-end smoke test (every layer: tags / EC2 / DNS / CF / waker)
#   setup     : manage shared AWS resources (ec2 / iam / lambda / cf / cf-function / acm / dns)
#   waker     : inspect and debug the waker Lambda
# ═══════════════════════════════════════════════════════════════════════════════

import sys
import time
from typing import Optional

import typer
from rich.console import Console
from rich.table   import Table

from sg_compute.cli.base.Spec__CLI__Defaults                              import DEFAULT_REGION
from sg_compute_specs.vault_publish.schemas.Safe_Str__Slug                import Safe_Str__Slug
from sg_compute_specs.vault_publish.schemas.Safe_Str__Vault__Key          import Safe_Str__Vault__Key
from sg_compute_specs.vault_publish.schemas.Schema__Vault_Publish__Register__Request import Schema__Vault_Publish__Register__Request
from sg_compute_specs.vault_publish.service.Vault_Publish__Service        import Vault_Publish__Service

app = typer.Typer(name='vault-publish', help='Vault Publish — subdomain-routing for vault-app stacks.', no_args_is_help=True)

from sg_compute_specs.vault_publish.setup.cli.Cli__Setup import app as setup_app
from sg_compute_specs.vault_publish.waker.cli.Cli__Waker import app as waker_app
app.add_typer(setup_app, name='setup')
app.add_typer(waker_app, name='waker')


def _svc() -> Vault_Publish__Service:
    return Vault_Publish__Service().setup()


@app.command(name='register', help='Publish a vault-app stack at <slug>.aws.sg-labs.app.')
def register(slug                  : str  = typer.Argument(..., help='DNS slug (e.g. sara-cv)'),
             vault_key             : str  = typer.Option(..., '--vault-key', '-k', help='Vault key identifier'),
             region                : str  = typer.Option(DEFAULT_REGION, '--region', '-r'),
             wait                  : bool = typer.Option(False, '--wait', '-w', help='After register, poll the EC2 until it is RUNNING + reachable. Same shape as `sg vp wake`.'),
             timeout               : int  = typer.Option(600, '--timeout', '-t', help='Max seconds to wait when --wait is set (covers EC2 launch + vault-app boot + LE cert init).'),
             no_tls                : bool = typer.Option(False, '--no-tls', help='Provision the EC2 WITHOUT cert-init / WITHOUT TLS on :443. Vault listens on :8080 HTTP only. Viewers still get HTTPS via the CloudFront wildcard cert (CF → Lambda → EC2 chain), but direct https://<ip>/ access from the operator will not work. Useful to validate the full routing chain without the cert dependency — issue the cert later with `sg va cert-renew`.'),
             ami                   : str  = typer.Option('', '--ami', help='AMI id to launch from. Empty (default) = auto-detect the latest baked vault-app AMI (`sg va ami list`); falls back to Amazon Linux 2023 if no baked AMI exists. Baked AMIs shave ~40-60s off boot by skipping dnf install + ECR pull.'),
             no_ami                : bool = typer.Option(False, '--no-ami', help='Skip baked-AMI auto-detection and force-launch from Amazon Linux 2023 (cold-start path). Useful when you want to verify the dnf-install / ECR-pull flow works against a fresh OS.'),
             force_region_mismatch : bool = typer.Option(False, '--force-region-mismatch', help='Proceed even when --region differs from the waker Lambda\'s deploy region. Routing still works (waker scans multiple regions) but Lambda → EC2 calls cross AZ boundaries — measurably slower.')):
    import os
    from sg_compute_specs.vault_publish.service.Vault_Publish__Service import _default_zone, _resolve_latest_baked_ami
    c = Console(highlight=False)
    t_register_started = time.monotonic()                                          # end-to-end clock baseline; used by the timing summary

    fqdn  = f'{slug}.{_default_zone()}'
    waker_region = os.environ.get('WAKER_DEPLOY_REGION', '') or _detect_waker_region()

    # Resolve AMI before the summary so the operator can see what'll be used.
    # --ami overrides everything; --no-ami forces empty (= AL2023 default);
    # default resolves to latest baked vault-app AMI in this region.
    if no_ami:
        ami_resolved = ''
        ami_source   = 'forced AL2023 (--no-ami)'
    elif ami:
        ami_resolved = ami
        ami_source   = 'explicit --ami'
    else:
        ami_resolved = _resolve_latest_baked_ami(region)
        ami_source   = 'auto-detected baked vault-app AMI' if ami_resolved else 'no baked AMI found → AL2023 default'

    # Up-front summary so the operator sees the exact call shape BEFORE it runs.
    c.print()
    tls_marker = '[yellow](no TLS — pure HTTP)[/]' if no_tls else '[green](TLS via LE)[/]'
    c.print(f'  [bold]sg vp register[/]  slug=[cyan]{slug}[/]  region=[cyan]{region}[/]  {tls_marker}')
    c.print(f'  [dim]→ FQDN              : {fqdn}[/]')
    if ami_resolved:
        c.print(f'  [dim]→ AMI               : [/][cyan]{ami_resolved}[/]  [dim]({ami_source})[/]')
    else:
        c.print(f'  [dim]→ AMI               : Amazon Linux 2023 (latest, via SSM param)  ({ami_source})[/]')
    c.print(f'  [dim]→ Underlying VA call: Vault_App__Service.create_stack([/]')
    c.print(f'  [dim]    stack_name      = {slug!r},[/]')
    c.print(f'  [dim]    region          = {region!r},[/]')
    c.print(f'  [dim]    with_aws_dns    = True,[/]')
    c.print(f'  [dim]    with_tls_check  = {(not no_tls)!r},[/]')
    if ami_resolved:
        c.print(f'  [dim]    from_ami        = {ami_resolved!r},[/]')
    if not no_tls:
        c.print(f'  [dim]    tls_hostname    = {fqdn!r},[/]')
        c.print(f'  [dim]    tls_mode        = "letsencrypt-hostname",[/]')
    c.print(f'  [dim]  )[/]')

    if waker_region and waker_region != region:
        c.print()
        c.print(f'  [red]✗  Region mismatch[/] — waker Lambda runs in [bold]{waker_region}[/], '
                f'this EC2 would land in [bold]{region}[/].')
        if not force_region_mismatch:
            c.print(f'  [dim]   Routing would still work (waker scans multiple regions) but every[/]')
            c.print(f'  [dim]   Lambda → EC2 describe_instances / start_instances call would cross[/]')
            c.print(f'  [dim]   region boundaries (measurably slower).[/]\n')
            c.print(f'  Either re-run with [cyan]--region {waker_region}[/] '
                    f'(or [cyan]AWS_DEFAULT_REGION={waker_region}[/]),')
            c.print(f'  or pass [cyan]--force-region-mismatch[/] to proceed anyway.\n')
            raise typer.Exit(2)
        c.print(f'  [yellow]   --force-region-mismatch set — proceeding anyway.[/]')

    c.print()
    c.print(f'  [yellow]→[/]  Registering [bold]{slug}[/]…')
    req = Schema__Vault_Publish__Register__Request(
        slug      = Safe_Str__Slug(slug),
        vault_key = Safe_Str__Vault__Key(vault_key),
        region    = region,
        with_tls  = not no_tls,
        from_ami  = ami_resolved)
    resp = _svc().register(req)
    if not str(getattr(resp, 'fqdn', '')):
        c.print(f'  [red]✗  {resp.message}[/]')
        raise typer.Exit(1)
    c.print(f'  [green]✓[/]  Registered [bold]{slug}[/]  '
            f'[dim](EC2 instance launched, elapsed: {resp.elapsed_ms}ms)[/]')
    access_token = str(getattr(resp, 'access_token', '') or '')
    if not access_token:
        c.print(f'      [yellow]Access token: (not returned — vault-app create response had no access_token field)[/]')
    c.print()

    # Per-slug A record (matches `sg va create --with-aws-dns`). Skipped in
    # --no-tls mode: a per-slug record pointing at the EC2 IP would override
    # the CF wildcard and break HTTPS-to-viewers (no cert on the EC2). With
    # TLS on, the LE HTTP-01 challenge needs the FQDN→EC2 mapping anyway,
    # and the wildcard remains as a propagation bridge until the specific
    # record converges.
    #
    # Auto-DNS now runs IN PARALLEL with the EC2 boot wait — the EC2 is
    # booting independently and we don't want the auto-dns 20-30s blocking
    # call to pad the total wall-clock time. The Phase 3 cert probe and the
    # final timing summary block on the auto-dns thread before reporting.
    import threading
    auto_dns_thread = None
    auto_dns_state  = {'started_at': 0.0, 'finished_at': 0.0, 'ok': False, 'ran': False}
    print_lock      = threading.Lock()
    def safe_print(*a, **kw):
        with print_lock:
            c.print(*a, **kw)
    if not no_tls and wait:
        c.print(f'  [yellow]→[/]  Spawning auto-DNS upsert in parallel with EC2 boot wait (matches `sg va create --with-aws-dns`)…')
        auto_dns_state['started_at'] = time.monotonic()
        def _auto_dns_worker():
            auto_dns_state['ran'] = True
            ok = _run_auto_dns(safe_print, region=region, slug=slug, fqdn=str(resp.fqdn))
            auto_dns_state['ok']          = ok
            auto_dns_state['finished_at'] = time.monotonic()
        auto_dns_thread = threading.Thread(target=_auto_dns_worker, name='vp-auto-dns', daemon=False)
        auto_dns_thread.start()
    elif not no_tls:
        # --no-wait path: keep auto-dns synchronous (we have no parallel work
        # to interleave it with, and the CLI exits as soon as auto-dns finishes).
        c.print(f'  [yellow]→[/]  Upserting per-slug DNS A record (matches `sg va create --with-aws-dns`)…')
        auto_dns_state['started_at'] = time.monotonic()
        auto_dns_state['ran']        = True
        auto_dns_state['ok']         = _run_auto_dns(c.print, region=region, slug=slug, fqdn=str(resp.fqdn))
        auto_dns_state['finished_at']= time.monotonic()
        c.print()

    timings = {}
    if wait:
        wait_started = time.monotonic()
        c.print(f'  [yellow]→[/]  Waiting (up to {timeout}s) for EC2 to be RUNNING + reachable…')
        timings = _run_post_register_wait(c, slug=slug, region=region, timeout=timeout,
                                          fqdn=resp.fqdn, with_tls=not no_tls,
                                          print_fn=safe_print)
        # Join auto-dns so the timing summary reflects its real wall-clock cost.
        if auto_dns_thread is not None and auto_dns_thread.is_alive():
            c.print(f'  [dim]→ joining auto-dns thread…[/]')
            auto_dns_thread.join(timeout=120)
        timings['wait_total_ms'] = int((time.monotonic() - wait_started) * 1000)

    _print_timing_summary(c, t_register_started, resp.elapsed_ms, auto_dns_state, timings, with_wait=wait)
    _print_next_steps(c, slug=slug, fqdn=str(resp.fqdn), access_token=access_token, vault_key=vault_key)


def _detect_waker_region() -> str:
    """Best-effort: ask the live Lambda for its deploy region. Returns '' on
    any failure so the warning path silently degrades to 'no comparison'."""
    try:
        import boto3
        from sg_compute_specs.vault_publish.setup.service.Setup__Lambda import WAKER_LAMBDA_NAME
        # Probe in the same region as our default for the CLI; if the Lambda
        # lives elsewhere we'll get ResourceNotFound and silently return ''.
        for region in (DEFAULT_REGION, 'eu-west-2', 'us-east-1'):
            try:
                resp = boto3.client('lambda', region_name=region).get_function(FunctionName=WAKER_LAMBDA_NAME)
                env  = (resp.get('Configuration', {}).get('Environment', {}) or {}).get('Variables', {}) or {}
                return env.get('WAKER_DEPLOY_REGION', '') or region
            except Exception:
                continue
    except Exception:
        pass
    return ''


def _run_auto_dns(print_fn, *, region: str, slug: str, fqdn: str,
                  ip_wait_timeout: int = 60) -> bool:
    # Mirrors `sg va create --with-aws-dns`'s post-launch worker: poll the
    # fresh EC2 for its public IP (allocated ~5-10s after run_instance),
    # then upsert the per-slug A record + wait INSYNC + run an authoritative
    # cross-NS check. Synchronous — total budget ~30-40s typical, 120s ceiling.
    #
    # `print_fn` is a callable (signature `print_fn(text)`). Callers that need
    # thread-safety wrap c.print in a lock and pass the wrapper here.
    from sg_compute_specs.vault_app.service.Vault_App__Service  import Vault_App__Service
    from sg_compute_specs.vault_app.service.Vault_App__Auto_DNS import Vault_App__Auto_DNS

    vault_app = Vault_App__Service().setup()
    deadline  = time.time() + ip_wait_timeout
    public_ip = ''
    while time.time() < deadline:
        info = vault_app.get_stack_info(region, slug)
        ip   = str(getattr(info, 'public_ip', '') or '') if info is not None else ''
        if ip:
            public_ip = ip
            break
        time.sleep(2)
    if not public_ip:
        print_fn(f'  [yellow]⚠[/]  auto-dns: gave up waiting for public IP after {ip_wait_timeout}s — '
                 f'skipping Route 53 work')
        print_fn(f'  [dim]   add manually: sg aws dns records add --name {fqdn} --type A --value <ip>[/]')
        return False

    def _progress(stage, detail):
        print_fn(f'  [dim]   auto-dns: {stage}  {detail}[/]')
    result = Vault_App__Auto_DNS().run(fqdn=fqdn, public_ip=public_ip, on_progress=_progress)
    # Partial NS agreement (e.g. 3/4) is normal during Route 53 propagation —
    # AWS sub-NSs converge over 30-120s after INSYNC. The record IS created;
    # the wait loop downstream gives the remaining NSs time to catch up. Only
    # hard-fail when the upsert itself or the INSYNC step didn't complete.
    insync_ok = bool(getattr(result, 'insync', False))
    if result.error and not insync_ok:
        print_fn(f'  [red]✗[/]  auto-dns failed: {result.error}')
        print_fn(f'  [dim]   add manually: sg aws dns records add --name {fqdn} --type A --value {public_ip}[/]')
        return False
    if result.error and insync_ok:
        print_fn(f'  [yellow]⚠[/]  auto-dns: {result.error}')
        print_fn(f'  [dim]   (record IS created; remaining NSs typically converge within 30-60s)[/]')
        return True
    print_fn(f'  [green]✓[/]  auto-dns: {fqdn} → {public_ip}  '
             f'(INSYNC + authoritative, {result.elapsed_ms}ms)')
    return True


def _print_timing_summary(c: Console, t_started: float, register_ms: int,
                          auto_dns_state: dict, wait_timings: dict, *, with_wait: bool) -> None:
    # Surface the phase timings as a digestible block. Phases are roughly:
    #   register      — service.register() up to EC2 launching
    #   auto-dns      — Route 53 upsert + INSYNC + authoritative-check (parallel with wait)
    #   wait-running  — EC2 transitions to RUNNING + has public IP
    #   wait-http     — HTTP probe sees status<500 + waker_state != warming
    #   wait-cert     — Phase 3 HTTPS-with-cert-validation probe
    # End-to-end is wall-clock from CLI start to end (parallel phases shrink it).
    total_ms = int((time.monotonic() - t_started) * 1000)
    c.print()
    c.print(f'  [bold]Timings[/]  [dim](end-to-end: {total_ms/1000:.1f}s)[/]')
    rows = []
    rows.append(('register call', register_ms, ''))
    if auto_dns_state.get('ran'):
        if auto_dns_state.get('finished_at'):
            ad_ms = int((auto_dns_state['finished_at'] - auto_dns_state['started_at']) * 1000)
        else:
            ad_ms = 0
        marker = '[dim](parallel with wait)[/]' if with_wait else '[dim](sequential — --no-wait)[/]'
        ok_marker = '' if auto_dns_state.get('ok') else '  [yellow](failed)[/]'
        rows.append((f'auto-dns {marker}', ad_ms, ok_marker))
    if wait_timings.get('phase1_running_ms') is not None:
        rows.append(('wait → RUNNING + IP'        , wait_timings['phase1_running_ms']    , ''))
    if wait_timings.get('phase2_http_ms') is not None:
        rows.append(('wait → vault HTTP responsive', wait_timings['phase2_http_ms']      , ''))
    if wait_timings.get('phase3_cert_ms') is not None:
        rows.append(('wait → HTTPS cert valid'    , wait_timings['phase3_cert_ms']       , ''))
    for label, ms, suffix in rows:
        c.print(f'    {label:<32} {ms/1000:>6.2f}s{suffix}')
    if not with_wait:
        c.print(f'  [dim]   (--wait not set — register returned as soon as launch was submitted)[/]')
    c.print()


def _print_next_steps(c: Console, *, slug: str, fqdn: str, access_token: str, vault_key: str) -> None:
    set_cookie_url = f'https://{fqdn}/auth/set-cookie-form'
    viewer_url     = f'https://{fqdn}/'
    eval_cmd       = f'sg vp eval {slug}'
    c.print(f'  [bold]Next steps[/]')
    c.print(f'    1. Set the cookie:  [link={set_cookie_url}]{set_cookie_url}[/link]')
    if access_token:
        c.print(f'       Access token : [bold]{access_token}[/]'
                + (' [dim](= --vault-key)[/]' if access_token == vault_key
                   else ' [yellow](auto-generated — --vault-key was empty/invalid)[/]'))
    c.print(f'    2. Open the vault:  [link={viewer_url}]{viewer_url}[/link]')
    c.print(f'    3. Re-verify:       [cyan]{eval_cmd}[/]   [dim](7-step health check)[/]')
    c.print()


def _run_post_register_wait(c: Console, *, slug: str, region: str, timeout: int,
                              fqdn: str = '', with_tls: bool = True,
                              print_fn=None) -> dict:
    """Poll the just-created EC2 until it is RUNNING and the vault-app HTTP
    listener responds. Returns a timings dict with phase durations in ms.

    `print_fn` is an optional thread-safe print wrapper for the case where
    auto-dns is running in parallel (the register flow passes one). Defaults
    to c.print when None — same behaviour as before."""
    from sg_compute_specs.vault_publish.service.Slug__Registry              import Slug__Registry
    from sg_compute_specs.vault_publish.waker.Endpoint__Resolver__EC2       import Endpoint__Resolver__EC2
    from sg_compute_specs.vault_publish.waker.schemas.Enum__Instance__State import Enum__Instance__State

    p = print_fn or c.print                                                          # noqa — `p` is the thread-safe printer
    registry  = Slug__Registry(region=region)
    resolver  = Endpoint__Resolver__EC2(_registry_factory=lambda: registry)
    t_start    = time.time()
    last_state = ''
    timings    = {'phase1_running_ms': None, 'phase2_http_ms': None, 'phase3_cert_ms': None}

    # Phase 1 — wait for RUNNING + IP
    while True:
        elapsed = time.time() - t_start
        if elapsed > timeout:
            p(f'  [red]✗  timed out after {timeout}s waiting for RUNNING (last state: {last_state})[/]\n')
            raise typer.Exit(1)
        resolution = resolver.resolve(slug)
        if str(resolution.state) != last_state:
            p(f'  [dim]  {int(elapsed)}s: state {last_state or "(unknown)"} → {resolution.state}[/]')
            last_state = str(resolution.state)
        if resolution.state == Enum__Instance__State.RUNNING and resolution.public_ip:
            break
        time.sleep(3)

    phase1_ms = int((time.time() - t_start) * 1000)
    timings['phase1_running_ms'] = phase1_ms
    p(f'  [green]✓[/]  RUNNING at {resolution.public_ip}  ({phase1_ms}ms)')

    # Phase 2 — poll the viewer URL until vault-app responds.
    # When with_tls=True, we poll https://{fqdn}/ui/ with cert validation. The
    # cert validates whether the request lands on the EC2 directly (LE-hostname
    # cert) OR on CloudFront (wildcard cert) — both cover {fqdn}. The previous
    # IP-based poll always failed verification because the EC2 cert is bound
    # to the FQDN, not its IP.
    # When with_tls=False, no per-slug A record exists and the EC2 has no cert,
    # so we poll http://{ip}:8080/ui/ directly to bypass CF and confirm the
    # vault itself is up (rather than just the warming page).
    if with_tls and fqdn:
        probe_url = f'https://{fqdn}/ui/'
    else:
        probe_url = resolution.vault_url.rstrip('/') + '/ui/'
    p(f'  [yellow]→[/]  Polling {probe_url} until reachable…')
    delay        = 3
    attempts     = 0
    last_err     = ''
    phase2_start = time.time()
    while True:
        elapsed = time.time() - t_start
        if elapsed > timeout:
            p(f'  [red]✗  timed out after {timeout}s waiting for HTTP reachable[/]')
            if last_err:
                p(f'  [dim]   last error: {last_err}[/]')
            p(f'  [dim]   (vault-app + LE init can take 60–180s — retry with --timeout 900)[/]\n')
            raise typer.Exit(1)
        attempts += 1
        try:
            import urllib3
            t0   = time.time()
            resp = urllib3.PoolManager(timeout=urllib3.Timeout(connect=2, read=5)).request(
                'GET', probe_url, preload_content=False, retries=False)
            ms   = int((time.time() - t0) * 1000)
            # X-Waker-State='warming' means Lambda is still waiting for the
            # vault's _health_ok to pass — the body is the Lambda warming
            # page, NOT the actual vault. With parallel auto-dns the probe
            # may land on the wildcard → Lambda before the per-slug A
            # record converges, so this check stops us false-succeeding on
            # the warming HTML before the vault is really up.
            waker_state = (resp.headers.get('X-Waker-State') or '').lower()
            if resp.status < 500 and waker_state != 'warming':
                total = int((time.time() - t_start) * 1000)
                via_proxy = bool(waker_state)
                path_lbl  = ('[yellow]via CloudFront → Lambda → EC2[/]   (per-slug DNS still propagating)'
                             if via_proxy
                             else '[green]direct to EC2[/]   (per-slug DNS converged)')
                p(f'  [green]✓[/]  HTTP {resp.status} in {ms}ms  [dim](after {attempts} attempts, {total}ms total)[/]')
                p(f'  [dim]   Path       :[/] {path_lbl}')
                if with_tls and fqdn:
                    direct_ip_url = f'https://{resolution.public_ip}/ui/'
                    p(f'  [dim]   Viewer URL : [link={probe_url}]{probe_url}[/link]  '
                      f'(cert validates for {fqdn})[/]')
                    p(f'  [dim]   Direct (IP): {direct_ip_url}  '
                      f'(SSL verify fails by design — cert is for FQDN, not IP)[/]')
                else:
                    viewer_url = f'https://{fqdn}/' if fqdn else ''
                    if viewer_url:
                        p(f'  [dim]   Viewer URL : [link={viewer_url}]{viewer_url}[/link]  (via CloudFront wildcard)[/]')
                    p(f'  [dim]   Direct URL : [link={probe_url}]{probe_url}[/link]  (EC2 IP :8080)[/]')
                timings['phase2_http_ms'] = int((time.time() - phase2_start) * 1000)
                break
            last_err = (f'HTTP {resp.status} (waker_state={waker_state})' if waker_state
                        else f'HTTP {resp.status}')
        except Exception as exc:
            last_err = str(exc).splitlines()[0][:120]
        if attempts % 5 == 0:
            p(f'  [dim]  {int(elapsed)}s: still waiting… ({last_err})[/]')
        time.sleep(delay)
        delay = min(delay + 1, 6)
    else:
        return timings

    # Phase 3 — external HTTPS probe of the FQDN to confirm the cert was issued
    # for the hostname (not the IP). For .app TLDs the browser refuses any
    # cert mismatch (HSTS preload), so we must validate hostname matching here.
    # Skipped when --no-tls: no cert-init ran, no :443 listener exists, and
    # viewers will route through CloudFront's wildcard cert anyway.
    if not fqdn:
        p('')
        return timings
    if not with_tls:
        p(f'\n  [dim]·  Skipping Phase 3 HTTPS cert probe (--no-tls).[/]')
        p(f'  [dim]   Viewers will see HTTPS via CloudFront wildcard. '
          f'Run [cyan]sg va cert-renew {slug} --mode letsencrypt-hostname '
          f'--hostname {fqdn}[/dim][dim] later to enable direct HTTPS to the EC2.[/]')
        p('')
        return timings
    https_url = f'https://{fqdn}/'
    p(f'  [yellow]→[/]  Probing {https_url} (with cert validation) to confirm LE issued '
      f'a hostname-bound cert…')
    phase3_start = time.time()
    cert_ok, detail = _probe_https_with_cert(https_url)
    timings['phase3_cert_ms'] = int((time.time() - phase3_start) * 1000)
    if cert_ok:
        p(f'  [green]✓[/]  HTTPS handshake passed — cert is valid for {fqdn}')
        return timings
    p(f'  [yellow]⚠[/]  {detail}')
    p(f'  [yellow]→[/]  Auto-running `sg va cert-renew {slug} --mode letsencrypt-hostname '
      f'--hostname {fqdn}` to fix it…')
    try:
        from sg_compute_specs.vault_app.service.Vault_App__Service import Vault_App__Service
        from sg_compute_specs.vault_publish.service.Slug__Registry import Slug__Registry
        svc = Vault_App__Service().setup()
        # Resolve via registry (already cached from phase 1)
        entry = Slug__Registry(region=region).get(slug, region)
        stack_name = str(entry.stack_name) if entry else slug
        # Detect engine from the live tags
        import boto3
        ec2 = boto3.client('ec2', region_name=region)
        info = ec2.describe_instances(Filters=[
            {'Name': f'tag:StackName', 'Values': [stack_name]},
            {'Name': 'tag:StackType',   'Values': ['vault-app']},
        ])
        engine = 'docker'
        for res in info.get('Reservations', []):
            for inst in res.get('Instances', []):
                for t in inst.get('Tags', []):
                    if t.get('Key') == 'StackEngine':
                        engine = (t.get('Value') or 'docker').lower()
        compose = 'podman-compose' if engine == 'podman' else 'docker compose'
        ssm = (
            f'set -e; '
            f'ENV=/opt/vault-app/.env; touch "$ENV"; '
            f'update_kv(){{ if grep -q "^$1=" "$ENV" 2>/dev/null; then '
            f'  sed -i "s|^$1=.*|$1=$2|" "$ENV"; else echo "$1=$2" >> "$ENV"; fi; }}; '
            f'update_kv SG__CERT_INIT__MODE letsencrypt-hostname; '
            f'update_kv SG__CERT_INIT__TLS_HOSTNAME {fqdn}; '
            # `up -d --force-recreate` (NOT restart) — compose only re-reads
            # .env and re-resolves ${VAR} placeholders on a fresh container.
            f'cd /opt/vault-app && {compose} up -d --force-recreate --no-deps cert-init 2>&1 | tail -20'
        )
        svc.exec(region, stack_name, ssm, timeout_sec=60)
        p(f'  [green]✓[/]  cert-renew triggered — re-probe in ~60s with '
          f'`sg vp eval {slug}`')
    except Exception as exc:
        p(f'  [red]✗  cert-renew failed: {exc}[/]')
        p(f'  [dim]   run manually: sg va cert-renew {slug} '
          f'--mode letsencrypt-hostname --hostname {fqdn}[/]')
    return timings


def _probe_https_with_cert(url: str) -> tuple:
    """HTTPS GET that verifies the server cert against the URL's hostname.
    Returns (ok, human_readable_detail)."""
    try:
        import urllib3
        pm = urllib3.PoolManager(cert_reqs='CERT_REQUIRED',
                                 timeout=urllib3.Timeout(connect=3, read=5))
        resp = pm.request('GET', url, preload_content=False, retries=False)
        return True, f'HTTP {resp.status}'
    except Exception as exc:
        msg = str(exc).splitlines()[0][:200]
        return False, f'cert validation failed: {msg}'


@app.command(name='adopt', help='Adopt an existing EC2 (created via `sg va create`) into vault-publish: add sg:slug/sg:fqdn/sg:zone tags, create the per-slug Route 53 A record pointing at the EC2 IP, trigger LE cert renewal, and invalidate the waker cache. Counterpart to register for instances that already exist.')
def adopt(slug         : str  = typer.Argument(..., help='Slug to adopt (must match the EC2\'s StackName tag, or the existing sg:slug tag).'),
          zone         : str  = typer.Option('', '--zone', '-z', help='DNS apex (defaults to $SG_AWS__DNS__DEFAULT_ZONE).'),
          skip_dns     : bool = typer.Option(False, '--skip-dns', help='Tag the EC2 but do NOT create the Route 53 A record.'),
          skip_cert    : bool = typer.Option(False, '--skip-cert', help='Do not trigger LE cert renewal (cert-init restart on the EC2).'),
          skip_cache   : bool = typer.Option(False, '--skip-cache-clear', help='Do not invalidate the live waker cache after tagging.'),
          cert_timeout : int  = typer.Option(180, '--cert-timeout', help='Max seconds to wait for cert-init when --skip-cert is not set (LE issuance can take 20-90s after DNS lands).')):
    import os, boto3
    c = Console(highlight=False)
    resolved_zone = zone or os.environ.get('SG_AWS__DNS__DEFAULT_ZONE', 'aws.sg-labs.app')
    fqdn          = f'{slug}.{resolved_zone}'

    c.print()
    c.print(f'  [bold]sg vp adopt[/]  slug=[cyan]{slug}[/]  fqdn=[cyan]{fqdn}[/]')
    c.print(f'  [dim]→ scan regions for an EC2 with tag:sg:slug or tag:StackName = {slug}[/]')

    # 1. Find the EC2 across regions (same multi-region scan the resolver uses)
    instance, region = _find_existing_ec2(slug)
    if not instance:
        c.print(f'\n  [red]✗  no EC2 with sg:slug={slug} OR StackName={slug} '
                f'(StackType=vault-app) found in any scanned region.[/]')
        c.print(f'  [dim]   If the instance exists in a region we don\'t scan, set '
                f'WAKER_SCAN_REGIONS=… and re-run.[/]\n')
        raise typer.Exit(1)

    iid       = instance.get('InstanceId', '')
    public_ip = instance.get('PublicIpAddress', '')
    state     = instance.get('State', {}).get('Name', '')
    tags      = {t.get('Key',''): t.get('Value','') for t in instance.get('Tags', [])}
    stack_name = tags.get('StackName', slug)
    tls_on    = str(tags.get('StackTLS', '')).lower() in ('true', '1', 'yes')
    c.print(f'  [green]✓[/]  Found EC2 [bold]{iid}[/] in {region}  '
            f'(state={state}, public_ip={public_ip or "(none)"}, '
            f'StackName={stack_name}, StackTLS={tls_on})')

    # 2. Tag the instance
    c.print(f'  [yellow]→[/]  Tagging with sg:slug / sg:fqdn / sg:zone…')
    try:
        boto3.client('ec2', region_name=region).create_tags(
            Resources=[iid],
            Tags=[
                {'Key': 'sg:slug', 'Value': slug},
                {'Key': 'sg:fqdn', 'Value': fqdn},
                {'Key': 'sg:zone', 'Value': resolved_zone},
            ],
        )
        c.print(f'  [green]✓[/]  Tagged')
    except Exception as exc:
        c.print(f'  [red]✗  create_tags failed: {exc}[/]\n')
        raise typer.Exit(1)

    # 3. Create per-slug Route 53 A record
    dns_ok = False
    if skip_dns:
        c.print(f'  [dim]·  Skipping DNS (--skip-dns)[/]')
    elif not public_ip:
        c.print(f'  [yellow]⚠[/]  No public IP — skipping DNS (start the instance first)')
    else:
        c.print(f'  [yellow]→[/]  Upserting Route 53 A record {fqdn} → {public_ip}…')
        try:
            from sg_compute_specs.vault_app.service.Vault_App__Auto_DNS import Vault_App__Auto_DNS
            result = Vault_App__Auto_DNS().run(
                fqdn        = fqdn,
                public_ip   = public_ip,
                on_progress = lambda stage, detail: c.print(f'  [dim]   {stage}: {detail}[/]'),
            )
            dns_ok = bool(getattr(result, 'change_id', '') or getattr(result, 'completed', False))
            icon = '[green]✓[/]' if dns_ok else '[yellow]⚠[/]'
            c.print(f'  {icon}  DNS record upserted')
        except Exception as exc:
            c.print(f'  [yellow]⚠  DNS upsert failed: {exc}  (proceeding anyway)[/]')

    # 4. Trigger LE cert renewal — only meaningful when TLS was enabled at create
    #    AND DNS is now in place (LE HTTP-01 needs the FQDN to resolve to this IP).
    if skip_cert:
        c.print(f'  [dim]·  Skipping cert renewal (--skip-cert)[/]')
    elif not tls_on:
        c.print(f'  [dim]·  Skipping cert renewal (instance not created with --with-tls-check)[/]')
    elif not dns_ok and not skip_dns:
        c.print(f'  [yellow]⚠  Skipping cert renewal — DNS upsert was not confirmed; '
                f'run `sg va cert-renew {stack_name}` manually after DNS settles.[/]')
    else:
        c.print(f'  [yellow]→[/]  Triggering Let\'s Encrypt cert renewal '
                f'(recreate cert-init container on EC2 to pick up new .env, '
                f'wait up to {cert_timeout}s)…')
        try:
            from sg_compute_specs.vault_app.service.Vault_App__Service import Vault_App__Service
            svc = Vault_App__Service().setup()
            engine = (tags.get('StackEngine', '') or 'docker').lower()
            compose = 'podman-compose' if engine == 'podman' else 'docker compose'
            # Always force letsencrypt-hostname mode targeting this slug's FQDN —
            # the EC2 may have been originally provisioned with letsencrypt-ip
            # (the default for plain `sg va create`), which issues a cert for
            # the IP, not the hostname. .app TLDs are HSTS-preloaded so the
            # browser refuses the IP-CN cert.
            ssm = (
                f'set -e; '
                f'ENV=/opt/vault-app/.env; touch "$ENV"; '
                f'update_kv(){{ if grep -q "^$1=" "$ENV" 2>/dev/null; then '
                f'  sed -i "s|^$1=.*|$1=$2|" "$ENV"; else echo "$1=$2" >> "$ENV"; fi; }}; '
                f'update_kv SG__CERT_INIT__MODE letsencrypt-hostname; '
                f'update_kv SG__CERT_INIT__TLS_HOSTNAME {fqdn}; '
                # `up -d --force-recreate` (NOT restart) — compose only re-reads
            # .env and re-resolves ${VAR} placeholders on a fresh container.
            f'cd /opt/vault-app && {compose} up -d --force-recreate --no-deps cert-init 2>&1 | tail -20'
            )
            svc.exec(region, stack_name, ssm, timeout_sec=60)
            # Poll for success
            import time as _t
            container = 'vault-app-cert-init-1'
            ps_cmd = (f'{"docker" if engine != "podman" else "podman"} ps -a '
                       f'--filter name={container} --format "{{{{.Status}}}}"')
            t0 = _t.time()
            last_status = ''
            while True:
                elapsed = _t.time() - t0
                if elapsed > cert_timeout:
                    c.print(f'  [yellow]⚠  cert-init timed out after {cert_timeout}s '
                            f'(last status: {last_status!r}) — inspect with '
                            f'`sg va logs {stack_name} --source cert-init`[/]')
                    break
                r = svc.exec(region, stack_name, ps_cmd, timeout_sec=30)            # SSM SendCommand minimum is 30s
                status = str(getattr(r, 'stdout', '') or '').strip().splitlines()
                status = status[0] if status else ''
                if status != last_status:
                    c.print(f'  [dim]   {int(elapsed)}s: {status or "(no container yet)"}[/]')
                    last_status = status
                if 'Exited (0)' in status:
                    c.print(f'  [green]✓[/]  cert-init succeeded')
                    # Show what cert-init actually issued (now that logs are complete)
                    docker = 'docker' if engine != 'podman' else 'podman'
                    logs_r = svc.exec(region, stack_name,
                                       f'{docker} logs vault-app-cert-init-1 2>&1 | tail -20',
                                       timeout_sec=30)
                    logs = str(getattr(logs_r, 'stdout', '') or '').strip()
                    if logs:
                        for line in logs.splitlines()[-10:]:
                            c.print(f'  [dim]    {line}[/]')
                    # Restart vault to pick up the new cert (replaced /certs/cert.pem
                    # doesn't reload — vault reads it at process startup only).
                    c.print(f'  [yellow]→[/]  Restarting sg-send-vault to load the new cert…')
                    svc.exec(region, stack_name,
                             f'cd /opt/vault-app && {compose} restart --no-deps sg-send-vault '
                             f'2>&1 | tail -5',
                             timeout_sec=60)
                    c.print(f'  [green]✓[/]  Vault restarted (HTTPS should be valid in ~5s)')
                    break
                if 'Exited' in status and '(0)' not in status:
                    c.print(f'  [red]✗  cert-init exited non-zero: {status}[/]')
                    c.print(f'  [dim]   Inspect: sg va logs {stack_name} --source cert-init[/]')
                    break
                _t.sleep(3)
        except Exception as exc:
            c.print(f'  [yellow]⚠  cert-renew failed: {exc}[/]')
            c.print(f'  [dim]   Run manually: sg va cert-renew {stack_name}[/]')

    # 5. Clear the waker's slug cache so the next request picks up the new tags
    if skip_cache:
        c.print(f'  [dim]·  Skipping cache-clear (--skip-cache-clear)[/]')
    else:
        c.print(f'  [yellow]→[/]  Invalidating waker cache for slug={slug}…')
        try:
            _waker_cmd_cache_clear(slug)
            c.print(f'  [green]✓[/]  Cache cleared')
        except Exception as exc:
            c.print(f'  [yellow]⚠  cache-clear via Lambda RPC failed: {exc}'
                    f'  (the entry will expire naturally within ~60s)[/]')

    c.print()
    c.print(f'  [green]✓[/]  Adopted [bold]{slug}[/] — try [cyan]https://{fqdn}/[/]\n')


def _find_existing_ec2(slug: str):
    """Scan the same regions the waker resolver scans, looking for an EC2 with
    sg:slug OR StackName matching the slug. Returns (instance_dict, region) or
    (None, '')."""
    import os, boto3
    raw = os.environ.get('WAKER_SCAN_REGIONS', '')
    if raw:
        regions = [r.strip() for r in raw.split(',') if r.strip()]
    else:
        seed = (os.environ.get('AWS_REGION', '') or
                os.environ.get('AWS_DEFAULT_REGION', '') or 'eu-west-2')
        regions = [seed, 'eu-west-2', 'us-east-1', 'us-west-2', 'eu-west-1']
    seen = set()
    regions = [r for r in regions if not (r in seen or seen.add(r))]
    states = ['running', 'stopped', 'pending', 'stopping']
    for r in regions:
        try:
            ec2 = boto3.client('ec2', region_name=r)
            for tag_key in ('sg:slug', 'StackName'):
                resp = ec2.describe_instances(Filters=[
                    {'Name': f'tag:{tag_key}',         'Values': [slug]},
                    {'Name': 'tag:StackType',          'Values': ['vault-app']},
                    {'Name': 'instance-state-name',    'Values': states},
                ])
                for res in resp.get('Reservations', []):
                    for inst in res.get('Instances', []):
                        return inst, r
        except Exception:
            continue
    return None, ''


def _waker_cmd_cache_clear(slug: str):
    """Call the live Lambda's /__waker__/cmd?name=cache-clear&slug=<slug> via
    boto3.invoke — no HTTPS / CloudFront propagation involved. Raises on
    error so the caller can surface it."""
    import json, uuid, boto3, urllib.parse
    from datetime import datetime, timezone
    from sg_compute_specs.vault_publish.setup.service.Setup__Lambda import WAKER_LAMBDA_NAME
    from sgraph_ai_service_playwright__cli.aws._shared.Aws__Region__Resolver import Aws__Region__Resolver
    qs = urllib.parse.urlencode([('name', 'cache-clear'), ('slug', slug)])
    event = {
        'version'       : '2.0',
        'rawPath'       : '/__waker__/cmd',
        'rawQueryString': qs,
        'headers'       : {'host': 'localhost', 'user-agent': 'sg-vp-adopt/0.1'},
        'requestContext': {
            'http'     : {'method': 'GET', 'path': '/__waker__/cmd', 'sourceIp': '127.0.0.1'},
            'requestId': f'sg-adopt-{uuid.uuid4().hex[:8]}',
            'time'     : datetime.now(timezone.utc).strftime('%d/%b/%Y:%H:%M:%S +0000'),
        },
        'body'           : None,
        'isBase64Encoded': False,
    }
    lam = boto3.client('lambda', region_name=str(Aws__Region__Resolver().resolve()))
    resp = lam.invoke(FunctionName=WAKER_LAMBDA_NAME, InvocationType='RequestResponse',
                      Payload=json.dumps(event).encode())
    payload = json.loads(resp['Payload'].read())
    if payload.get('statusCode', 0) >= 400:
        raise RuntimeError(f'cache-clear returned status {payload.get("statusCode")}: {payload.get("body")}')


@app.command(name='unpublish', help='Remove a slug, its stack, and its DNS record.')
def unpublish(slug  : str  = typer.Argument(..., help='Slug to unpublish'),
              region: str  = typer.Option(DEFAULT_REGION, '--region', '-r'),
              yes   : bool = typer.Option(False, '--yes', '-y', help='Skip confirmation')):
    c = Console(highlight=False)
    if not yes:
        typer.confirm(f"\n  Delete slug '{slug}' and its vault-app stack?", default=True, abort=True)
    c.print(f'\n  [yellow]→[/]  Unpublishing [bold]{slug}[/]…')
    resp = _svc().unpublish(slug)
    if not getattr(resp, 'deleted', False):
        c.print(f'  [red]✗  {resp.message}[/]')
        raise typer.Exit(1)
    c.print(f'  [green]✓[/]  Unpublished [bold]{slug}[/]  (stack: {resp.stack_name})')
    c.print()


@app.command(name='status', help='Show EC2 state and FQDN for a registered slug.')
def status(slug  : str = typer.Argument(..., help='Slug to query'),
           region: str = typer.Option(DEFAULT_REGION, '--region', '-r')):
    c    = Console(highlight=False)
    resp = _svc().status(slug)
    c.print()
    c.print(f'  Slug  : {slug}')
    c.print(f'  State : {resp.state}')
    c.print(f'  FQDN  : {resp.fqdn}')
    if getattr(resp, 'vault_url', ''):
        c.print(f'  URL   : {resp.vault_url}')
    if getattr(resp, 'public_ip', ''):
        c.print(f'  IP    : {resp.public_ip}')
    c.print()


@app.command(name='wake', help='Resolve a slug → start EC2 if stopped → wait for RUNNING + reachable. Mirrors the waker Lambda.')
def wake(slug    : str  = typer.Argument(..., help='Slug to wake'),
         region  : str  = typer.Option(DEFAULT_REGION, '--region', '-r'),
         timeout : int  = typer.Option(300, '--timeout', '-t', help='Max total seconds to wait for RUNNING + HTTP reachable'),
         no_wait : bool = typer.Option(False, '--no-wait', help='Trigger start_instances but exit immediately'),
         no_probe: bool = typer.Option(False, '--no-probe', help='Skip HTTP health probe after RUNNING')):
    from sg_compute_specs.vault_publish.service.Slug__Registry              import Slug__Registry
    from sg_compute_specs.vault_publish.waker.Endpoint__Resolver__EC2       import Endpoint__Resolver__EC2
    from sg_compute_specs.vault_publish.waker.schemas.Enum__Instance__State import Enum__Instance__State

    c        = Console(highlight=False)
    registry = Slug__Registry(region=region)
    resolver = Endpoint__Resolver__EC2(_registry_factory=lambda: registry)

    c.print(f'\n  [yellow]→[/]  Resolving [bold]{slug}[/]…')
    resolution = resolver.resolve(slug)
    if resolution.state == Enum__Instance__State.UNKNOWN:
        c.print(f'  [red]✗  no EC2 instance tagged sg:slug={slug} in {region}[/]')
        c.print(f'  [dim]   Register first: sg vp register {slug} --vault-key <key>[/]\n')
        raise typer.Exit(1)

    c.print(f'  [dim]  instance: {resolution.instance_id}  state: {resolution.state}  ip: {resolution.public_ip or "(none)"}[/]')

    if resolution.state == Enum__Instance__State.STOPPED:
        c.print(f'  [yellow]→[/]  Instance STOPPED — calling start_instances…')
        ok = resolver.start(resolution.instance_id)
        if not ok:
            c.print(f'  [red]✗  start_instances failed (check IAM / region)[/]\n')
            raise typer.Exit(1)
        c.print(f'  [green]✓[/]  start triggered')
    elif resolution.state in (Enum__Instance__State.PENDING, Enum__Instance__State.STOPPING):
        c.print(f'  [yellow]→[/]  Instance {resolution.state} — waiting for stable state…')
    elif resolution.state == Enum__Instance__State.RUNNING:
        c.print(f'  [green]✓[/]  Instance already RUNNING')

    if no_wait:
        c.print(f'\n  [dim]--no-wait: returning before EC2 is ready[/]\n')
        return

    t_start = time.time()

    # ── Phase 1 — wait for RUNNING + public IP ───────────────────────────────
    last_state = resolution.state
    while True:
        elapsed = time.time() - t_start
        if elapsed > timeout:
            c.print(f'  [red]✗  timed out after {timeout}s waiting for RUNNING (last state: {last_state})[/]\n')
            raise typer.Exit(1)
        resolution = resolver.resolve(slug)
        if resolution.state != last_state:
            c.print(f'  [dim]  {int(elapsed)}s: state {last_state} → {resolution.state}[/]')
            last_state = resolution.state
        if resolution.state == Enum__Instance__State.RUNNING and resolution.public_ip:
            break
        time.sleep(2)

    run_ms = int((time.time() - t_start) * 1000)
    c.print(f'  [green]✓[/]  RUNNING at {resolution.public_ip}  ({run_ms}ms since start)')

    if no_probe:
        c.print()
        return

    # ── Phase 2 — poll HTTP probe until reachable or overall timeout ─────────
    probe_url = resolution.vault_url.rstrip('/') + '/ui/#!/login'
    c.print(f'  [yellow]→[/]  Polling {probe_url} until reachable…')
    last_err  = ''
    delay     = 2
    attempts  = 0
    while True:
        elapsed = time.time() - t_start
        remaining = timeout - elapsed
        if remaining <= 0:
            c.print(f'  [red]✗  timed out after {timeout}s waiting for HTTP reachable[/]')
            if last_err:
                c.print(f'  [dim]   last error: {last_err}[/]')
            c.print(f'  [dim]   (vault-app boot can take 30–90s after RUNNING; try `sg vp wake {slug} -t 600`)[/]\n')
            raise typer.Exit(1)

        attempts += 1
        try:
            import urllib3
            p0   = time.time()
            resp = urllib3.PoolManager(timeout=urllib3.Timeout(connect=2, read=5)).request(
                'GET', probe_url, preload_content=False, retries=False)
            probe_ms = int((time.time() - p0) * 1000)
            if resp.status < 500:
                total_ms = int((time.time() - t_start) * 1000)
                c.print(f'  [green]✓[/]  HTTP {resp.status} in {probe_ms}ms  '
                        f'[dim](after {attempts} attempt(s), {total_ms}ms total)[/]')
                c.print()
                return
            last_err = f'HTTP {resp.status}'
        except Exception as exc:
            last_err = _short_err(exc)

        # progress beep every ~10s
        if attempts % 5 == 0:
            c.print(f'  [dim]  {int(elapsed)}s: still waiting… ({last_err})[/]')
        time.sleep(delay)
        delay = min(delay + 1, 5)


def _short_err(exc: Exception) -> str:
    msg = str(exc)
    # urllib3 errors are noisy; keep first line
    return msg.splitlines()[0][:120] if msg else type(exc).__name__


@app.command(name='dns', help='DNS diagnostics for a slug (Route 53 record + public resolver lookup).')
def dns(slug  : str = typer.Argument(..., help='Slug to inspect'),
        zone  : str = typer.Option('', '--zone', '-z', help='DNS apex (defaults to $SG_AWS__DNS__DEFAULT_ZONE)')):
    import os
    from sg_compute_specs.vault_publish.service.Slug__Registry import Slug__Registry

    c             = Console(highlight=False)
    resolved_zone = zone or os.environ.get('SG_AWS__DNS__DEFAULT_ZONE', 'aws.sg-labs.app')
    fqdn          = f'{slug}.{resolved_zone}'
    registry      = Slug__Registry()
    entry         = registry.get(slug)

    c.print()
    c.print(f'  Slug : [bold]{slug}[/]')
    c.print(f'  FQDN : {fqdn}')
    c.print(f'  Zone : {resolved_zone}')
    c.print()

    # ── Registry view (tag-derived) ──────────────────────────────────────────
    if entry:
        c.print(f'  [green]✓[/]  Registry: instance tagged sg:slug={slug}  fqdn={entry.fqdn}')
    else:
        c.print(f'  [yellow]⚠[/]  Registry: no EC2 instance tagged sg:slug={slug}')

    # ── Route 53 lookup ──────────────────────────────────────────────────────
    try:
        from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__AWS__Client      import Route53__AWS__Client
        from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Route53__Record_Type   import Enum__Route53__Record_Type
        r53      = Route53__AWS__Client()
        zone_obj = r53.find_hosted_zone_by_name(resolved_zone)
        if not zone_obj:
            c.print(f'  [yellow]⚠[/]  Route 53: hosted zone {resolved_zone!r} not found')
        else:
            # Per-slug record (set by Vault_App__Auto_DNS when register was called with TLS)
            rec_a = r53.get_record(str(zone_obj.zone_id), fqdn, Enum__Route53__Record_Type.A)
            if rec_a:
                vals = ', '.join(list(rec_a.values)) if rec_a.values else (rec_a.alias_target or '(alias)')
                c.print(f'  [green]✓[/]  Route 53 A record : {fqdn} → {vals}  (ttl={rec_a.ttl})')
            else:
                c.print(f'  [dim]ℹ[/]   Route 53 A record : (none — relying on wildcard *.{resolved_zone})')

            # Wildcard at *.{zone} that catches everything for the CF distribution
            wild = f'*.{resolved_zone}'
            for rt in (Enum__Route53__Record_Type.A, Enum__Route53__Record_Type.CNAME):
                rec_w = r53.get_record(str(zone_obj.zone_id), wild, rt)
                if rec_w:
                    vals = ', '.join(list(rec_w.values)) if rec_w.values else (rec_w.alias_target or '(alias)')
                    c.print(f'  [green]✓[/]  Wildcard {rt.value:5}    : {wild} → {vals}')
                    break
            else:
                c.print(f'  [red]✗  Wildcard         : no {wild} record (CF fallback broken)[/]')
    except Exception as exc:
        c.print(f'  [red]✗  Route 53 lookup failed: {exc}[/]')

    # ── Public resolver lookup (cheap sanity check) ──────────────────────────
    import socket
    try:
        ips = sorted({addr[4][0] for addr in socket.getaddrinfo(fqdn, None)})
        c.print(f'  [green]✓[/]  Public DNS resolves to: {", ".join(ips)}')
    except socket.gaierror as exc:
        c.print(f'  [red]✗  Public DNS resolution failed: {exc}[/]')
    c.print()


@app.command(name='eval', help='End-to-end smoke test: every layer between registration and viewer-served HTML.')
def eval_(slug    : str  = typer.Argument(..., help='Slug to evaluate'),
          region  : str  = typer.Option(DEFAULT_REGION, '--region', '-r'),
          zone    : str  = typer.Option('', '--zone', '-z', help='DNS apex (defaults to $SG_AWS__DNS__DEFAULT_ZONE)'),
          no_wake : bool = typer.Option(False, '--no-wake', help='Skip start-if-stopped step (probe in-place state only)')):
    import os, socket, time as _t
    from sg_compute_specs.vault_publish.service.Slug__Registry              import Slug__Registry
    from sg_compute_specs.vault_publish.waker.Endpoint__Resolver__EC2       import Endpoint__Resolver__EC2
    from sg_compute_specs.vault_publish.waker.schemas.Enum__Instance__State import Enum__Instance__State

    c             = Console(highlight=False)
    resolved_zone = zone or os.environ.get('SG_AWS__DNS__DEFAULT_ZONE', 'aws.sg-labs.app')
    fqdn          = f'{slug}.{resolved_zone}'
    registry      = Slug__Registry(region=region)
    resolver      = Endpoint__Resolver__EC2(_registry_factory=lambda: registry)
    failures      = 0

    c.print(f'\n  [bold]Evaluating[/] [cyan]{fqdn}[/]\n')

    # 1 — Slug registered (tag lookup)
    entry = registry.get(slug)
    if entry:
        _step(c, 1, 'slug registered', True, f'instance tagged sg:slug={slug}')
    else:
        _step(c, 1, 'slug registered', False, f'no EC2 tagged sg:slug={slug} in {region}')
        failures += 1
        c.print()
        raise typer.Exit(failures)

    # 2 — EC2 present + state
    resolution = resolver.resolve(slug)
    ok = resolution.state != Enum__Instance__State.UNKNOWN
    _step(c, 2, 'ec2 instance present', ok,
          f'{resolution.instance_id} state={resolution.state} ip={resolution.public_ip or "(none)"}')
    failures += 0 if ok else 1

    # 2b — Optional wake
    if not no_wake and resolution.state == Enum__Instance__State.STOPPED:
        c.print('     [dim]→ STOPPED — calling start_instances and waiting up to 120s…[/]')
        resolver.start(resolution.instance_id)
        deadline = _t.time() + 120
        while _t.time() < deadline:
            resolution = resolver.resolve(slug)
            if resolution.state == Enum__Instance__State.RUNNING and resolution.public_ip:
                break
            _t.sleep(2)

    running = (resolution.state == Enum__Instance__State.RUNNING and bool(resolution.public_ip))

    # 3 — Direct IP HTTP probe
    if running and resolution.vault_url:
        ok, detail = _http_probe(resolution.vault_url.rstrip('/') + '/ui/#!/login')
        _step(c, 3, 'direct IP reachable', ok, f'{resolution.vault_url} → {detail}')
        failures += 0 if ok else 1
    else:
        _step(c, 3, 'direct IP reachable', False, 'skipped — instance not RUNNING with public IP')
        failures += 1

    # 4 — Per-slug Route 53 A record (set by Vault_App__Auto_DNS on register).
    # Only created when TLS is on — in --no-tls mode the wildcard catches the
    # FQDN and a specific A record would override CF and break HTTPS-to-viewers.
    instance_tls = _instance_has_tls_tag(resolution.instance_id, resolution.region)
    if not instance_tls:
        _step(c, 4, 'per-slug DNS record', True,
              f'skipped — StackTLS=false (record would override CF wildcard)')
    else:
        try:
            from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__AWS__Client    import Route53__AWS__Client
            from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Route53__Record_Type import Enum__Route53__Record_Type
            r53      = Route53__AWS__Client()
            zone_obj = r53.find_hosted_zone_by_name(resolved_zone)
            if zone_obj:
                rec = r53.get_record(str(zone_obj.zone_id), fqdn, Enum__Route53__Record_Type.A)
                if rec:
                    vals = ', '.join(list(rec.values)) if rec.values else (rec.alias_target or '(alias)')
                    _step(c, 4, 'per-slug DNS record', True, f'A {fqdn} → {vals}')
                else:
                    _step(c, 4, 'per-slug DNS record', False,
                          f'no A record for {fqdn} — register may not have run with TLS, or DNS was deleted')
                    failures += 1
            else:
                _step(c, 4, 'per-slug DNS record', False, f'hosted zone {resolved_zone!r} not found')
                failures += 1
        except Exception as exc:
            _step(c, 4, 'per-slug DNS record', False, f'Route 53 lookup failed: {exc}')
            failures += 1

    # 5 — Public DNS resolution
    try:
        ips = sorted({addr[4][0] for addr in socket.getaddrinfo(fqdn, None)})
        _step(c, 5, 'public DNS resolves', True, f'{fqdn} → {", ".join(ips[:4])}')
    except socket.gaierror as exc:
        _step(c, 5, 'public DNS resolves', False, str(exc))
        failures += 1

    # 6 — HTTPS through CloudFront → waker → vault-app
    https_url = f'https://{fqdn}/'
    ok, detail, waker_headers = _https_probe(https_url)
    _step(c, 6, 'HTTPS via CloudFront', ok, f'{https_url} → {detail}')
    failures += 0 if ok else 1

    # 7 — Waker X-Waker-* response headers
    if waker_headers:
        state_h  = waker_headers.get('X-Waker-State', '')
        action_h = waker_headers.get('X-Waker-Action', '')
        host_h   = waker_headers.get('X-Waker-Host', '')
        host_ok  = (host_h == fqdn) if host_h else False
        ok       = bool(state_h) and host_ok
        _step(c, 7, 'waker headers correct', ok,
              f'state={state_h} action={action_h} host={host_h or "(empty)"}'
              + ('' if host_ok else '  [yellow]← host mismatch (CloudFront Function missing?)[/]'))
        failures += 0 if ok else 1
    else:
        _step(c, 7, 'waker headers correct', False, 'no X-Waker-* headers received')
        failures += 1

    c.print()
    if failures:
        c.print(f'  [red]✗  {failures} step(s) failed[/]\n')
        raise typer.Exit(1)
    c.print(f'  [green]✓  all {7} steps passed[/]\n')


def _instance_has_tls_tag(instance_id: str, region: str) -> bool:
    # Best-effort StackTLS read. Returns True only when the tag is unambiguously
    # 'true' — any failure / missing tag / 'false' value yields False so eval
    # treats no-TLS instances as the "wildcard-only" routing case.
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


def _step(c: Console, n: int, label: str, ok: bool, detail: str = '') -> None:
    icon = '[green]✓[/]' if ok else '[red]✗[/]'
    c.print(f'  {n}. {icon}  {label:<24} {detail}')


def _http_probe(url: str) -> tuple:
    try:
        import urllib3
        t0   = time.time()
        resp = urllib3.PoolManager(timeout=urllib3.Timeout(connect=2, read=5)).request(
            'GET', url, preload_content=True)
        ms   = int((time.time() - t0) * 1000)
        return (resp.status < 500, f'HTTP {resp.status} in {ms}ms')
    except Exception as exc:
        return (False, f'request failed: {exc}')


def _https_probe(url: str) -> tuple:
    try:
        import urllib3
        t0   = time.time()
        resp = urllib3.PoolManager(timeout=urllib3.Timeout(connect=5, read=15)).request(
            'GET', url, preload_content=True, retries=False)
        ms   = int((time.time() - t0) * 1000)
        # Filter just X-Waker-* headers
        waker_headers = {k: v for k, v in resp.headers.items() if k.lower().startswith('x-waker-')}
        ok = resp.status < 500
        return (ok, f'HTTP {resp.status} in {ms}ms', waker_headers)
    except Exception as exc:
        return (False, f'request failed: {exc}', {})


@app.command(name='list', help='List all registered slugs (vault keys redacted).')
def list_slugs():
    c    = Console(highlight=False)
    resp = _svc().list_slugs()
    if not resp.total:
        c.print('\n  (no slugs registered)\n')
        return
    tbl = Table(box=None, show_header=True, padding=(0, 2))
    tbl.add_column('Slug',       style='bold')
    tbl.add_column('FQDN',       style='cyan')
    tbl.add_column('Stack',      style='dim')
    tbl.add_column('Region',     style='dim')
    tbl.add_column('Created',    style='dim')
    for entry in resp.entries:
        tbl.add_row(str(entry.slug), str(entry.fqdn), str(entry.stack_name),
                    str(entry.region), str(entry.created_at))
    c.print()
    c.print(tbl)
    c.print(f'\n  Total: {resp.total}\n')



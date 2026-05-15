# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Spec__CLI__Builder
# Factory that produces a fully-wired typer.Typer for one spec.  Each
# Cli__{Pascal}.py is a small call into this builder.
#
# The builder is NOT a Type_Safe — typer reflects on function annotations
# via inspect.signature which conflicts with Type_Safe's metaclass. (Risk R1)
# ═══════════════════════════════════════════════════════════════════════════════

import inspect
import os
from typing import Any, List, Optional, Tuple

import typer
from rich.console import Console

from sg_compute.cli.base.Schema__Spec__CLI__Spec  import Schema__Spec__CLI__Spec
from sg_compute.cli.base.Spec__CLI__Defaults      import (DEFAULT_EXEC_TIMEOUT ,
                                                           DEFAULT_MAX_HOURS    ,
                                                           DEFAULT_POLL_SEC     ,
                                                           DEFAULT_REGION       ,
                                                           DEFAULT_TIMEOUT_SEC  )
from sg_compute.cli.base.Spec__CLI__Errors        import set_debug, spec_cli_errors
from sg_compute.cli.base.Spec__CLI__Renderers__Base import (render_ami_bake          ,
                                                             render_create_preview   ,
                                                             render_ami_delete  ,
                                                             render_ami_list    ,
                                                             render_ami_wait    ,
                                                             render_create      ,
                                                             render_delete      ,
                                                             render_exec_result ,
                                                             render_health_probe,
                                                             render_info        ,
                                                             render_list        )
from sg_compute.cli.base.Spec__CLI__Resolver      import Spec__CLI__Resolver
from sg_compute.core.ami.service.AMI__Service     import AMI__Service


def render_cert_info(info, console: Console) -> None:                                  # shared by every `cert` sub-command
    from datetime import datetime, timezone

    from rich.table import Table

    def _fmt(ms):
        if not ms:
            return '—'
        return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=16, no_wrap=True)
    t.add_column()
    t.add_row('source',      str(getattr(info, 'source', '') or '—'))
    t.add_row('subject',     str(getattr(info, 'subject', '') or '—'))
    t.add_row('issuer',      str(getattr(info, 'issuer', '') or '—'))
    self_signed = bool(getattr(info, 'is_self_signed', False))
    t.add_row('self-signed', '[yellow]yes[/] (browser will warn)' if self_signed else '[green]no[/]')
    expired = bool(getattr(info, 'is_expired', False))
    days    = int(getattr(info, 'days_remaining', 0) or 0)
    t.add_row('validity', f'[red]EXPIRED[/]' if expired else f'[green]valid[/]  [dim]{days}d remaining[/]')
    t.add_row('not-after',   _fmt(getattr(info, 'not_after', 0)))
    sans = list(getattr(info, 'sans', []) or [])
    if sans:
        t.add_row('sans', ', '.join(str(s) for s in sans))
    t.add_row('fingerprint', f'[dim]{getattr(info, "fingerprint_sha256", "") or "—"}[/]')
    console.print()
    console.print(t)
    console.print()


class Spec__CLI__Builder:

    def __init__(self, cli_spec: Schema__Spec__CLI__Spec,
                       extra_create_options: Optional[List[Tuple[str, type, Any, str]]] = None):
        self.cli_spec             = cli_spec
        self.extra_create_options = extra_create_options or []
        self.resolver             = Spec__CLI__Resolver()

    def build(self) -> typer.Typer:
        app = typer.Typer(no_args_is_help  = True                                       ,
                          help             = f'Manage {self.cli_spec.display_name} stacks.',
                          add_completion   = False                                       )

        @app.callback()
        def _root(debug: bool = typer.Option(False, '--debug', '-D',
                                             help='Show full Python traceback on errors.')):
            set_debug(debug)

        self._register_list   (app)
        self._register_info   (app)
        self._register_create (app)
        self._register_wait   (app)
        self._register_health (app)
        self._register_connect(app)
        self._register_exec   (app)
        self._register_delete (app)
        self._register_ami    (app)
        self._register_cert   (app)
        return app

    # ── internal helpers ──────────────────────────────────────────────────────

    def _service(self):
        return self.cli_spec.service_factory()

    def _build_typed_fn(self, impl, params: List[Tuple[str, type, Any]], name: str):
        parameters = [
            inspect.Parameter(pname, inspect.Parameter.POSITIONAL_OR_KEYWORD,
                              default=pdefault, annotation=ptype)
            for pname, ptype, pdefault in params
        ]
        sig = inspect.Signature(parameters)

        def wrapper(*args, **kwargs):
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            return impl(**bound.arguments)

        wrapper.__signature__ = sig
        wrapper.__name__      = name
        wrapper.__annotations__ = {p.name: p.annotation for p in parameters}
        return wrapper

    def _wait_healthy(self, svc, region: str, stack_name: str) -> None:
        c   = Console(highlight=False)
        c.print(f'\n  [dim]Waiting for {self.cli_spec.spec_id} stack {stack_name!r} to be healthy …[/]')
        result = svc.health(region, stack_name,
                             timeout_sec=DEFAULT_TIMEOUT_SEC, poll_sec=DEFAULT_POLL_SEC)
        render_health_probe(result, c)
        if not getattr(result, 'healthy', False):
            Console(highlight=False, stderr=True).print(
                f'  [red]✗[/]  Stack {stack_name!r} did not become healthy in {DEFAULT_TIMEOUT_SEC}s')
            raise typer.Exit(1)

    # ── verb registrations ────────────────────────────────────────────────────

    def _register_list(self, app):
        service_factory = self.cli_spec.service_factory

        @app.command(name='list')
        @spec_cli_errors
        def list_stacks(region: str = typer.Option(DEFAULT_REGION, '--region', '-r',
                                                   help='AWS region.')):
            """List all running stacks in the region."""
            svc     = service_factory()
            listing = svc.list_stacks(region)
            render_list(listing, Console(highlight=False, width=200))

    def _register_info(self, app):
        service_factory = self.cli_spec.service_factory
        resolver        = self.resolver
        spec_id         = self.cli_spec.spec_id
        render_info_fn  = getattr(self.cli_spec, 'render_info_fn', None) or render_info

        @app.command()
        @spec_cli_errors
        def info(name  : Optional[str] = typer.Argument(None,
                          help='Stack name; auto-selected when only one exists.'),
                 region: str           = typer.Option(DEFAULT_REGION, '--region', '-r')):
            """Show detailed info for a single stack."""
            svc  = service_factory()
            name = resolver.resolve(svc, name, region, spec_id)
            data = svc.get_stack_info(region, name)
            if data is None:
                Console(highlight=False, stderr=True).print(
                    f'  [red]✗  No {spec_id} stack matched {name!r}[/]')
                raise typer.Exit(1)
            render_info_fn(data, Console(highlight=False, width=200))

    def _register_create(self, app):
        cli_spec         = self.cli_spec
        resolver         = self.resolver
        service_factory  = self.cli_spec.service_factory
        spec_id          = self.cli_spec.spec_id
        extra_options    = self.extra_create_options
        render_create_fn = getattr(self.cli_spec, 'render_create_fn', None) or render_create
        render_info_fn   = getattr(self.cli_spec, 'render_info_fn',   None) or render_info

        base_params = [
            ('name',          Optional[str], typer.Option(None, '--name', '-n',
                              help='Stack name; auto-generated if omitted.')),
            ('region',        str,           typer.Option(DEFAULT_REGION, '--region', '-r')),
            ('instance_type', str,           typer.Option(cli_spec.default_instance_type,
                                                          '--instance-type', '-t')),
            ('max_hours',     float,         typer.Option(DEFAULT_MAX_HOURS, '--max-hours', '--mh')),
            ('ami',           str,           typer.Option('', '--ami',
                                            help='AMI ID; resolved from spec helper if blank.')),
            ('caller_ip',     str,           typer.Option('', '--caller-ip',
                                            help='Source IP for SG; auto-detected if blank.')),
            ('wait',          bool,          typer.Option(False, '--wait',
                                            help='Block until healthy after create.')),
        ]
        extra_params  = []
        advanced_keys = set()
        for opt in extra_options:
            n, t, d, h   = opt[:4]
            is_advanced  = len(opt) > 4 and opt[4]
            flag = f'--{n.replace("_", "-")}'
            if t is bool and d is True:
                flag = f'{flag}/--no-{n.replace("_", "-")}'                                       # dual-flag pattern lets the user opt out of true-by-default flags
            extra_params.append((n, t, typer.Option(d, flag, help=h, hidden=is_advanced)))
            if is_advanced:
                advanced_keys.add(n)
        all_params = base_params + extra_params

        # Defaults for the pre-launch preview banner — must match base_params + extras.
        preview_defaults = {
            'region'       : DEFAULT_REGION                ,
            'instance_type': cli_spec.default_instance_type,
            'max_hours'    : DEFAULT_MAX_HOURS             ,
            'ami'          : ''                            ,
            'caller_ip'    : ''                            ,
            'wait'         : False                         ,
        }
        for opt in extra_options:
            preview_defaults[opt[0]] = opt[2]

        def create_impl(**kwargs):
            console = Console(highlight=False, width=200)
            render_create_preview(spec_id, 'create', kwargs.get('name') or '',
                                  kwargs, preview_defaults, console,
                                  advanced_keys=advanced_keys)
            svc    = service_factory()
            region = kwargs['region']
            name   = kwargs.get('name') or (
                svc.name_gen.generate() if hasattr(svc, 'name_gen') else f'{spec_id}-auto')
            req    = cli_spec.create_request_cls()
            if hasattr(req, 'stack_name'):
                setattr(req, 'stack_name', name)
            if hasattr(req, 'region'):
                setattr(req, 'region', region)
            for attr, kwarg in (('instance_type', 'instance_type'),
                                 ('max_hours',     'max_hours'    ),
                                 ('from_ami',      'ami'          ),
                                 ('caller_ip',     'caller_ip'   )):
                if hasattr(req, attr):
                    setattr(req, attr, kwargs[kwarg])
            if cli_spec.extra_create_field_setters:
                cli_spec.extra_create_field_setters(req, **{
                    opt[0]: kwargs[opt[0]] for opt in extra_options
                })
            resp       = svc.create_stack(req)
            render_create_fn(resp, console)
            # Optional post-launch hook — kicks off background work (e.g. vault-app
            # --with-aws-dns running Route 53 upsert + INSYNC wait in parallel with
            # the EC2 boot). The returned task (or None) is joined after _wait_healthy
            # so the parallel work has the entire EC2 boot window to finish.
            post_launch_task = None
            if cli_spec.post_launch_fn is not None:
                try:
                    post_launch_task = cli_spec.post_launch_fn(svc, region, req, resp, kwargs, console)
                except Exception as exc:                                                # never crash create on a hook failure — print and continue
                    Console(highlight=False, stderr=True).print(
                        f'  [yellow]⚠[/]  post_launch hook failed: {type(exc).__name__}: {exc}')
            if kwargs.get('wait'):
                info      = getattr(resp, 'stack_info', None) or resp
                real_name = str(getattr(info, 'stack_name', '') or name)
                self._wait_healthy(svc, region, real_name)
                if post_launch_task is not None and hasattr(post_launch_task, 'join'):
                    post_launch_task.join(timeout=180)                                  # 3-min ceiling so a stuck task can't hang the CLI indefinitely
                # surface the final info block so the URLs / access token / cert info
                # are visible without a second `sp <spec> info` call
                fresh = svc.get_stack_info(region, real_name)
                if fresh is not None:
                    render_info_fn(fresh, console)

        fn = self._build_typed_fn(create_impl, all_params, 'create')
        fn.__doc__ = 'Launch a new stack. Prints a preview banner then submits to AWS.'
        app.command()(spec_cli_errors(fn))

    def _register_wait(self, app):
        service_factory = self.cli_spec.service_factory
        resolver        = self.resolver
        spec_id         = self.cli_spec.spec_id

        @app.command()
        @spec_cli_errors
        def wait(name   : Optional[str] = typer.Argument(None,
                           help='Stack name; auto-selected when only one exists.'),
                 region : str           = typer.Option(DEFAULT_REGION, '--region', '-r'),
                 timeout: int           = typer.Option(DEFAULT_TIMEOUT_SEC, '--timeout',
                                         help='Max seconds to wait.'),
                 poll   : int           = typer.Option(DEFAULT_POLL_SEC, '--poll',
                                         help='Seconds between polls.')):
            """Block until the stack is healthy (or timeout expires)."""
            svc    = service_factory()
            name   = resolver.resolve(svc, name, region, spec_id)
            result = svc.health(region, name, timeout_sec=timeout, poll_sec=poll)
            render_health_probe(result, Console(highlight=False, width=200))
            if not getattr(result, 'healthy', False):
                raise typer.Exit(1)

    def _register_health(self, app):
        service_factory = self.cli_spec.service_factory
        resolver        = self.resolver
        spec_id         = self.cli_spec.spec_id

        @app.command()
        @spec_cli_errors
        def health(name   : Optional[str] = typer.Argument(None,
                              help='Stack name; auto-selected when only one exists.'),
                   region : str           = typer.Option(DEFAULT_REGION, '--region', '-r'),
                   timeout: int           = typer.Option(0, '--timeout',
                                           help='0 = instant probe; >0 = wait up to N seconds.')):
            """Probe the stack health endpoint. Exit 1 if unhealthy."""
            svc    = service_factory()
            name   = resolver.resolve(svc, name, region, spec_id)
            result = svc.health(region, name, timeout_sec=timeout)
            render_health_probe(result, Console(highlight=False, width=200))

    def _register_connect(self, app):
        service_factory = self.cli_spec.service_factory
        resolver        = self.resolver
        spec_id         = self.cli_spec.spec_id

        @app.command()
        @spec_cli_errors
        def connect(name  : Optional[str] = typer.Argument(None,
                               help='Stack name; auto-selected when only one exists.'),
                    region: str           = typer.Option(DEFAULT_REGION, '--region', '-r')):
            """Open an interactive SSM session on the instance."""
            svc         = service_factory()
            name        = resolver.resolve(svc, name, region, spec_id)
            instance_id = svc.connect_target(region, name)
            Console(highlight=False).print(
                f'  [dim]Connecting to {name} ({instance_id}) in {region}…[/]\n')
            os.execvp('aws', ['aws', 'ssm', 'start-session',
                               '--target', instance_id, '--region', region])

    def _register_exec(self, app):
        service_factory = self.cli_spec.service_factory
        resolver        = self.resolver
        spec_id         = self.cli_spec.spec_id

        @app.command(name='exec')
        @spec_cli_errors
        def exec_cmd(args   : Optional[List[str]] = typer.Argument(None,
                                help='[STACK-NAME] CMD [ARGS…] — stack auto-selected when one exists.'),
                     region : str                 = typer.Option(DEFAULT_REGION, '--region', '-r'),
                     timeout: int                 = typer.Option(DEFAULT_EXEC_TIMEOUT, '--timeout'),
                     cwd    : str                 = typer.Option('', '--cwd',
                                help='Working directory on the remote host.')):
            """Run a shell command on the instance via SSM and print the output.

            \b
            All three forms work:
              exec STACK-NAME CMD [ARGS…]   e.g.  exec lean-euler docker images
              exec CMD [ARGS…]              e.g.  exec docker images   (auto-resolve)
              exec "CMD ARGS"               e.g.  exec "docker ps -a"  (quoted)
            """
            if not args:
                raise typer.BadParameter('Provide a command: exec [STACK-NAME] CMD [ARGS…]')
            svc     = service_factory()
            listing = svc.list_stacks(region)
            known   = {str(s.stack_name) for s in listing.stacks if str(s.stack_name)}
            if len(args) > 1 and args[0] in known:
                name    = args[0]
                command = ' '.join(args[1:])
            else:
                stacks = sorted(known)
                if not stacks:
                    Console(highlight=False, stderr=True).print(
                        f'\n  [yellow]No {spec_id} stacks in {region}.[/]\n')
                    raise typer.Exit(1)
                if len(stacks) == 1:
                    Console(highlight=False).print(
                        f'\n  [dim]One stack found — using [bold]{stacks[0]}[/][/]')
                    name = stacks[0]
                else:
                    name = resolver.resolve(svc, None, region, spec_id)
                command = ' '.join(args)
            result = svc.exec(region, name, command, timeout_sec=timeout, cwd=cwd)
            render_exec_result(result, Console(highlight=False, width=200))

    def _register_delete(self, app):
        service_factory = self.cli_spec.service_factory
        resolver        = self.resolver
        spec_id         = self.cli_spec.spec_id

        @app.command()
        @spec_cli_errors
        def delete(name  : Optional[str] = typer.Argument(None,
                              help='Stack name; auto-selected when only one exists.'),
                   region: str           = typer.Option(DEFAULT_REGION, '--region', '-r'),
                   yes   : bool          = typer.Option(False, '--yes', '-y',
                              help='Skip confirmation prompt.')):
            """Terminate the instance and delete its security group."""
            svc  = service_factory()
            name = resolver.resolve(svc, name, region, spec_id)
            if not yes:
                typer.confirm(f'Delete {spec_id} stack {name!r} in {region}?', default=True, abort=True)
            result = svc.delete_stack(region, name)
            render_delete(name, getattr(result, 'deleted', False),
                          Console(highlight=False, width=200))
            if not getattr(result, 'deleted', False):
                raise typer.Exit(1)

    def _register_ami(self, app):
        service_factory = self.cli_spec.service_factory
        resolver        = self.resolver
        spec_id         = self.cli_spec.spec_id
        display_name    = self.cli_spec.display_name

        ami_app = typer.Typer(no_args_is_help = True                                          ,
                              help            = f'Manage {display_name} AMIs (list/bake/wait/delete).',
                              add_completion  = False                                          )

        @ami_app.command(name='list')
        @spec_cli_errors
        def ami_list(region: str = typer.Option(DEFAULT_REGION, '--region', '-r')):
            result = AMI__Service(region=region).list_amis(spec_id)
            render_ami_list(result, Console(highlight=False, width=200))

        @ami_app.command(name='bake')
        @spec_cli_errors
        def ami_bake(name      : Optional[str] = typer.Argument(None,
                                  help='Stack name to bake; auto-selected when only one exists.'),
                     region    : str           = typer.Option(DEFAULT_REGION, '--region', '-r'),
                     ami_name  : str           = typer.Option('', '--name', '-n',
                                  help=f'AMI name; auto-generated as {spec_id}-<stack>-<epoch> if blank.'),
                     reboot    : bool          = typer.Option(False, '--reboot',
                                  help='Reboot before snapshot (filesystem-consistent; ~30s downtime).'),
                     wait      : bool          = typer.Option(False, '--wait',
                                  help='Block until the AMI reaches state=available (5–15 min).')):
            import time
            svc  = service_factory()
            name = resolver.resolve(svc, name, region, spec_id)
            info = svc.get_stack_info(region, name)
            if info is None:
                Console(highlight=False, stderr=True).print(
                    f'  [red]✗  No {spec_id} stack matched {name!r}[/]')
                raise typer.Exit(1)
            instance_id = str(info.instance_id)
            final_name  = ami_name or f'{spec_id}-{name}-{int(time.time())}'
            ami_svc     = AMI__Service(region=region)
            baked       = ami_svc.bake(region       = region        ,
                                       spec_id      = spec_id       ,
                                       instance_id  = instance_id   ,
                                       ami_name     = final_name    ,
                                       source_stack = name          ,
                                       no_reboot    = not reboot    )
            render_ami_bake(baked, Console(highlight=False, width=200))
            if wait:
                self._wait_ami_available(ami_svc, region, str(baked.ami_id))

        @ami_app.command(name='wait')
        @spec_cli_errors
        def ami_wait(ami_id : str = typer.Argument(..., help='AMI ID to wait on.'),
                     region : str = typer.Option(DEFAULT_REGION, '--region', '-r')):
            self._wait_ami_available(AMI__Service(region=region), region, ami_id)

        @ami_app.command(name='delete')
        @spec_cli_errors
        def ami_delete(ami_id: str  = typer.Argument(..., help='AMI ID to deregister.'),
                       region: str  = typer.Option(DEFAULT_REGION, '--region', '-r'),
                       yes   : bool = typer.Option(False, '--yes', '-y',
                                  help='Skip confirmation prompt.')):
            if not yes:
                typer.confirm(f'Deregister {ami_id} and delete its snapshots?',
                              default=True, abort=True)
            deregistered, snapshots_deleted = AMI__Service(region=region).delete(region, ami_id)
            render_ami_delete(ami_id, deregistered, snapshots_deleted,
                              Console(highlight=False, width=200))
            if not deregistered:
                raise typer.Exit(1)

        app.add_typer(ami_app, name='ami')

    def _register_cert(self, app):
        service_factory = self.cli_spec.service_factory
        resolver        = self.resolver
        spec_id         = self.cli_spec.spec_id

        cert_app = typer.Typer(no_args_is_help = True                                                  ,
                               help            = 'Inspect, generate and verify TLS certificates.'      ,
                               add_completion  = False                                                  )

        @cert_app.command(name='generate')
        @spec_cli_errors
        def cert_generate(common_name: str       = typer.Option(..., '--common-name', '--cn',
                                                  help='Cert CN; also added as a SAN entry.'),
                          san        : List[str] = typer.Option(None, '--san',
                                                  help='Extra SAN entry — repeat for more.'),
                          days       : int       = typer.Option(160, '--days',
                                                  help='Validity window in days (default 160 — the LE shortlived ceiling).'),
                          out_cert   : str       = typer.Option('cert.pem', '--out-cert'),
                          out_key    : str       = typer.Option('key.pem',  '--out-key')):
            """Generate a self-signed cert + key locally. No AWS, works offline."""
            from sg_compute.platforms.tls.Cert__Generator import Cert__Generator
            from sg_compute.platforms.tls.Cert__Inspector import Cert__Inspector
            Cert__Generator().generate_to_files(cert_path   = out_cert            ,
                                                key_path    = out_key             ,
                                                common_name = common_name         ,
                                                sans        = list(san or [])     ,
                                                days_valid  = days                )
            c = Console(highlight=False)
            c.print(f'\n  [green]✓[/]  self-signed cert written  [dim]cert={out_cert}  key={out_key}[/]')
            render_cert_info(Cert__Inspector().inspect_file(out_cert), c)

        @cert_app.command(name='inspect')
        @spec_cli_errors
        def cert_inspect(file: str = typer.Option('', '--file', '-f', help='PEM file to decode.'),
                         host: str = typer.Option('', '--host',       help='Live host to TLS-probe instead of a file.'),
                         port: int = typer.Option(443, '--port')):
            """Decode a cert from a PEM file or a live TLS handshake."""
            from sg_compute.platforms.tls.Cert__Inspector import Cert__Inspector
            if not file and not host:
                raise typer.BadParameter('provide --file or --host')
            inspector = Cert__Inspector()
            info      = inspector.inspect_file(file) if file else inspector.inspect_host(host, port)
            render_cert_info(info, Console(highlight=False))

        @cert_app.command(name='show')
        @spec_cli_errors
        def cert_show(name  : Optional[str] = typer.Argument(None,
                              help='Stack name; auto-selected when only one exists.'),
                      region: str           = typer.Option(DEFAULT_REGION, '--region', '-r'),
                      port  : int           = typer.Option(443, '--port')):
            """Show the TLS cert the stack is currently serving on :443."""
            from sg_compute.platforms.tls.Cert__Inspector import Cert__Inspector
            svc  = service_factory()
            name = resolver.resolve(svc, name, region, spec_id)
            info = svc.get_stack_info(region, name)
            ip   = str(getattr(info, 'public_ip', '') or '') if info else ''
            if not ip:
                Console(highlight=False, stderr=True).print(
                    f'  [red]✗  {name!r} has no public IP yet[/]')
                raise typer.Exit(1)
            c = Console(highlight=False)
            c.print(f'\n  [bold]{name}[/]  [dim]{ip}:{port}[/]')
            render_cert_info(Cert__Inspector().inspect_host(ip, port), c)

        @cert_app.command(name='check')
        @spec_cli_errors
        def cert_check(name  : Optional[str] = typer.Argument(None,
                              help='Stack name; auto-selected when only one exists.'),
                       region: str           = typer.Option(DEFAULT_REGION, '--region', '-r'),
                       port  : int           = typer.Option(443, '--port')):
            """Probe the stack: TLS cert + the last browser-reported secure-context result."""
            import json
            import ssl
            import urllib.request

            from sg_compute.platforms.tls.Cert__Inspector import Cert__Inspector
            svc  = service_factory()
            name = resolver.resolve(svc, name, region, spec_id)
            info = svc.get_stack_info(region, name)
            ip   = str(getattr(info, 'public_ip', '') or '') if info else ''
            if not ip:
                Console(highlight=False, stderr=True).print(
                    f'  [red]✗  {name!r} has no public IP yet[/]')
                raise typer.Exit(1)
            c = Console(highlight=False)
            c.print(f'\n  [bold]{name}[/]  [dim]{ip}:{port}[/]')
            render_cert_info(Cert__Inspector().inspect_host(ip, port), c)

            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode    = ssl.CERT_NONE
            try:
                url = f'https://{ip}:{port}/tls/secure-context-last'
                with urllib.request.urlopen(url, timeout=5, context=ctx) as resp:
                    last = json.loads(resp.read().decode())
            except Exception as exc:
                c.print(f'  [yellow]⚠[/]  could not read secure-context report  [dim]{str(exc)[:80]}[/]\n')
                raise typer.Exit(1)

            if not last.get('recorded'):
                c.print(f'  [dim]no browser has reported yet — open[/] '
                        f'[cyan]https://{ip}:{port}/tls/secure-context-check[/]\n')
                return
            secure = bool(last.get('is_secure_context'))
            crypto = bool(last.get('has_web_crypto'))
            ok     = '[green]PASS[/]'
            bad    = '[red]FAIL[/]'
            c.print(f'  window.isSecureContext   {ok if secure else bad}')
            c.print(f'  window.crypto.subtle     {ok if crypto else bad}')
            c.print()
            if not (secure and crypto):
                raise typer.Exit(1)

        app.add_typer(cert_app, name='cert')

    def _wait_ami_available(self, ami_svc, region: str, ami_id: str,
                                  timeout_sec: int = 1800, poll_sec: int = 15) -> None:        # 30-min ceiling: bake of a 250 GiB Ollama AMI runs 8–15 min
        import time
        c       = Console(highlight=False)
        c.print(f'\n  [dim]Waiting for AMI {ami_id} to be available …[/]')
        deadline = time.monotonic() + timeout_sec
        state    = ''
        while time.monotonic() < deadline:
            state = ami_svc.describe_state(region, ami_id)
            if state in ('available', 'failed', 'invalid', 'error'):
                break
            time.sleep(poll_sec)
        elapsed = int(timeout_sec - max(0, deadline - time.monotonic()))
        render_ami_wait(ami_id, state, elapsed, c)
        if state != 'available':
            raise typer.Exit(1)

# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute_specs vault_app/fargate — Phase__Progress__Renderer
# Live rich.Live table renderer for Phase__Timer.progress_cb.
# Use as a context manager; wire up via as_progress_cb().
#
#   phases = ['ecr', 'iam', 'cluster', 'task-def']
#   with Phase__Progress__Renderer(title='Setup', phases=phases) as renderer:
#       timer = Phase__Timer(progress_cb=renderer.as_progress_cb())
#       with timer.phase('ecr'): ...
# ═══════════════════════════════════════════════════════════════════════════════

import time

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_app.fargate.enums.Enum__VAF__Phase__Status import Enum__VAF__Phase__Status


_STATUS_ICON = {                                                                 # rich markup strings for each lifecycle state
    'PENDING': '[dim]⏳[/dim]',
    'RUNNING': '[cyan]▶[/cyan]',
    'OK':      '[green]✓[/green]',
    'SKIPPED': '[yellow]≡[/yellow]',
    'WARN':    '[yellow]⚠[/yellow]',
    'ERROR':   '[red]✗[/red]',
}


class Phase__Progress__Renderer(Type_Safe):
    title  : str  = 'Phases'
    phases : list = None                                                         # ordered list of phase name strings

    def __enter__(self):
        from rich.console import Console
        from rich.live    import Live

        self._state = {                                                          # per-phase mutable state dict
            name: {'status': Enum__VAF__Phase__Status.PENDING,
                   'started_at': None, 'elapsed_ms': 0, 'detail': ''}
            for name in (self.phases or [])
        }
        self._live = Live(self._build_table(), refresh_per_second=4)
        self._live.start()
        return self

    def __exit__(self, *exc):
        if self._live:
            self._live.update(self._build_table())
            self._live.stop()

    def on_phase(self, name: str, status, detail: str = ''):                    # update state for name and refresh the live table
        if name not in self._state:                                              # surface unknown phases rather than silently drop
            self._state[name] = {'status': Enum__VAF__Phase__Status.PENDING,
                                 'started_at': None, 'elapsed_ms': 0, 'detail': ''}
            if self.phases is not None:
                self.phases.append(name)
        entry = self._state[name]
        now   = time.monotonic()
        if status == Enum__VAF__Phase__Status.RUNNING:
            entry['status']     = status
            entry['started_at'] = now
            entry['detail']     = detail
        else:
            entry['status']  = status
            entry['detail']  = detail
            if entry['started_at'] is not None:
                entry['elapsed_ms'] = int((now - entry['started_at']) * 1000)
        if self._live:
            self._live.update(self._build_table())

    def _build_table(self):                                                      # build a rich Table from current _state
        from rich.table import Table

        t = Table(title=self.title, box=None, show_header=True, padding=(0, 2))
        t.add_column('Status',  style='')
        t.add_column('Phase',   style='bold')
        t.add_column('Elapsed', style='dim', justify='right')
        t.add_column('Detail',  style='dim')

        total_ms = 0
        for name in (self.phases or []):
            entry  = self._state.get(name, {})
            status = entry.get('status', Enum__VAF__Phase__Status.PENDING)
            status_key = str(status) if isinstance(status, Enum__VAF__Phase__Status) else str(status)
            icon   = _STATUS_ICON.get(status_key, status_key)
            ms     = entry.get('elapsed_ms', 0)
            detail = entry.get('detail', '')
            elapsed_s = f'{ms / 1000:.1f}s' if ms else ''
            t.add_row(icon, name, elapsed_s, detail)
            if status not in (Enum__VAF__Phase__Status.PENDING, Enum__VAF__Phase__Status.RUNNING):
                total_ms += ms

        # totals row
        total_s = f'{total_ms / 1000:.1f}s' if total_ms else ''
        t.add_row('[dim]─[/dim]' * 1, '[dim]Total[/dim]', f'[dim]{total_s}[/dim]', '')
        return t

    def as_progress_cb(self):                                                    # returns a closure suitable for Phase__Timer.progress_cb
        return lambda name, status, detail='': self.on_phase(name, status, detail)

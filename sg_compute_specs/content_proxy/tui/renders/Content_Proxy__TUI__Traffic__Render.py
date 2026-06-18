# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: traffic render (mockup 2)
# PURE — returns Rich markup strings. One line per flow: via, method, host/path,
# status, action, fastapi. Testable on 3.11.
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Flow__Action          import Enum__Content_Proxy__Flow__Action


_ACTION_COLOUR = {Enum__Content_Proxy__Flow__Action.INJECTED: 'green' ,
                  Enum__Content_Proxy__Flow__Action.BLOCKED : 'red'   ,
                  Enum__Content_Proxy__Flow__Action.CACHED  : 'cyan'  ,
                  Enum__Content_Proxy__Flow__Action.SKIPPED : 'dim'   ,
                  Enum__Content_Proxy__Flow__Action.FALLBACK: 'yellow',
                  Enum__Content_Proxy__Flow__Action.PASSED  : 'white' }


def traffic_markup(flows) -> str:                                                  # flows = iterable of Schema__Content_Proxy__Flow__Summary
    flows = list(flows)
    lines = ['[bold]Content-Transformation Proxy — Traffic[/]', '']
    if not flows:
        lines += ['  [dim]no flows captured yet[/]', '']
    for f in flows:
        colour = _ACTION_COLOUR.get(f.action, 'white')
        status = str(f.status_code) if f.status_code else '—'
        fa     = '[green]connected[/]' if f.fastapi_connected else '[dim]—[/]'
        lines.append(f'  [dim]{f.via.value}[/]  {str(f.method):<4}  '
                     f'{str(f.host)}{str(f.path)}  '
                     f'{status:<4}  [{colour}]{f.action.value}[/]  {fa}')
    lines += ['', '[dim]injected=script added · blocked=403 · cached=answered in request · '
                  'fallback=FastAPI down[/]',
              '[dim][enter] flow detail   [v] ext/int   [r] refresh   [q] quit[/]']
    return '\n'.join(lines)


def traffic_plain(flows) -> str:                                                   # no-TTY fallback
    out = []
    for f in list(flows):
        status = str(f.status_code) if f.status_code else '-'
        out.append(f'{f.via.value} {str(f.method)} {str(f.host)}{str(f.path)} '
                   f'{status} {f.action.value} '
                   f'{"connected" if f.fastapi_connected else "-"}')
    return '\n'.join(out)

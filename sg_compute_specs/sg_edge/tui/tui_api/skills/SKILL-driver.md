# SG/Edge local edge — TUI API (for drivers / pytest)

Construct the provider over an injected source (no mocks, no AWS):

```python
from sg_compute_specs.sg_edge.local.Local__Edge__Stack            import Local__Edge__Stack
from sg_compute_specs.sg_edge.tui.source.SG_Edge__TUI__Local_Source import SG_Edge__TUI__Local_Source
from sg_compute_specs.sg_edge.tui.tui_api.SG_Edge__Tui_Api__Provider import SG_Edge__Tui_Api__Provider
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Registry        import Tui_Api__Registry
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Execution_Center import Tui_Api__Execution_Center

source   = SG_Edge__TUI__Local_Source(stack=Local__Edge__Stack(state_dir='/tmp/x'))
registry = Tui_Api__Registry().register(SG_Edge__Tui_Api__Provider(source=source))
center   = Tui_Api__Execution_Center(registry=registry)

center.execute('sg-edge.local', 'setup',    {}, on_confirm=lambda *_: True)
center.execute('sg-edge.local', 'register', {'slug': 'alice'}, on_confirm=lambda *_: True)
center.execute('sg-edge.local', 'request',  {'slug': 'alice'})        # read-only, no gate
```

- Read actions need no confirm; WRITE/CRUD/DESTRUCTIVE need `on_confirm` returning
  `True` (or `SG_TUI_API__ALLOW_MUTATIONS=1`).
- `center.available_actions('sg-edge.local')` returns only the currently-available
  actions (write actions vanish when `state()['can_act']` is False — the AWS source).
- An AWS source: `SG_Edge__TUI__AWS_Source(dns=SG_Edge__DNS__Helper(route53=Route53__AWS__Client__In_Memory()))`.

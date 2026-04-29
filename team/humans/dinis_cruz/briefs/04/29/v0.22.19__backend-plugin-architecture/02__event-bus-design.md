# 02 — Event Bus Design

**Status:** PROPOSED
**Read after:** `01__plugin-registry-design.md`

---

## What this doc gives you

The full design of the in-process event bus: API surface, payload conventions, event vocabulary, and how plugins emit/listen without inter-plugin imports.

## Mental model

The event bus is **an in-process publish/subscribe register**. Plugins emit events ("a Linux stack was just created"); other plugins or core code listen for events of interest ("when any stack is created, log it to the activity vault file"). Listeners are best-effort. If no one is listening, the event is silently dropped.

This is **not**:
- A message queue (no persistence)
- A cross-process bus (no Redis, no SQS, no EventBridge)
- A replacement for direct method calls (if A needs B to do something *and acknowledge*, that's a method call, not an event)
- A guaranteed-delivery system (a listener that throws does not stop other listeners but is logged)

This **is**:
- A way for plugins to announce facts ("X happened") without knowing or caring who's listening
- A way for new plugins to start observing existing facts without touching the emitter
- An audit/logging seam — anything written to the vault as activity log entries comes through here

## Why now, why this shape

The current UI already uses a DOM-event variant of this pattern (`vault:connected`, `sp-cli:vault-bus:read-started`, `sp-cli:stack-selected`) and it works. The backend is direct method calls today (`catalog_service.list_all_stacks()` → calls `vnc_service.list_stacks()` directly). For the *current* set of compute types this works. But:

1. **Cross-cutting concerns** (audit log, billing, telemetry) want to react to "any stack created" without each compute type knowing about the audit listener.
2. **Plugin loose-coupling** is the brief's central principle. If `vnc/` had to call `audit_service.log()` directly, it would have to import from `audit/`, breaking the layering rule.
3. **Future cross-process** events become tractable once the in-process pattern is established. Vault-as-bus (forward roadmap) is a drop-in replacement for the in-process implementation.

## API

```python
# sgraph_ai_service_playwright__cli/core/event_bus/Event__Bus.py

from typing                          import Callable
from osbot_utils.type_safe.Type_Safe import Type_Safe
from osbot_utils.utils.Misc          import logger


class Event__Bus(Type_Safe):
    """In-process pub/sub. Module-level singleton — import `event_bus`."""
    _listeners : dict[str, list[Callable]] = None     # event_name → [handlers]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._listeners = {}

    def emit(self, event_name: str, payload: dict | Type_Safe) -> int:
        """Fire `event_name` with `payload` to all listeners.
           Returns the number of listeners that handled it (zero is fine).
           Listener exceptions are caught and logged — they do not propagate
           to the emitter."""
        handlers = self._listeners.get(event_name, [])
        delivered = 0
        for handler in handlers:
            try:
                handler(payload)
                delivered += 1
            except Exception as e:
                logger().error(f'event_bus: handler for {event_name!r} raised: {e}')
        return delivered

    def on(self, event_name: str, handler: Callable) -> Callable:
        """Register `handler` for `event_name`. Returns the handler so
           the caller can store a reference for later off()."""
        self._listeners.setdefault(event_name, []).append(handler)
        return handler

    def off(self, event_name: str, handler: Callable) -> bool:
        """Unregister. Returns True if the handler was registered."""
        if handler in self._listeners.get(event_name, []):
            self._listeners[event_name].remove(handler)
            return True
        return False

    def listener_count(self, event_name: str) -> int:
        return len(self._listeners.get(event_name, []))

    def reset(self):
        """Test helper — clears all listeners."""
        self._listeners = {}


# Module-level singleton — every plugin imports this exact instance.
event_bus = Event__Bus()
```

## Naming convention

`{plugin}:{noun}.{verb}` — colon between scope and topic, dot between noun and verb.

Examples:

| Event | When it fires |
|---|---|
| `core:plugin.loaded` | Registry has successfully loaded a plugin manifest |
| `core:plugin.skipped` | Plugin was skipped due to manifest `enabled=False` or env override |
| `core:plugin.failed` | Plugin module raised on import |
| `linux:stack.created` | `Linux__Service.create_stack()` succeeded |
| `linux:stack.deleted` | `Linux__Service.delete_stack()` succeeded |
| `linux:stack.health.changed` | A health probe transitioned from one state to another |
| `vnc:stack.created` | `Vnc__Service.create_stack()` succeeded |
| `vnc:stack.deleted` | `Vnc__Service.delete_stack()` succeeded |
| `vnc:stack.health.changed` | (same) |
| `docker:stack.created` | (same) |
| `docker:stack.deleted` | (same) |
| `elastic:stack.created` | (same) |
| `elastic:stack.deleted` | (same) |
| `prometheus:stack.created` | (same) |
| `prometheus:stack.deleted` | (same) |
| `opensearch:stack.created` | (when the type goes available) |
| `opensearch:stack.deleted` | (when the type goes available) |

The frontend's existing event vocabulary (`vault:connected`, `sp-cli:vault-bus:*`, etc.) is **not changed by this brief**. The new convention is for backend events. Frontend events stay as they are. They don't share a wire — frontend events are DOM-events; backend events are Python in-process. The same naming style applies to both, by convention.

### Why this shape

- **`{plugin}:{noun}.{verb}`** keeps the plugin scope first, so an audit listener can subscribe to a glob pattern in the future (`*:stack.created`) without false matches across unrelated topics.
- **`.created` / `.deleted` / `.changed`** are past-tense facts. Events describe what happened, not what should happen. ("Commands" — "do X" — are method calls.)
- **No `_started` / `_completed` pairs** for synchronous operations. If `create_stack()` returns successfully, fire `stack.created` once. The brief's "every read/write fires before/after" is for the frontend `vault-bus` (where async progress matters and the trace pane is the UX); the backend doesn't have a trace pane.

## Standard payload — `Schema__Stack__Event`

All `*:stack.*` events use the same payload shape. Defined once in core:

```python
# sgraph_ai_service_playwright__cli/core/event_bus/schemas/Schema__Stack__Event.py

from osbot_utils.type_safe.Type_Safe                                       import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text import Safe_Str__Text
from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Type     import Enum__Stack__Type


class Schema__Stack__Event(Type_Safe):
    type_id      : Enum__Stack__Type      # which compute type — linux, vnc, etc.
    stack_name   : Safe_Str__Text         # the canonical name (e.g. linux-quiet-fermi)
    region       : Safe_Str__Text         # AWS region
    instance_id  : Safe_Str__Text         # i-xxx — empty for delete events fired before instance exists
    timestamp    : Safe_Str__Text         # ISO 8601 UTC
    detail       : Safe_Str__Text         # free-form one-liner describing the event
```

Other event families (e.g. `core:plugin.*`) use their own small payload schemas defined alongside the bus.

## How plugins emit

Plugins emit events from their service classes. Example — adding emit to the existing `Vnc__Service.create_stack()`:

```python
# sgraph_ai_service_playwright__cli/vnc/service/Vnc__Service.py
# (existing file — only the emit lines are new)

from sgraph_ai_service_playwright__cli.core.event_bus.Event__Bus              import event_bus
from sgraph_ai_service_playwright__cli.core.event_bus.schemas.Schema__Stack__Event \
                                                                              import Schema__Stack__Event

class Vnc__Service(Type_Safe):

    def create_stack(self, ...) -> Schema__Vnc__Stack__Create__Response:
        # ... existing logic ...
        result = self._do_create_stack(...)

        event_bus.emit('vnc:stack.created', Schema__Stack__Event(
            type_id     = Enum__Stack__Type.VNC,
            stack_name  = result.stack_name,
            region      = result.region,
            instance_id = result.instance_id,
            timestamp   = utc_now_iso(),
            detail      = f'created via {entry_point}',
        ))
        return result
```

The emit is a **single line** at the success site. If `create_stack()` raises, no event fires — that's correct, because the event is "stack was created," and a failed creation didn't create one.

## How code listens

Listeners register at startup. The plugin registry is the natural place for plugins-that-listen to set up:

```python
class Plugin__Manifest__Audit(Plugin__Manifest__Base):
    name : str = 'audit'

    def setup(self):
        # Listen for ALL stack events to write to vault activity log.
        for event_name in [
            'linux:stack.created',   'linux:stack.deleted',
            'docker:stack.created',  'docker:stack.deleted',
            'vnc:stack.created',     'vnc:stack.deleted',
            'elastic:stack.created', 'elastic:stack.deleted',
            'prometheus:stack.created', 'prometheus:stack.deleted',
        ]:
            event_bus.on(event_name, self._record_to_audit_log)

    def _record_to_audit_log(self, event: Schema__Stack__Event):
        # write to S3, vault, CloudWatch — whatever this plugin does
        ...
```

(`audit` plugin doesn't exist in this brief — it's an example. The brief's listeners are the trivial test fixtures and the future vault-as-bus listener.)

## Test helpers

The bus's `reset()` method is for tests. Standard pattern:

```python
class test_event_bus(TestCase):

    def setUp(self):
        event_bus.reset()                                         # clean state per test

    def test__emit_with_no_listener__silently_drops(self):
        delivered = event_bus.emit('test:nothing.happened', {})
        assert delivered == 0

    def test__emit_with_listener__delivers(self):
        received = []
        event_bus.on('test:thing.happened', lambda payload: received.append(payload))
        delivered = event_bus.emit('test:thing.happened', {'a': 1})
        assert delivered == 1
        assert received == [{'a': 1}]

    def test__listener_exception__does_not_break_emit(self):
        def bad_handler(_): raise ValueError('boom')
        good_received = []
        event_bus.on('test:x.happened', bad_handler)
        event_bus.on('test:x.happened', lambda p: good_received.append(p))
        delivered = event_bus.emit('test:x.happened', {})
        assert delivered == 1                                     # only the good handler counted
        assert good_received == [{}]
```

## Anti-patterns to avoid

1. **Don't emit "should X happen?" events.** Events are facts, not requests. If you find yourself wanting `linux:stack.create_requested`, that's a method call.
2. **Don't make events into a synchronous workflow.** If A emits and waits for B to do something, A and B are coupled — make it a method call. Events are fire-and-forget.
3. **Don't use the bus to pass pointers/objects.** Payloads should be Type_Safe schemas serialisable to JSON. Don't pass live AWS clients or file handles.
4. **Don't import another plugin to call its emit-helpers.** Plugins emit on their own service paths. If two plugins fire identical events, that's two facts about the same thing — fine.
5. **Don't replace direct API calls with events.** If the catalog service needs the live list of stacks NOW to render a response, that's a method call to each plugin's `list_stacks()`. Events are async-shape.
6. **Don't accumulate handlers in tests without `event_bus.reset()`.** Test pollution is real.

## Forward-compatibility note

The current implementation is in-process only. The forward roadmap (doc 03) describes vault-as-bus — events appended to a vault file, providing durability + audit + cross-process visibility. The API surface is **already designed to be a drop-in upgrade**:

- `emit()` becomes "write to vault"
- `on()` becomes "subscribe to vault file changes"
- The naming convention is preserved
- Schemas are unchanged

So when vault-as-bus lands later, no plugin code changes; only the bus implementation.

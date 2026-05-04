# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Event__Bus
# In-process pub/sub. Plugins emit facts ("stack created"); other code listens
# without needing to import the emitter. Best-effort delivery — a failing
# listener does not propagate to the emitter and does not block other listeners.
#
# Module-level singleton `event_bus` is the shared instance; every plugin
# imports it directly. Tests call event_bus.reset() in setUp.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                              import Callable
from osbot_utils.type_safe.Type_Safe     import Type_Safe


class Event__Bus(Type_Safe):
    listeners : dict[str, list[Callable]]   # event_name → registered handlers

    def emit(self, event_name: str, payload) -> int:
        handlers  = self.listeners.get(event_name, [])
        delivered = 0
        for handler in handlers:
            try:
                handler(payload)
                delivered += 1
            except Exception:                                                   # handler failure is isolated; emitter never sees it
                pass
        return delivered

    def on(self, event_name: str, handler: Callable) -> Callable:
        self.listeners.setdefault(event_name, []).append(handler)
        return handler

    def off(self, event_name: str, handler: Callable) -> bool:
        if handler in self.listeners.get(event_name, []):
            self.listeners[event_name].remove(handler)
            return True
        return False

    def listener_count(self, event_name: str) -> int:
        return len(self.listeners.get(event_name, []))

    def reset(self):                                                             # test helper — clears all listeners between tests
        self.listeners.clear()


event_bus = Event__Bus()                                                        # module-level singleton imported by all plugins

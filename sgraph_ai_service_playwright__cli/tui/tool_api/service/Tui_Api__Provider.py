# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api: Tui_Api__Provider
# The seam every host implements to expose a TUI API. B1 subset: manifest / skills /
# state / dispatch (+ an action() lookup). events / export / orientation / dry_run /
# actions_available are added in later slices (B3 / B6). Subclass per host.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Action      import Schema__Tui_Api__Action
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Manifest    import Schema__Tui_Api__Manifest
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Orientation import Schema__Tui_Api__Orientation
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Result      import Schema__Tui_Api__Result


class Tui_Api__Provider(Type_Safe):

    def manifest(self) -> Schema__Tui_Api__Manifest:                              # the static contract — subclass MUST implement
        raise NotImplementedError

    def skills(self) -> dict:                                                     # {'human':..,'api':..,'driver':..} markdown
        return {}

    def state(self) -> dict:                                                      # outbound 'state' surface (brief 1) — optional
        return {}

    def dispatch(self, action: str, params: dict) -> Schema__Tui_Api__Result:     # mode-free; the execution center (B3) owns mode
        raise NotImplementedError

    def dry_run(self, action: str, params: dict) -> dict:                         # preview a change-set without committing (override where supported)
        return {}

    def orientation(self) -> Schema__Tui_Api__Orientation:                        # the 'now what?' surface — override to add status + changes
        return Schema__Tui_Api__Orientation(tool=str(self.manifest().tool), status={'healthy': True})

    def action(self, name: str) -> Schema__Tui_Api__Action:                       # convenience lookup into the manifest
        for action in self.manifest().actions:
            if str(action.name) == name:
                return action
        return None

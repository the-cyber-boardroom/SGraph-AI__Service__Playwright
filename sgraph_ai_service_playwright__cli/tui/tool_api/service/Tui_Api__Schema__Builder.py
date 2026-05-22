# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api: Tui_Api__Schema__Builder
# Derives a real JSON Schema from a Type_Safe params class (decision #9 — no
# hand-written JSON). Wraps osbot's Type_Safe__Schema_For__LLMs and corrects the one
# gap: Safe_Str/Safe_Int primitives are str/int subclasses (not `is str`), so the
# emitter renders them as {"type":"object"} — we map them back to their JSON type.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                  import Type_Safe
from osbot_utils.helpers.llms.actions.Type_Safe__Schema_For__LLMs     import Type_Safe__Schema_For__LLMs
from osbot_utils.type_safe.type_safe_core.shared.Type_Safe__Cache     import type_safe_cache


class Tui_Api__Schema__Builder(Type_Safe):

    def input_schema(self, params_cls) -> dict:
        schema = Type_Safe__Schema_For__LLMs().export(params_cls)
        self.fix_primitive_subclasses(params_cls, schema)
        return schema

    def fix_primitive_subclasses(self, params_cls, schema: dict) -> None:         # rewrite Safe_* primitive fields the emitter missed
        props = schema.get('properties', {})
        for name, var_type in type_safe_cache.get_class_annotations(params_cls):
            json_type = self.json_type_for(var_type)
            if json_type is None:
                continue
            prop = {'type': json_type}
            max_length = getattr(var_type, 'max_length', None)
            if json_type == 'string' and isinstance(max_length, int) and max_length > 0:
                prop['maxLength'] = max_length
            existing = props.get(name, {})
            if 'description' in existing:                                         # keep any comment-derived description
                prop['description'] = existing['description']
            props[name] = prop

    def json_type_for(self, var_type):                                            # only for primitive SUBCLASSES the emitter renders as 'object'
        if not isinstance(var_type, type):
            return None
        if var_type in (str, int, float, bool):                                   # plain primitives are already handled by the emitter
            return None
        if issubclass(var_type, bool):  return 'boolean'                          # bool before int (bool is an int subclass)
        if issubclass(var_type, int):   return 'integer'
        if issubclass(var_type, float): return 'number'
        if issubclass(var_type, str):   return 'string'
        return None

# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Step__Result__Base (spec §5.7)
#
# Common fields for every step result. Subclasses (Get_Content / Get_Url /
# Evaluate) exist for typed construction inside the executor, but they redeclare
# fields that are ALSO defined here as optional. This is the BUG-2 fix
# (debrief 2026-05-30): when Schema__Sequence__Response.step_results is typed
# `List[Schema__Step__Result__Base]`, FastAPI / Pydantic / Type_Safe serialise
# each item using the BASE schema and silently drop subclass-only fields. Lifting
# the fields here means the wire format always carries them (None when N/A).
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                         import Any, Dict, List

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe
from osbot_utils.type_safe.primitives.core.Safe_UInt                                                import Safe_UInt
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text                        import Safe_Str__Text
from osbot_utils.type_safe.primitives.domains.http.safe_str.Safe_Str__Http__Content_Type            import Safe_Str__Http__Content_Type

from sg_compute_specs.playwright.core.schemas.artefact.Schema__Artefact__Ref                            import Schema__Artefact__Ref
from sg_compute_specs.playwright.core.schemas.enums.Enum__Content__Format                               import Enum__Content__Format
from sg_compute_specs.playwright.core.schemas.enums.Enum__Evaluate__Return_Type                         import Enum__Evaluate__Return_Type
from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Action                                  import Enum__Step__Action
from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Error__Type                             import Enum__Step__Error__Type
from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Status                                  import Enum__Step__Status
from sg_compute_specs.playwright.core.schemas.primitives.identifiers.Step_Id                            import Step_Id
from sg_compute_specs.playwright.core.schemas.primitives.numeric.Safe_UInt__Milliseconds                import Safe_UInt__Milliseconds
from sg_compute_specs.playwright.core.schemas.primitives.text.Safe_Str__Page__Content                   import Safe_Str__Page__Content
from sg_compute_specs.playwright.core.schemas.primitives.text.Safe_Str__Url__Permissive                 import Safe_Str__Url__Permissive


class Schema__Step__Result__Base(Type_Safe):                                        # Common fields for every step result
    # ── universal fields ──────────────────────────────────────────────────────
    step_id             : Step_Id
    step_index          : Safe_UInt                                                 # Position in sequence (0-based)
    action              : Enum__Step__Action
    status              : Enum__Step__Status
    duration_ms         : Safe_UInt__Milliseconds
    error_message       : Safe_Str__Text          = None                            # Populated on failure (free-text)
    error_type          : Enum__Step__Error__Type = None                            # Structured failure class — lets clients branch on category without parsing the message
    artefacts           : List[Schema__Artefact__Ref]                               # Artefacts produced by this step
    # ── verb-specific fields (lifted from subclasses for serialisation safety) ─
    # Populated only for the verb that produces them; None for every other step.
    # See header — this is the BUG-2 fix.
    content             : Safe_Str__Page__Content      = None                       # get_content : full text/HTML
    content_format      : Enum__Content__Format        = None                       # get_content : html | text
    content_type        : Safe_Str__Http__Content_Type = None                       # get_content : MIME (text/html | text/plain | …)
    url                 : Safe_Str__Url__Permissive    = None                       # get_url     : page.url at step time (Permissive so vault URLs with ':' in fragment round-trip)
    return_value        : Any                          = None                       # evaluate    : JS expression's return value (any JSON-serialisable)
    return_type         : Enum__Evaluate__Return_Type  = None                       # evaluate    : classified type (json|string|number|boolean)
    # ── Φ3 — FR-2 DOM reads + FR-5b a11y. Same lift-to-base pattern for serialisation safety. ─
    text                : Safe_Str__Page__Content      = None                       # get_text       : innerText of page/selector (10 MB cap for SPA-sized payloads)
    html                : Safe_Str__Page__Content      = None                       # get_html       : outerHTML of page/selector
    dom_tree            : Dict                         = None                       # get_dom_tree   : compact JSON {tag,id,class,role,accessible_name,rect,visible,child_count,children}
    accessibility_tree  : Dict                         = None                       # get_a11y_tree  : page.accessibility.snapshot()
    # ── Φ4 — FR-5c console + network capture. Same lift-to-base pattern. ───────
    console_log         : List                         = None                       # get_console_tail     : List[{type,text,timestamp,location?}] — page.on('console') events
    network_failures    : List                         = None                       # get_network_failures : List[{url,method,failure_text,timestamp}] — page.on('requestfailed') events

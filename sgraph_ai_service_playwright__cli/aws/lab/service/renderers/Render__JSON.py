# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/lab — Render__JSON
# Pretty JSON renderer for Schema__Lab__Run__Result.
# ═══════════════════════════════════════════════════════════════════════════════

import json

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.lab.schemas.Schema__Lab__Run__Result import Schema__Lab__Run__Result


class Render__JSON(Type_Safe):

    def render(self, result: Schema__Lab__Run__Result) -> str:
        data = {
            'run_id'      : str(result.run_id),
            'status'      : str(result.status),
            'started_at'  : result.started_at,
            'finished_at' : result.finished_at,
            'duration_ms' : int(result.duration_ms),
            'error'       : result.error,
            'notes'       : result.notes,
            'samples'     : [
                {
                    'label'      : s.label,
                    'elapsed_ms' : int(s.elapsed_ms),
                    'success'    : s.success,
                    'detail'     : s.detail,
                }
                for s in result.samples
            ],
        }
        return json.dumps(data, indent=2)

# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Request__Validator
# ALL cross-field validation rules for stack-creation requests live here.
# Routes call validate_create() before delegating to the plugin service.
# Returns (is_valid: bool, error_message: str | None).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                    import Type_Safe

from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Creation_Mode         import Enum__Stack__Creation_Mode
from sgraph_ai_service_playwright__cli.catalog.schemas.Schema__Stack__Create__Request__Base import Schema__Stack__Create__Request__Base


class Request__Validator(Type_Safe):

    def validate_create(self, request: Schema__Stack__Create__Request__Base) -> tuple[bool, str | None]:
        mode   = request.creation_mode
        ami_id = str(request.ami_id)

        if mode == Enum__Stack__Creation_Mode.FROM_AMI:
            if not ami_id:
                return False, 'ami_id is required when creation_mode is from-ami'
            if not ami_id.startswith('ami-'):
                return False, f'ami_id must start with "ami-"; got {ami_id!r}'
        else:
            if ami_id:
                return False, f'ami_id must be absent when creation_mode is {mode.value!r}; got {ami_id!r}'

        return True, None

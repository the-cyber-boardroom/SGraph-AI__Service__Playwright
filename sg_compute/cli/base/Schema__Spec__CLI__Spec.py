# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__Spec__CLI__Spec
# Per-spec configuration consumed by Spec__CLI__Builder.
# Plain class (not Type_Safe) because it holds callable and class references
# that conflict with Type_Safe's metaclass attribute validation.
# ═══════════════════════════════════════════════════════════════════════════════


class Schema__Spec__CLI__Spec:

    def __init__(self,
                 spec_id                    : str,
                 display_name               : str,
                 default_instance_type      : str,
                 create_request_cls,
                 service_factory,
                 health_path                : str  = '/',
                 health_port                : int  = 80,
                 extra_create_field_setters        = None):
        self.spec_id                   = spec_id
        self.display_name              = display_name
        self.default_instance_type     = default_instance_type
        self.create_request_cls        = create_request_cls
        self.service_factory           = service_factory
        self.health_path               = health_path
        self.health_port               = health_port
        self.extra_create_field_setters = extra_create_field_setters

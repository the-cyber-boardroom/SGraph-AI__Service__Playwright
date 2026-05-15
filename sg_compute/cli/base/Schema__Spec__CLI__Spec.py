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
                 health_scheme              : str  = 'https',
                 extra_create_field_setters        = None,
                 render_info_fn                    = None,
                 render_create_fn                  = None,
                 post_launch_fn                    = None):
        self.spec_id                   = spec_id
        self.display_name              = display_name
        self.default_instance_type     = default_instance_type
        self.create_request_cls        = create_request_cls
        self.service_factory           = service_factory
        self.health_path               = health_path
        self.health_port               = health_port
        self.health_scheme             = health_scheme
        self.extra_create_field_setters = extra_create_field_setters
        self.render_info_fn            = render_info_fn
        self.render_create_fn          = render_create_fn
        # Optional hook called by Spec__CLI__Builder.create_impl after create_stack returns
        # and BEFORE _wait_healthy starts blocking. Signature:
        #   post_launch_fn(svc, region, request, response, kwargs, console) -> Optional[Background_Task]
        # The returned task (anything with a .join(timeout=...) method) is joined after
        # _wait_healthy completes. Used by vault-app for --with-aws-dns parallelism.
        self.post_launch_fn            = post_launch_fn

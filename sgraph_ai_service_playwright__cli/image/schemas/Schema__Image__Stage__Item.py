# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Image__Stage__Item
# One thing to copy into the Docker build context's tempdir before
# `docker build` runs. Two flavours: a single file (is_tree=False) or a
# whole directory tree (is_tree=True). For trees, extra_ignore_names is
# applied on top of Image__Build__Service's default ignore set.
#
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.image.collections.List__Str                  import List__Str


class Schema__Image__Stage__Item(Type_Safe):
    source_path         : str                                                       # Absolute filesystem source — file or directory
    target_name         : str                                                       # Name (no path traversal) within the build context
    is_tree             : bool       = False                                        # True ⇒ shutil.copytree(); False ⇒ shutil.copy()
    extra_ignore_names  : List__Str                                                 # Additional names filtered out during copytree (defaults applied by service)

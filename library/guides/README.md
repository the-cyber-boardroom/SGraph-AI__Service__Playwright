# Guides

Framework guides — read these before writing code against the corresponding library. Each guide's version prefix is the version of the upstream library at the time the guide was written.

| Guide | Version | When to read |
|-------|--------:|-------------|
| [`v3.63.4__type_safe.md`](v3.63.4__type_safe.md)                     | 3.63.4 | **Before writing any class.** Core rules, kwargs_to_self, forbidden patterns |
| [`v3.63.4__python_formatting.md`](v3.63.4__python_formatting.md)     | 3.63.4 | When formatting any file — alignment, `═══` headers, inline comments, no docstrings |
| [`v3.28.0__safe_primitives.md`](v3.28.0__safe_primitives.md)         | 3.28.0 | When declaring a new `Safe_*` primitive or picking one from the standard catalogue |
| [`v3.63.3__collections_subclassing.md`](v3.63.3__collections_subclassing.md) | 3.63.3 | When creating `Dict__*`, `List__*`, or `Set__*` subclasses |
| [`v3.1.1__testing_guidance.md`](v3.1.1__testing_guidance.md)         | 3.1.1  | When writing tests — context managers, `.obj()`, `__SKIP__`, no-mocks discipline |
| [`v0.24.2__fast_api_routes.md`](v0.24.2__fast_api_routes.md)         | 0.24.2 | When adding or modifying a FastAPI route class |
| [`v0.34.0__unified_service_client.md`](v0.34.0__unified_service_client.md) | 0.34.0 | When wiring the stateless client or service registry for tests |
| [`v0.2.15__markdown_doc_style.md`](v0.2.15__markdown_doc_style.md)   | 0.2.15 | When writing any Markdown brief / plan / debrief / review — YAML frontmatter, not `═══` heading blocks |

---

## Non-Negotiable Rules (summarised)

- **Type_Safe everywhere** — no Pydantic, no `dataclass`, no plain Python classes for data
- **Zero raw primitives** — no `str`, `int`, `float`, `list`, `dict` as Type_Safe attributes
- **No Literals** — fixed-value sets use `Enum__*` classes
- **No mocks, no patches** — real implementations only; in-memory stack
- **No docstrings** — inline `# comments` only, aligned to the right of code
- **`═══` 80-char section headers** — every file, every section

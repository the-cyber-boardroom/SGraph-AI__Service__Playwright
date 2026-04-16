# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Enumeration Types
#
# All enums subclass (str, Enum) for transparent JSON serialisation.
# Every enum exposes __str__ returning the underlying value.
# No Literal types anywhere in this module — all fixed-value sets are Enum__*.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


# ═══════════════════════════════════════════════════════════════════════════════
# Browser and Deployment
# ═══════════════════════════════════════════════════════════════════════════════

class Enum__Browser__Name(str, Enum):                                               # Which browser engine
    CHROMIUM = "chromium"
    FIREFOX  = "firefox"
    WEBKIT   = "webkit"

    def __str__(self): return self.value


class Enum__Browser__Provider(str, Enum):                                           # How the browser is obtained
    LOCAL_SUBPROCESS = "local_subprocess"                                           # Spawn chromium process in this container
    CDP_CONNECT      = "cdp_connect"                                                # Connect via CDP to a pre-existing browser
    BROWSERLESS      = "browserless"                                                # Cloud provider (browserless.io)

    def __str__(self): return self.value


class Enum__Deployment__Target(str, Enum):                                          # Where the service is running
    LAPTOP     = "laptop"                                                           # Direct uvicorn / docker run
    CI         = "ci"                                                               # GitHub Actions or similar
    CLAUDE_WEB = "claude_web"                                                       # Running inside a Claude session
    CONTAINER  = "container"                                                        # Generic docker/K8s/Fargate
    LAMBDA     = "lambda"                                                           # AWS Lambda container

    def __str__(self): return self.value


# ═══════════════════════════════════════════════════════════════════════════════
# Session / Sequence / Step lifecycle
# ═══════════════════════════════════════════════════════════════════════════════

class Enum__Session__Lifetime(str, Enum):                                           # Caller's lifetime expectation
    EPHEMERAL              = "ephemeral"                                            # One request; closed immediately
    PERSISTENT_SINGLE      = "persistent_single"                                    # Persists across HTTP requests; single container
    PERSISTENT_DISTRIBUTED = "persistent_distributed"                               # Not supported; reserved for future

    def __str__(self): return self.value


class Enum__Session__Status(str, Enum):                                             # Current state of a session
    CREATED = "created"                                                             # Record exists, browser not yet launched
    ACTIVE  = "active"                                                              # Browser running, ready for actions
    IDLE    = "idle"                                                                # Browser running, no recent activity
    CLOSING = "closing"                                                             # Teardown in progress
    CLOSED  = "closed"                                                              # Browser gone, session ended cleanly
    ERROR   = "error"                                                               # Session in an error state

    def __str__(self): return self.value


class Enum__Sequence__Status(str, Enum):                                            # Overall sequence outcome
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"                                                         # All steps passed
    FAILED    = "failed"                                                            # At least one step failed, halt_on_error=True
    PARTIAL   = "partial"                                                           # At least one step failed, halt_on_error=False

    def __str__(self): return self.value


class Enum__Step__Status(str, Enum):                                                # Per-step outcome
    PENDING = "pending"
    RUNNING = "running"
    PASSED  = "passed"
    FAILED  = "failed"
    SKIPPED = "skipped"                                                             # Skipped due to prior failure with halt_on_error

    def __str__(self): return self.value


# ═══════════════════════════════════════════════════════════════════════════════
# Step language
# ═══════════════════════════════════════════════════════════════════════════════

class Enum__Step__Action(str, Enum):                                                # The declarative step vocabulary
    NAVIGATE       = "navigate"                                                     # Go to URL
    CLICK          = "click"                                                        # Click element
    FILL           = "fill"                                                         # Fill form field
    PRESS          = "press"                                                        # Press keyboard key
    SELECT         = "select"                                                       # Select option from dropdown
    HOVER          = "hover"                                                        # Mouse hover
    SCROLL         = "scroll"                                                       # Scroll viewport or element
    WAIT_FOR       = "wait_for"                                                     # Wait for selector / url / state
    SCREENSHOT     = "screenshot"                                                   # Capture screenshot
    VIDEO_START    = "video_start"                                                  # Begin session recording
    VIDEO_STOP     = "video_stop"                                                   # End session recording
    EVALUATE       = "evaluate"                                                     # Run JS expression (allowlist-gated)
    DISPATCH_EVENT = "dispatch_event"                                               # Synthetic DOM event
    SET_VIEWPORT   = "set_viewport"                                                 # Change viewport dimensions
    GET_CONTENT    = "get_content"                                                  # Return page HTML / text
    GET_URL        = "get_url"                                                      # Return current URL

    def __str__(self): return self.value


class Enum__Wait__State(str, Enum):                                                 # Page-load state for navigate/wait_for
    LOAD               = "load"                                                     # load event fired
    DOM_CONTENT_LOADED = "domcontentloaded"                                         # DOMContentLoaded event
    NETWORK_IDLE       = "networkidle"                                              # No network activity for 500ms

    def __str__(self): return self.value


class Enum__Mouse__Button(str, Enum):                                               # Mouse button for click actions
    LEFT   = "left"
    RIGHT  = "right"
    MIDDLE = "middle"

    def __str__(self): return self.value


class Enum__Evaluate__Return_Type(str, Enum):                                       # Expected return from page.evaluate()
    JSON    = "json"
    STRING  = "string"
    NUMBER  = "number"
    BOOLEAN = "boolean"

    def __str__(self): return self.value


class Enum__Content__Format(str, Enum):                                             # get_content return format
    HTML = "html"                                                                   # innerHTML
    TEXT = "text"                                                                   # innerText

    def __str__(self): return self.value


# ═══════════════════════════════════════════════════════════════════════════════
# Artefacts
# ═══════════════════════════════════════════════════════════════════════════════

class Enum__Artefact__Sink(str, Enum):                                              # Where a captured artefact goes
    VAULT      = "vault"                                                            # SG/Send vault path
    INLINE     = "inline"                                                           # Base64 in HTTP response
    S3         = "s3"                                                               # Direct S3 write
    LOCAL_FILE = "local_file"                                                       # Filesystem path (dev/container only)

    def __str__(self): return self.value


class Enum__Artefact__Type(str, Enum):                                              # What kind of artefact
    SCREENSHOT   = "screenshot"
    VIDEO        = "video"
    PDF          = "pdf"
    HAR          = "har"                                                            # HTTP Archive
    TRACE        = "trace"                                                          # Playwright trace ZIP
    CONSOLE_LOG  = "console_log"
    NETWORK_LOG  = "network_log"
    PAGE_CONTENT = "page_content"                                                   # HTML snapshot

    def __str__(self): return self.value


class Enum__Video__Codec(str, Enum):                                                # Video encoding
    WEBM = "webm"                                                                   # Playwright default; universal browser support
    MP4  = "mp4"                                                                    # Broader compatibility; requires transcode

    def __str__(self): return self.value


# ═══════════════════════════════════════════════════════════════════════════════
# Keyboard
# ═══════════════════════════════════════════════════════════════════════════════

class Enum__Keyboard__Key(str, Enum):                                               # Common keyboard keys (extensible)
    ENTER       = "Enter"
    TAB         = "Tab"
    ESCAPE      = "Escape"
    BACKSPACE   = "Backspace"
    DELETE      = "Delete"
    ARROW_UP    = "ArrowUp"
    ARROW_DOWN  = "ArrowDown"
    ARROW_LEFT  = "ArrowLeft"
    ARROW_RIGHT = "ArrowRight"
    CONTROL_A   = "Control+a"
    CONTROL_C   = "Control+c"
    CONTROL_V   = "Control+v"

    def __str__(self): return self.value

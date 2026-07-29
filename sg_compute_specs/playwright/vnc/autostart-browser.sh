#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# sg-playwright-vnc — autostart-browser oneshot (supervisord program)
# When SG_PLAYWRIGHT__AUTOSTART_BROWSER=chromium|firefox is set, wait for the
# FastAPI service on :8000 and POST /desktop/browser so the noVNC desktop greets
# the user with a browser already open (content_proxy fleet sets this + a start
# URL). No env → exit 0 silently (plain vnc-mode image, user opens via API).
# Auth: the service's own key is in this container's env — same-origin call.
# ═══════════════════════════════════════════════════════════════════════════════
set -u

ENGINE="${SG_PLAYWRIGHT__AUTOSTART_BROWSER:-}"
[ -z "$ENGINE" ] && exit 0

# start_url is OPTIONAL and, when sent, must be a real http(s):// URL — the API's
# Safe_Str__Url__Permissive schema rejects about:blank / chrome:// et al. Default
# empty → omit the field so a plain blank browser opens (sending about:blank made
# the boot POST 500 → no browser → black noVNC screen).
START_URL="${SG_PLAYWRIGHT__AUTOSTART_START_URL:-}"
WINDOW_MODE="${SG_PLAYWRIGHT__AUTOSTART_WINDOW_MODE:-maximised}"                     # normal | maximised | kiosk
KEY_NAME="${FAST_API__AUTH__API_KEY__NAME:-X-API-Key}"
KEY_VALUE="${FAST_API__AUTH__API_KEY__VALUE:-}"

for i in $(seq 1 30); do                                                             # -H auth: health may be key-gated depending on deploy config
    curl -sf -o /dev/null -H "${KEY_NAME}: ${KEY_VALUE}" "http://localhost:8000/health/status" && break
    sleep 2
done

if [ -n "$START_URL" ]; then                                                         # include start_url only when a real URL is set
    BODY="{\"engine\": \"${ENGINE}\", \"window_mode\": \"${WINDOW_MODE}\", \"start_url\": \"${START_URL}\"}"
    echo "[autostart-browser] opening headed ${ENGINE} (${WINDOW_MODE}) at ${START_URL}"
else
    BODY="{\"engine\": \"${ENGINE}\", \"window_mode\": \"${WINDOW_MODE}\"}"
    echo "[autostart-browser] opening headed ${ENGINE} (${WINDOW_MODE}, blank page)"
fi
curl -sf -X POST "http://localhost:8000/desktop/browser" \
     -H "content-type: application/json" \
     -H "${KEY_NAME}: ${KEY_VALUE}" \
     -d "$BODY" \
  || echo "[autostart-browser] WARNING: POST /desktop/browser failed — open it manually via the API"
exit 0

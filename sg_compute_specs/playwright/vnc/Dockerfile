# ═══════════════════════════════════════════════════════════════════════════════
# sg-playwright-vnc — the sg-playwright service image + a visible desktop
#
# Adds Xvfb (virtual X display :99), openbox (window manager), x11vnc (VNC server,
# container-internal :5900) and noVNC/websockify (browser VNC client on :6080) on
# top of the sg-playwright image, all supervised by supervisord alongside the
# existing FastAPI service on :8000. Browsers launched headed (headless=false)
# render on :99 and are watchable/drivable from any browser at :6080 — the same
# browser is reachable through the API AND the human viewer.
#
# BASE_IMAGE: CI pins this to the exact by-digest sg-playwright image built in the
# same pipeline run (both images always carry the same code + version). Local
# builds default to the floating :latest.
#
# Build (from repo root):
#   docker build -f sg_compute_specs/playwright/vnc/Dockerfile \
#                -t diniscruz/sg-playwright-vnc:<version> .
#   docker build --build-arg BASE_IMAGE=diniscruz/sg-playwright@sha256:<digest> …
#
# Run:
#   docker run -p 8000:8000 -p 6080:6080 \
#     -e FAST_API__AUTH__API_KEY__VALUE=<key> \
#     diniscruz/sg-playwright-vnc:<version>
#   → API on :8000 (unchanged), noVNC desktop on http://localhost:6080/vnc.html
# ═══════════════════════════════════════════════════════════════════════════════

ARG BASE_IMAGE=diniscruz/sg-playwright:latest
FROM ${BASE_IMAGE}

# X stack + supervisor. novnc pulls websockify; openbox gives windows borders /
# move / close (a bare Xvfb renders browsers into an unmanageable void).
# --no-install-recommends keeps the layer lean (novnc recommends a full desktop).
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        xvfb \
        openbox \
        x11vnc \
        novnc \
        websockify \
        supervisor \
        libnss3-tools \
        ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# DISPLAY_MODE=vnc: the service (P2) reads it to default headed launches; the
# supervisord conf is the process tree either way. DISPLAY matches the Xvfb
# program below — Browser__Launcher's browsers render there.
ENV DISPLAY=:99 \
    SG_PLAYWRIGHT__DISPLAY_MODE=vnc

COPY sg_compute_specs/playwright/vnc/supervisord.conf   /etc/supervisor/conf.d/sg-playwright-vnc.conf
COPY sg_compute_specs/playwright/vnc/autostart-browser.sh /usr/local/bin/autostart-browser.sh
COPY sg_compute_specs/playwright/vnc/install-ca-trust.sh  /usr/local/bin/install-ca-trust.sh
RUN chmod +x /usr/local/bin/autostart-browser.sh /usr/local/bin/install-ca-trust.sh

EXPOSE 8000 6080

# -n: stay in the foreground as PID 1 (container lifetime = supervisor lifetime)
CMD ["supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]

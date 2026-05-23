# ═══════════════════════════════════════════════════════════════════════════════
# SG/Sentinel — httpget echo server (origin / measurement tool)
# Dependency-free stdlib server; the same Echo__Payload runs local / docker / EC2 /
# Lambda. Build context is the repo root so the package import path resolves:
#   docker build -f sgraph_ai_service_playwright__cli/sentinel/traffic/echo/docker/Dockerfile -t sg-sentinel-httpget .
#   docker run -p 8080:8080 sg-sentinel-httpget
# ═══════════════════════════════════════════════════════════════════════════════
FROM python:3.12-slim

WORKDIR /app
COPY sgraph_ai_service_playwright__cli/sentinel/traffic/echo/Echo__Payload.py /app/Echo__Payload.py
COPY sgraph_ai_service_playwright__cli/sentinel/traffic/echo/Echo__Server.py  /app/Echo__Server.py
ENV PYTHONPATH=/app PORT=8080
EXPOSE 8080

# run the pure server module directly (sibling-import fallback; no project deps)
CMD ["python", "-c", "import os; from Echo__Server import serve; serve('0.0.0.0', int(os.environ.get('PORT','8080')))"]

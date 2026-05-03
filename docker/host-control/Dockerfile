FROM python:3.12-alpine

WORKDIR /app

# Runtime deps: osbot-fast-api-serverless pulls osbot-utils + fastapi transitively
COPY docker/host-control/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Docker CLI client — talks to the host daemon via the mounted socket
# (daemon not needed; socket is bind-mounted at runtime via -v /var/run/docker.sock)
RUN apk add --no-cache docker-cli

# Copy the host package source (not yet on PyPI — installed from repo)
COPY sgraph_ai_service_playwright__host/ ./sgraph_ai_service_playwright__host/

ENV PYTHONPATH=/app

# API key is injected at runtime via FAST_API__AUTH__API_KEY__VALUE env var
# Port 8000 is mapped to host port 19009 by the `docker run` in user-data
EXPOSE 8000

CMD ["uvicorn", "sgraph_ai_service_playwright__host.fast_api.lambda_handler:_app", "--host", "0.0.0.0", "--port", "8000"]

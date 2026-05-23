# ═══════════════════════════════════════════════════════════════════════════════
# SG/Sentinel — CloudFront-environment simulation (Target C)
# Runs the L1 JS engine under a Node runtime as a stand-in for the CloudFront
# Functions environment. CloudFront Functions is not Node (custom ES5.1-ish engine),
# so there is no exact match — the discipline lives in sentinel_l1.js staying
# CF-compatible (no require/Buffer/process at top level). Node version: 22-slim.
#
# Build context is produced by Sentinel__Docker__Runtime: it materialises
# sentinel_l1.js (BANNED_IPS inlined, the same substitution the CF deployer does)
# into the context before `docker build`.
# ═══════════════════════════════════════════════════════════════════════════════
FROM node:22-slim

WORKDIR /app
COPY sentinel_l1.js /app/sentinel_l1.js
COPY server.node.js /app/server.node.js

ENV PORT=8080
EXPOSE 8080

CMD ["node", "/app/server.node.js"]

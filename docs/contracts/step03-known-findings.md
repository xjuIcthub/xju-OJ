# Step 03 Known Findings

- The non-production Ubuntu/Docker/Compose/BuildKit preflight passed on Ubuntu 22.04.5 amd64.
- The target has 22G free on a 40G root filesystem, but no production data-size measurement exists yet; restore/backup capacity remains Step 19 evidence.
- The default Buildx builder is persistent and healthy for amd64. No arm64 worker/cache is configured on this amd64 target; arm64 is not claimed as production-ready.
- UFW is inactive and IPv6 Docker forwarding defaults to ACCEPT. Current host listeners are 22, 80, and 443 plus loopback services; ports 8000, 8080, 5432, and 6379 are not listening. The IPv6 policy needs a later network review; it was not changed in this preflight.
- Runtime roots are intentionally empty and root-owned. The external production Secret gate is still pending; no secret was generated or requested. This is the explicit stop condition before any production release or Step 04 claim that depends on a completed Step 03.

# xju-OJ agent and developer guidance

## Frontend-first development

For rapid frontend iteration, use the repository-level full-stack development mode:

```bash
./deploy.sh --dev frontend
```

This command starts PostgreSQL, Redis, `backend-api`, `backend-worker`, and
`judge-server` with Docker, but deliberately does not start the Docker frontend.
It then runs `frontend/pnpm dev` on the host. Vite listens on
`http://127.0.0.1:5173` and proxies `/api` and `/public` to the backend at
`http://127.0.0.1:8000`.

- Keep `frontend/` changes frontend-only whenever possible; Vite HMR should be
  used instead of rebuilding the frontend image.
- The development bridge is defined in `compose.dev.yaml` and is loaded only by
  `./deploy.sh --dev frontend`.
- The backend development bridge binds only to loopback. Do not change it to
  `0.0.0.0` or a public address.
- `OJ_DEV_MODE=1` permits only the local Vite HTTP origin for CSRF. Production
  deployment retains strict HTTPS trusted origins.
- Ctrl-C stops the host Vite process only; it does not delete or stop Docker
  data services. Stop them explicitly with a targeted `docker compose stop` if
  needed.
- Production deployment remains `./deploy.sh`; do not use the development
  override for production.

## Validation

Before committing frontend or deployment changes, run the checks relevant to
the change:

```bash
sh -n deploy.sh
pnpm --dir frontend run lint:modern
pnpm --dir frontend run test:routes
pnpm --dir frontend run build
```

Do not commit `.env`, secret files, OIDC client secrets, judge tokens, cookies,
or other runtime/private data.

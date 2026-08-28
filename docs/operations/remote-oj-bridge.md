# Remote OJ bridge

XJU-OJ can reuse practice problems from Luogu, Nowcoder, and Codeforces without
storing third-party passwords or cookies on the server. A ScriptCat userscript
runs the provider interaction inside each user's own browser session.

## User setup

1. Open `/remote-bridge` on the OJ.
2. Install ScriptCat if the browser does not already have it. The Edge add-on is
   preferred for lab computers with domestic network access.
3. Click **Install userscript** once. ScriptCat uses the script's `updateURL` for
   later updates.
4. Log in to each external OJ that the user wants to submit to.

The script is served from
`/static/userscripts/xju-oj-remote-bridge.user.js`. Nginx disables caching for
this file so updates are immediately visible to ScriptCat.

## Submission flow

Remote problems use the same editor and submit button as local problems. The
visible lifecycle is:

```text
Submitting -> Judging -> provider verdict
```

The OJ creates the submission row first and sends a validated, allowlisted task to
the userscript. The userscript opens the provider problem page and submits with
the provider account that is already logged in to that browser.

If the provider requests Turnstile, NetEase/YIDUN, an image CAPTCHA, login, or a
risk-control check, the provider's native page remains open for the user to
complete it. The OJ never attempts to solve or proxy the challenge. Once the
provider accepts the submission, the provider tab closes, focus returns to the
OJ, and the userscript continues polling the provider result in the OJ tab.

Supported browser-side adapters:

- Codeforces: native submission form and official submission-status API.
- Luogu: `/fe/api/problem/submit/{pid}`, native verification fallback, and
  record polling.
- Nowcoder ACM/problem pages: session submit API, native risk-control fallback,
  and result polling.

## Admin problem import

The admin problem list exposes **Import Remote Problem** for both the public
library and a contest.

- Luogu accepts IDs such as `P1001` or a problem URL.
- Nowcoder accepts IDs such as `NC322024`, numeric ACM problem IDs, legacy UUIDs,
  and `ac.nowcoder.com/acm/problem/...` URLs.
- Codeforces accepts IDs such as `4A` or a problem URL. If the server is stopped
  by Cloudflare, the userscript opens Codeforces, waits for the browser challenge,
  reads only the rendered problem statement, and sends that statement back to
  the admin import API.

Imports are deduplicated by `(provider, remote_problem_id)`. Imported statements,
limits, samples, source metadata, provider language IDs, and provider URLs are
stored locally; test data is not copied because judging remains remote.

When editing a contest, an admin can either:

- select any public problem already in XJU-OJ, including self-authored and
  previously imported remote problems; or
- import a new remote problem directly as `A`, `B`, and so on.

A newly imported contest problem reserves a public display ID. A delayed backend
worker publishes a copy into the public library after the contest ends. Public
and admin problem-list requests also perform the same idempotent check, so an
expired task is repaired automatically. If the reserved ID was occupied later,
publication stays queued instead of silently choosing another ID.

## Security and trust boundary

- Provider credentials and cookies stay in the user's browser.
- Remote URLs and event transitions are allowlisted and validated by the backend.
- Provider pages never receive the user's XJU-OJ session credentials.
- The userscript has a 1 MiB source limit; Codeforces statement relay has a 2 MiB
  backend limit.
- Browser-reported remote verdicts are suitable for ordinary practice. They are
  inherently less trustworthy than local sandbox results because a user who can
  modify browser scripts can forge browser events. Do not use remote-provider
  verdicts as the sole authority for a formal ranked contest.

## Validation and release

Before release, run:

```bash
sh -n deploy.sh
node --check frontend/static/userscripts/xju-oj-remote-bridge.user.js
pnpm --dir frontend run lint:modern
pnpm --dir frontend run test:routes
pnpm --dir frontend run build
```

Apply Django migrations during the normal deployment. Production deployment is
still `./deploy.sh`; do not use the frontend development override in production.

Real-account acceptance should cover one accepted and one rejected submission
per provider, plus one forced verification/login flow. External DOM and private
API details can change independently of this repository, so this browser check
is required even when automated tests pass.

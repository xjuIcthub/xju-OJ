# Step 01 Baseline Known Failures

These are observed baseline facts, not silently fixed in the characterization Step.

1. `python manage.py check` and the isolated contract tests report 15 Django `fields.W904` warnings for use of `django.contrib.postgres.fields.JSONField`. This is the expected compatibility debt for Step 14.
2. The unlabelled baseline command `python manage.py test` completes with `Ran 0 tests`; the new explicitly labelled baseline suite `python manage.py test tests.contracts` runs 7 tests and passes. Existing test discovery/collection must be revisited separately; no tests were deleted or reclassified to hide this fact.
3. In an isolated Nginx gateway using the committed `frontend/dist`, `/`, `/admin/`, deep links, `/public/` and `/api/website/` return the expected HTTP boundary, but Playwright observes repeated `Unexpected token '<'` page errors. The committed dist HTML references `__STATIC_CDN_HOST__` asset URLs; the current history fallback returns HTML for a missing JS asset URL (`200 text/html` with an HTML body), so the browser cannot boot from this artifact. This remains a baseline blocker for browser-rendered SPA assertions.
4. Full JudgeServer compiler/Seccomp runtime cases were not run in Step 01 because no existing baseline JudgeServer image/service was available in the local environment. The transport/protocol contract suite runs 4 tests and passes; runtime corpus execution remains a required follow-up before a release claim.

The API, Session/CSRF, Redis DB1/DB4 identity, migration/schema snapshot, gateway HTTP boundary, and Judge transport contracts are repeatable in isolated temporary PostgreSQL 10/Redis 4 services. No production data, secret, token, dump, RDB/AOF, or user upload was used.

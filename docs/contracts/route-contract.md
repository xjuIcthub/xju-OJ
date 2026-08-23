# Route Contract Golden

The Step 01 baseline freezes the two history-mode SPA entry points and the same-origin gateway boundary.

## Positive cases

| Request | Expected behavior |
|---|---|
| `GET /` | Serve the user SPA entry point or its history fallback. |
| `GET /admin/` | Serve the admin SPA entry point. |
| `GET /api/website/` | Proxy to backend and preserve the JSON `error`/`data` envelope. |
| `GET /public/<existing-file>` | Return the static file from the public data root. |
| `GET /problem/<id>` | User SPA history fallback, not a backend route. |
| `GET /admin/problem/create` | Admin SPA history fallback. |

## Negative/redirect cases

| Request | Expected behavior |
|---|---|
| `GET /admin` | Redirect to `/admin/`; do not serve a second admin base. |
| `GET /public/<missing-file>` | Return a missing-file response; never fall through to either SPA. |
| `GET /api/website/` with a non-JSON API error | Keep the API response boundary; do not turn it into an SPA document. |
| Direct backend/JudgeServer host-port access | Not part of the production route contract; only frontend publishes a host port. |

The browser regression runner must exercise at least one deep-link refresh for each SPA and compare the URL, status, content type, and response body boundary. No credential or production URL belongs in this corpus.

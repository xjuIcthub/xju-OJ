# Judge Protocol Golden

The baseline JudgeServer contract is intentionally independent of the framework and image migration.

## Endpoints

| Endpoint | Method | Positive result | Negative result |
|---|---|---|---|
| `/ping` | POST | `{"err": null, "data": {"action": "pong", ...}}` | missing/wrong token returns `err = "TokenVerificationFailed"` |
| `/judge` | POST | `err = null`; preserve `cpu_time`, `memory`, `real_time`, `result`, `signal`, `exit_code`, `error`, `output_md5`, `output`, and `test_case` | compile/runtime/resource failures remain in `err`/`data`, not an HTTP/SPA response |
| `/compile_spj` | POST | `err = null`, `data = "success"` | invalid source/config returns the existing error class in `err` |
| backend heartbeat | POST | backend response uses `{"error": null, "data": ...}` | invalid token returns the existing backend error envelope |

## Header and input rules

- The client sends `X-Judge-Server-Token` as the SHA-256 hex digest of the supplied token.
- Requests use `Content-Type: application/json`.
- `/judge` accepts exactly one of `test_case_id` or an inline `test_case` list.
- `/test_case` is read-only from the JudgeServer perspective.
- The test corpus covers AC, CE, WA, CPU TLE, real-time TLE, MLE, RE, system error, invalid token, malformed request, SPJ, and heartbeat recovery without storing a real token.

The executable unit contract in `server/judge-server/tests/test_protocol_contract.py` mocks transport and validates header hashing, endpoint paths, envelope shape, and the mutually exclusive test-case input rule. Runtime compiler/Seccomp cases remain in the existing `server/judger/tests` corpus.

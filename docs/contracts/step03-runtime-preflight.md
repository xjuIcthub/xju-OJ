# Step 03 Runtime Preflight

> Captured 2026-08-24 on `huawei1`. Only empty directory roots were created. No database, Redis, queue, upload, log, or secret content was read or modified.

## Paths created

`RUNTIME_ROOT=/srv/xju-oj/runtime` and `BACKUP_ROOT=/var/backups/xju-oj` were used with the plan's separate-generation layout:

```text
/srv/xju-oj/
  runtime/backend/
  runtime/public/
  runtime/test_case/
  runtime/judger/
  runtime/log/
  volumes/postgres/10/
  volumes/postgres/18/
  volumes/redis/4/
  volumes/redis/6.2/
  volumes/redis/7.4/
  volumes/redis/8.2/
  deployments/
  secrets/
/var/backups/xju-oj/
```

The user executed the non-destructive `install -d` command. Verification found no regular files: `/srv/xju-oj` used 72K for directories and `/var/backups/xju-oj` used 4.0K.

## Modes and ownership

- `/srv/xju-oj` and all runtime/volume/deployment directories: `0750 root:root`.
- `/srv/xju-oj/secrets` and `/var/backups/xju-oj`: `0700 root:root`.
- No Secret file exists yet. This is intentional: Step 03 must not generate, print, or place production secrets. The external secret manager/file provisioning gate remains pending and must fail closed when files are absent.
- The root-owned `0750` layout is compatible with the planned root-starting JudgeServer entrypoint; later image-specific UID/GID ownership of database volumes and Judge scratch subdirectories is revalidated after pinned images exist. The SSH user cannot traverse these roots directly, which is expected for this root-owned preflight and must not be “fixed” by broadening permissions.

## Mount permission tests

Using the current Judge image only as a shell test harness, with temporary probe files removed in the same command:

- root container process can write and remove a probe under `/srv/xju-oj/runtime/judger`;
- root container process can write and remove a probe under `/srv/xju-oj/runtime/log`;
- `runtime/public` mounted `:ro` is readable and rejects a write;
- `runtime/test_case` mounted `:ro` is readable and rejects a write.

No production service was started and no host volume was pruned or replaced.

## Secret gate

Expected production files are PostgreSQL password, Django `SECRET_KEY`, Judge token, initial administrator password, and optional TLS material. The directory is currently empty. This satisfies the safety requirement not to create production secrets, but it does **not** satisfy the Phase 5 production release gate. Phase 1–4 may use isolated, disposable, Git-ignored test Secret files outside the production secret root; a test helper may create them, while `deploy.sh` only validates/consumes them. Production deployment must check absolute paths, mode `0600`, and non-empty content without printing values; missing files must abort before production migrations, workers, or public service startup.

## Rollback

Only the empty directories created by this Step may be removed during rollback. Do not remove old data directories, run `docker compose down -v`, prune volumes, or delete any externally provisioned Secret file.

# Data Identity Golden

These identities are characterization facts, not a migration permission.

## Django identity

- App labels remain `account`, `announcement`, `conf`, `problem`, `contest`, `utils`, `submission`, `options`, and `judge`.
- The isolated migrated baseline contains `user`, `user_profile`, `announcement`, `judge_server`, `problem`, `problem_tag`, `contest`, `acm_contest_rank`, `oi_contest_rank`, `contest_announcement`, `options_sysoptions`, `submission`, `django_dramatiq_task`, and Django's auth/contenttypes/session tables.
- `DEFAULT_AUTO_FIELD`, applied migration names, migration dependencies, and historical JSONField migration state are frozen.

## Redis identity

- DB1: Django session/cache and `waiting_queue`.
- DB4: Dramatiq broker/result data.
- Cache and broker URLs must retain their DB suffixes and existing key/TTL/serialization behavior.

## Schema/queue snapshot requirements

The repeatable baseline command records `showmigrations --plan`, `makemigrations --check --dry-run`, model table names, sequence names, Redis DB1/DB4 URL suffixes, and empty isolated queue/result key counts. It does not include production rows, dumps, RDB/AOF files, credentials, or user uploads. The concrete isolated snapshot is `schema-redis-golden.json` and the migration plan is `migration-plan.txt`.

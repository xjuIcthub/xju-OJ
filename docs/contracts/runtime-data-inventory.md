# 运行时数据与备份资产清单

- 采集时间：2026-08-20T12:17:28Z
- 外部快照目录：`/home/winbeau/.cache/xju-oj/baseline-20260820T121728Z`
- 安全约束：本文只记录类别、路径、数量、大小和状态；不记录数据库连接参数、密码、Token、Cookie、密钥、证书或日志内容。

## 快照文件

| 文件 | 状态 | 内容边界 |
|---|---|---|
| `source-tree.tgz` | 存在且可读取 | 排除 `.git`、`node_modules`、`__pycache__`、`data/config/secret.key`、`data/ssl/*.key`、`data/ssl/*.crt`；外部副本中的已知硬编码 DSN 已替换为 `<redacted>` |
| `backend-data.tgz` | 存在且可读取 | 采集时备份 `OnlineJudge/data/{config,public,test_case,ssl,log}`；当时仅有占位文件，没有检测到实际题库/上传/日志数据 |
| `all-files.txt` / `all-files.sha256` | 存在 | 记录采集时工作树文件清单和 SHA-256；不把该清单当作运行时数据备份 |
| `source-snapshot-safety.txt` | 存在 | 记录外部源码快照的二次脱敏和文件名核验；不包含敏感值 |

尝试使用计划示例的 `/secure-backup/xju-oj/...` 时因当前用户无权限创建 `/secure-backup` 失败，未继续提权；改用仓库外、权限为 0700 的用户缓存目录保存快照。该降级事实写入执行日志。

## 仓库内运行时目录

采集时的目录状态（不含后来为开发检查生成的临时 `secret.key`）：

| 目录 | 文件数 | 总大小 | 采集状态 |
|---|---:|---:|---|
| `OnlineJudge/data/config` | 1 | 0 bytes | 只有 `.gitkeep`，配置密钥未提供 |
| `OnlineJudge/data/public` | 3 | 83,865 bytes | 默认头像、favicon 和上传占位目录；不是数据库资产 |
| `OnlineJudge/data/test_case` | 1 | 0 bytes | 只有 `.gitkeep`，未发现题目测试数据 |
| `OnlineJudge/data/ssl` | 1 | 0 bytes | 只有 `.gitkeep`，未发现证书或私钥 |
| `OnlineJudge/data/log` | 1 | 0 bytes | 只有 `.gitkeep`，未发现日志 |
| 根 `data/postgres` | 不存在 | — | 当前仓库没有 PostgreSQL 数据卷 |
| 根 `data/redis` | 不存在 | — | 当前仓库没有 Redis 数据卷 |
| 根 `data/judge_server` | 不存在 | — | 当前仓库没有 JudgeServer 日志/运行卷 |

为满足开发环境基线命令，随后在被忽略的 `OnlineJudge/data/config/secret.key` 生成了 32 字节随机临时值，权限为 0600；值未显示、未写入本文、未进入 Git，也未作为生产密钥使用。该临时文件不改变生产数据备份结论。

## PostgreSQL / Redis 状态

| 资产 | 检查 | 结果 | 结论 |
|---|---|---|---|
| PostgreSQL | `pg_isready -h 127.0.0.1 -p 5435` | no response | 未连接到开发数据库；未执行 `pg_dump`；生产数据库备份状态为“未验证” |
| Redis DB 1 | `redis-cli -h 127.0.0.1 -p 6380 -n 1 llen waiting_queue` | connection refused | waiting queue 长度为“未验证” |
| Redis DB 4 | `redis-cli -h 127.0.0.1 -p 6380 -n 4 dbsize` | connection refused | Dramatiq broker/result 大小为“未验证” |

本阶段没有执行 `migrate`、数据修复、清空 Redis、`FLUSHALL` 或生产导出。阶段 6 前必须由运维提供受控 PostgreSQL 连接和 Redis 卷/RDB/AOF 备份演练记录。

## 恢复与风险备注

1. 当前可恢复对象是源码快照和仓库内已发现的占位/公开静态资产；不能宣称恢复了生产数据库、Redis 队列、测试数据、上传文件、日志或密钥。
2. `OnlineJudge/data/test_case/<test_case_id>` 与 `Problem.test_case_id` 有数据库绑定关系；目录重组不得改变该关系或把测试数据暴露给前端。
3. Redis DB 1 同时承载 Session、cache 和 `waiting_queue`，Redis DB 4 承载 Dramatiq broker/result；备份/恢复必须按 DB 和运行时一致性设计，不能用 `FLUSHALL` 代替。
4. 所有备份路径均在仓库外；仅将脱敏状态和 hash 提交 Git。

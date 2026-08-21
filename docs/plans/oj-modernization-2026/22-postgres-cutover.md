# Step 22：PostgreSQL 生产切换

## 目标

把生产 PostgreSQL 从 PG10 切到已演练的 PG18.6（或已批准的 PG17.11），不同时升级 Django、Psycopg、Redis、Dramatiq 或 schema。

## 进入条件

- Step 21 至少两次 restore rehearsal 通过。
- Step 19 最终备份、Step 20 Redis 状态和 queue drain runbook 已批准。
- 旧 PG10 volume、备份和回滚主机仍可用。
- 已安排维护窗口、观察窗口和数据回灌决策人。

## T-7 天以上

- 锁定目标 PG image digest 和 Compose manifest。
- 再次验证磁盘：旧集群、新集群、dump、restore 临时空间并存。
- 演练 `pg_restore` 时长、健康检查、应用启动和回滚。
- 冻结 schema migration 与其他不可逆变更。

## T-24h / T-60m

- T-24h：备份 globals/database/runtime，生成 hash；确认 runtime 文件与 DB 对应。
- T-60m：进入维护，冻结 submission/rejudge/admin batch 等 producer。
- 保持旧 Worker/Server 自然 drain；确认 `waiting_queue=0`、PG PENDING/JUDGING=0、DB4 未完成项为0。
- 优雅停止 Worker 和写入口，确认无业务写连接。

## T0 切换

1. 生成最终 PG10 dump/hash。
2. 创建 fresh PG target volume。
3. 恢复 globals/database，`ANALYZE`。
4. 保持 target read-only，执行 catalog/业务/API/Session/CSRF/Judge smoke。
5. 由明确 GO/NO-GO 人员批准开放写入。
6. 启动 backend-api、worker、frontend、JudgeServer，逐步解除 producer freeze。
7. 进入观察窗口，保留 PG10 volume 和旧镜像。

## 计划命令

```bash
# 实际由受控 runbook 执行；示意
pg_dumpall --globals-only > "$BACKUP_DIR/final/globals.sql"
pg_dump -Fd --file="$BACKUP_DIR/final/database" "$DATABASE_NAME"
pg_restore --exit-on-error -j "$PG_RESTORE_JOBS" \
  --dbname="$TARGET_DATABASE" "$BACKUP_DIR/final/database"
```

禁止命令：

```text
docker compose down -v
rm -rf <old-volume>
DROP DATABASE 自动执行
pg18 data directory 挂给 pg10
```

## 验收

- API/admin/public、Session/CSRF、上传、题目/提交/比赛、Worker/Judge 全通过。
- migration history、关键 row counts、JSONB、sequence、index、ACL、timezone 一致。
- queue manifest 可解释；没有重复判题或静默丢任务。
- 观察窗口内错误率、延迟、连接数、锁等待和磁盘正常。

## 回滚边界

- target 尚未开放写入：停 target，切回未改动 PG10 和旧服务。
- target 已接受写入：PG10 已落后，不能直接切回；必须停写、盘点新写入，按批准的数据回灌/PITR/损失窗口处理。
- 永远不能用 PG18 data directory 启动 PG10。

## 停止条件

- 最终 dump/restore/hash/业务校验任何一项失败。
- waiting_queue/DB4 未清空或 producer/旧 Worker 仍活动。
- target 写入后才发现旧代码不兼容。
- 需要删除旧卷、修改历史 migration 或跳过 read-only gate。

## 完成标志

提交格式建议：

```text
ops: cut over PostgreSQL to validated target cluster
```

完成后保留旧 PG10 和备份至少一个批准的观察周期，再进入 Django5.2/最终 driver 发布。

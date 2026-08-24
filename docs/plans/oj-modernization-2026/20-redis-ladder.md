# Step 20：Redis 4 → 6.2 → 7.4 → 8.2

## 目标

在保持 DB1/DB4 业务职责和 RESP2 的前提下，逐代迁移 Redis；不切 Valkey，不直接声称 Redis4 RDB 可无损加载 Redis8。

## Phase 执行模式

- Phase 2：在隔离 volume 上用 fixture/脱敏 snapshot 完整演练 ladder，供 WSL 应用兼容开发；不取得生产消费权。
- Phase 5：使用 Step19 final snapshot/manifest、producer freeze、queue drain 和独立维护窗口执行生产 ladder。

## 进入条件

- 当前环境对应的 Step 19 Redis snapshot、manifest、restore rehearsal 通过；Phase 2 可使用 fixture/脱敏 clone，Phase 5 必须使用 final production evidence。
- 已实现 producer freeze、queue drain 和只有一套 Worker 消费权的 runbook。
- 旧 Redis4 volume 只读保留。

## 目标与桥接

```text
Redis 4.0
  -> Redis 6.2.23
  -> client/worker bridge 验证
  -> Redis 7.4.10
  -> Redis 8.2.8
```

每一跳使用新 volume、新容器和独立维护窗口。Redis8 许可已通过组织审查；本计划不在此窗口引入 Valkey。

## 切换顺序

1. 冻结 submission/rejudge/admin batch 等 producer。
2. 旧 Worker/Server 自然消费。
3. 同时确认 `LLEN waiting_queue=0`、PG `PENDING/JUDGING=0`、DB4 ready/delayed/ACK 未完成项为 0。
4. 发送优雅 SIGTERM，等待最长 actor 完成；禁止 kill -9。
5. 保存最终 DB1/DB4 manifest 和快照。
6. 启动下一代 Redis，新卷加载并比较 type/TTL/业务 manifest。
7. 在兼容的旧应用 client 下执行 Session/cache/waiting_queue/worker smoke。
8. soak 后才进入下一跳。
9. 全部通过后解除 producer freeze。

## 应用边界

- DB1：Session、cache、waiting_queue。
- DB4：Dramatiq broker/result。
- 迁移期保持 `redis://redis:6379/1`、`/4` 语义和 RESP2。
- 不得用 `FLUSHDB` 清理 Session/cache；waiting_queue 非零时不得失效整个 DB1。

## 故障注入

- snapshot 加载失败/不完整。
- Redis 重启、网络中断、旧 Worker 误启动。
- producer 未完全冻结。
- waiting_queue 非空时尝试切换。
- ACK 中消息、重复消费、result TTL 异常。

## 计划命令

```bash
# 每一代使用不同 COMPOSE_PROJECT_NAME/volume；示意，不自动删除旧卷
docker compose -f <redis-bridge-compose> up -d redis
redis-cli -h <internal-host> ping
redis-cli -h <internal-host> -n 1 INFO keyspace
redis-cli -h <internal-host> -n 4 INFO keyspace
```

不要把生产密码、RDB 内容或完整 key 值写入输出；manifest 工具必须脱敏。

## 验收

- 每一代真实 snapshot 加载、重启、恢复和业务 manifest 比较通过。
- Session/CSRF、cache TTL、waiting_queue、Dramatiq enqueue/result 全通过。
- 新旧 Worker 没有并行消费；没有重复判题、静默丢任务或异常 result。
- 旧 volume、快照和回滚元数据在观察窗口内保留。

## 停止条件

- 任一代 snapshot 加载不完整或 key type/TTL 差异无法解释。
- queue 不为零、ACK 未核账或 producer 未冻结。
- 只能用 `FLUSHDB`/删除 key 才能启动。
- Redis client/Worker 兼容组合没有实测证据。

## 回滚

新 Redis 尚未接受写入/消费前，停新容器，恢复上一代 volume/旧 Worker。已消费后必须重新 freeze、drain 并核对 PG/DB1/DB4；不能直接挂回旧卷。

## 完成标志

提交格式建议：

```text
ops: migrate Redis through supported ladder
```

Redis8 stable 后才批准 Step 18 的最终 Worker 生态升级。

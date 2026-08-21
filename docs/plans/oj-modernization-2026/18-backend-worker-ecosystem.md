# Step 18：Worker 与 Redis 客户端生态

## 目标

在 Django5.2 稳定后，分批升级 django-redis、redis-py、Dramatiq、django-dramatiq 和 DRF，保持 DB1/DB4、消息、结果和至少一次语义。

## 进入条件

- Step 17 Django5.2 全量通过。
- Step 20 Redis ladder 已达到目标 Redis（或已批准的中间版本），并有 DB1/DB4 manifest。
- 只有一套生产 Worker 有消费权；可执行 producer freeze/drain。

## 分批顺序

1. `django-redis` → 7.0.0：只验证 cache/session，DB1、key、TTL 不变。
2. `redis-py` → 7.4.1：只改 client，保持 RESP2，不切 RESP3。
3. Dramatiq 1.x bridge：先保持现有消息/result 兼容。
4. Dramatiq 1 → 2.2.0：独立维护窗口；必要时 drain DB4 后切换。
5. `django-dramatiq` 0.15.0：在目标 Django5.2/worker 组合中验证 startup、migrate、admin、worker。
6. DRF 3.17.2 → 3.18.0：最后单独做 API contract release。

不要把以上全部版本放在一个 lockfile 变更里一次上线；每一批独立提交、镜像、测试和回滚点。

## 测试

### DB1

- Session 创建/读取/过期/注销。
- cache TTL、序列化、`waiting_queue` push/pop、重启恢复。
- 不允许 `FLUSHDB`；不允许 DB1/DB4 交叉。

### DB4

- enqueue、ready/delayed/ACK/result/DLQ（以实际 backend 实现为准）。
- retry、timeout、SIGTERM、worker restart、result TTL。
- 同一 submission 不重复状态更新，不静默丢任务。

### Worker

- 只有一套生产消费权。
- 升级前冻结 producer，旧 Worker 自然 drain，再优雅停止。
- 新 Worker 不能读取旧版本未知的 message/result 格式。

## 计划命令

```bash
cd backend
uv add 'django-redis==7.0.0' 'redis==7.4.1'
uv lock
uv sync --locked --group test
uv run --locked --no-sync python manage.py test
python backend/deploy/runtime_smoke.py --worker
```

Dramatiq major 和 DRF 要在独立提交中执行；命令中的版本需先通过 Step00复核。

## 验收

- DB1/DB4 manifest 可解释，key/type/TTL 和业务数量无异常。
- enqueue→消费→result 全链路、retry、优雅停止、重启和 recovery 通过。
- API pagination/error-data、Session/CSRF 和 Judge dispatch 不变。
- 新旧 Worker 不并行消费；生产切换有 drain 记录。

## 停止条件

- 需要清空 DB4 才能“解决”兼容问题。
- message/result 序列化、ACK、retry 或 result TTL 改变且无迁移方案。
- `waiting_queue` 不是零却开始 Redis major 切换。
- 新旧 Worker 同时拥有生产消费权。

## 回滚

新 Worker 未消费前可切旧镜像/旧 Redis 卷；消费后必须重新 freeze、drain、核对 PostgreSQL/DB1/DB4，再决定回退或 forward-fix。禁止直接把新队列卷挂给旧版本。

## 完成标志

提交格式建议按批次：

```text
build(backend): upgrade redis client compatibility
build(backend): upgrade dramatiq worker runtime
build(backend): upgrade DRF after API contract review
```

完成后进入最终 Compose/deploy 编排。

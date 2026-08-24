# Phase 4：huawei1 隔离演练

## 目标

把 Phase 3 在 WSL 接受的同一 source SHA、Compose manifest 和 immutable image digest 部署到 `huawei1` 的隔离 project，证明 Ubuntu 主机运行行为一致。不得在 huawei1 用 mutable tag 重建另一套 artifact。

## 复用的 Step 清单

- Step 03：只重跑发生变化的 host、filesystem、Docker、port、Seccomp 检查。
- Step 19–21：对可用 protected clone/fixture 运行 inventory、Redis rehearsal、PG restore。
- Step 26：在真实 kernel/cgroup/amd64 上重跑 Judge security corpus。
- Step 27–29：消费 digest、启动隔离 Compose、运行 deploy.sh 全栈 smoke。

Phase 4 不执行 Step22，不切生产 PostgreSQL/Redis，不占用当前生产 project/volume/端口。

## 环境隔离

- 使用独立 `COMPOSE_PROJECT_NAME`、runtime、volume、backup 和 frontend rehearsal bind。
- 测试 Secret 位于隔离、权限受控、Git 外目录；可销毁，不复用生产 Secret。
- 若 protected real clone 暂不可用，先用与 WSL 相同 seed/fixture 完成 runtime smoke，把 real-clone restore 标为 Phase5 gate。
- 只拉取/导入 Phase3 digest；记录本地实际运行 digest 与 source SHA。

## 执行顺序

1. 校验 host 版本、磁盘、端口和隔离路径；不重做无变化的文档盘点。
2. 获取 Phase3 deployment manifest 和 image digest。
3. 准备 test Secret 与 fixture/protected clone。
4. 运行 deploy.sh first-install/pull 模式和 `up --wait`。
5. 运行 browser/API/worker/Judge/data/network smoke。
6. 运行普通升级、config-only、故障保留现场和 image rollback。
7. 若有真实 clone，完成两次 PG fresh restore、Redis ladder 和 runtime manifest；否则明确登记 Phase5 gate。

## Phase 验收

- huawei1 运行的 frontend/backend/server/toolchain digest 与 WSL release candidate 一致。
- 只有隔离 frontend bind 对宿主开放；不影响现有 80/443 服务。
- API/Session/CSRF/admin/public、worker/DB1/DB4、Judge protocol/Seccomp/resource corpus 通过。
- deploy.sh 首装、pull、普通升级、config-only、smoke failure、image rollback 通过。
- host-specific ownership、read-only mount、cgroup、Seccomp、DNS、registry、restart 行为有记录。
- production project、volume、Secret、queue 和 traffic 未改变。

## Soft failure 处理

- huawei1 DNS/proxy/registry/port/storage/firewall/ownership 差异：修复隔离环境后重试。
- 拉取失败可安全传输 OCI artifact，但必须校验 digest；不得改用 mutable tag。
- 性能或恢复时间超预期：记录实测并调整 Phase5 window，不停止功能 smoke。
- real clone/production Secret 未提供：只登记 release gate，不阻塞 fixture runtime 验收。

## Hard stop

- 隔离部署会覆盖现有生产路径、volume、project 或端口。
- 实际运行 digest 无法确认，或需要临时关闭 Judge 安全隔离。
- production Secret/数据被复制到不受控位置或写入日志。
- restore/rollback 证明数据无法恢复；停止进入 Phase5。

## 回滚

只停止隔离 Compose project，并保留其日志/metadata；删除隔离 volume 前必须确认不含 protected clone 的唯一副本。不得运行全局 prune，不改当前生产服务。

## 完成标志

相同升级 artifact 已在 WSL 和 huawei1 跑通。若只要求“升级版可运行”，到此已达成；生产迁移另进入 [Phase 5](05-production-release.md)。

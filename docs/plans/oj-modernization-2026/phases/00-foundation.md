# Phase 0：基线、合同与宿主前置

> 状态：**已完成**。下一次对话不重做，除非版本锁或目标宿主发生实质变化。

## 包含 Step

- Step 00：决策门与版本锁
- Step 01：行为合同与特征测试
- Step 02：现状盘点与构建基线
- Step 03：WSL/huawei1 非生产宿主前置

## 已完成证据

| Step | Commit | 结果 |
|---:|---|---|
| 00 | `f899a96deffa16aedd8a2fc2e803f77c0adc6da4` | 锁定 Python3.10、Node/pnpm、PG/Redis、Judge/toolchain 候选和 digest |
| 01 | `3e209be8e5574aa4f4ec211dc0da2ce054e0f358` | API/Session/CSRF、数据 identity、frontend route、Judge 协议合同 |
| 02 | `6aead8a81cc708d861263baf0bfcabe1a913db35` | 源码/依赖/镜像/构建/runtime baseline |
| 03 | `68f2775f01730ec9b1399458a9f3e71897facbb5` | huawei1 Ubuntu22、Docker/Compose/BuildKit、目录和 mount 权限预检 |

详细事实见 `../execution-log.md` 和 `../../../contracts/`。

## Phase 结论

- WSL 可用于源码构建和隔离 Compose。
- `huawei1` 已验证 Ubuntu 22.04.5、x86_64、cgroup v2、Docker 29.7.1、Compose 5.4.0、Buildx 0.36.0。
- `/srv/xju-oj` 的空 runtime/volume/backup 目录已建立；未触碰生产数据。
- `/srv/xju-oj/secrets` 为空只阻塞 Phase 5 生产发布，不阻塞 Phase 1–4。
- Phase 1–4 使用独立、可销毁、Git ignored 的测试 Secret；禁止把测试 Secret 混入生产路径或提交。

## 重新执行条件

仅当以下之一发生时重跑相关检查，而不是整 Phase 重做：

- Step 00 锁定版本或基础镜像 digest 改变。
- WSL Docker/BuildKit 运行方式改变。
- huawei1 OS、内核、Docker、文件系统或目标架构改变。
- 兼容合同经用户批准修改。

## 下一步

执行 [Phase 1：组件桥接与可重复构建](01-component-bridge.md)。

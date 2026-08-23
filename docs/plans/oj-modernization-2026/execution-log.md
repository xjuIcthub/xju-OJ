# 2026 现代化迁移执行记录

> 此文件只记录已经实际执行并验证的事实；计划文本、预估结果和“应当通过”不能写成完成事实。

## 全局信息

- 生产宿主：Ubuntu >=22.04（精确版本与支持状态：待 Step 00 锁定）
- Python：3.10.x（精确 micro：待 Step 00 锁定）
- 当前分支：`main`
- 计划入口：[README.md](README.md)
- 当前 Step：未开始
- 最近完成 Step：无

## 记录格式

每完成一个 Step，追加一条：

```text
### YYYY-MM-DD — Step NN

- Commit:
- 变更摘要:
- 实际命令:
- 测试/验收结果:
- 镜像与 digest:
- 数据/Redis/queue 证据:
- 已知风险:
- 回滚点:
- 下一步:
```

## 禁止记录

- Secret、密码、Token、私钥、Cookie、Authorization header。
- 完整生产数据库 dump、Redis RDB/AOF、用户上传文件或判题运行数据。
- 未执行的命令结果、未验证的版本或推测性的“已完成”。

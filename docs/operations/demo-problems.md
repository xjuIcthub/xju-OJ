# OJ 演示题填充方案

这组题用于验证 OJ 的题目展示、普通判题和 Special Judge，不依赖真实用户数据。

## 题目清单

| Display ID | 题目 | 判题 | 测试点 | 样例 |
| --- | --- | --- | ---: | --- |
| `demo-ab` | A+B | ACM 标准输出 | 20 | `1 2` → `3`；`-100 58` → `-42` |
| `demo-spj` | Special Judge：合法排列 | ACM + C SPJ | 20 | `n=5` → `1 2 3 4 5`；`n=4` → `4 1 3 2` |

两题都使用当前 OJ 配置的全部语言、Standard IO、Low difficulty 和 `demo` tag。题目由 `winbeau` 创建，直接作为 standalone visible problem 出现在题目列表中。

## 测试点设计

### `demo-ab`

测试点依次为：

```text
0+0, 1+2, -1+1, -5+-7, 100+200,
-100+250, 12345+67890, -12345+67890,
999999999+1, -1000000000+1,
1000000000+1000000000, -1000000000+-1000000000,
214748364+987654321, -214748364+-987654321,
314159265+271828182, -314159265+271828182,
42+-42, 7+0, -999999999+999999999, 1000000000+-1000000000
```

输入范围为 `-10^9 <= a,b <= 10^9`，结果范围仍在有符号 32 位整数范围内。

### `demo-spj`

测试点的 `n` 依次为：

```text
1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
16, 25, 31, 50, 64, 100, 127, 256, 512, 1000
```

SPJ 检查：

1. 输出恰好 `n` 个整数；
2. 每个整数在 `[1,n]`；
3. 不允许重复或遗漏；
4. 末尾只能有空白，不能有额外 token；
5. 检查器异常返回系统错误，普通不合法答案返回 WA。

## 安全、幂等和回滚

脚本位于 [`deploy/ops/seed-demo-problems.py`](../../deploy/ops/seed-demo-problems.py)，默认是 `check`，不会写数据库或测试数据。它会验证固定 display ID、创建者、题面字段、SPJ 源码、测试文件和 `info`；同 ID 存在但内容不一致时停止，不覆盖既有题目。

`apply` 模式先在测试数据目录中写入临时目录，再原子改名；数据库写入使用事务。重复执行只报告 existing。若此前导入的同源题目是 hidden，`apply` 只将其设为 visible，不修改提交统计或历史数据。

执行 apply 前可先备份当前 fixture；回滚只删除本次脚本创建且 display ID/source 均匹配的两道题及其测试目录，不能使用全局 `delete`、`down -v` 或 volume prune。生产回滚建议优先将题目切回 hidden，再按管理员批准执行定向删除。

## 部署后执行

在 huawei1 的 `/home/winbeau/xju-OJ` 目录执行。`manage.py shell -c` 从标准输入读取仓库脚本，因此不需要把脚本复制进容器镜像：

```bash
cd /home/winbeau/xju-OJ

docker compose exec -T backend-api \
  python manage.py shell -c \
  'exec(compile(__import__("sys").stdin.read(), "<seed-demo-problems>", "exec"))' \
  < deploy/ops/seed-demo-problems.py

docker compose exec -T backend-api \
  env DEMO_PROBLEMS_MODE=apply \
  python manage.py shell -c \
  'exec(compile(__import__("sys").stdin.read(), "<seed-demo-problems>", "exec"))' \
  < deploy/ops/seed-demo-problems.py
```

第二条只在第一条 `check passed` 且题目冲突检查无异常后执行。成功后分别提交：

- `demo-ab`：提交 `scanf/iostream` 读取两个整数并输出和，预期 AC；
- `demo-spj`：提交顺序输出 `1..n`，预期 AC；再提交重复或越界数字，预期 WA；提交乱序排列，预期 AC。

脚本不读取或输出密码、OIDC secret、Judge token、Cookie 或数据库私有数据。

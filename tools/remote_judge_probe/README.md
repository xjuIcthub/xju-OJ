# Remote judge probes

这是一组与现有 OJ 后端、前端隔离的真实提交 PoC。目标是先验证：

```text
源码文本/文件 -> 第三方 OJ 提交 -> 远程提交 ID -> 最终判题结果
```

PoC 不抓取题面或样例，也不会把 Cookie、密码或源码写入日志。Cookie 文件必须放在
Git 仓库之外；`capture_session.py` 创建的文件权限为 `0600`。

## 1. 捕获专用测试账号会话

每个平台使用独立 Chrome profile。命令会打开浏览器，人工完成登录后回到终端按
Enter。不要复用日常浏览器 profile。

```bash
python3 tools/remote_judge_probe/capture_session.py codeforces \
  --profile-dir ~/.local/share/xju-oj/remote-probe/profiles/codeforces \
  --output ~/.local/share/xju-oj/remote-probe/codeforces.cookies.json

python3 tools/remote_judge_probe/capture_session.py nowcoder \
  --profile-dir ~/.local/share/xju-oj/remote-probe/profiles/nowcoder \
  --output ~/.local/share/xju-oj/remote-probe/nowcoder.cookies.json
```

## 2. 实际提交

所有会产生真实提交的命令都要求显式增加 `--confirm-submit`。源码可由 `--source`、
`--code` 或 stdin 提供。

Codeforces 推荐浏览器提交，结果通过官方 `user.status` API 查询：

```bash
python3 tools/remote_judge_probe/probe.py codeforces \
  --problem 4A --language 54 \
  --browser-profile ~/.local/share/xju-oj/remote-probe/profiles/codeforces \
  --source /path/to/main.cpp --confirm-submit --wait
```

浏览器模式会从已登录页面自动识别 handle。如果账号 Cookie 可以直接访问提交表单，
也可以把 `--browser-profile` 换成 `--cookie-file`，此时还需要显式提供
`--handle`。遇到 Codeforces challenge 时使用浏览器模式。

洛谷使用官方 Open Platform，不需要网页 Cookie 或验证码。先将 OpenApp Token
（格式为 `client_id:secret`）保存到仓库外的 `0600` 文件，也可以设置环境变量
`LUOGU_OPENAPP_TOKEN`。建议先检查鉴权和评测额度：

```bash
install -m 600 /dev/null ~/.local/share/xju-oj/remote-probe/luogu-openapp.token
# 使用编辑器将 client_id:secret 写入上述文件，不要把 Token 直接放进 shell 历史

python3 tools/remote_judge_probe/probe.py luogu-quota \
  --token-file ~/.local/share/xju-oj/remote-probe/luogu-openapp.token
```

C++17 的开放平台语言标识为 `cxx/17/gcc`。实际提交命令为：

```bash
python3 tools/remote_judge_probe/probe.py luogu \
  --problem P1001 --language cxx/17/gcc \
  --token-file ~/.local/share/xju-oj/remote-probe/luogu-openapp.token \
  --track-id xju-oj-debug-1 \
  --source tools/remote_judge_probe/examples/luogu_P1001.cpp \
  --confirm-submit --wait
```

如果提交后终端中断，可使用已输出的 Request ID 恢复查询，避免重复提交：

```bash
python3 tools/remote_judge_probe/probe.py luogu-result \
  --request-id REQUEST_ID \
  --token-file ~/.local/share/xju-oj/remote-probe/luogu-openapp.token \
  --wait
```

常用语言标识：C 为 `c/99/gcc`，C++20 为 `cxx/20/gcc`，Python 3 为
`python3/c`，Java 8 为 `java/8`，Go 为 `go`，Node.js 为 `js/node/lts`。
接口文档见 <https://docs.lgapi.cn/open/judge/api/luogu-problem>。

牛客 PoC 支持当前 `ac.nowcoder.com/acm/problem` 题目和公开
`questionTerminal` 编程题，C++ 语言 ID 当前为 `2`：

```bash
python3 tools/remote_judge_probe/probe.py nowcoder \
  --problem NC322024 --language 2 \
  --cookie-file ~/.local/share/xju-oj/remote-probe/nowcoder.cookies.json \
  --source /path/to/main.cpp --confirm-submit --wait
```

输出为逐行 JSON，事件顺序为 `submitted -> status... -> finished`。POST 请求发生网络
异常时，PoC 会返回 `AmbiguousSubmission`，不会自动重试。

## 3. 测试

```bash
PYTHONPATH=tools/remote_judge_probe \
  python3 -m unittest discover -s tools/remote_judge_probe/tests -v
```

三条链路均需要平台允许的专用测试账号，并应控制并发和提交频率。洛谷链路使用官方
OpenApp Token；Token、Cookie 和其他凭据都不能提交到 Git。

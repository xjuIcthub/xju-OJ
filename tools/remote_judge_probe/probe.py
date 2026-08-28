#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROBE_ROOT = Path(__file__).resolve().parent
if str(PROBE_ROOT) not in sys.path:
    sys.path.insert(0, str(PROBE_ROOT))

from remote_probe.codeforces import CodeforcesProvider
from remote_probe.common import (
    ProbeError,
    RemoteResult,
    RemoteSubmission,
    poll_until_finished,
    print_json,
    read_source,
    require_confirmed,
)
from remote_probe.luogu import LuoguOpenPlatformProvider, load_openapp_token
from remote_probe.nowcoder import NowcoderProvider


def add_source_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source", help="UTF-8 源码文件；不指定时可使用 stdin")
    parser.add_argument("--code", help="直接传入源码文本，仅建议短测试代码")
    parser.add_argument(
        "--confirm-submit",
        action="store_true",
        help="确认向第三方 OJ 产生一次真实提交",
    )
    parser.add_argument("--wait", action="store_true", help="轮询到最终判题结果")
    parser.add_argument("--timeout", type=float, default=180, help="判题等待秒数，默认 180")
    parser.add_argument("--poll-interval", type=float, default=2, help="轮询间隔秒数，默认 2")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="xju-OJ 三方远程提交 PoC")
    subparsers = root.add_subparsers(dest="provider", required=True)

    cf = subparsers.add_parser("codeforces")
    cf.add_argument("--problem", required=True, help="例如 4A 或 Codeforces 题目 URL")
    cf.add_argument("--language", required=True, help="Codeforces programTypeId")
    cf.add_argument("--handle", default="", help="浏览器模式可从登录页自动识别")
    cf.add_argument("--cookie-file", help="capture_session.py 导出的 Cookie JSON")
    cf.add_argument("--browser-profile", help="使用 Chrome 专用登录配置进行提交")
    cf.add_argument("--headed", action="store_true", help="浏览器提交时显示窗口")
    add_source_arguments(cf)

    luogu = subparsers.add_parser("luogu")
    luogu.add_argument("--problem", required=True, help="例如 P1001 或洛谷题目 URL")
    luogu.add_argument(
        "--language",
        required=True,
        help="开放平台语言标识，例如 C++17 为 cxx/17/gcc",
    )
    luogu.add_argument("--token-file", help="OpenApp Token 文件；也可使用 LUOGU_OPENAPP_TOKEN")
    luogu.add_argument("--o2", action="store_true", help="请求开启 O2 优化")
    luogu.add_argument("--track-id", help="最多 64 字节，用于在洛谷侧关联本地提交")
    add_source_arguments(luogu)

    luogu_quota = subparsers.add_parser("luogu-quota", help="检查 OpenApp 鉴权和评测额度")
    luogu_quota.add_argument(
        "--token-file", help="OpenApp Token 文件；也可使用 LUOGU_OPENAPP_TOKEN"
    )

    luogu_result = subparsers.add_parser(
        "luogu-result", help="按 Request ID 查询或继续等待洛谷评测"
    )
    luogu_result.add_argument("--request-id", required=True, help="提交返回的 Request ID")
    luogu_result.add_argument(
        "--token-file", help="OpenApp Token 文件；也可使用 LUOGU_OPENAPP_TOKEN"
    )
    luogu_result.add_argument("--wait", action="store_true", help="轮询到最终判题结果")
    luogu_result.add_argument("--timeout", type=float, default=180, help="判题等待秒数")
    luogu_result.add_argument("--poll-interval", type=float, default=2, help="轮询间隔秒数")

    nowcoder = subparsers.add_parser("nowcoder")
    nowcoder.add_argument("--problem", required=True, help="NC322024、ACM/公开题 URL、UUID 或数字 questionId")
    nowcoder.add_argument("--language", required=True, help="牛客语言 ID，例如 C++ 为 2")
    nowcoder.add_argument("--cookie-file", required=True)
    add_source_arguments(nowcoder)
    return root


def emit_update(result: RemoteResult) -> None:
    print_json({"event": "status", **result.public_dict()})


def run(args: argparse.Namespace) -> int:
    if args.provider == "luogu-quota":
        provider = LuoguOpenPlatformProvider(load_openapp_token(args.token_file))
        print_json({"event": "quota", **provider.quota()})
        return 0

    if args.provider == "luogu-result":
        if args.timeout <= 0 or args.poll_interval <= 0:
            raise ProbeError("--timeout 和 --poll-interval 必须大于 0")
        provider = LuoguOpenPlatformProvider(load_openapp_token(args.token_file))
        submission = RemoteSubmission(
            provider="luogu",
            remote_id=args.request_id,
            problem_id="",
            submitted_at=0,
        )
        if args.wait:
            result = poll_until_finished(
                lambda: provider.query(submission),
                timeout_seconds=args.timeout,
                interval_seconds=args.poll_interval,
                on_update=emit_update,
            )
        else:
            result = provider.query(submission)
        event = "finished" if result.finished else "status"
        print_json({"event": event, **result.public_dict()})
        return 0

    require_confirmed(args.confirm_submit)
    if args.timeout <= 0 or args.poll_interval <= 0:
        raise ProbeError("--timeout 和 --poll-interval 必须大于 0")
    code = read_source(args.source, args.code)

    if args.provider == "codeforces":
        if bool(args.cookie_file) == bool(args.browser_profile):
            raise ProbeError("Codeforces 必须且只能选择 --cookie-file 或 --browser-profile")
        provider = CodeforcesProvider(args.handle, args.cookie_file)
        if args.browser_profile:
            submission = provider.submit_browser(
                args.problem, args.language, code, args.browser_profile, args.headed
            )
        else:
            submission = provider.submit_requests(args.problem, args.language, code)
    elif args.provider == "luogu":
        provider = LuoguOpenPlatformProvider(load_openapp_token(args.token_file))
        submission = provider.submit(
            args.problem,
            args.language,
            code,
            o2=args.o2,
            track_id=args.track_id,
        )
    else:
        provider = NowcoderProvider(args.cookie_file)
        submission = provider.submit(args.problem, args.language, code)

    print_json({"event": "submitted", **submission.public_dict()})
    if args.wait:
        result = poll_until_finished(
            lambda: provider.query(submission),
            timeout_seconds=args.timeout,
            interval_seconds=args.poll_interval,
            on_update=emit_update,
        )
        print_json({"event": "finished", **result.public_dict()})
    return 0


def main() -> int:
    args = parser().parse_args()
    try:
        return run(args)
    except ProbeError as exc:
        print_json(
            {
                "event": "error",
                "error_type": exc.__class__.__name__,
                "message": str(exc),
            }
        )
        return exc.exit_code
    except KeyboardInterrupt:
        print_json({"event": "cancelled", "message": "用户取消"})
        return 130


if __name__ == "__main__":
    raise SystemExit(main())

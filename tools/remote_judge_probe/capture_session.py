#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROBE_ROOT = Path(__file__).resolve().parent
if str(PROBE_ROOT) not in sys.path:
    sys.path.insert(0, str(PROBE_ROOT))

from remote_probe.common import ProbeError, print_json, write_private_json


LOGIN_URLS = {
    "codeforces": "https://codeforces.com/enter",
    "nowcoder": "https://www.nowcoder.com/login",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="使用独立 Chrome 配置登录并导出远程 OJ Cookie")
    parser.add_argument("provider", choices=sorted(LOGIN_URLS))
    parser.add_argument("--output", required=True, help="Cookie JSON 输出路径（文件权限将设为 0600）")
    parser.add_argument("--profile-dir", required=True, help="该远程账号专用 Chrome profile 目录")
    args = parser.parse_args()

    try:
        from selenium import webdriver
    except ImportError as exc:
        print_json({"event": "error", "message": "需要安装 selenium"})
        return 1

    profile = Path(args.profile_dir).expanduser().resolve()
    profile.mkdir(parents=True, exist_ok=True)
    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={profile}")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        driver.get(LOGIN_URLS[args.provider])
        input("请在打开的浏览器中完成登录；确认已登录后回到终端按 Enter: ")
        driver.get(LOGIN_URLS[args.provider].split("/enter")[0].split("/auth/login")[0].split("/login")[0] + "/")
        cookies = driver.get_cookies()
        user_agent = driver.execute_script("return navigator.userAgent")
        if not cookies:
            raise ProbeError("浏览器没有返回任何 Cookie")
        output = write_private_json(
            args.output,
            {
                "provider": args.provider,
                "user_agent": user_agent,
                "cookies": cookies,
            },
        )
        print_json(
            {
                "event": "captured",
                "provider": args.provider,
                "cookie_file": str(output),
                "cookie_count": len(cookies),
                "profile_dir": str(profile),
            }
        )
        return 0
    except (ProbeError, EOFError) as exc:
        print_json({"event": "error", "message": str(exc)})
        return 1
    finally:
        if driver is not None:
            driver.quit()


if __name__ == "__main__":
    raise SystemExit(main())

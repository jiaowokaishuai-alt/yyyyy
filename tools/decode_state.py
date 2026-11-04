#!/usr/bin/env python3
"""把 Secret XIANYU_STATE_B64 还原成项目要的登录态 JSON。

只打印结构性信息（是否合法、cookie 条数），绝不打印 cookie 内容。
"""
from __future__ import annotations

import argparse
import base64
import binascii
import json
import os
import re
from pathlib import Path


def decode(raw: str) -> bytes:
    text = raw.strip().strip('"').strip("'")
    if text.startswith("{"):
        return text.encode("utf-8")
    cleaned = re.sub(r"[\s]+", "", text)
    try:
        return base64.b64decode(cleaned, validate=False)
    except (binascii.Error, ValueError) as exc:
        raise SystemExit(
            "XIANYU_STATE_B64 既不是合法 base64，也不是直接的 JSON："
            f"{exc}。请重新导出闲鱼登录态后更新 Secret。"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", default="app")
    parser.add_argument("--state-file", default="state/acc_1.json")
    args = parser.parse_args()

    raw = os.environ.get("XIANYU_STATE_B64", "")
    if not raw.strip():
        raise SystemExit(
            "缺少 Secret XIANYU_STATE_B64（闲鱼登录态）。"
            "请在仓库 Settings → Secrets and variables → Actions 里添加后再运行。"
        )

    payload = decode(raw)
    try:
        data = json.loads(payload.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise SystemExit(f"登录态解码后不是合法 JSON：{exc}")

    target = Path(args.app) / args.state_file
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload.decode("utf-8"), encoding="utf-8")
    target.chmod(0o600)

    if isinstance(data, dict) and isinstance(data.get("cookies"), list):
        cookies = data["cookies"]
        enhanced = any(k in data for k in ("env", "headers", "page", "storage"))
        domains = {str(c.get("domain", "")) for c in cookies if isinstance(c, dict)}
        print(
            f"[state] 已写入 {target}：{len(payload)} 字节，{len(cookies)} 条 cookie，"
            f"格式={'增强快照' if enhanced else 'storage_state'}，"
            f"含 goofish 域={'是' if any('goofish' in d for d in domains) else '否'}"
        )
    else:
        print(f"[state] 已写入 {target}：{len(payload)} 字节（结构非标准 storage_state，仍按原样交给项目解析）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

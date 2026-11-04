#!/usr/bin/env python3
"""生成项目 .env。密钥只从环境变量读取，脚本只报告是否已设置，绝不打印值。"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

BASE_LINES = [
    "# 由 tools/write_env.py 生成；密钥来自 GitHub Secrets，请勿手写进仓库",
    "OPENAI_BASE_URL=https://api.deepseek.com",
    "OPENAI_MODEL_NAME=deepseek-flash",
    "RUN_HEADLESS=true",
    "RUNNING_IN_DOCKER=true",
    "LOGIN_IS_EDGE=false",
    "PCURL_TO_MOBILE=true",
    "ENABLE_THINKING=false",
    "ENABLE_RESPONSE_FORMAT=true",
    "AI_DEBUG_MODE=false",
    "TASK_FAILURE_THRESHOLD=3",
    "TASK_FAILURE_PAUSE_SECONDS=86400",
]

OPTIONAL_KEYS = ("BARK_URL", "WX_BOT_URL", "PUSHPLUS_TOKEN", "WEBHOOK_URL")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", default="app")
    args = parser.parse_args()

    app = Path(args.app)
    app.mkdir(parents=True, exist_ok=True)

    key = os.environ.get("OPENAI_API_KEY", "").strip()
    lines = list(BASE_LINES)
    lines.append(f"OPENAI_API_KEY={key}")

    configured = []
    for name in OPTIONAL_KEYS:
        value = os.environ.get(name, "").strip()
        if value:
            lines.append(f"{name}={value}")
            configured.append(name)
    if configured:
        lines.append('WEBHOOK_METHOD=POST')
        lines.append('WEBHOOK_CONTENT_TYPE=JSON')

    target = app / ".env"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        target.chmod(0o600)
    except OSError:
        pass

    print(f"[env] 已写入 {target}")
    print(f"[env] OPENAI_API_KEY: {'已设置' if key else '缺失（未配置 Secret，AI 分析会被跳过）'}")
    print(f"[env] 模型: {os.environ.get('OPENAI_BASE_URL', 'https://api.deepseek.com')} / deepseek-flash")
    print(f"[env] 通知渠道: {', '.join(configured) if configured else '未配置（命中也不会有推送）'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

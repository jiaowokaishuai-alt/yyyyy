#!/usr/bin/env python3
"""把本轮抓取结果整理成 GitHub Actions 运行摘要。

只读本地的结果库与运行日志，不打印任何 cookie、密钥内容。
"""
from __future__ import annotations

import argparse
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

LOGIN_PATTERN = (
    "登录失效",
    "未找到可用的登录状态文件",
    "FAIL_SYS_USER_VALIDATE",
    "baxia-dialog",
    "J_MIDDLEWARE_FRAME_WIDGET",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", default="app")
    parser.add_argument("--log", default="app/run.log")
    parser.add_argument("--hours", type=int, default=6, help="摘要回看的时间窗口（小时）")
    args = parser.parse_args()

    app = Path(args.app)
    db_rel = os.environ.get("APP_DATABASE_FILE", "data/app.sqlite3").strip() or "data/app.sqlite3"
    db = Path(db_rel)
    if not db.is_absolute():
        db = app / db_rel
    since = (datetime.now(timezone.utc) - timedelta(hours=args.hours)).strftime("%Y-%m-%d %H:%M:%S")

    print("## 闲鱼监控 · 本轮运行摘要")
    print()
    print(f"- 生成时间（UTC）：{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"- 统计窗口：最近 {args.hours} 小时入库的商品")

    log_path = Path(args.log)
    if log_path.exists():
        text = log_path.read_text(encoding="utf-8", errors="ignore")
        hits = [p for p in LOGIN_PATTERN if p in text]
        if hits:
            print("- 登录态提示：日志里出现登录失效或风控相关字样，建议重新导出登录态并更新 Secret XIANYU_STATE_B64")

    if not db.exists():
        print()
        print("本轮没有生成结果库（多半是登录态缺失或抓取在早期就失败了），请看上方日志。")
        return 0

    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        total = conn.execute("SELECT COUNT(*) FROM result_items").fetchone()[0]
        total_lifetime = conn.execute(
            "SELECT COUNT(*) FROM result_items WHERE substr(crawl_time,1,19) >= ?", (since,)
        ).fetchone()[0]
        rows = conn.execute(
            """
            SELECT task_name, keyword, title, price_display, price, link, is_recommended, analysis_source
            FROM result_items
            WHERE substr(crawl_time,1,19) >= ?
            ORDER BY is_recommended DESC, price ASC
            """,
            (since,),
        ).fetchall()
    except sqlite3.Error as exc:
        print()
        print(f"读取结果库失败：{exc}")
        return 0
    finally:
        conn.close()

    recommended = [r for r in rows if r["is_recommended"]]
    print()
    print(f"- 本轮新入库：{len(rows)} 条，其中判定为符合条件：{len(recommended)} 条")
    print(f"- 结果库累计记录：{total} 条（跨轮次去重用）")

    if recommended:
        print()
        print("### 命中商品（本轮）")
        print()
        print("| 任务 | 标题 | 标价 | 链接 |")
        print("| --- | --- | --- | --- |")
        for row in recommended[:10]:
            title = str(row["title"] or "").replace("|", "／")[:60]
            price = row["price_display"] or row["price"] or "-"
            link = row["link"] or ""
            print(f"| {row['task_name']} | {title} | {price} | {link} |")
        if len(recommended) > 10:
            print()
            print(f"（只列出前 10 条，本轮共 {len(recommended)} 条）")
    else:
        print()
        print("本轮没有新的符合条件商品；已抓到的商品都会写入结果库，下一轮不会重复分析。")

    print()
    print("命中商品的推送由项目自身按 .env 里配置的通知渠道发出；失败信息见上方日志。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

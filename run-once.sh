#!/usr/bin/env bash
# 单轮抓取入口：抓一轮就退出，适合 GitHub Actions 这类没有常驻服务的环境。
# 用法: bash run-once.sh [--app app]
# 可以通过环境变量调整：DEBUG_LIMIT（每任务最多处理 N 个新商品，0=不限）、TASK_NAME（只跑某个任务名）、STATE_FILE（登录态路径，默认 state/acc_1.json）
set -uo pipefail

APP_DIR="app"
while [ $# -gt 0 ]; do
  case "$1" in
    --app) APP_DIR="${2:-app}"; shift 2 ;;
    *) echo "未知参数: $1" >&2; exit 64 ;;
  esac
done

DEBUG_LIMIT="${DEBUG_LIMIT:-0}"
TASK_NAME="${TASK_NAME:-}"
STATE_REL="${STATE_FILE:-state/acc_1.json}"
LOG_PATH="${LOG_PATH:-run.log}"

if [ ! -d "$APP_DIR" ]; then
  echo "找不到项目目录 $APP_DIR（工作流里应该已经克隆上游项目）" >&2
  exit 65
fi

cd "$APP_DIR" || exit 65

# 把本仓库里的配置与提示词叠进项目目录
cp -f ../config.json ./config.json || exit 65
mkdir -p prompts
cp -f ../prompts/nitro_9070xt_criteria.txt prompts/ 2>/dev/null || true

if [ ! -s "$STATE_REL" ]; then
  echo "缺少闲鱼登录态文件 $APP_DIR/$STATE_REL，本轮跳过。请更新 Secret XIANYU_STATE_B64。" >&2
  exit 3
fi
if [ ! -s .env ]; then
  echo "缺少 $APP_DIR/.env，请检查工作流里生成 .env 的步骤。" >&2
  exit 4
fi

args=(--config config.json)
if [ "$DEBUG_LIMIT" != "0" ] && [ -n "$DEBUG_LIMIT" ]; then
  args+=(--debug-limit "$DEBUG_LIMIT")
fi
if [ -n "$TASK_NAME" ]; then
  args+=(--task-name "$TASK_NAME")
fi

echo "开始执行单轮抓取: python spider_v2.py ${args[*]}"
python spider_v2.py "${args[@]}" 2>&1 | tee "$LOG_PATH"
status="${PIPESTATUS[0]}"

# 登录态失效/风控的粗判：只输出结论，不回显日志内容
if grep -qE "登录失效|需要登录|未找到可用的登录状态文件|FAIL_SYS_USER_VALIDATE|baxia-dialog|J_MIDDLEWARE_FRAME_WIDGET" "$LOG_PATH"; then
  warning="闲鱼登录态可能已失效或被风控拦截：请重新导出登录态并更新 Secret XIANYU_STATE_B64。"
  echo "::warning::$warning"
  if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
    printf '> 注意：%s\n\n' "$warning" >> "$GITHUB_STEP_SUMMARY"
  fi
fi

echo "单轮抓取结束，退出码 $status"
exit "$status"

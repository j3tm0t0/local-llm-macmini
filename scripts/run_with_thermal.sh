#!/bin/bash
# run_with_thermal.sh — 任意コマンドを thermal ログ付きで走らせる wrapper
#
# 前提: 事前に `sudo -v` を叩いて sudo credentials をキャッシュしておく
#       (パスワード対話をこの wrapper 内では起こしたくないため)
#
# 使い方:
#   ./run_with_thermal.sh <log_prefix> <command...>
#
# 例:
#   ./run_with_thermal.sh ~/tmp/thermal_ollama_v3 bash /Users/moto/tmp/claude-code-local-llm/run_m5max.sh
#
# 出力:
#   $log_prefix.plist  — 生の powermetrics plist
#   $log_prefix.summary  — CPU/GPU 温度 min/avg/max + 実行時間

set -uo pipefail
[ $# -lt 2 ] && { echo "Usage: $0 <log_prefix> <cmd...>"; exit 1; }

LOG_PREFIX="$1"; shift
DIR=$(dirname "$0")
THERMAL="$DIR/thermal_monitor.sh"
[ -x "$THERMAL" ] || { echo "ERROR: thermal_monitor.sh not executable at $THERMAL"; exit 1; }

# powermetrics に sudo -n で入れるか確認 (NOPASSWD 経路想定)
if ! sudo -n /usr/bin/powermetrics -n 1 -i 1000 --samplers thermal >/dev/null 2>&1; then
    echo "ERROR: sudo powermetrics 非対話で実行できず。次のいずれか:"
    echo "  1. NOPASSWD を設定: /etc/sudoers.d/powermetrics に "
    echo "     moto ALL=(ALL) NOPASSWD: /usr/bin/powermetrics"
    echo "  2. sudo -v で generic sudo cache してから再実行"
    exit 1
fi

PLIST="${LOG_PREFIX}.plist"
SUMMARY="${LOG_PREFIX}.summary"
START_TS=$(date +%s)
START_ISO=$(date -Iseconds 2>/dev/null || date "+%Y-%m-%dT%H:%M:%S%z")

echo "=== thermal_monitor start $START_ISO → $PLIST ==="
"$THERMAL" --start "$PLIST"
sleep 2   # 最初のサンプル取得を待つ

# メインコマンド実行
echo "=== running command: $* ==="
"$@"
RC=$?

# thermal 停止
"$THERMAL" --stop

END_TS=$(date +%s)
END_ISO=$(date -Iseconds 2>/dev/null || date "+%Y-%m-%dT%H:%M:%S%z")
ELAPSED=$((END_TS - START_TS))

echo ""
echo "=== summary → $SUMMARY ==="
{
    echo "command: $*"
    echo "start: $START_ISO"
    echo "end:   $END_ISO"
    echo "elapsed: ${ELAPSED}s"
    echo "exit_code: $RC"
    echo ""
    "$THERMAL" --summary "$PLIST" 2>&1
} | tee "$SUMMARY"

exit $RC

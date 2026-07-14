#!/bin/bash
# thermal_monitor.sh — powermetrics で M5 Max の温度/fan/CPU/GPU を 5s 間隔でログ
#
# 使い方:
#   ./thermal_monitor.sh <out.log>              # foreground、Ctrl-C で停止
#   ./thermal_monitor.sh --start <out.log>      # background、PID を /tmp/thermal_monitor.pid に記録
#   ./thermal_monitor.sh --stop                 # background 停止
#   ./thermal_monitor.sh --summary <out.log>    # 温度 max/avg 集計
#
# ※初回は sudo password 要求。連続 bench 中に何度も聞かれると鬱陶しいので
#   /etc/sudoers.d/powermetrics に NOPASSWD ルールを入れる方法もある (後述)。

set -uo pipefail
PIDFILE=/tmp/thermal_monitor.pid
INTERVAL_MS=5000    # 5 秒間隔
# macOS 26 では smc sampler は削除されており die temperature を powermetrics から直接取れない。
# thermal_pressure (nominal/moderate/heavy/critical) を throttling proxy に、
# CPU/GPU power を発熱 proxy にする。
SAMPLERS="thermal,cpu_power,gpu_power"

start_bg() {
    local out="$1"
    [ -f "$PIDFILE" ] && kill -0 "$(cat $PIDFILE)" 2>/dev/null && {
        echo "already running (pid $(cat $PIDFILE))"; exit 1
    }
    # sudo -n = 非対話 (キャッシュされてなければ失敗)。事前に一度 sudo -v が必要
    sudo -n powermetrics --samplers "$SAMPLERS" -i "$INTERVAL_MS" \
        -f plist > "$out" 2>&1 &
    local pid=$!
    echo $pid > "$PIDFILE"
    echo "started thermal_monitor pid=$pid → $out"
}

stop_bg() {
    if [ -f "$PIDFILE" ]; then
        local pid=$(cat "$PIDFILE")
        if kill -0 "$pid" 2>/dev/null; then
            sudo kill "$pid" 2>/dev/null
            echo "stopped pid=$pid"
        fi
        rm -f "$PIDFILE"
    else
        echo "no PID file"
    fi
}

summary() {
    local log="$1"
    python3 <<PY
import plistlib, statistics
from collections import Counter
from pathlib import Path

log = Path("$log")
raw = log.read_bytes()
# powermetrics -f plist は 複数の <plist>...</plist> を \n\x00 区切りで連結して書き出す
chunks = raw.split(b'</plist>')
chunks = [c + b'</plist>' for c in chunks if b'<plist' in c]
# 先頭の \n\x00 を除去
chunks = [c.lstrip(b'\n\x00') for c in chunks]

thermal_pressures = []       # Nominal / Moderate / Heavy / Critical (throttling level)
cpu_power_mW = []            # processor.cpu_power (mW)
gpu_power_mW = []            # processor.gpu_power (mW)
combined_power_mW = []       # processor.combined_power (mW, CPU+GPU+ANE)
ok = 0
for c in chunks:
    try:
        d = plistlib.loads(c)
        ok += 1
    except Exception:
        continue
    tp = d.get("thermal_pressure")
    if tp:
        thermal_pressures.append(tp)
    proc = d.get("processor", {}) or {}
    if "cpu_power" in proc:      cpu_power_mW.append(proc["cpu_power"])
    if "gpu_power" in proc:      gpu_power_mW.append(proc["gpu_power"])
    if "combined_power" in proc: combined_power_mW.append(proc["combined_power"])

def _stat(name, arr, unit=""):
    if not arr:
        print(f"  {name:<22} n=0 (not sampled)")
        return
    print(f"  {name:<22} n={len(arr)}  min={min(arr):.0f}{unit}  avg={statistics.mean(arr):.0f}{unit}  max={max(arr):.0f}{unit}")

print(f"=== summary: $log ({ok}/{len(chunks)} samples parsed) ===")
if thermal_pressures:
    c = Counter(thermal_pressures)
    total = sum(c.values())
    breakdown = ", ".join(f"{k}={v} ({v*100/total:.0f}%)" for k, v in c.most_common())
    print(f"  thermal_pressure       {breakdown}")
else:
    print("  thermal_pressure       n=0 (not sampled)")
_stat("CPU power (mW)", cpu_power_mW)
_stat("GPU power (mW)", gpu_power_mW)
_stat("Combined power (mW)", combined_power_mW)
PY
}

case "${1:-}" in
    --start)  start_bg "${2:-thermal.plist}" ;;
    --stop)   stop_bg ;;
    --summary) summary "${2:-thermal.plist}" ;;
    "" | -h | --help) sed -n '2,10p' "$0" | sed 's/^# //; s/^#//' ;;
    *)
        # foreground
        sudo powermetrics --samplers "$SAMPLERS" -i "$INTERVAL_MS" \
            -f plist > "$1"
        ;;
esac

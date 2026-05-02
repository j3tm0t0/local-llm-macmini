#!/bin/bash
# 1 モデルを完走させる: サーバ停止 → 新モデルでサーバ起動 → claude /quit & 再起動 → fixtures reset → T2〜T5
# Usage: ./run_one_model.sh <model_repo> [pane]
set -e
MODEL="${1:?Usage: $0 <model_repo> [pane]}"
PANE="${2:-0:5.1}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT=8000
LOG="/tmp/vllm-mlx-server.log"

echo "===== run_one_model: $MODEL ====="
echo "$(date)"

# 1. サーバ停止
echo "[1/5] stop existing vllm-mlx server"
pkill -f "vllm-mlx serve" 2>/dev/null || true
sleep 3
while pgrep -f "vllm-mlx serve" >/dev/null 2>&1; do sleep 1; done

# 2. 新モデルでサーバ起動
echo "[2/5] start vllm-mlx with $MODEL"
nohup "$ROOT/scripts/start_server.sh" "$MODEL" "$PORT" > "$LOG" 2>&1 &
disown $! 2>/dev/null || true
until curl -fs "http://localhost:$PORT/v1/models" >/dev/null 2>&1; do
    if ! pgrep -f "vllm-mlx serve" >/dev/null; then
        echo "ERROR: server died. tail of log:"
        tail -40 "$LOG"
        exit 1
    fi
    sleep 3
done
echo "  server ready"

# 3. claude /quit & cd & 再起動
echo "[3/5] restart claude in pane $PANE with $MODEL"
tmux send-keys -t "$PANE" C-c
sleep 1
tmux send-keys -t "$PANE" '/quit' Enter
sleep 4
tmux send-keys -t "$PANE" "cd $ROOT" Enter
sleep 1
tmux send-keys -t "$PANE" "claude --model $MODEL --permission-mode bypassPermissions" Enter
sleep 10  # let UI render

# 4. fixtures reset
echo "[4/5] reset fixtures"
"$ROOT/scripts/reset_fixtures.sh"

# 5. T2-T5
echo "[5/5] run T2-T5"
COOLDOWN="${COOLDOWN:-45}" "$ROOT/tests/run_practical.sh" "$MODEL" "$PANE"

echo "===== done: $MODEL ====="
echo "$(date)"

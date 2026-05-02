#!/bin/bash
# 実践テスト: 指定モデルで T2〜T5 を連続実行
# Usage: ./run_practical.sh <model_name>
# Claude Code を対話的に起動し、send-keys でプロンプトを投入する

MODEL="${1:?Usage: $0 <model_name>}"
PANE="${2:-0:local-llm}"
LOGDIR="$(cd "$(dirname "$0")/.." && pwd)/results"
mkdir -p "$LOGDIR"
LOGFILE="$LOGDIR/practical_$(echo "$MODEL" | tr ':/' '__').log"

echo "=== Practical test for $MODEL ===" | tee "$LOGFILE"
echo "Start: $(date)" | tee -a "$LOGFILE"

# Helper: send prompt, wait for completion, capture result
run_test() {
    local test_id="$1"
    local prompt="$2"

    echo "" | tee -a "$LOGFILE"
    echo "--- $test_id ---" | tee -a "$LOGFILE"
    echo "Prompt: $prompt" | tee -a "$LOGFILE"

    # Snapshot the previous timing line (if any) so we can detect a NEW one
    local prev_timing
    prev_timing=$(tmux capture-pane -t "$PANE" -p -S -200 2>&1 | grep -oE "✻ [A-Z][a-zA-Zé]+ for [0-9]+[ms].*" | tail -1)

    local start_sec=$SECONDS

    # Send prompt
    tmux send-keys -t "$PANE" "$prompt"
    sleep 1
    tmux send-keys -t "$PANE" Enter

    # Wait until a NEW timing line (different from prev_timing) appears in the visible tail
    sleep 5
    local waited=5
    local cur=""
    while true; do
        cur=$(tmux capture-pane -t "$PANE" -p 2>&1 | grep -oE "✻ [A-Z][a-zA-Zé]+ for [0-9]+[ms].*" | tail -1)
        if [ -n "$cur" ] && [ "$cur" != "$prev_timing" ]; then
            break
        fi
        sleep 5
        waited=$((waited + 5))
        if [ $waited -gt 600 ]; then
            echo "TIMEOUT after 600s (prev_timing=$prev_timing, last_seen=$cur)" | tee -a "$LOGFILE"
            return 1
        fi
    done

    local elapsed=$((SECONDS - start_sec))

    # Capture result
    local result
    result=$(tmux capture-pane -t "$PANE" -p -S -200 2>&1)

    local timing="$cur"

    echo "Elapsed: ${elapsed}s" | tee -a "$LOGFILE"
    echo "Timing: $timing" | tee -a "$LOGFILE"
    echo "$result" >> "$LOGFILE"
    echo "---" >> "$LOGFILE"
}

# テスト間クールダウン (秒)。GPU 温度を下げて熱スロットリング回避
COOLDOWN="${COOLDOWN:-45}"
cooldown() {
    if [ "$COOLDOWN" -gt 0 ]; then
        echo "[cooldown ${COOLDOWN}s]" | tee -a "$LOGFILE"
        sleep "$COOLDOWN"
    fi
}

# T2: Bug fix
run_test "T2_bugfix" "Read the file tests/T2_buggy.py, identify the bug(s), fix them in-place, and run the fixed version. Show the corrected output. Be concise."
cooldown

# T3: Multi-file project
run_test "T3_multifile" "Create a small Python package called calc with: 1) calc/__init__.py that exports add and multiply, 2) calc/ops.py with the actual functions, 3) test_calc.py that imports from calc and runs 3 assertions. Run the test and show results."
cooldown

# T4: Refactoring
run_test "T4_refactor" "Read tests/T4_messy.py, refactor it to remove code duplication and improve readability. Keep the same behavior. Run the original and refactored versions to verify output matches."
cooldown

# T5: CLI tool with error handling
run_test "T5_cli" "Create a CLI tool wc_tool.py that takes a filename argument, prints line/word/char counts like the wc command. Handle the case where the file does not exist with a friendly error message. Test it on tests/T2_buggy.py and on a nonexistent file called nope.txt."

echo "" | tee -a "$LOGFILE"
echo "=== All tests done ===" | tee -a "$LOGFILE"
echo "End: $(date)" | tee -a "$LOGFILE"
echo "Log: $LOGFILE"

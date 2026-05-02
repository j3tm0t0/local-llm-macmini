#!/bin/bash
#
# 実践ベンチマーク: 3モデル比較 (T2〜T5)
# 別ターミナルから実行:
#   bash /Users/moto/tmp/claude-code-local-llm/run_all_practical.sh
#
# 所要時間目安: 20〜40分 (3モデル × 4テスト)

set -uo pipefail

export ANTHROPIC_AUTH_TOKEN=ollama
export ANTHROPIC_API_KEY=""
export ANTHROPIC_BASE_URL=http://localhost:11434

WORKDIR=/Users/moto/tmp/claude-code-local-llm
RESULTS="$WORKDIR/results"
mkdir -p "$RESULTS"

MODELS=(
    "qwen3.6:35b-a3b-coding-nvfp4"
    "qwen3.6:35b-a3b-coding-mxfp8"
    "gpt-oss:20b"
)

PROMPTS=(
    'T2|Read the file tests/T2_buggy.py, identify the bug(s), fix them in-place, and run the fixed version. Show the corrected output. Be concise.'
    'T3|Create a small Python package called calc with: 1) calc/__init__.py that exports add and multiply, 2) calc/ops.py with the actual functions, 3) test_calc.py that imports from calc and runs 3 assertions. Run the test and show results.'
    'T4|Read tests/T4_messy.py, refactor it to remove code duplication and improve readability. Keep the same behavior. Run the original and refactored versions to verify output matches.'
    'T5|Create a CLI tool wc_tool.py that takes a filename argument, prints line/word/char counts. Handle the case where the file does not exist with a friendly error message. Test it on tests/T2_buggy.py and on a nonexistent file called nope.txt.'
)

# T2_buggy.py のオリジナル (バグ版) を毎回復元する用
BUGGY_ORIGINAL='def factorial(n):
    if n == 0:
        return 0
    return n * factorial(n - 1)


def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


if __name__ == "__main__":
    print(f"factorial(5) = {factorial(5)}")
    print(f"factorial(0) = {factorial(0)}")
    print(f"fibonacci(7) = {fibonacci(7)}")'

clean_workdir() {
    find "$WORKDIR" -maxdepth 1 -name '*.py' -delete 2>/dev/null || true
    rm -rf "$WORKDIR/calc" 2>/dev/null || true
    # T2_buggy.py をバグ版に復元
    echo "$BUGGY_ORIGINAL" > "$WORKDIR/tests/T2_buggy.py"
}

echo "============================================"
echo "  実践ベンチマーク 3モデル比較"
echo "  $(date)"
echo "============================================"
echo ""

for MODEL in "${MODELS[@]}"; do
    MODEL_SLUG=$(echo "$MODEL" | tr ':/' '__')
    MODEL_DIR="$RESULTS/$MODEL_SLUG"
    mkdir -p "$MODEL_DIR"

    echo "========================================"
    echo "MODEL: $MODEL"
    echo "========================================"

    # モデルを事前ウォームアップ (最初のリクエストのロード時間を除外)
    echo "  Warming up model..."
    curl -s -X POST http://localhost:11434/v1/messages \
      -H "Content-Type: application/json" \
      -H "anthropic-version: 2023-06-01" \
      -d "{\"model\":\"$MODEL\",\"max_tokens\":5,\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}]}" > /dev/null 2>&1
    echo "  Warm."

    for ENTRY in "${PROMPTS[@]}"; do
        TEST_ID="${ENTRY%%|*}"
        PROMPT="${ENTRY#*|}"
        OUTFILE="$MODEL_DIR/${TEST_ID}.txt"

        echo ""
        echo "  --- $TEST_ID ---"
        clean_workdir

        START=$(date +%s)

        if timeout 300 claude --model "$MODEL" \
            --permission-mode bypassPermissions \
            --no-session-persistence \
            --print "$PROMPT" > "$OUTFILE" 2>&1; then
            STATUS="OK"
        else
            RC=$?
            if [ $RC -eq 124 ]; then
                STATUS="TIMEOUT"
                echo "  TIMEOUT (300s)" >> "$OUTFILE"
            else
                STATUS="EXIT_$RC"
            fi
        fi

        END=$(date +%s)
        ELAPSED=$((END - START))

        echo "  $TEST_ID: ${STATUS} (${ELAPSED}s)"
        echo "${TEST_ID}:${ELAPSED}s:${STATUS}" >> "$MODEL_DIR/times.txt"
    done

    # モデルアンロード
    echo ""
    echo "  Unloading $MODEL..."
    curl -s -X POST http://localhost:11434/api/generate \
        -d "{\"model\":\"$MODEL\",\"keep_alive\":0}" > /dev/null 2>&1
    sleep 3
    echo ""
done

echo "============================================"
echo "  全テスト完了: $(date)"
echo "============================================"
echo ""
echo "=== タイミングまとめ ==="
for MODEL in "${MODELS[@]}"; do
    MODEL_SLUG=$(echo "$MODEL" | tr ':/' '__')
    echo ""
    echo "[$MODEL]"
    cat "$RESULTS/$MODEL_SLUG/times.txt" 2>/dev/null || echo "(no results)"
done
echo ""
echo "結果は $RESULTS/ に保存されています。"
echo "Claude Code セッションに戻ってレポートを生成してください。"

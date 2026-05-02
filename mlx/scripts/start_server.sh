#!/bin/bash
# vllm-mlx サーバ起動 (Anthropic /v1/messages 互換)
# Usage: ./start_server.sh <model> [port]
# 例: ./start_server.sh mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit-DWQ 8000

set -e
MODEL="${1:?Usage: $0 <model> [port]}"
PORT="${2:-8000}"

# Tool パーサ & reasoning パーサ自動判定
REASON_PARSER=""
case "$MODEL" in
    *Qwen3-Coder*|*qwen3-coder*) PARSER="qwen3_coder" ;;
    *gpt-oss*|*Harmony*)
        PARSER="harmony"
        REASON_PARSER="gpt_oss"  # reasoning channel を tool_use と分離
        ;;
    *Qwen3*|*Qwen3.6*|*qwen3*)
        PARSER="qwen"
        REASON_PARSER="qwen3"
        ;;
    *) PARSER="auto" ;;
esac

echo "=== vllm-mlx serve ==="
echo "Model: $MODEL"
echo "Port:  $PORT"
echo "Tool parser: $PARSER"
echo "Reasoning parser: ${REASON_PARSER:-<none>}"
echo

REASON_FLAG=""
if [ -n "$REASON_PARSER" ]; then
    REASON_FLAG="--reasoning-parser $REASON_PARSER"
fi

exec vllm-mlx serve "$MODEL" \
    --port "$PORT" \
    --host 127.0.0.1 \
    --enable-auto-tool-choice \
    --tool-call-parser "$PARSER" \
    $REASON_FLAG \
    --enable-prefix-cache

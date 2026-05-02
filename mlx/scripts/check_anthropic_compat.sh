#!/bin/bash
# vllm-mlx の Anthropic /v1/messages 互換動作チェック
# Usage: ./check_anthropic_compat.sh [port]
PORT="${1:-8000}"

# 起動中モデルを /v1/models から自動取得
MODEL=$(curl -s "http://localhost:${PORT}/v1/models" | python3 -c 'import sys,json; print(json.load(sys.stdin)["data"][0]["id"])' 2>/dev/null)
if [ -z "$MODEL" ]; then echo "FAIL: cannot reach server"; exit 1; fi
echo "Detected model: $MODEL"
echo

echo "=== /v1/models ==="
curl -s "http://localhost:${PORT}/v1/models" | python3 -m json.tool || echo "FAIL: /v1/models"

echo
echo "=== /v1/messages (text only) ==="
curl -s -X POST "http://localhost:${PORT}/v1/messages" \
    -H 'Content-Type: application/json' \
    -H 'x-api-key: mlx' \
    -H 'anthropic-version: 2023-06-01' \
    -d '{
        "model": "'"$MODEL"'",
        "max_tokens": 64,
        "messages": [{"role": "user", "content": "Reply with the single word PONG."}]
    }' | python3 -m json.tool || echo "FAIL: /v1/messages basic"

echo
echo "=== /v1/messages (tool_use) ==="
curl -s -X POST "http://localhost:${PORT}/v1/messages" \
    -H 'Content-Type: application/json' \
    -H 'x-api-key: mlx' \
    -H 'anthropic-version: 2023-06-01' \
    -d '{
        "model": "'"$MODEL"'",
        "max_tokens": 256,
        "tools": [{
            "name": "get_weather",
            "description": "Get weather for a city.",
            "input_schema": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"]
            }
        }],
        "messages": [{"role": "user", "content": "What is the weather in Tokyo? Use the tool."}]
    }' | python3 -m json.tool || echo "FAIL: /v1/messages tool_use"

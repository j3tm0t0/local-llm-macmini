#!/bin/bash
# Claude Code を vllm-mlx ローカルサーバ向けに起動
# Usage: ./local_claude.sh <model> [port]
# 例: ./local_claude.sh mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit-DWQ 8000

MODEL="${1:?Usage: $0 <model> [port]}"
PORT="${2:-8000}"

export ANTHROPIC_BASE_URL="http://localhost:${PORT}"
export ANTHROPIC_AUTH_TOKEN="mlx"
export ANTHROPIC_API_KEY=""

exec claude --model "$MODEL" --permission-mode bypassPermissions

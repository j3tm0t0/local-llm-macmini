# local-llm-macmini

Mac 上で **Claude Code** をローカル LLM (Ollama / MLX / ds4) で動かす検証の、**スクリプト・設定・計測ログ** を収めたリポジトリ。

📡 **検証結果と解説**: <https://j3tm0t0.github.io/local-llm-macmini/>

検証時の環境 (再現用):

- 現行 (2026-07): **MacBook Pro M5 Max / 128GB / macOS 26.5.2 / Claude Code v2.1.207 / Ollama 0.31.2 / vllm-mlx 0.4.0 / ds4 build 2026-07-13**
- 参考 (2026-05): Mac mini M4 Pro / 14 cores / 64GB / macOS 25.4 / Claude Code v2.1.126 / Ollama 0.22.1 / vllm-mlx 0.2.9 / robustonian/mlx-lm `feature/anthropic-compat-api` (mlx 0.30.6)

## ディレクトリ構成

| パス | 内容 |
|---|---|
| [`ollama/`](ollama/) | Ollama 経由の検証一式 (`run_all_practical.sh` + tmux 駆動 runner + T2/T4 fixture) |
| [`mlx/`](mlx/) | MLX 経由の検証一式 (vllm-mlx 起動・claude 起動・互換スモーク・fixtures reset・1 モデル完走 pipeline) |
| [`reference/results/`](reference/results/) | Anthropic クラウド版 (Opus 4.7 / Sonnet 4.6) の T2-T5 計測ログ (M4 Pro 世代) |
| [`scripts/generate_chart.py`](scripts/generate_chart.py) | 比較チャート生成 (`uv` inline-deps、`./scripts/generate_chart.py` で再生成) |
| [`docs/`](docs/) | GitHub Pages 用 Jekyll サイトのソース (just-the-docs テーマ)。詳細はこちら |

## ライセンス

[Apache License 2.0](LICENSE)

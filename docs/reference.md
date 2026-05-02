---
title: 参考 - クラウド版 (Opus 4.7 / Sonnet 4.6)
layout: default
nav_order: 6
---

# 参考: Anthropic 標準モデル (Opus 4.7 / Sonnet 4.6)

ローカル LLM の速度感を「現実的なベースライン」と比較するため、**同一テストスイート T2-T5・同一マシン (Mac mini M4 Pro)・同一 tmux send-keys 駆動**で Anthropic クラウド版を計測した。

## 計測条件

- ペイン: 検証セッションの直下に `tmux split-window -v` で作成
- 環境変数: `ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN` / `ANTHROPIC_API_KEY` をすべて unset → Claude Max の標準認証
- 起動: `claude --model claude-opus-4-7 --permission-mode bypassPermissions` / `claude --model claude-sonnet-4-6 --permission-mode bypassPermissions`
- Runner: `mlx/tests/run_practical.sh` をそのまま流用 (cooldown は API なので 5s に短縮)
- ログ: [reference/results/](https://github.com/j3tm0t0/local-llm-macmini/tree/main/reference/results) 配下に保管

## タスク別タイミング

| タスク | Opus 4.7 | Sonnet 4.6 |
|---|---|---|
| T2 バグ修正 (`factorial(0)` を `1` に修正) | 16s (Sautéed for 13s) | 16s (Cooked for 14s) |
| T3 マルチファイル package (`calc/` + test) | 27s (Churned for 20s) | 21s (Crunched for 18s) |
| T4 リファクタ (3 関数の重複除去 + 動作確認) | 26s (Sautéed for 24s) | 27s (Cogitated for 21s) |
| T5 CLI + エラーハンドリング (`wc_tool.py`) | 21s (Churned for 16s) | 16s (Cooked for 13s) |
| **累計** | **1m30s (90s)** | **1m20s (80s)** |
| 全 artifact 検証 | ✅ | ✅ |

## ローカル LLM との速度比 (Sonnet 4.6 = 1.00x)

| ベース | 累計 | Sonnet 4.6 比 |
|---|---|---|
| Sonnet 4.6 (クラウド) | 80s | 1.00x |
| Opus 4.7 (クラウド) | 90s | 1.13x |
| Ollama nvfp4 (ローカル最良) | 333s | **4.2x 遅い** |
| MLX UD-4bit (MLX 最良) | 585s | **7.3x 遅い** |
| Ollama gpt-oss:20b | 662s | 8.3x |
| MLX robustonian fork | 1106s | 13.8x |

## 観察

- **Opus 4.7 と Sonnet 4.6 は今回の T2-T5 では誤差レベルの差**。Sonnet がわずかに速いのは生成トークンが軽快なため。これくらいの粒度の素直なコーディングタスクでは差が出にくい。
- **クラウド版は「やる気だけ問題」を起こさない**。tool block を確実に発火し、artifact が決定論的に作られる。ローカル LLM 検証で発見した `qwen3:30b-instruct` / `gpt-oss-20b-MXFP4-Q4` 系の空走は Anthropic クラウドでは観測されず、これは商用モデルの基本品質として期待できる。
- **ローカルでは 4-13 倍遅い**。Mac mini M4 Pro でローカル LLM を選ぶ動機は「速度」では成立せず、**機密データ / オフライン / 課金回避 / 学習価値** に依存することが定量的に裏付けられた。

## 再現方法

```bash
# 1. ベンチ用ディレクトリ
mkdir -p ~/tmp/cc-reference-bench/{tests,scripts,results}
cp mlx/tests/run_practical.sh        ~/tmp/cc-reference-bench/tests/
cp mlx/scripts/reset_fixtures.sh     ~/tmp/cc-reference-bench/scripts/
~/tmp/cc-reference-bench/scripts/reset_fixtures.sh

# 2. tmux で下に pane を作って Claude Code (Anthropic 認証) 起動
tmux split-window -v -c ~/tmp/cc-reference-bench
# 新 pane で:
unset ANTHROPIC_BASE_URL ANTHROPIC_AUTH_TOKEN ANTHROPIC_API_KEY
claude --model claude-opus-4-7 --permission-mode bypassPermissions

# 3. 元 pane から runner を起動 (PANE は新 pane の番号)
cd ~/tmp/cc-reference-bench
COOLDOWN=5 ./tests/run_practical.sh claude-opus-4-7 0:4.1

# 4. Sonnet も同様に
~/tmp/cc-reference-bench/scripts/reset_fixtures.sh
# 新 pane で `/quit` → claude --model claude-sonnet-4-6 --permission-mode bypassPermissions
COOLDOWN=5 ./tests/run_practical.sh claude-sonnet-4-6 0:4.1
```

## 計測ログ (raw)

GitHub リポジトリに保管しています。

| ファイル | 内容 |
|---|---|
| [`runner_claude-opus-4-7.log`](https://github.com/j3tm0t0/local-llm-macmini/blob/main/reference/results/runner_claude-opus-4-7.log) | Opus 4.7 のタイミングサマリ (1.4 KB) |
| [`runner_claude-sonnet-4-6.log`](https://github.com/j3tm0t0/local-llm-macmini/blob/main/reference/results/runner_claude-sonnet-4-6.log) | Sonnet 4.6 のタイミングサマリ (1.4 KB) |
| [`practical_claude-opus-4-7.log`](https://github.com/j3tm0t0/local-llm-macmini/blob/main/reference/results/practical_claude-opus-4-7.log) | Opus 4.7 のフル tmux キャプチャ (33 KB) |
| [`practical_claude-sonnet-4-6.log`](https://github.com/j3tm0t0/local-llm-macmini/blob/main/reference/results/practical_claude-sonnet-4-6.log) | Sonnet 4.6 のフル tmux キャプチャ (55 KB) |

---

[Source on GitHub](https://github.com/j3tm0t0/local-llm-macmini/tree/main/reference){: .btn .btn-outline }

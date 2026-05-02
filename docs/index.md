---
title: "Claude Code、ローカル LLM でどこまで戦える？"
layout: default
nav_order: 1
description: "Mac mini M4 Pro 64GB で Ollama / MLX / Anthropic クラウドを T2-T5 同条件で徹底比較。常用はやはり厳しいが、Claude が落ちている時の避難先としてなら成立する"
permalink: /
---

# Claude Code、ローカル LLM でどこまで戦える？
{: .fs-9 }

Mac mini M4 Pro 64GB で Ollama / MLX / Anthropic クラウドを T2-T5 同条件で徹底比較。<br>
**結論: クラウド比 4〜13 倍遅い。常用は厳しいが、Claude が落ちている時の避難先としては成立する。**
{: .fs-5 .fw-300 }

---

Mac mini M4 Pro (64GB) で **Claude Code** をローカル LLM で動かすための検証結果・設定・スクリプト集。
Ollama 版と MLX (vllm-mlx / robustonian-mlx-lm) 版を **同一テストスイート** (T2-T5) で突き合わせている。

> **GitHub リポジトリ**: [j3tm0t0/local-llm-macmini](https://github.com/j3tm0t0/local-llm-macmini)
> 各ページ末尾の "Source" リンクから元の Markdown / シェルスクリプトに直接アクセスできます。

- 検証日: 2026-05-02
- ハードウェア: Mac mini M4 Pro / 14 cores (10P+4E) / 64GB unified memory / macOS 25.4 系
- Claude Code: v2.1.126
- Ollama: v0.22.1 (Anthropic Messages API ネイティブ互換あり)
- MLX サーバ: vllm-mlx 0.2.9 / robustonian/mlx-lm `feature/anthropic-compat-api` (mlx 0.30.6)

---

## TL;DR

- **総合一位は Ollama nvfp4**: `qwen3.6:35b-a3b-coding-nvfp4` (21GB) が T2-T5 を **5m33s** で全クリア。tool 互換 / 速度 / 省メモリの三拍子で現状の本命。
- **MLX は今のところ Ollama より遅い**: 同等量子化の `unsloth/Qwen3.6-35B-A3B-UD-MLX-4bit` (20GB) で 9m45s。Apple Silicon ネイティブ MLX への素朴な期待 (Ollama より速いはず) は今回の vllm-mlx 0.2.9 構成では裏切られた。
- **Tool 互換性はサーバ × モデルの組み合わせ次第**: Qwen3-Coder 30B は **Ollama では失敗・MLX では救済**、gpt-oss 20b は **Ollama で動作・MLX で空走** と逆転する。
- **新たな地雷タイプ「やる気だけモデル」**: Ollama の `qwen3:30b-instruct` と MLX の `gpt-oss-20b-MXFP4-Q4` は、tool block を一切発火せず自然文で「完了」を宣言する。ベンチ数字だけ見ると最速に見えるが artifact ゼロ。**`ls` で確認しないと騙される**。
- **参考: Anthropic 標準モデル**: 同じテストを Claude Code + クラウド版 **Opus 4.7 で 90s / Sonnet 4.6 で 80s** で完走。Sonnet 4.6 比でローカル最良 (Ollama nvfp4) は 4.2x、MLX 最良は 7.3x 遅い。詳細は [参考ページ](reference.md)。

---

## 統合サマリー (T2-T5 累計)

![モデル比較チャート](assets/model-comparison.png)

> 図: T2-T5 累計時間 (秒) を横軸、モデルを縦軸に並べた横棒グラフ。
> 青 = Anthropic クラウド / 緑 = Ollama / オレンジ = MLX / 赤の斜線 = artifact 0/4 の「やる気だけ型空走」。
> 青の破線が Sonnet 4.6 ベースライン (80s)。

T2 バグ修正 / T3 マルチファイルパッケージ / T4 リファクタ / T5 CLI + エラーハンドリングの 4 タスクを Claude Code 対話セッションで連続実行した結果。

| バックエンド | モデル | サイズ | 累計 | Tool 発火 | 全クリア | 備考 |
|---|---|---|---|---|---|---|
| Anthropic クラウド | **Claude Sonnet 4.6** *(参考)* | (API) | **1m20s** | ✅ | ✅✅✅✅ | ⭐ 速度上限の参考値 |
| Anthropic クラウド | **Claude Opus 4.7** *(参考)* | (API) | **1m30s** | ✅ | ✅✅✅✅ | ⭐ 速度上限の参考値 |
| Ollama | **qwen3.6:35b-a3b-coding-nvfp4** | 21GB | **5m33s** | ✅ | ✅✅✅✅ | ⭐ ローカル総合本命 |
| Ollama | qwen3.6:35b-a3b-coding-mxfp8 | 37GB | 6m06s | ✅ | ✅✅✅✅ | nvfp4 比 +10% で精度上振れ |
| Ollama | gpt-oss:20b | 13GB | 11m02s | ✅ | ✅✅✅✅ | 安定動作・軽量機向け |
| Ollama | qwen3:30b-instruct | 18GB | (3m05s) | ❌ | 0/4 | **「やる気だけ」型空走** |
| MLX (vllm-mlx) | **unsloth/Qwen3.6-35B-A3B-UD-MLX-4bit** | 20GB | 9m45s | ✅ | ✅✅✅✅ | ⭐ MLX 第一候補 |
| MLX (vllm-mlx) | mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit-DWQ | 16GB | 22m36s | ✅ | △ T5 タイムアウト | Ollama では XML 漏れで失敗 |
| MLX (robustonian) | mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit-DWQ | 16GB | **18m26s** | ✅ | ✅✅✅✅ | vllm-mlx 比 18% 速い |
| MLX (vllm-mlx) | mlx-community/gpt-oss-20b-MXFP4-Q4 | 10GB | (4m30s) | ❌ | 0/4 | **harmony parser 不全による空走** |
| MLX (vllm-mlx) | unsloth/Qwen3.6-27B-MLX-8bit | 30GB | DNF | (T2 のみ ✅) | ❌ | dense 8bit はメモリ帯域飽和で対話実用外 |

カッコ付きの累計は「`ls` で artifact が確認できない」/「タスク完了せず短時間で idle に戻った」見せかけの数字。**速度ランキングだけで判断してはいけない**。

### ローカル vs クラウドの速度比

| ベース | 累計 | Sonnet 4.6 比 |
|---|---|---|
| Sonnet 4.6 (クラウド) | 80s | 1.00x |
| Opus 4.7 (クラウド) | 90s | 1.13x |
| Ollama nvfp4 (ローカル最良) | 333s | **4.2x 遅い** |
| MLX UD-4bit (MLX 最良) | 585s | **7.3x 遅い** |
| Ollama gpt-oss:20b | 662s | 8.3x |
| MLX robustonian fork | 1106s | 13.8x |

ローカル LLM が Anthropic クラウド版に **速度で勝つ場面はない**。それでもローカルを選ぶ理由は「オフライン要件 / 機密データ / API 課金回避 / 学習価値」のいずれかに絞られる。「Mac mini で Claude Code 体験を高速化したい」だけならクラウド版を素直に使うのが最も合理的。

実用上の現実的な位置付けは、**「常用は厳しいが、Claude が落ちている時の避難先 (フォールバック) としてなら成立する」** あたり。OpenAI や Anthropic のサービス障害時に作業を止めない保険として、`local-claude` エイリアスを忍ばせておくのは悪くない投資。

---

## 用途別の推奨

| ユースケース | 推奨 |
|---|---|
| Claude Code をローカル LLM で本気運用 (一番楽) | **Ollama + qwen3.6:35b-a3b-coding-nvfp4** |
| VRAM 余裕 + 精度上振れ狙い (Ollama) | qwen3.6:35b-a3b-coding-mxfp8 (37GB) |
| RAM 16GB クラス / 並行作業優先 | Ollama + gpt-oss:20b |
| MLX を主軸に運用したい (qwen3.6 系) | **vllm-mlx + unsloth/Qwen3.6-35B-A3B-UD-MLX-4bit** |
| MLX で qwen3-coder 系を活かしたい | **robustonian/mlx-lm fork (mlx 0.30.6) + Qwen3-Coder-30B-A3B-Instruct-4bit-DWQ** (vllm-mlx 比 18% 速い、T5 完走) |
| gpt-oss 系を tool 込みで動かす | **Ollama 一択** (MLX 系はどちらも tool 互換が壊れている) |
| 速さに釣られると事故るので避ける | qwen3:30b-instruct (Ollama) / gpt-oss-20b-MXFP4-Q4・Q8 (MLX) |
| 旧世代地雷 (Claude Code 連携時) | qwen3-coder:30b (Ollama)・qwen2.5-coder:14b/32b (Ollama) — tool フォーマット漏れで全失敗 |

---

## クイックスタート

### Ollama 版 (一番楽)

```bash
# 1. モデル取得
ollama pull qwen3.6:35b-a3b-coding-nvfp4

# 2. Claude Code を Ollama に向ける (環境変数 3 つだけ)
export ANTHROPIC_AUTH_TOKEN=ollama   # 文字列 "ollama" で OK、認証なし
export ANTHROPIC_API_KEY=""
export ANTHROPIC_BASE_URL=http://localhost:11434

claude --model qwen3.6:35b-a3b-coding-nvfp4 --permission-mode bypassPermissions
```

`claude-code-router` などのプロキシは不要。Ollama 0.14+ に Anthropic Messages API 互換が組み込まれている。

### MLX 版 (vllm-mlx)

```bash
# 1. vllm-mlx 導入 + モデル取得 (HF からの自動 pull)
uv tool install vllm-mlx

# 2. サーバ起動 (tool パーサ自動判定の wrapper を同梱)
./mlx/scripts/start_server.sh unsloth/Qwen3.6-35B-A3B-UD-MLX-4bit 8000

# 3. 別シェルで Claude Code を MLX に向ける
./mlx/scripts/local_claude.sh unsloth/Qwen3.6-35B-A3B-UD-MLX-4bit 8000
```

スクリプト本体: [mlx/scripts/](https://github.com/j3tm0t0/local-llm-macmini/tree/main/mlx/scripts)

### MLX 版 (robustonian fork、Qwen3-Coder 系最速)

```bash
# qwen3_5_moe (Qwen3.6) アーキテクチャは未対応。Qwen3-Coder 系のみ対応
uv venv --python 3.12 robustonian-env && cd robustonian-env
uv pip install "git+https://github.com/robustonian/mlx-lm.git@feature/anthropic-compat-api"
# !!! upstream MLX 0.31.x のスレッドバグ回避で 0.30.6 に固定
uv pip install "mlx==0.30.*" "mlx-metal==0.30.*"

.venv/bin/python -m mlx_lm server \
  --model mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit-DWQ \
  --host 127.0.0.1 --port 8080 --max-tokens 32000
```

---

## 共通エイリアス (~/.zshrc 用)

```bash
local-claude() {
  export ANTHROPIC_AUTH_TOKEN=ollama
  export ANTHROPIC_API_KEY=""
  export ANTHROPIC_BASE_URL=http://localhost:11434
  claude --model "${1:-qwen3.6:35b-a3b-coding-nvfp4}" \
         --permission-mode bypassPermissions "${@:2}"
}
```

`local-claude` で本命起動、`local-claude gpt-oss:20b` で軽量切替。

### モデル切替時の GPU メモリ即時解放 (Ollama)

```bash
curl -s -X POST http://localhost:11434/api/generate \
  -d '{"model":"qwen3.6:35b-a3b-coding-nvfp4","keep_alive":0}'
```

### コンテキスト拡張 (Ollama / macOS App)

```bash
launchctl setenv OLLAMA_CONTEXT_LENGTH 131072
# 再起動後反映。Claude Code は履歴がすぐ太るので 128K は欲しい
```

---

## 検証で得た 4 つの教訓

1. **Ollama 0.22.1+ は Anthropic Messages API ネイティブ互換**。プロキシ不要、環境変数 3 つで Claude Code 直結。
2. **Tool 互換性は「モデル単体」では決まらない**。同じ `Qwen3-Coder-30B-A3B-Instruct-4bit-DWQ` でも、Ollama なら XML 生テキスト漏れで全失敗、MLX (vllm-mlx の `qwen3_coder` パーサ経由) なら正常発火する。逆に gpt-oss:20b は Ollama では完璧、MLX では完全空走。**サーバ × モデル × 量子化フォーマット × parser 実装の組み合わせ全部に依存する**。
3. **「やる気だけモデル」は最も危険な失敗モード**。XML / JSON が画面に漏れる従来型不一致 (qwen3-coder 系の旧症状) は一目で気付くが、`Let me read the file...` と宣言した直後 idle に戻り、自然文だけ綺麗に出力するパターンは **ベンチ数字上は最速に見える**。Ollama の `qwen3:30b-instruct` と MLX の `gpt-oss-20b-MXFP4-Q4` で発生。**ログ末尾の "Cooked for X" は仕事した保証にはならない。`ls` で artifact を必ず確認**。
4. **連続生成時のサーマルスロットリング**: M4 Pro は GPU が 10 秒で 92°C に達してスロットリング入りする。比較ベンチを取るなら **テスト間に 30〜60 秒のクールダウン**を挟むこと。MLX 版テストスクリプトでは 45s 固定で挿入している。

---

## ページ一覧

| ページ | 内容 |
|---|---|
| [参考: クラウド版 Opus 4.7 / Sonnet 4.6](reference.md) | 速度上限ベースライン・再現コマンド・raw ログへのリンク |

> 詳細レポート / ブログ調記事は当面公開停止中です (書き直し予定)。本ページの統合サマリーで主要な数字・推奨は確認できます。

---

## リポジトリ上の主要ファイル (GitHub 直リンク)

| 種類 | パス |
|---|---|
| Ollama 連続バッチ走者 | [ollama/run_all_practical.sh](https://github.com/j3tm0t0/local-llm-macmini/blob/main/ollama/run_all_practical.sh) |
| Ollama tmux 駆動 runner | [ollama/tests/run_practical.sh](https://github.com/j3tm0t0/local-llm-macmini/blob/main/ollama/tests/run_practical.sh) |
| MLX サーバ起動 (parser 自動判定) | [mlx/scripts/start_server.sh](https://github.com/j3tm0t0/local-llm-macmini/blob/main/mlx/scripts/start_server.sh) |
| MLX 1 モデル完走 pipeline | [mlx/scripts/run_one_model.sh](https://github.com/j3tm0t0/local-llm-macmini/blob/main/mlx/scripts/run_one_model.sh) |
| MLX Anthropic 互換スモーク | [mlx/scripts/check_anthropic_compat.sh](https://github.com/j3tm0t0/local-llm-macmini/blob/main/mlx/scripts/check_anthropic_compat.sh) |
| Fixture リセット | [mlx/scripts/reset_fixtures.sh](https://github.com/j3tm0t0/local-llm-macmini/blob/main/mlx/scripts/reset_fixtures.sh) |
| 共通プロンプト集 | [tests/practical_prompts.md](https://github.com/j3tm0t0/local-llm-macmini/blob/main/mlx/tests/practical_prompts.md) |
| クラウド版 raw ログ | [reference/results/](https://github.com/j3tm0t0/local-llm-macmini/tree/main/reference/results) |

---

## 参考リンク

- Ollama Anthropic 互換: <https://ollama.com/blog/anthropic-api>
- vllm-mlx: <https://github.com/waybarrios/vllm-mlx>
- robustonian/mlx-lm Anthropic 互換フォーク: <https://github.com/robustonian/mlx-lm/tree/feature/anthropic-compat-api>
- robustonian さん Zenn scrap: <https://zenn.dev/robustonian/scraps/6dde9d158346de>
- claude-code-local (MLX 駆動 Anthropic API サーバ): <https://github.com/nicedreamzapp/claude-code-local>
- LM Studio Anthropic 互換: <https://lmstudio.ai/docs/developer/anthropic-compat>

---

[Source on GitHub](https://github.com/j3tm0t0/local-llm-macmini/blob/main/README.md){: .btn .btn-outline }

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

## やったこと

Mac mini M4 Pro (M4 Pro / 64GB / macOS 25.4) に **Claude Code v2.1.126** を入れて、Anthropic クラウドではなくローカル LLM 経由で動かしたらどこまで戦えるかを試した。バックエンドは Ollama 0.22.1 (Anthropic Messages API ネイティブ互換あり) と MLX 系 2 種 (vllm-mlx 0.2.9 / robustonian-mlx-lm)。**比較対象は同じマシンで Anthropic クラウド版 (Opus 4.7 / Sonnet 4.6) も同じ tmux 駆動で計測**。

T2-T5 は全部同じプロンプト、ファイル fixture も同じ:

- **T2** バグ修正 (`factorial(0)` → `1` に直して実行)
- **T3** マルチファイル package 作成 (`calc/__init__.py` + `calc/ops.py` + `test_calc.py`)
- **T4** リファクタ (3 関数の重複除去 + 動作同一性確認)
- **T5** CLI ツール作成 (`wc_tool.py` + 存在しないファイルへのエラーハンドリング)

11 構成 (cloud 2 + Ollama 4 + MLX 5) を同じセッションで走らせて累計時間と artifact を比較。

![モデル比較チャート](assets/model-comparison.png)

---

## 3 つの発見

### 1. クラウド比 4〜13 倍遅い

Sonnet 4.6 が **80s** で T2-T5 を片付けるテストが、ローカル最良 (Ollama nvfp4) で **333s**、MLX 最良 (Qwen3.6-35B-A3B-UD-MLX-4bit) で **585s**。Apple Silicon ネイティブの MLX なら Ollama より速いはず、という素朴な期待は今回の vllm-mlx 0.2.9 構成では成立しなかった。

### 2. tool 互換性は「サーバ × モデル × parser」の組み合わせで決まる

同じ `Qwen3-Coder-30B-A3B-Instruct-4bit-DWQ` が **Ollama だと XML テキスト垂れ流しで全失敗、MLX (vllm-mlx の `qwen3_coder` parser 経由) だと正規発火で全成功** に逆転した。逆に `gpt-oss:20b` は **Ollama では完璧に動くのに MLX 系では tool block ゼロの完全空走**。モデル単体の性能だけ見て選ぶと事故る。

### 3.「やる気だけモデル」が一番怖い

`<function=Write>...` が画面に漏れる従来型の不一致は一目で気付くが、**`Let me read the file...` と宣言した直後 idle に戻り、自然文だけ綺麗に出力する** パターンは見落とす。Ollama の `qwen3:30b-instruct` と MLX の `gpt-oss-20b-MXFP4-Q4` で発生。何もしてないので速く見える (T2-T5 で 3m05s ! ) が artifact は 0/4。**ベンチ数字を信じる前に `ls` で生成ファイルを確認しないと騙される**。

---

## おまけ: 冷却ファンを置いたら劇的に変わった

Mac mini に外付けの静音ファンを横から当てて active cooling を効かせて再走行したところ、**MLX vllm-mlx + Qwen3-Coder DWQ の T5 verbose loop (10 分タイムアウト) が消えて累計 22m36s → 13m12s (-42%)**。Ollama gpt-oss:20b も -15%、軽いモデルでも -7%。Apple 純正の冷却機構は LLM 連続生成を想定していないらしい。

ただし robustonian fork は VRAM 16→38GB 肥大化のメモリ圧で逆効果 (+5%) とか、短い T2 タスクで一貫して +15% (cooldown 入れすぎペナルティ?) とか、構成依存の挙動も観測。

詳細データ → [冷却ファンセクション](details.md#冷却ファン投入で-thermal-throttling-を抑えるとどうなる)

---

## 結論

ローカル LLM が **速度で Anthropic クラウドに勝つ場面は無い**。「Mac mini で Claude Code 体験を高速化したい」だけなら素直にクラウド版を使うのが合理的。

それでもローカルを置く理由があるとすれば「機密データ / オフライン要件 / API 課金回避 / **Anthropic が落ちている時の避難先 (フォールバック保険)**」のいずれか。`local-claude` エイリアスを忍ばせて、いざ障害が来たとき切替えで作業を止めない、くらいの位置付けが現実的。

---

## もっと詳しく

- 📊 [**詳細データ・推奨モデル・運用 Tips**](details.md) — 全 11 構成の比較表、用途別推奨、クイックスタート (Ollama / MLX / robustonian)、共通エイリアス、4 つの教訓、冷却検証の詳細、クラウド版 (Opus 4.7 / Sonnet 4.6) のタスク別タイミング
- 🔧 [**GitHub リポジトリ**](https://github.com/j3tm0t0/local-llm-macmini) — スクリプト、テスト fixture、計測ログ、チャート生成コード

---

[Source on GitHub](https://github.com/j3tm0t0/local-llm-macmini){: .btn .btn-outline }

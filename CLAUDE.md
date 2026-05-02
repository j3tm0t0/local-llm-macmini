# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

This is **a benchmark / research artifact**, not a software project. There is no build, no lint, no application code — only:

- Markdown content (`docs/index.md`, `docs/reference.md`) — the long-form narrative + comparison table + chart
- Shell scripts that drive `claude` (Claude Code itself) via `tmux send-keys` against local LLM servers (Ollama / vllm-mlx / robustonian-mlx-lm) or Anthropic cloud
- Captured logs under `reference/results/`

The canonical narrative lives in **`docs/index.md`** (published at <https://j3tm0t0.github.io/local-llm-macmini/>). `README.md` is intentionally short — just a repo description + link to the site + directory map. Do not pad `README.md` back into an article; the user explicitly asked to keep it brief.

When you add a new measurement, update `docs/index.md` (and `docs/reference.md` if cloud-baseline). Then re-run `./scripts/generate_chart.py` to refresh `docs/assets/model-comparison.png`.

Note: detailed sub-reports (`ollama/REPORT.md` / `BLOG.md`, `mlx/REPORT.md` / `BLOG.md`) were intentionally **removed** from this repo (will be rewritten later). Do not re-add them without checking with the user.

## Hardware / version pinning is part of the data

Numbers in this repo are only meaningful in the documented context: Mac mini M4 Pro / 14 cores (10P+4E) / 64GB unified / macOS 25.4 系 / Claude Code v2.1.126 / Ollama v0.22.1 / vllm-mlx 0.2.9 / robustonian/mlx-lm `feature/anthropic-compat-api` (mlx 0.30.6). Do not delete or "tidy up" these version stamps — re-runs on different versions are a new measurement, not a correction.

## How a benchmark run actually works

Both `ollama/tests/run_practical.sh` and `mlx/tests/run_practical.sh` (and the cloud-baseline runs) follow the same pattern:

1. A separate tmux pane has `claude` running interactively (with `--permission-mode bypassPermissions`).
2. The runner script in another pane uses `tmux send-keys` to inject the T2-T5 prompts into that pane.
3. The runner detects completion by polling `tmux capture-pane -p` for Claude Code's `✻ Worked for / Cooked for / Sautéed for / ...` timing line and treating each new line as the previous test finishing.
4. **Fixtures (`tests/T2_buggy.py`, `tests/T4_messy.py`) live on disk and must be reset between models** — `mlx/scripts/reset_fixtures.sh` handles that. `ollama/run_all_practical.sh` resets inline because it uses `claude --print` (non-interactive) instead of tmux.

The 5 tasks (T1-T5) are defined in both `ollama/tests/practical_prompts.md` and `mlx/tests/practical_prompts.md` — they are identical. Only T2-T5 are timed in the comparison; T1 was the original tool-format smoke test.

## Critical methodology rule: verify with `ls`

The most important finding in this repo is the **"やる気だけモデル" / silent-failure mode**: a local LLM can produce a clean, fast-looking session ("✻ Cooked for 40s" + "Done.") with **zero tool_use blocks fired and no files actually created**. Examples documented here: Ollama `qwen3:30b-instruct`, MLX `gpt-oss-20b-MXFP4-Q4`/`Q8`.

When running a new measurement:

```bash
# After T2-T5 completes:
head -3 tests/T2_buggy.py    # factorial(0) must return 1, not 0
ls calc/ test_calc.py wc_tool.py    # all three must exist
```

If any of these are missing, the run **failed** even if the runner reported "All tests done". Mark such runs in the table with parenthesized timings — `(4m30s)` — and add a note about the failure mode. Do not let a fast-but-empty run climb the speed ranking.

## Adding a new model row

Typical task. The runner expects a model already serving an Anthropic-compatible endpoint or a Claude Code session already running. Outline:

```bash
# Ollama (env vars only, no proxy):
export ANTHROPIC_AUTH_TOKEN=ollama
export ANTHROPIC_API_KEY=""
export ANTHROPIC_BASE_URL=http://localhost:11434
# Then either:
#   - bash ollama/run_all_practical.sh   (non-interactive --print mode, all models)
#   - launch claude in a tmux pane and run ollama/tests/run_practical.sh <model> <pane>

# MLX (vllm-mlx server):
mlx/scripts/run_one_model.sh <hf-repo-name> <pane>   # full pipeline: stop server → start → claude restart → fixtures → T2-T5

# Anthropic cloud baseline:
unset ANTHROPIC_BASE_URL ANTHROPIC_AUTH_TOKEN ANTHROPIC_API_KEY
claude --model claude-opus-4-7 --permission-mode bypassPermissions   # in target pane
COOLDOWN=5 ./tests/run_practical.sh claude-opus-4-7 <pane>            # COOLDOWN=5 because no thermal concern
```

After the run, copy the produced log to the right place (`ollama/results/`, `mlx/results/` in the source `~/tmp/...` workspaces, or `reference/results/` in this repo for cloud baselines) and update the comparison table.

## Known gotchas (do not retry these silently)

- **vllm-mlx `--continuous-batching` is broken with tool_use.** `RuntimeError: There is no Stream(gpu, 4) in current thread.` every time. Do not "helpfully" add it back.
- **MLX 0.31.x has a worker-thread Stream bug** that affects the robustonian fork too. Pin to `mlx==0.30.*` `mlx-metal==0.30.*` for the fork. The same `Stream(gpu, 0)` thread error reproduces in `_serve_single` via `mx.synchronize`.
- **`qwen3_5_moe` architecture (Qwen3.6 MoE) is not supported by mlx-lm 0.30.6**, so the robustonian fork cannot run `unsloth/Qwen3.6-35B-A3B-UD-MLX-4bit`. vllm-mlx is the only MLX path for that model today.
- **gpt-oss tool calls are broken on every MLX server tried** (vllm-mlx 0.2.9 harmony parser, robustonian fork without harmony parser). For gpt-oss-20b use Ollama, where it works.
- **M4 Pro thermal throttling**: GPU hits 92°C in ~10s of continuous generation. The MLX runner uses `COOLDOWN=45` between tests by default. For cloud-baseline runs this is unnecessary (`COOLDOWN=5` is fine). When comparing numbers, note whether cooldown was included.
- **For cloud baseline, you must `unset ANTHROPIC_BASE_URL ANTHROPIC_AUTH_TOKEN ANTHROPIC_API_KEY`** before launching `claude` — otherwise it inherits the local-LLM env from a parent shell and silently hits the wrong endpoint.

## Regenerating the comparison chart

`docs/assets/model-comparison.png` is produced by `scripts/generate_chart.py`. The script uses PEP 723 inline dependencies and runs via `uv` — no virtualenv setup needed:

```bash
./scripts/generate_chart.py
# → Wrote docs/assets/model-comparison.png
```

When you add or change a row in the comparison table, **also update the `ROWS` list inside `generate_chart.py`** and re-run it. Conventions in the script:

- `status="ok"` → solid colored bar (cloud=blue, ollama=green, mlx=amber)
- `status="partial"` → white with crosshatch (e.g. T5 timeout but other tasks done)
- `status="fail"` → red with diagonal hatch (the "やる気だけ" / artifact-0 case)
- DNF rows are intentionally excluded from the chart (would distort the X-axis)

Japanese labels render via `Hiragino Sans` (auto-detected at script start). On a non-macOS machine, the script falls back to whatever sans-serif is available — labels stay legible but Japanese may render as tofu.

## When updating the comparison table

The top-level table in `README.md` mixes backends (Anthropic cloud / Ollama / MLX-vllm / MLX-robustonian) in one ranking. Conventions in use:

- **⭐ markers** are reserved for the recommended pick in each tier (cloud baseline / Ollama best / MLX best). Don't sprinkle them onto every passing row.
- **Parenthesized 累計** = the run failed verification despite the runner declaring success. Keep these visible (the silent-failure pattern is part of the lesson) but never use them for "fastest model" claims.
- **DNF** = did not finish (e.g. `unsloth/Qwen3.6-27B-MLX-8bit` choking T2 at 12+ min and never reaching T3-T5).
- The `Sonnet 4.6 比` ratio table downstream uses Sonnet 4.6 (cloud) as 1.00x. If you add a faster cloud row in the future, re-pivot all the ratios — don't leave a stale baseline.

## docs/ is the published Jekyll site

`docs/` is the GitHub Pages source (just-the-docs remote theme, `permalink: pretty`). Current pages:

| File | Role |
|---|---|
| `docs/_config.yml` | Site config (theme / baseurl / aux_links) |
| `docs/index.md` | Landing page — adapted from `README.md` |
| `docs/reference.md` | Cloud baseline (Opus 4.7 / Sonnet 4.6) detail page |

Conventions for `docs/` Markdown:

1. Front-matter block at top (`title:`, `nav_order:`, `layout: default`).
2. Links to scripts and raw logs use **full GitHub blob URLs** (`https://github.com/j3tm0t0/local-llm-macmini/blob/main/<path>`), not relative paths — the scripts and `reference/results/` are not part of the Jekyll source set, so relative links would 404 on Pages.
3. `[Source on GitHub](...){: .btn .btn-outline }` footer at the bottom of each page where applicable.

When `README.md` is updated, mirror substantive changes into `docs/index.md`. The two are kept loosely in sync — `README.md` is the canonical narrative, `docs/index.md` adds front-matter and a few site-specific link rewrites.

To enable Pages: repo Settings → Pages → Source = `main` branch, folder = `/docs`. URL becomes `https://j3tm0t0.github.io/local-llm-macmini/`.

## Source workspaces (off-repo)

The original benchmark scratch dirs live outside this repo:

- `~/tmp/claude-code-local-llm/` — Ollama working dir + raw `results/practical_*.log`
- `~/tmp/claude-code-local-llm-mlx/` — MLX working dir + raw logs + the robustonian-env venv
- `~/tmp/cc-reference-bench/` — cloud baseline working dir created during the Opus/Sonnet reference run

This repo holds the cleaned-up, redistributable subset (scripts + reference logs). Only the cloud-baseline raw logs are checked in (`reference/results/`); Ollama / MLX practical logs from the original off-repo workspaces are not committed. When adding a new model, decide whether the full log is worth committing — usually only a numeric line in the README comparison table is needed.

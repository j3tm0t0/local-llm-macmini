#!/usr/bin/env -S uv run --quiet
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "matplotlib>=3.8",
# ]
# ///
"""
T2-T5 cumulative time comparison charts.

Run: ./scripts/generate_chart.py
Outputs:
  - docs/assets/model-comparison.png   (main backend comparison)
  - docs/assets/cooling-impact.png     (warm vs active-cooled, same models)
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

# Use a Japanese-capable font on macOS if available.
_JP_FONT_CANDIDATES = ["Hiragino Sans", "Hiragino Maru Gothic Pro", "Yu Gothic", "Noto Sans CJK JP", "IPAexGothic"]
for _name in _JP_FONT_CANDIDATES:
    if any(f.name == _name for f in fm.fontManager.ttflist):
        matplotlib.rcParams["font.family"] = _name
        break
matplotlib.rcParams["axes.unicode_minus"] = False


@dataclass
class Row:
    label: str
    seconds: int
    backend: str  # cloud / ollama / mlx / ds4
    status: str   # ok / fail / partial


# 2026-07-13 M5 Max 128GB 全面再測定 (Claude Code v2.1.207 / Ollama 0.31.2 /
# vllm-mlx 0.4.0 / ds4 build 2026-07-13). 元 M4 Pro / 64GB データは
# reference として details.md の「M4 Pro 参考」セクションで保持。
# コマンド経路: 全 backend が claude --print --model ... の同一 --print パスで実行、
# ANTHROPIC_BASE_URL の切替でエンドポイントを差し替え。tmux 駆動は今回不採用。
ROWS: list[Row] = [
    Row("Opus 4.8 (cloud)",                                         106, "cloud",  "ok"),
    Row("Ollama qwen3.6:35b-a3b-coding-nvfp4",                      111, "ollama", "ok"),
    Row("Sonnet 5 (cloud)",                                         112, "cloud",  "ok"),
    Row("Fable 5 (cloud)",                                          116, "cloud",  "ok"),
    Row("Ollama qwen3-coder-next:q4_K_M (80B-A3B)",                 117, "ollama", "ok"),
    Row("MLX unsloth/Qwen3.6-35B-A3B-UD-MLX-4bit (vllm-mlx 0.4.0)", 121, "mlx",    "ok"),
    Row("Ollama qwen3.6:35b-a3b-coding-mxfp8",                      134, "ollama", "ok"),
    Row("Ollama gpt-oss:120b (65GB, M4 Pro では全 TIMEOUT だった)", 199, "ollama", "ok"),
    Row("Ollama gpt-oss:20b",                                       216, "ollama", "ok"),
    Row("Ollama gemma4:26b-mxfp8 (a4b MoE)",                        257, "ollama", "ok"),
    Row("ds4 / DeepSeek V4 Flash q2 (~81GB, ~284B/13B active)",     284, "ds4",    "ok"),
    Row("MLX Qwen3-Coder-30B-A3B-DWQ (vllm-mlx 0.4.0)",             451, "mlx",    "ok"),
    Row("Ollama qwen3.6:27b-coding-mxfp8 (dense, M4 Pro は DNF)",   830, "ollama", "ok"),
    Row("Ollama gemma4:31b-coding-mtp-bf16 (coding + MTP)",         897, "ollama", "ok"),
    Row("Ollama devstral-small-2 (T2/T3 で空走、T5 のみ artifact)", 108, "ollama", "fail"),
    Row("Ollama batiai/minimax-m2.7:q3 (128GB でも OOM で全失敗)",  719, "ollama", "fail"),
]

# Sort: ok+partial by time ascending, fail block at bottom (separately sorted).
ok_rows = sorted([r for r in ROWS if r.status in ("ok", "partial")], key=lambda r: r.seconds)
fail_rows = sorted([r for r in ROWS if r.status == "fail"], key=lambda r: r.seconds)
ordered = ok_rows + fail_rows

# Colors per backend.
BACKEND_COLOR = {
    "cloud":  "#3b82f6",  # blue
    "ollama": "#22c55e",  # green
    "mlx":    "#f59e0b",  # amber
    "ds4":    "#a855f7",  # purple (DwarfStar / DeepSeek)
}
FAIL_COLOR = "#ef4444"  # red, overrides backend

fig, ax = plt.subplots(figsize=(11, 6.5))

labels = [r.label for r in ordered]
values = [r.seconds for r in ordered]
colors = [
    FAIL_COLOR if r.status == "fail" else BACKEND_COLOR[r.backend]
    for r in ordered
]
hatches = [
    "///" if r.status == "fail" else ("xx" if r.status == "partial" else None)
    for r in ordered
]

y_positions = list(range(len(ordered)))[::-1]  # top is fastest

bars = ax.barh(y_positions, values, color=colors, edgecolor="black", linewidth=0.4)
for bar, h in zip(bars, hatches):
    if h:
        bar.set_hatch(h)

ax.set_yticks(y_positions)
ax.set_yticklabels(labels, fontsize=9)
ax.set_xlabel("T2-T5 累計時間 (秒) — 短いほど良い")
ax.set_title("Claude Code × ローカル LLM ベンチマーク (MacBook Pro M5 Max / 128GB)", fontsize=12, pad=15)

# Reference vertical line at Opus 4.8 = 106s (M5 Max 上のクラウド最良)
opus_x = 106
ax.axvline(opus_x, color="#3b82f6", linestyle="--", linewidth=1.2, alpha=0.6)
ax.text(opus_x + 8, len(ordered) - 0.4, "Opus 4.8 ベースライン (106s)",
        color="#1e3a8a", fontsize=8, va="top")

# Annotate values
for y, r in zip(y_positions, ordered):
    suffix = ""
    if r.status == "fail":
        suffix = "  ← 見せかけの数字"
    elif r.status == "partial":
        suffix = "  ← 部分成功"
    ax.text(r.seconds + 12, y, f"{r.seconds}s ({r.seconds//60}m{r.seconds%60:02d}s){suffix}",
            va="center", fontsize=8.5, color="#111")

ax.set_xlim(0, max(values) * 1.25)
ax.grid(axis="x", linestyle=":", alpha=0.4)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

# Legend
legend_handles = [
    Patch(facecolor=BACKEND_COLOR["cloud"], edgecolor="black", label="Anthropic クラウド"),
    Patch(facecolor=BACKEND_COLOR["ollama"], edgecolor="black", label="Ollama (ローカル)"),
    Patch(facecolor=BACKEND_COLOR["mlx"], edgecolor="black", label="MLX (vllm-mlx)"),
    Patch(facecolor=BACKEND_COLOR["ds4"], edgecolor="black", label="ds4 (DwarfStar / DeepSeek V4)"),
    Patch(facecolor=FAIL_COLOR, edgecolor="black", hatch="///", label="失敗 (artifact 不足 or OOM)"),
]
ax.legend(handles=legend_handles, loc="lower right", fontsize=8.5, framealpha=0.95)

plt.tight_layout()

OUT = Path(__file__).resolve().parent.parent / "docs" / "assets" / "model-comparison.png"
OUT.parent.mkdir(parents=True, exist_ok=True)
plt.savefig(OUT, dpi=180, bbox_inches="tight")
plt.close(fig)
print(f"Wrote {OUT.relative_to(Path(__file__).resolve().parent.parent)}")


# ============================================================
# Second chart: warm vs active-cooled, same 5 configurations
# ============================================================

@dataclass
class CoolingPair:
    label: str
    warm: int
    cooled: int
    note: str = ""

# Data pulled from REPORT.md §11 / BLOG.md cooling section.
COOLING: list[CoolingPair] = [
    CoolingPair("Ollama qwen3.6:35b-a3b-coding-nvfp4",       333, 308, "-7.5%"),
    CoolingPair("Ollama qwen3.6:35b-a3b-coding-mxfp8",       366, 341, "-7%"),
    CoolingPair("Ollama gpt-oss:20b",                        662, 562, "-15%"),
    CoolingPair("MLX vllm-mlx + Qwen3-Coder-30B-A3B-DWQ",   1356, 792, "-42% (T5 完走)"),
    CoolingPair("MLX robustonian + Qwen3-Coder-30B-A3B-DWQ", 1106, 1157, "+5% (逆効果)"),
]
# Sort by warm time ascending so eye reads small→large left-to-right.
COOLING.sort(key=lambda p: p.warm)

fig2, ax2 = plt.subplots(figsize=(11, 5.5))

n = len(COOLING)
y = list(range(n))[::-1]  # top is fastest warm
bar_h = 0.36

warm_vals = [p.warm for p in COOLING]
cool_vals = [p.cooled for p in COOLING]

ax2.barh([yi + bar_h/2 for yi in y], warm_vals, height=bar_h,
         color="#94a3b8", edgecolor="black", linewidth=0.4, label="昨日 (no fan)")
ax2.barh([yi - bar_h/2 for yi in y], cool_vals, height=bar_h,
         color="#22d3ee", edgecolor="black", linewidth=0.4, label="冷却 (active fan)")

ax2.set_yticks(y)
ax2.set_yticklabels([p.label for p in COOLING], fontsize=9)
ax2.set_xlabel("T2-T5 累計時間 (秒) — 短いほど良い")
ax2.set_title("冷却ファン投入による thermal throttling の影響", fontsize=12, pad=15)

for yi, p in zip(y, COOLING):
    ax2.text(p.warm + 14, yi + bar_h/2, f"{p.warm}s", va="center", fontsize=8.5, color="#aaa")
    color = "#22d3ee" if p.cooled < p.warm else "#f472b6"
    ax2.text(p.cooled + 14, yi - bar_h/2, f"{p.cooled}s ({p.note})", va="center", fontsize=8.5, color=color)

ax2.set_xlim(0, max(max(warm_vals), max(cool_vals)) * 1.32)
ax2.grid(axis="x", linestyle=":", alpha=0.4)
ax2.spines["top"].set_visible(False)
ax2.spines["right"].set_visible(False)
ax2.legend(loc="lower right", fontsize=9, framealpha=0.95)

plt.tight_layout()

OUT2 = Path(__file__).resolve().parent.parent / "docs" / "assets" / "cooling-impact.png"
plt.savefig(OUT2, dpi=180, bbox_inches="tight")
plt.close(fig2)
print(f"Wrote {OUT2.relative_to(Path(__file__).resolve().parent.parent)}")


# ============================================================
# Third chart: M5 Max 3-condition cooling (baseline / fan auto / fan max)
# 2026-07 検証: MacBook Pro M5 Max では Macs Fan Control で fan RPM を
# 手動で MAX にしないと sustained LLM で thermal_pressure=Heavy が入り
# T4/T5 で確率的 verbose loop が発生して 20-45x に膨張する。
# fan MAX にすると thermal_pressure=Nominal 100% で spike 消失。
# ============================================================

@dataclass
class CoolingPairFan:
    label: str
    fan_on: int     # fan on だが auto RPM (静音優先) → 実質効いてない
    fan_max: int    # Macs Fan Control で fans を 100% にピン留め
    fan_on_note: str = ""
    fan_max_note: str = ""

# Data: results_cooling/cool_0714_1202/ (fan auto), results_cooling/fanmax_0715_0019/ (fan MAX)
# cumulative T2-T5 秒数、両条件とも sudo powermetrics で thermal_pressure 並行計測
COOLING_M5MAX: list[CoolingPairFan] = [
    CoolingPairFan("Ollama qwen3.6:35b-a3b-coding-nvfp4",
                   4054, 140, "Heavy 6% / T4 TIMEOUT", "Nominal 100%"),
    CoolingPairFan("Ollama gpt-oss:120b",
                   1455, 240, "Heavy 10% / T5 verbose", "Nominal 100%"),
    CoolingPairFan("MLX unsloth/Qwen3.6-35B-A3B-UD-MLX-4bit",
                   2615, 116, "Heavy 20% / T2,T3 verbose", "Nominal 100%"),
    CoolingPairFan("MLX Qwen3-Coder-30B-A3B-DWQ",
                   2381, 142, "Heavy 25% / T4 verbose", "Nominal 100%"),
]

fig3, ax3 = plt.subplots(figsize=(12, 5.5))
n3 = len(COOLING_M5MAX)
y3 = list(range(n3))[::-1]
bh = 0.36

fanon_vals  = [p.fan_on   for p in COOLING_M5MAX]
fanmax_vals = [p.fan_max  for p in COOLING_M5MAX]

ax3.barh([yi + bh/2 for yi in y3], fanon_vals, height=bh,
         color="#f472b6", edgecolor="black", linewidth=0.4, label="fan auto (静音優先 = 実質効かず)")
ax3.barh([yi - bh/2 for yi in y3], fanmax_vals, height=bh,
         color="#22d3ee", edgecolor="black", linewidth=0.4, label="fan MAX (Macs Fan Control で 100%)")

ax3.set_yticks(y3)
ax3.set_yticklabels([p.label for p in COOLING_M5MAX], fontsize=9)
ax3.set_xlabel("T2-T5 累計時間 (秒) — 短いほど良い / log scale")
ax3.set_xscale("log")
ax3.set_title("MacBook Pro M5 Max: Macs Fan Control 有無による thermal throttling 影響",
              fontsize=12, pad=15)

for yi, p in zip(y3, COOLING_M5MAX):
    ax3.text(p.fan_on * 1.05, yi + bh/2, f"{p.fan_on}s ({p.fan_on_note})",
             va="center", fontsize=9, color="#c026d3")
    ax3.text(p.fan_max * 1.05, yi - bh/2, f"{p.fan_max}s ({p.fan_max_note})",
             va="center", fontsize=9, color="#0891b2")

ax3.set_xlim(80, max(fanon_vals) * 3)
ax3.grid(axis="x", linestyle=":", alpha=0.4, which="both")
ax3.spines["top"].set_visible(False)
ax3.spines["right"].set_visible(False)
ax3.legend(loc="lower right", fontsize=9.5, framealpha=0.95)

plt.tight_layout()
OUT3 = Path(__file__).resolve().parent.parent / "docs" / "assets" / "cooling-impact-m5max.png"
plt.savefig(OUT3, dpi=180, bbox_inches="tight")
plt.close(fig3)
print(f"Wrote {OUT3.relative_to(Path(__file__).resolve().parent.parent)}")

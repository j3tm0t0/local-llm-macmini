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
    backend: str  # cloud / ollama / mlx
    status: str   # ok / fail / partial


# Numbers come from README.md and reference/results/.
ROWS: list[Row] = [
    Row("Sonnet 4.6 (cloud)",                                       80,  "cloud",  "ok"),
    Row("Opus 4.7 (cloud)",                                         90,  "cloud",  "ok"),
    Row("Ollama qwen3.6:35b-a3b-coding-nvfp4",                      333, "ollama", "ok"),
    Row("Ollama qwen3.6:35b-a3b-coding-mxfp8",                      366, "ollama", "ok"),
    Row("MLX unsloth/Qwen3.6-35B-A3B-UD-MLX-4bit (vllm-mlx)",       585, "mlx",    "ok"),
    Row("Ollama gpt-oss:20b",                                       662, "ollama", "ok"),
    Row("MLX Qwen3-Coder-30B-A3B-DWQ (robustonian fork)",           1106,"mlx",    "ok"),
    Row("MLX Qwen3-Coder-30B-A3B-DWQ (vllm-mlx, T5 timeout)",       1356,"mlx",    "partial"),
    Row("Ollama qwen3:30b-instruct (やる気だけ — artifact 0/4)",    185, "ollama", "fail"),
    Row("MLX gpt-oss-20b-MXFP4-Q4 (やる気だけ — artifact 0/4)",     270, "mlx",    "fail"),
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
ax.set_title("Claude Code × ローカル LLM ベンチマーク (Mac mini M4 Pro / 64GB)", fontsize=12, pad=15)

# Reference vertical line at Sonnet 4.6 = 80s
sonnet_x = 80
ax.axvline(sonnet_x, color="#3b82f6", linestyle="--", linewidth=1.2, alpha=0.6)
ax.text(sonnet_x + 8, len(ordered) - 0.4, "Sonnet 4.6 ベースライン (80s)",
        color="#1e3a8a", fontsize=8, va="top")

# Annotate values
for y, r in zip(y_positions, ordered):
    suffix = ""
    if r.status == "fail":
        suffix = "  ← artifact なし"
    elif r.status == "partial":
        suffix = "  ← T5 timeout"
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
    Patch(facecolor=BACKEND_COLOR["mlx"], edgecolor="black", label="MLX (vllm-mlx / robustonian)"),
    Patch(facecolor=FAIL_COLOR, edgecolor="black", hatch="///", label="やる気だけ型空走 (artifact 0/4)"),
    Patch(facecolor="white", edgecolor="black", hatch="xx", label="部分成功 (T5 timeout)"),
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

#!/usr/bin/env -S uv run --quiet
# /// script
# requires-python = ">=3.11"
# dependencies = ["radon>=6.0"]
# ///
"""
T2-T5 の artifact を functional に採点する。
入力: results/<model>/artifacts_T<N>/... (runner が archive したもの)
出力: 標準出力に model × task スコア表 + results/functional_scores.csv

スコア (各タスク 0.0 - 1.0):
  T2 factorial: 8ケース (0..7) + factorial(-1) 例外 + fibonacci 4ケース の正答率
  T3 calc pkg: import + add/multiply 8 テスト + test_calc.py の pass
  T4 refactor: original vs refactored の stdout 完全一致 + LOC 削減 + CC 削減
  T5 wc_tool: 6 edge invocation vs system wc + friendly error 存在

注意: score_functional.py 自身は workdir (`/Users/moto/tmp/claude-code-local-llm/`) の
maxdepth 1 に置くと clean_workdir に消される。repo/scripts/ に置いて実行すること。
"""
from __future__ import annotations
import subprocess, sys, os, tempfile, csv
from pathlib import Path

RESULTS = Path("/Users/moto/tmp/claude-code-local-llm/results")
# T4 の "元 messy" は runner の archive では取れない (task 実行後だと refactor 済み)。
# repo の fixture を信頼できる origin として使う。
REPO_T4_FIXTURE = Path("/Users/moto/Dropbox/src/github.com/j3tm0t0/local-llm-macmini/mlx/tests/T4_messy.py")
PY = sys.executable

# ============================================================
# T2: factorial(0..7) + factorial(-1) + fibonacci(0,1,2,7)
# ============================================================
def score_t2(artifact_dir: Path) -> tuple[float, str]:
    f = artifact_dir / "T2_buggy.py"
    if not f.exists():
        return 0.0, "no_file"

    driver = """
import sys, importlib.util
spec = importlib.util.spec_from_file_location("t2", sys.argv[1])
mod = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(mod)
except Exception as e:
    print("LOAD_ERR", repr(e)); sys.exit(1)

def check(name, fn, arg, expected):
    try:
        v = fn(arg)
        print(f"{name}({arg})={v} exp={expected} {'OK' if v==expected else 'NG'}")
    except RecursionError:
        print(f"{name}({arg})=RecursionError NG")
    except Exception as e:
        print(f"{name}({arg})={type(e).__name__} NG")

for n, e in [(0,1),(1,1),(2,2),(3,6),(4,24),(5,120),(6,720),(7,5040)]:
    check("factorial", getattr(mod,"factorial",lambda x:None), n, e)
try:
    v = mod.factorial(-1)
    print(f"factorial(-1)={v} handled OK")
except RecursionError:
    print("factorial(-1)=RecursionError NG")
except Exception:
    print("factorial(-1)=raised OK")
for n, e in [(0,0),(1,1),(2,1),(7,13)]:
    check("fibonacci", getattr(mod,"fibonacci",lambda x:None), n, e)
"""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tf:
        tf.write(driver); tf.flush()
        try:
            r = subprocess.run([PY, tf.name, str(f)], capture_output=True, text=True, timeout=15)
        except subprocess.TimeoutExpired:
            return 0.0, "timeout"
        finally:
            os.unlink(tf.name)
    lines = r.stdout.strip().splitlines()
    ok = sum(1 for L in lines if L.endswith(" OK"))
    total = 8 + 1 + 4
    return ok / total, f"{ok}/{total}"

# ============================================================
# T3: import calc + add/multiply の 6 テスト + test_calc.py 実行
# ============================================================
def score_t3(artifact_dir: Path) -> tuple[float, str]:
    calc = artifact_dir / "calc"
    if not calc.is_dir():
        return 0.0, "no_calc"

    driver = """
import sys
sys.path.insert(0, sys.argv[1])
try:
    import calc
except Exception as e:
    print("IMPORT_ERR", repr(e)); sys.exit(1)
def check(desc, cond):
    print(f"{desc} {'OK' if cond else 'NG'}")
add = getattr(calc, "add", None); mul = getattr(calc, "multiply", None)
check("has_add", callable(add))
check("has_mul", callable(mul))
if callable(add):
    check("add_2_3=5", add(2,3)==5)
    check("add_-1_1=0", add(-1,1)==0)
    check("add_0_0=0", add(0,0)==0)
if callable(mul):
    check("mul_3_4=12", mul(3,4)==12)
    check("mul_-2_5=-10", mul(-2,5)==-10)
    check("mul_0_9=0", mul(0,9)==0)
"""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tf:
        tf.write(driver); tf.flush()
        try:
            r = subprocess.run([PY, tf.name, str(artifact_dir)], capture_output=True, text=True, timeout=15)
        except subprocess.TimeoutExpired:
            return 0.0, "timeout"
        finally:
            os.unlink(tf.name)
    lines = r.stdout.strip().splitlines()
    ok = sum(1 for L in lines if L.endswith(" OK"))
    total = 8
    tc = artifact_dir / "test_calc.py"
    tc_bonus = 0.0
    if tc.exists():
        try:
            r2 = subprocess.run([PY, str(tc)], capture_output=True, text=True, timeout=15, cwd=str(artifact_dir))
            tc_bonus = 0.2 if r2.returncode == 0 else 0.0
        except Exception:
            tc_bonus = 0.0
    base = ok / total
    return min(1.0, base * 0.8 + tc_bonus), f"{ok}/{total}+tc={'y' if tc_bonus else 'n'}"

# ============================================================
# T4: original vs refactored の stdout 一致 + LOC 削減 + CC 削減
# ============================================================
def _run_capture(path: Path) -> tuple[int, str]:
    try:
        r = subprocess.run([PY, str(path)], capture_output=True, text=True, timeout=15,
                           cwd=str(path.parent))
        return r.returncode, r.stdout
    except subprocess.TimeoutExpired:
        return 124, ""

def score_t4(artifact_dir: Path) -> tuple[float, str]:
    # 元 messy は repo fixture から (runner archive は task 後なので refactor 済みが入ってる)
    if not REPO_T4_FIXTURE.exists():
        return 0.0, "no_fixture"
    orig_bytes = REPO_T4_FIXTURE.read_bytes()

    # モデルの refactored 候補 (別名保存 → in-place 修正の順に確認)
    refactored = None
    for name in ["T4_refactored.py", "T4_clean.py", "T4_messy.py"]:
        cand = artifact_dir / name
        if cand.exists() and cand.read_bytes() != orig_bytes:
            refactored = cand
            break
    if not refactored:
        return 0.0, "no_change"

    # 元 messy を tmpfile に書いて実行
    with tempfile.NamedTemporaryFile("wb", suffix="_orig.py", delete=False) as tf:
        tf.write(orig_bytes); tf.flush()
        orig_path = Path(tf.name)
    try:
        rc_o, out_o = _run_capture(orig_path)
    finally:
        os.unlink(orig_path)
    rc_r, out_r = _run_capture(refactored)
    stdout_match = (rc_o == 0 and rc_r == 0 and out_o == out_r)

    orig_lines = len([L for L in orig_bytes.decode(errors="replace").splitlines() if L.strip() and not L.strip().startswith("#")])
    ref_lines  = len([L for L in refactored.read_text().splitlines() if L.strip() and not L.strip().startswith("#")])
    loc_reduction = max(0.0, (orig_lines - ref_lines) / max(orig_lines, 1))

    try:
        from radon.complexity import cc_visit
        cc_o = sum(c.complexity for c in cc_visit(orig_bytes.decode(errors="replace")))
        cc_r = sum(c.complexity for c in cc_visit(refactored.read_text()))
    except Exception:
        cc_o = cc_r = 0
    cc_reduction = max(0.0, (cc_o - cc_r) / max(cc_o, 1))

    # スコア設計:
    #   0.6 diff (動作維持が最重要): stdout 完全一致 = 0.6
    #   0.2 CC (複雑度膨張の罰): cc <= 元 → 0.2, 倍以上 → 0 (線形補間)
    #   0.2 LOC (可読性膨張の罰): ref <= 1.5*orig → 0.2, ref >= 3*orig → 0
    #     ※LOC 削減自体は加点しない (type hints / docstring 追加で行数増は普通)
    cc_component = 0.0
    if cc_o > 0:
        cc_component = 0.2 * max(0.0, 1.0 - max(0.0, (cc_r - cc_o) / cc_o))
    loc_component = 0.0
    if orig_lines > 0:
        loc_ratio = ref_lines / orig_lines
        loc_component = 0.2 * max(0.0, 1.0 - max(0.0, (loc_ratio - 1.5) / 1.5))
    score = (0.6 if stdout_match else 0.0) + cc_component + loc_component
    return round(score, 3), f"diff={'ok' if stdout_match else 'ng'} loc={orig_lines}->{ref_lines} cc={cc_o}->{cc_r}"

# ============================================================
# T5: wc_tool.py を 6 edge case で叩き system wc と比較
# ============================================================
def score_t5(artifact_dir: Path) -> tuple[float, str]:
    tool = artifact_dir / "wc_tool.py"
    if not tool.exists():
        return 0.0, "no_tool"

    def _wc_parse(s: str) -> tuple[int|None, int|None, int|None]:
        nums = [int(x) for x in s.replace(",", " ").split() if x.isdigit()]
        if len(nums) >= 3:
            return nums[0], nums[1], nums[2]
        return None, None, None

    def _run_tool(args, timeout=10) -> tuple[int, str]:
        try:
            r = subprocess.run([PY, str(tool)] + args, capture_output=True, text=True, timeout=timeout)
            return r.returncode, (r.stdout + r.stderr)
        except subprocess.TimeoutExpired:
            return 124, ""

    checks = 0; total = 0
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        f1 = tdp / "normal.txt"; f1.write_text("hello world\nfoo bar baz\nline three\n")
        f2 = tdp / "empty.txt";  f2.write_text("")
        f3 = tdp / "binary.bin"; f3.write_bytes(bytes(range(256)) * 4)
        d4 = tdp / "adir"; d4.mkdir()
        f6 = tdp / "big.txt";    f6.write_text("line\n" * 1000)

        # 通常/空/大きめ: system wc と数値一致
        for path in [f1, f2, f6]:
            total += 1
            rc, out = _run_tool([str(path)])
            if rc != 0: continue
            wl, ww, wc = _wc_parse(out)
            sys_r = subprocess.run(["wc", str(path)], capture_output=True, text=True)
            sl, sw, sc = _wc_parse(sys_r.stdout)
            if (wl, ww, wc) == (sl, sw, sc):
                checks += 1

        # バイナリ: crash しなければ OK
        total += 1
        rc, out = _run_tool([str(f3)])
        if rc == 0: checks += 1

        # 存在しない: friendly error (traceback 出さない、何かメッセージ出す)
        total += 1
        rc, out = _run_tool([str(tdp / "nope.txt")])
        if rc != 0 and "Traceback" not in out and out.strip():
            checks += 1

        # ディレクトリ: エラーで返す
        total += 1
        rc, out = _run_tool([str(d4)])
        if rc != 0 or "error" in out.lower() or "directory" in out.lower():
            checks += 1

    return checks / total, f"{checks}/{total}"

# ============================================================
# main
# ============================================================
SCORERS = {"T2": score_t2, "T3": score_t3, "T4": score_t4, "T5": score_t5}

def main():
    rows = []
    model_dirs = sorted([d for d in RESULTS.iterdir() if d.is_dir() and (d / "times.txt").exists()])
    for md in model_dirs:
        model = md.name
        result = {"model": model}
        for tid, fn in SCORERS.items():
            adir = md / f"artifacts_{tid}"
            if not adir.exists():
                result[tid] = None
                result[f"{tid}_note"] = "no_artifact"
                continue
            score, note = fn(adir)
            result[tid] = round(score, 3)
            result[f"{tid}_note"] = note
        scores = [result[t] for t in ["T2","T3","T4","T5"] if result[t] is not None]
        result["avg"] = round(sum(scores)/len(scores), 3) if scores else None
        rows.append(result)

    rows.sort(key=lambda r: (-(r["avg"] if r["avg"] is not None else -1)))

    hdr = f"{'model':<48}  {'T2':>6} {'T3':>6} {'T4':>6} {'T5':>6}  {'avg':>6}  notes"
    print(hdr); print("-" * len(hdr))
    for r in rows:
        cells = [f"{r[t] if r[t] is not None else '-':>6}" for t in ["T2","T3","T4","T5"]]
        avg = f"{r['avg']:>6}" if r["avg"] is not None else " " * 6
        notes = " | ".join(f"{t}:{r[t+'_note']}" for t in ["T2","T3","T4","T5"] if r[t] is not None)
        print(f"{r['model']:<48}  {' '.join(cells)}  {avg}  {notes}")

    out = RESULTS / "functional_scores.csv"
    with open(out, "w", newline="") as fp:
        w = csv.writer(fp)
        w.writerow(["model","T2","T3","T4","T5","avg","T2_note","T3_note","T4_note","T5_note"])
        for r in rows:
            w.writerow([r["model"], r.get("T2"), r.get("T3"), r.get("T4"), r.get("T5"), r.get("avg"),
                        r.get("T2_note"), r.get("T3_note"), r.get("T4_note"), r.get("T5_note")])
    print(f"\nWrote {out}")

if __name__ == "__main__":
    main()

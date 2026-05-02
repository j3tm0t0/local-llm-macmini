# 実践比較テスト プロンプト集

## T1: ファイル作成+実行 (既存テスト)
> Create a Python script prime_check.py with function is_prime(n) that prints all primes from 2 to 30. Then run it and tell me the output. Be brief.

## T2: バグ修正
> Read the file tests/T2_buggy.py, identify the bug(s), fix them in-place, and run the fixed version. Show the corrected output. Be concise.

## T3: マルチファイルプロジェクト
> Create a small Python package called "calc" with: 1) calc/__init__.py that exports add and multiply, 2) calc/ops.py with the actual functions, 3) test_calc.py that imports from calc and runs 3 assertions. Run the test and show results.

## T4: 既存コードのリファクタリング
> Read tests/T4_messy.py, refactor it to remove code duplication and improve readability. Keep the same behavior. Run it to verify. Show a brief diff summary of your changes.

## T5: エラーハンドリング + CLI ツール
> Create a CLI tool `wc_tool.py` that takes a filename argument, prints line/word/char counts. Handle the case where the file doesn't exist with a friendly error. Test it on an existing file and a nonexistent file.

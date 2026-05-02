#!/bin/bash
# T2〜T5 が触るファイルを初期状態に戻す。各モデルのテスト前に呼ぶ。
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# T2: バグった factorial に戻す
cat > tests/T2_buggy.py <<'EOF'
def factorial(n):
    if n == 0:
        return 0
    return n * factorial(n - 1)


def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


if __name__ == "__main__":
    print(f"factorial(5) = {factorial(5)}")
    print(f"factorial(0) = {factorial(0)}")
    print(f"fibonacci(7) = {fibonacci(7)}")
EOF

# T4: messy 重複コードに戻す
cat > tests/T4_messy.py <<'EOF'
"""Messy code that needs refactoring."""

def process_users(users):
    result = []
    for u in users:
        if u.get("active"):
            name = u.get("name", "Unknown")
            email = u.get("email", "no-email")
            result.append({"display": f"{name} <{email}>", "type": "active"})
    return result


def process_admins(admins):
    result = []
    for a in admins:
        if a.get("active"):
            name = a.get("name", "Unknown")
            email = a.get("email", "no-email")
            result.append({"display": f"{name} <{email}>", "type": "admin"})
    return result


def process_guests(guests):
    result = []
    for g in guests:
        if g.get("active"):
            name = g.get("name", "Unknown")
            email = g.get("email", "no-email")
            result.append({"display": f"{name} <{email}>", "type": "guest"})
    return result


if __name__ == "__main__":
    users = [
        {"name": "Alice", "email": "alice@example.com", "active": True},
        {"name": "Bob", "email": "bob@example.com", "active": False},
    ]
    admins = [
        {"name": "Charlie", "email": "charlie@example.com", "active": True},
    ]
    guests = [
        {"name": "Dave", "email": "dave@example.com", "active": True},
        {"name": "Eve", "active": False},
    ]
    print("Users:", process_users(users))
    print("Admins:", process_admins(admins))
    print("Guests:", process_guests(guests))
EOF

# T3 / T5 で生成される副産物を削除 (前モデルの残滓を除去)
rm -rf calc test_calc.py wc_tool.py tests/T4_messy_refactored.py 2>/dev/null || true
rm -f tests/T2_buggy_fixed.py 2>/dev/null || true

echo "Fixtures reset OK"

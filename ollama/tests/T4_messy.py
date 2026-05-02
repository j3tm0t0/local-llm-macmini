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

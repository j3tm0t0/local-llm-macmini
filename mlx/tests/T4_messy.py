"""Refactored code with reduced duplication."""

def _process_items(items, item_type):
    """Helper function to process items of a specific type."""
    result = []
    for item in items:
        if item.get("active"):
            name = item.get("name", "Unknown")
            email = item.get("email", "no-email")
            result.append({"display": f"{name} <{email}>", "type": item_type})
    return result

def process_users(users):
    return _process_items(users, "active")

def process_admins(admins):
    return _process_items(admins, "admin")

def process_guests(guests):
    return _process_items(guests, "guest")


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

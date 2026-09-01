import os
import random
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import get_db

USER_ID = 2
COUNT = 5
MONTHS = 3

CATEGORY_WEIGHTS = {
    "Food": 30,
    "Transport": 20,
    "Bills": 15,
    "Shopping": 15,
    "Other": 10,
    "Entertainment": 5,
    "Health": 5,
}

CATEGORY_RANGES = {
    "Food": (50, 800),
    "Transport": (20, 500),
    "Bills": (200, 3000),
    "Health": (100, 2000),
    "Entertainment": (100, 1500),
    "Shopping": (200, 5000),
    "Other": (50, 1000),
}

DESCRIPTIONS = {
    "Food": [
        "Swiggy order - dinner", "Zomato lunch delivery", "Groceries at BigBasket",
        "Tea and snacks", "Local dhaba meal", "Vegetable market shopping",
    ],
    "Transport": [
        "Ola cab ride", "Uber to office", "Metro card recharge",
        "Auto rickshaw fare", "Petrol refill", "Bus pass renewal",
    ],
    "Bills": [
        "Electricity bill", "Mobile recharge - Jio", "Broadband bill - Airtel",
        "Water bill", "Gas cylinder booking", "DTH recharge",
    ],
    "Health": [
        "Pharmacy - medicines", "Doctor consultation fee", "Gym membership",
        "Health checkup", "Dental visit",
    ],
    "Entertainment": [
        "Movie tickets - PVR", "Netflix subscription", "Concert tickets",
        "Bowling with friends", "Spotify Premium",
    ],
    "Shopping": [
        "Myntra clothing order", "Amazon purchase", "New shoes",
        "Electronics - headphones", "Home decor items", "Flipkart order",
    ],
    "Other": [
        "Donation", "Gift for friend", "Salon visit", "Miscellaneous expense",
        "Courier charges",
    ],
}


def random_date_within_months(months):
    today = datetime.now()
    max_days_back = months * 30
    days_back = random.randint(0, max_days_back)
    return today - timedelta(days=days_back)


def generate_expense(user_id, months):
    categories = list(CATEGORY_WEIGHTS.keys())
    weights = list(CATEGORY_WEIGHTS.values())
    category = random.choices(categories, weights=weights, k=1)[0]
    lo, hi = CATEGORY_RANGES[category]
    amount = round(random.uniform(lo, hi), 2)
    description = random.choice(DESCRIPTIONS[category])
    date = random_date_within_months(months).strftime("%Y-%m-%d")
    return (user_id, amount, category, date, description)


def main():
    conn = get_db()
    try:
        expenses = [generate_expense(USER_ID, MONTHS) for _ in range(COUNT)]

        conn.execute("BEGIN")
        cursor_ids = []
        for expense in expenses:
            cursor = conn.execute(
                """
                INSERT INTO expenses (user_id, amount, category, date, description)
                VALUES (?, ?, ?, ?, ?)
                """,
                expense,
            )
            cursor_ids.append(cursor.lastrowid)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pass

    rows = conn.execute(
        "SELECT id, amount, category, date, description FROM expenses WHERE id IN ({})".format(
            ",".join("?" * len(cursor_ids))
        ),
        cursor_ids,
    ).fetchall()
    conn.close()

    dates = [r["date"] for r in rows]
    print(f"Inserted {len(rows)} expenses for user_id={USER_ID}")
    print(f"Date range: {min(dates)} to {max(dates)}")
    print("Sample records:")
    for r in sorted(rows, key=lambda r: r["date"])[:5]:
        print(f"  [{r['id']}] {r['date']} | {r['category']:<13} | Rs.{r['amount']:>8} | {r['description']}")


if __name__ == "__main__":
    main()

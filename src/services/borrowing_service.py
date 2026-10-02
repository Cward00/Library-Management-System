from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import Counter

from src.database.data_access import (
    get_item_by_id, get_user_by_id, save_item, save_user,
    create_loan, get_active_loan, get_active_loans_for_user, return_loan,
    get_items_borrowed_by_user, get_users_who_borrowed_item,
    get_items_borrowed_by_users, get_all_loans
)
from src.models.library_item import LibraryItem
from src.models.user import User

# Fine rate: £0.50 per day overdue
FINE_RATE_PER_DAY = 0.50
MAX_BORROW_LIMIT = 5


def borrow_item(user_id: int, item_id: int) -> Tuple[bool, str]:
    """
    Process a borrowing request.
    Returns: (success, message)
    """
    # 1. Get user and item from database
    user = get_user_by_id(user_id)
    if not user:
        return False, f"User with ID {user_id} not found."

    item = get_item_by_id(item_id)
    if not item:
        return False, f"Item with ID {item_id} not found."

    # 2. Check if item is available
    if not item.is_available():
        return False, f"'{item.title}' is currently unavailable (0 copies left)."

    # 3. Check if user has reached borrowing limit
    active_loans = get_active_loans_for_user(user_id)
    if len(active_loans) >= MAX_BORROW_LIMIT:
        return False, f"User '{user.username}' has reached the maximum borrow limit of {MAX_BORROW_LIMIT} items."

    # 4. Check if user already borrowed this specific item (not returned yet)
    existing = get_active_loan(user_id, item_id)
    if existing:
        return False, f"User already has '{item.title}' borrowed (due {existing['due_date']})."

    # 5. All checks passed — process the borrow
    # Calculate due date (today + item's borrowing days)
    due_date = (datetime.now() + timedelta(days=item.get_borrowing_days())).strftime("%Y-%m-%d")

    # Create the loan record
    create_loan(user_id, item_id, due_date)

    # Reduce available copies
    item.available_copies -= 1
    save_item(item)

    # Update user's borrowed list (in-memory)
    user.borrow_item(item_id)
    save_user(user)

    return True, f"Successfully borrowed '{item.title}'. Due date: {due_date}."


def return_item(user_id: int, item_id: int) -> Tuple[bool, str, float]:
    """
    Process a return request.
    Returns: (success, message, fine_amount)
    """
    # 1. Get user and item
    user = get_user_by_id(user_id)
    if not user:
        return False, f"User with ID {user_id} not found.", 0.0

    item = get_item_by_id(item_id)
    if not item:
        return False, f"Item with ID {item_id} not found.", 0.0

    # 2. Find the active loan
    loan = get_active_loan(user_id, item_id)
    if not loan:
        return False, f"User does not have an active loan for '{item.title}'.", 0.0

    # 3. Calculate fine if overdue
    due_date = datetime.strptime(loan["due_date"], "%Y-%m-%d")
    today = datetime.now().date()
    fine = 0.0
    days_overdue = (today - due_date.date()).days
    if days_overdue > 0:
        fine = days_overdue * FINE_RATE_PER_DAY

    # 4. Mark loan as returned
    return_loan(loan["id"])

    # 5. Increase available copies
    item.available_copies += 1
    save_item(item)

    # 6. Remove from user's borrowed list
    user.return_item(item_id)
    save_user(user)

    fine_msg = f" (Overdue by {days_overdue} days. Fine: £{fine:.2f})" if fine > 0 else " (Returned on time)"
    return True, f"Successfully returned '{item.title}'{fine_msg}", fine


def get_user_borrowing_history(user_id: int) -> List[Dict]:
    """
    Get the full borrowing history of a user (including returned items).
    """
    all_loans = get_all_loans()
    user_loans = [loan for loan in all_loans if loan["user_id"] == user_id]
    
    result = []
    for loan in user_loans:
        item = get_item_by_id(loan["item_id"])
        item_title = item.title if item else "Unknown Item"
        result.append({
            "item_title": item_title,
            "borrow_date": loan["borrow_date"],
            "due_date": loan["due_date"],
            "returned": bool(loan["returned"]),
            "loan_id": loan["id"]
        })
    return result


# ========== RECOMMENDATION ENGINE ==========

def get_recommendations(user_id: int, limit: int = 5) -> List[Dict]:
    """
    Get personalized recommendations for a user using collaborative filtering.
    
    Algorithm:
    1. Find all items the user has borrowed.
    2. Find all users who borrowed those same items.
    3. Find all items those users borrowed.
    4. Exclude items the user already borrowed.
    5. Rank by popularity (how many of those users borrowed it).
    6. Return top 'limit' recommendations with item details.
    """
    # 1. Get items this user has already borrowed
    user_items = get_items_borrowed_by_user(user_id)
    if not user_items:
        return []  # No history, can't recommend
    
    # 2. Find all users who borrowed those items (excluding the user themselves)
    similar_users = []
    for item_id in user_items:
        users = get_users_who_borrowed_item(item_id)
        similar_users.extend([u for u in users if u != user_id])
    
    # Remove duplicates
    similar_users = list(set(similar_users))
    if not similar_users:
        return []  # No other users with similar borrowing history
    
    # 3. Get all items borrowed by these similar users
    similar_user_items = get_items_borrowed_by_users(similar_users)
    
    # 4. Exclude items the user already borrowed
    recommendation_ids = [item_id for item_id in similar_user_items if item_id not in user_items]
    
    if not recommendation_ids:
        return []  # No new items to recommend
    
    # 5. Rank by popularity (count how many similar users borrowed each item)
    popularity = Counter()
    for item_id in recommendation_ids:
        # Count how many of the similar users borrowed this item
        borrowers = get_users_who_borrowed_item(item_id)
        count = len([u for u in borrowers if u in similar_users])
        popularity[item_id] = count
    
    # Sort by popularity (highest first)
    sorted_recommendations = sorted(popularity.items(), key=lambda x: x[1], reverse=True)
    
    # 6. Get item details for the top 'limit' recommendations
    results = []
    for item_id, score in sorted_recommendations[:limit]:
        item = get_item_by_id(item_id)
        if item:
            results.append({
                "id": item.id,
                "title": item.title,
                "type": item.get_item_type(),
                "author": item.author or "N/A",
                "year": item.year or "N/A",
                "available": item.available_copies,
                "score": score,  # How many similar users borrowed it
                "reason": f"Recommended because {score} similar users borrowed it"
            })
    
    return results
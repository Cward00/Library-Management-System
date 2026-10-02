import sqlite3
from typing import List, Optional, Union
from src.database.connection import get_connection
from src.models.book import Book
from src.models.dvd import DVD
from src.models.journal import Journal
from src.models.user import User
from src.models.library_item import LibraryItem


# ========== HELPER: Convert DB row to Python object ==========

def _row_to_item(row: sqlite3.Row) -> Optional[LibraryItem]:
    """Convert a database row into the correct LibraryItem subclass."""
    item_type = row["item_type"]
    
    # Create the appropriate object based on type
    if item_type == "book":
        return Book(
            id=row["id"],
            title=row["title"],
            author=row["author"],
            year=row["year"],
            total_copies=row["total_copies"],
            available_copies=row["available_copies"]
        )
    elif item_type == "dvd":
        return DVD(
            id=row["id"],
            title=row["title"],
            author=row["author"],
            year=row["year"],
            total_copies=row["total_copies"],
            available_copies=row["available_copies"]
        )
    elif item_type == "journal":
        return Journal(
            id=row["id"],
            title=row["title"],
            author=row["author"],
            year=row["year"],
            total_copies=row["total_copies"],
            available_copies=row["available_copies"]
        )
    return None


def _row_to_user(row: sqlite3.Row) -> User:
    """Convert a database row into a User object."""
    return User(
        id=row["id"],
        username=row["username"],
        join_date=row["join_date"]
    )


# ========== ITEM CRUD OPERATIONS ==========

def save_item(item: LibraryItem) -> int:
    """
    Save an item to the database.
    If item.id is None, insert a new record.
    If item.id exists, update the existing record.
    Returns the ID of the saved item.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    if item.id is None:
        # INSERT new item
        cursor.execute('''
            INSERT INTO items (title, item_type, author, year, total_copies, available_copies)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            item.title,
            item.get_item_type(),
            item.author,
            item.year,
            item.total_copies,
            item.available_copies
        ))
        item.id = cursor.lastrowid
    else:
        # UPDATE existing item
        cursor.execute('''
            UPDATE items
            SET title = ?, item_type = ?, author = ?, year = ?,
                total_copies = ?, available_copies = ?
            WHERE id = ?
        ''', (
            item.title,
            item.get_item_type(),
            item.author,
            item.year,
            item.total_copies,
            item.available_copies,
            item.id
        ))
    
    conn.commit()
    conn.close()
    return item.id


def get_item_by_id(item_id: int) -> Optional[LibraryItem]:
    """Retrieve a single item by its ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM items WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return _row_to_item(row)
    return None


def get_all_items() -> List[LibraryItem]:
    """Retrieve all items from the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM items ORDER BY title")
    rows = cursor.fetchall()
    conn.close()
    
    return [_row_to_item(row) for row in rows if _row_to_item(row) is not None]


def search_items_by_title(query: str) -> List[LibraryItem]:
    """Search for items whose title contains the query string (case-insensitive)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM items WHERE title LIKE ? ORDER BY title",
        (f"%{query}%",)
    )
    rows = cursor.fetchall()
    conn.close()
    
    return [_row_to_item(row) for row in rows if _row_to_item(row) is not None]


def delete_item(item_id: int) -> bool:
    """Delete an item by ID. Returns True if deleted, False if not found."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


# ========== USER CRUD OPERATIONS ==========

def save_user(user: User) -> int:
    """
    Save a user to the database. 
    If the username already exists, update that user.
    Otherwise, insert a new user.
    Returns the ID of the saved user.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # First, check if this username already exists
    existing = get_user_by_username(user.username)
    
    if existing:
        # Username exists - update the existing record
        cursor.execute('''
            UPDATE users SET username = ? WHERE id = ?
        ''', (user.username, existing.id))
        user.id = existing.id
    else:
        # Username is new - insert it
        cursor.execute('''
            INSERT INTO users (username, join_date)
            VALUES (?, DATE('now'))
        ''', (user.username,))
        user.id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    return user.id


def get_user_by_id(user_id: int) -> Optional[User]:
    """Retrieve a user by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return _row_to_user(row)
    return None


def get_user_by_username(username: str) -> Optional[User]:
    """Retrieve a user by username (case-insensitive)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (username,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return _row_to_user(row)
    return None


def get_all_users() -> List[User]:
    """Retrieve all users."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users ORDER BY username")
    rows = cursor.fetchall()
    conn.close()
    
    return [_row_to_user(row) for row in rows]


# ========== LOAN CRUD OPERATIONS ==========

def create_loan(user_id: int, item_id: int, due_date: str) -> int:
    """
    Create a new loan record.
    Returns the loan ID.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO loans (user_id, item_id, due_date)
        VALUES (?, ?, ?)
    ''', (user_id, item_id, due_date))
    loan_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return loan_id


def get_active_loan(user_id: int, item_id: int):
    """
    Get the active (not returned) loan for a specific user and item.
    Returns the row as a dict, or None if no active loan.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM loans
        WHERE user_id = ? AND item_id = ? AND returned = 0
        ORDER BY borrow_date DESC LIMIT 1
    ''', (user_id, item_id))
    row = cursor.fetchone()
    conn.close()
    return row


def get_active_loans_for_user(user_id: int) -> List:
    """
    Get all active (not returned) loans for a user.
    Returns a list of rows.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM loans
        WHERE user_id = ? AND returned = 0
        ORDER BY borrow_date DESC
    ''', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_active_loans_for_item(item_id: int) -> List:
    """
    Get all active (not returned) loans for a specific item.
    Returns a list of loan rows.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM loans
        WHERE item_id = ? AND returned = 0
    ''', (item_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def return_loan(loan_id: int) -> None:
    """
    Mark a loan as returned.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE loans SET returned = 1
        WHERE id = ?
    ''', (loan_id,))
    conn.commit()
    conn.close()


def get_all_loans() -> List:
    """
    Get all loan records (for reporting/history).
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM loans ORDER BY borrow_date DESC
    ''')
    rows = cursor.fetchall()
    conn.close()
    return rows


# ========== RECOMMENDATION ENGINE HELPER FUNCTIONS ==========

def get_items_borrowed_by_user(user_id: int) -> List[int]:
    """
    Get all item IDs that a user has borrowed (both active and returned).
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT DISTINCT item_id FROM loans
        WHERE user_id = ?
    ''', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [row["item_id"] for row in rows]


def get_users_who_borrowed_item(item_id: int) -> List[int]:
    """
    Get all user IDs who have borrowed a specific item.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT DISTINCT user_id FROM loans
        WHERE item_id = ?
    ''', (item_id,))
    rows = cursor.fetchall()
    conn.close()
    return [row["user_id"] for row in rows]


def get_items_borrowed_by_users(user_ids: List[int]) -> List[int]:
    """
    Get all item IDs borrowed by a list of users.
    """
    if not user_ids:
        return []
    placeholders = ",".join(["?"] * len(user_ids))
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f'''
        SELECT DISTINCT item_id FROM loans
        WHERE user_id IN ({placeholders})
    ''', user_ids)
    rows = cursor.fetchall()
    conn.close()
    return [row["item_id"] for row in rows]
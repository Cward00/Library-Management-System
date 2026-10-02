"""
SEED DATA SCRIPT
Run this to populate your database with realistic data for testing the recommendation engine.
WARNING: This will DELETE all existing loans, items, and users from your database!
"""

from datetime import datetime, timedelta
import random
from rich.console import Console
from rich.panel import Panel

from src.database.connection import init_database, get_connection
from src.database.data_access import (
    save_user, save_item, create_loan, 
    get_user_by_username, get_all_users, get_all_items
)
from src.models.user import User
from src.models.book import Book
from src.models.dvd import DVD
from src.models.journal import Journal

console = Console()

# ------------------- DATA DEFINITIONS -------------------

USERS = [
    {"username": "alice_sci_fi"},
    {"username": "bob_tech"},
    {"username": "charlie_fantasy"},
    {"username": "diana_movies"},
    {"username": "eve_academic"},
]

ITEMS = [
    # Sci-Fi Books
    Book(title="Dune", author="Frank Herbert", year=1965, total_copies=3, available_copies=3),
    Book(title="Neuromancer", author="William Gibson", year=1984, total_copies=2, available_copies=2),
    Book(title="The Martian", author="Andy Weir", year=2011, total_copies=4, available_copies=4),
    # Tech Books
    Book(title="Clean Code", author="Robert Martin", year=2008, total_copies=3, available_copies=3),
    Book(title="The Pragmatic Programmer", author="Andy Hunt", year=1999, total_copies=2, available_copies=2),
    Book(title="Design Patterns", author="Erich Gamma", year=1994, total_copies=1, available_copies=1),
    # Fantasy Books
    Book(title="The Hobbit", author="J.R.R. Tolkien", year=1937, total_copies=5, available_copies=5),
    Book(title="The Way of Kings", author="Brandon Sanderson", year=2010, total_copies=3, available_copies=3),
    # Classics & Fiction
    Book(title="1984", author="George Orwell", year=1949, total_copies=3, available_copies=3),
    Book(title="To Kill a Mockingbird", author="Harper Lee", year=1960, total_copies=2, available_copies=2),
    # DVDs
    DVD(title="Inception", author="Christopher Nolan", year=2010, total_copies=4, available_copies=4),
    DVD(title="The Matrix", author="Lana Wachowski", year=1999, total_copies=3, available_copies=3),
    DVD(title="Interstellar", author="Christopher Nolan", year=2014, total_copies=2, available_copies=2),
    DVD(title="The Shining", author="Stanley Kubrick", year=1980, total_copies=2, available_copies=2),
    # Journals
    Journal(title="Nature: AI Special", author="Various", year=2023, total_copies=1, available_copies=1),
    Journal(title="IEEE Software", author="Various", year=2024, total_copies=2, available_copies=2),
]

# Pre-defined borrowing history to create overlapping patterns
# Format: (username, item_title, days_ago_borrowed, days_ago_returned)
# If returned is None, it is still active (checked out)
LOAN_HISTORY = [
    # Alice (Sci-Fi lover) borrows sci-fi books
    ("alice_sci_fi", "Dune", 30, 25),
    ("alice_sci_fi", "Neuromancer", 20, 15),
    ("alice_sci_fi", "The Matrix", 10, 5),
    ("alice_sci_fi", "The Martian", 5, None),  # Currently borrowed
    
    # Bob (Tech lover) borrows tech books
    ("bob_tech", "Clean Code", 28, 22),
    ("bob_tech", "Design Patterns", 18, 12),
    ("bob_tech", "The Pragmatic Programmer", 8, None), # Currently borrowed
    ("bob_tech", "IEEE Software", 15, 10),
    ("bob_tech", "The Martian", 3, None),  # Overlap with Alice! (both like it)
    
    # Charlie (Fantasy + Sci-Fi)
    ("charlie_fantasy", "The Hobbit", 25, 20),
    ("charlie_fantasy", "The Way of Kings", 15, 10),
    ("charlie_fantasy", "Interstellar", 7, 2),
    ("charlie_fantasy", "The Martian", 12, 8),  # Overlap with Alice & Bob
    ("charlie_fantasy", "Dune", 2, None),       # Currently borrowed
    
    # Diana (Movies + Classics)
    ("diana_movies", "Inception", 22, 18),
    ("diana_movies", "The Shining", 14, 10),
    ("diana_movies", "1984", 6, None),           # Currently borrowed
    ("diana_movies", "Interstellar", 1, None),   # Currently borrowed (overlap with Charlie)
    ("diana_movies", "To Kill a Mockingbird", 30, 25),
    
    # Eve (Academic + Wide reader)
    ("eve_academic", "Nature: AI Special", 20, 15),
    ("eve_academic", "IEEE Software", 10, 5),
    ("eve_academic", "Clean Code", 5, None),      # Overlap with Bob
    ("eve_academic", "Dune", 14, 10),             # Overlap with Alice/Charlie
    ("eve_academic", "The Matrix", 9, 4),         # Overlap with Alice
]

# ------------------- SEEDING LOGIC -------------------

def clear_database():
    """Wipe existing data cleanly (respect foreign keys)."""
    conn = get_connection()
    cursor = conn.cursor()
    
    console.print("[yellow]Clearing existing loans, users, and items...[/yellow]")
    cursor.execute("DELETE FROM loans")
    cursor.execute("DELETE FROM items")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='items'")  # Reset IDs
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='users'")
    cursor.execute("DELETE FROM users")
    
    conn.commit()
    conn.close()
    console.print("[green]Database cleared![/green]")


def seed_users():
    """Create all users and return a dict {username: user_id}."""
    console.print("[cyan]Seeding users...[/cyan]")
    user_ids = {}
    for user_data in USERS:
        username = user_data["username"]
        user = User(username=username)
        user_id = save_user(user)
        user_ids[username] = user_id
        console.print(f"  ✅ Created user: {username} (ID: {user_id})")
    return user_ids


def seed_items():
    """Create all items and return a dict {item_title: item_id}."""
    console.print("[cyan]Seeding items...[/cyan]")
    item_ids = {}
    for item in ITEMS:
        item_id = save_item(item)
        item_ids[item.title] = item_id
        console.print(f"  ✅ Created item: {item.title} (ID: {item_id})")
    return item_ids


def seed_loans(user_ids, item_ids):
    """Create the loan history based on the LOAN_HISTORY definitions."""
    console.print("[cyan]Seeding loans...[/cyan]")
    today = datetime.now().date()
    
    # Build a map of item titles to item objects
    item_obj_map = {item.title: item for item in ITEMS}
    
    for entry in LOAN_HISTORY:
        username, title, days_ago_borrow, days_ago_return = entry
        
        user_id = user_ids.get(username)
        item_obj = item_obj_map.get(title)
        if not user_id or not item_obj:
            console.print(f"  [red]Skipping invalid entry: {username} - {title}[/red]")
            continue
        
        item_id = item_ids.get(title)
        if not item_id:
            console.print(f"  [red]Skipping: Item ID not found for {title}[/red]")
            continue
        
        # Calculate dates
        borrow_date = today - timedelta(days=days_ago_borrow)
        due_days = item_obj.get_borrowing_days()
        due_date = borrow_date + timedelta(days=due_days)
        
        # Create the loan
        loan_id = create_loan(user_id, item_id, due_date.strftime("%Y-%m-%d"))
        
        # If returned, mark it as returned
        if days_ago_return is not None:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE loans 
                SET returned = 1, borrow_date = ? 
                WHERE id = ?
            """, (borrow_date.strftime("%Y-%m-%d"), loan_id))
            conn.commit()
            conn.close()
            status = "Returned"
        else:
            # Active loan - update borrow_date
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE loans 
                SET borrow_date = ? 
                WHERE id = ?
            """, (borrow_date.strftime("%Y-%m-%d"), loan_id))
            conn.commit()
            conn.close()
            status = "Active"
        
        console.print(f"  ✅ Created loan: {username} -> {title} ({status})")


def main():
    """Run the seeding process."""
    console.print(Panel.fit("🌱 DATABASE SEEDER", style="bold green"))
    
    # Warning
    console.print("[bold red]WARNING: This will DELETE all existing data![/bold red]")
    confirm = input("Type 'yes' to proceed: ")
    if confirm.lower() != 'yes':
        console.print("[yellow]Seeding cancelled.[/yellow]")
        return
    
    # Initialize DB
    init_database()
    
    # Clear everything
    clear_database()
    
    # Seed in order
    user_ids = seed_users()
    item_ids = seed_items()
    seed_loans(user_ids, item_ids)
    
    # Summary
    console.print(Panel.fit("✅ SEEDING COMPLETE!", style="bold green"))
    console.print(f"[bold]Users created:[/bold] {len(user_ids)}")
    console.print(f"[bold]Items created:[/bold] {len(item_ids)}")
    console.print(f"[bold]Loans created:[/bold] {len(LOAN_HISTORY)}")
    
    console.print("\n[cyan]You can now run your Library System and check the data![/cyan]")


if __name__ == "__main__":
    main()
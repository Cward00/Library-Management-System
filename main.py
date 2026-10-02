from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.panel import Panel
from rich import box
import sys
import os

# Import your database and services
from src.database.connection import init_database
from src.database.data_access import (
    get_all_items, search_items_by_title, save_item, 
    get_user_by_username, save_user, get_all_users,
    get_user_by_id, delete_item, get_active_loans_for_item,
    get_item_by_id
)
from src.services.borrowing_service import borrow_item, return_item, get_user_borrowing_history, get_recommendations
from src.models.book import Book
from src.models.dvd import DVD
from src.models.journal import Journal
from src.models.user import User

# Initialize the console for rich output
console = Console()

# Global variable to track the logged-in user
current_user = None


# ========== UI Helper Functions ==========

def print_header(title: str):
    """Print a fancy header."""
    console.print(Panel(title, style="bold cyan", border_style="blue"))


def print_success(message: str):
    """Print a success message in green."""
    console.print(f"[green]✅ {message}[/green]")


def print_error(message: str):
    """Print an error message in red."""
    console.print(f"[red]❌ {message}[/red]")


def print_info(message: str):
    """Print an info message in yellow."""
    console.print(f"[yellow]ℹ️  {message}[/yellow]")


# ========== Menu Actions ==========

def login_user():
    """Log in or register a new user."""
    global current_user
    
    print_header("👤 LOGIN / REGISTER")
    
    username = Prompt.ask("[cyan]Enter your username[/cyan]").strip()
    if not username:
        print_error("Username cannot be empty.")
        return
    
    # Check if user exists
    user = get_user_by_username(username)
    
    if user:
        current_user = user
        print_success(f"Welcome back, {user.username}! (ID: {user.id})")
    else:
        # Create new user
        print_info(f"User '{username}' not found. Creating new account...")
        user = User(username=username)
        user_id = save_user(user)
        current_user = get_user_by_id(user_id)  # Refresh to get ID
        print_success(f"Account created! Welcome, {username}! (ID: {user.id})")


def view_all_items():
    """Display all items in the library."""
    print_header("📚 ALL LIBRARY ITEMS")
    
    items = get_all_items()
    if not items:
        print_info("No items in the library yet.")
        return
    
    table = Table(title="Library Catalog", box=box.ROUNDED)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="bold white")
    table.add_column("Type", style="yellow")
    table.add_column("Author", style="green")
    table.add_column("Year", style="blue")
    table.add_column("Available", style="magenta")
    
    for item in items:
        available_str = f"{item.available_copies}/{item.total_copies}"
        table.add_row(
            str(item.id),
            item.title,
            item.get_item_type(),
            item.author or "N/A",
            str(item.year or "N/A"),
            available_str
        )
    
    console.print(table)


def search_items():
    """Search for items by title."""
    print_header("🔍 SEARCH ITEMS")
    
    query = Prompt.ask("[cyan]Enter search term[/cyan]").strip()
    if not query:
        print_error("Search term cannot be empty.")
        return
    
    results = search_items_by_title(query)
    if not results:
        print_info(f"No items found matching '{query}'.")
        return
    
    table = Table(title=f"Search Results for '{query}'", box=box.ROUNDED)
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="bold white")
    table.add_column("Type", style="yellow")
    table.add_column("Author", style="green")
    table.add_column("Available", style="magenta")
    
    for item in results:
        available_str = f"{item.available_copies}/{item.total_copies}"
        table.add_row(
            str(item.id),
            item.title,
            item.get_item_type(),
            item.author or "N/A",
            available_str
        )
    
    console.print(table)


def add_item():
    """Add a new item to the library."""
    print_header("➕ ADD NEW ITEM")
    
    # Choose type
    item_type = Prompt.ask(
        "[cyan]Select item type[/cyan]",
        choices=["book", "dvd", "journal"],
        default="book"
    )
    
    title = Prompt.ask("[cyan]Title[/cyan]").strip()
    if not title:
        print_error("Title cannot be empty.")
        return
    
    author = Prompt.ask("[cyan]Author[/cyan] (optional)").strip()
    year_input = Prompt.ask("[cyan]Year[/cyan] (optional)", default="")
    year = int(year_input) if year_input.isdigit() else None
    
    copies_input = IntPrompt.ask("[cyan]Number of copies[/cyan]", default=1)
    copies = copies_input if copies_input > 0 else 1
    
    # Create the appropriate object
    if item_type == "book":
        item = Book(title=title, author=author or None, year=year, total_copies=copies, available_copies=copies)
    elif item_type == "dvd":
        item = DVD(title=title, author=author or None, year=year, total_copies=copies, available_copies=copies)
    else:  # journal
        item = Journal(title=title, author=author or None, year=year, total_copies=copies, available_copies=copies)
    
    # Save to database
    item_id = save_item(item)
    print_success(f"'{title}' added successfully! (ID: {item_id})")


def borrow_item_action():
    """Borrow an item (requires logged-in user)."""
    global current_user
    
    if not current_user:
        print_error("You must be logged in to borrow items. Please Login first.")
        return
    
    print_header("📖 BORROW AN ITEM")
    
    item_id = IntPrompt.ask("[cyan]Enter the Item ID to borrow[/cyan]")
    if item_id <= 0:
        print_error("Invalid ID.")
        return
    
    success, message = borrow_item(current_user.id, item_id)
    if success:
        print_success(message)
    else:
        print_error(message)


def return_item_action():
    """Return an item (requires logged-in user)."""
    global current_user
    
    if not current_user:
        print_error("You must be logged in to return items. Please Login first.")
        return
    
    print_header("📤 RETURN AN ITEM")
    
    # Show currently borrowed items
    history = get_user_borrowing_history(current_user.id)
    active_items = [h for h in history if not h["returned"]]
    
    if not active_items:
        print_info("You have no items currently borrowed.")
        return
    
    print_info("Your currently borrowed items:")
    for idx, record in enumerate(active_items, 1):
        console.print(f"  {idx}. [bold]{record['item_title']}[/bold] (Due: {record['due_date']})")
    
    # Allow user to choose by title or ID
    # Let's just ask for the item ID directly for simplicity
    item_id = IntPrompt.ask("[cyan]Enter the Item ID to return[/cyan]")
    if item_id <= 0:
        print_error("Invalid ID.")
        return
    
    success, message, fine = return_item(current_user.id, item_id)
    if success:
        print_success(message)
        if fine > 0:
            console.print(f"[bold red]💰 Fine charged: £{fine:.2f}[/bold red]")
    else:
        print_error(message)


def view_my_history():
    """View the logged-in user's borrowing history."""
    global current_user
    
    if not current_user:
        print_error("You must be logged in to view your history.")
        return
    
    print_header(f"📜 BORROWING HISTORY: {current_user.username}")
    
    history = get_user_borrowing_history(current_user.id)
    if not history:
        print_info("No borrowing history found.")
        return
    
    table = Table(title=f"History for {current_user.username}", box=box.ROUNDED)
    table.add_column("Item", style="bold white")
    table.add_column("Borrowed", style="cyan")
    table.add_column("Due", style="yellow")
    table.add_column("Status", style="green")
    
    for record in history:
        status = "[green]Returned[/green]" if record["returned"] else "[red]Active[/red]"
        table.add_row(
            record["item_title"],
            record["borrow_date"],
            record["due_date"],
            status
        )
    
    console.print(table)


def switch_user():
    """Switch to a different user."""
    global current_user
    current_user = None
    print_info("Logged out. Please login again.")
    login_user()


def delete_item_action():
    """Delete an item from the library."""
    print_header("🗑️ DELETE AN ITEM")
    
    # Show all items first so the user knows what to delete
    items = get_all_items()
    if not items:
        print_info("No items in the library to delete.")
        return
    
    # Display items in a table
    table = Table(title="Existing Items", box=box.ROUNDED)
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="bold white")
    table.add_column("Type", style="yellow")
    table.add_column("Available", style="magenta")
    for item in items:
        available_str = f"{item.available_copies}/{item.total_copies}"
        table.add_row(
            str(item.id),
            item.title,
            item.get_item_type(),
            available_str
        )
    console.print(table)
    
    # Ask for ID
    item_id = IntPrompt.ask("[cyan]Enter the Item ID to delete[/cyan]")
    if item_id <= 0:
        print_error("Invalid ID.")
        return
    
    # Check if item exists
    item = get_item_by_id(item_id)
    if not item:
        print_error(f"Item with ID {item_id} not found.")
        return
    
    # Check if item is currently borrowed (important!)
    active_loans = get_active_loans_for_item(item_id)
    if active_loans:
        print_error(f"Cannot delete '{item.title}' because it is currently borrowed (someone has it out). Please return it first.")
        return
    
    # Confirm deletion (safety check)
    confirm = Confirm.ask(f"[bold red]Are you sure you want to permanently delete '{item.title}'?[/bold red]")
    if not confirm:
        print_info("Deletion cancelled.")
        return
    
    # Do the actual delete
    success = delete_item(item_id)
    if success:
        print_success(f"'{item.title}' deleted successfully.")
    else:
        print_error(f"Failed to delete item ID {item_id}.")


def view_recommendations():
    """Show personalized recommendations for the current user."""
    global current_user
    
    if not current_user:
        print_error("You must be logged in to get recommendations.")
        return
    
    print_header("🎯 PERSONALIZED RECOMMENDATIONS")
    
    recommendations = get_recommendations(current_user.id)
    
    if not recommendations:
        print_info("Not enough borrowing history to generate recommendations yet.")
        print_info("Borrow more items to get personalized suggestions!")
        return
    
    table = Table(title=f"Recommendations for {current_user.username}", box=box.ROUNDED)
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="bold white")
    table.add_column("Type", style="yellow")
    table.add_column("Author", style="green")
    table.add_column("Available", style="magenta")
    table.add_column("Why?", style="blue")
    
    for rec in recommendations:
        available = "✅ In stock" if rec["available"] > 0 else "❌ Unavailable"
        table.add_row(
            str(rec["id"]),
            rec["title"],
            rec["type"],
            rec["author"],
            available,
            f"{rec['score']} similar users"
        )
    
    console.print(table)
    print_info("💡 Tip: Borrow items you like to improve future recommendations!")


# ========== Main Menu ==========

def show_menu():
    """Display the main menu options."""
    console.print("\n" + "=" * 50)
    if current_user:
        console.print(f"[bold green]Logged in as: {current_user.username} (ID: {current_user.id})[/bold green]")
    else:
        console.print("[bold red]Not logged in[/bold red]")
    console.print("=" * 50)
    console.print("[1] 📚 View all items")
    console.print("[2] 🔍 Search items")
    console.print("[3] ➕ Add new item")
    console.print("[4] 📖 Borrow an item")
    console.print("[5] 📤 Return an item")
    console.print("[6] 📜 My borrowing history")
    console.print("[7] 👤 Switch user")
    console.print("[8] 🗑️  Delete an item")
    console.print("[9] 🎯 Get recommendations")
    console.print("[10] 🚪 Exit")
    console.print("=" * 50)


def main():
    """Main application loop."""
    global current_user
    
    # Initialize database
    init_database()
    
    # Welcome
    console.print(Panel.fit("📚 WELCOME TO THE LIBRARY MANAGEMENT SYSTEM 📚", style="bold cyan"))
    
    # First-time login
    login_user()
    
    while True:
        show_menu()
        choice = Prompt.ask(
            "[cyan]Choose an option[/cyan]", 
            choices=["1","2","3","4","5","6","7","8","9","10"], 
            default="10"
        )
        
        if choice == "1":
            view_all_items()
        elif choice == "2":
            search_items()
        elif choice == "3":
            add_item()
        elif choice == "4":
            borrow_item_action()
        elif choice == "5":
            return_item_action()
        elif choice == "6":
            view_my_history()
        elif choice == "7":
            switch_user()
        elif choice == "8":
            delete_item_action()
        elif choice == "9":
            view_recommendations()
        elif choice == "10":
            console.print("[bold yellow]Goodbye! 📚[/bold yellow]")
            sys.exit(0)
        
        # Pause before showing menu again
        if choice != "10":
            input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()
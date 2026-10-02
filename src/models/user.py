from dataclasses import dataclass
from typing import Optional, List

@dataclass
class User:
    """Represents a library member."""
    id: Optional[int] = None
    username: str = ""
    join_date: str = ""
    borrowed_item_ids: List[int] = None  # Stores IDs of items currently borrowed

    def __post_init__(self):
        if self.borrowed_item_ids is None:
            self.borrowed_item_ids = []

    def can_borrow(self) -> bool:
        """A user can borrow up to 5 items at once."""
        return len(self.borrowed_item_ids) < 5

    def borrow_item(self, item_id: int) -> bool:
        """Add item to borrowed list. Returns True if successful."""
        if self.can_borrow() and item_id not in self.borrowed_item_ids:
            self.borrowed_item_ids.append(item_id)
            return True
        return False

    def return_item(self, item_id: int) -> bool:
        """Remove item from borrowed list. Returns True if found."""
        if item_id in self.borrowed_item_ids:
            self.borrowed_item_ids.remove(item_id)
            return True
        return False

    def __str__(self) -> str:
        return f"User: {self.username} (Borrowed: {len(self.borrowed_item_ids)} items)"
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

@dataclass
class LibraryItem(ABC):
    """Abstract base class for all library items."""
    id: Optional[int] = None
    title: str = ""
    author: Optional[str] = None
    year: Optional[int] = None
    total_copies: int = 1
    available_copies: int = 1

    @abstractmethod
    def get_item_type(self) -> str:
        """Return the type of item (book, dvd, journal)."""
        pass

    @abstractmethod
    def get_borrowing_days(self) -> int:
        """Return how many days this item can be borrowed for."""
        pass

    def is_available(self) -> bool:
        """Check if at least one copy is available."""
        return self.available_copies > 0

    def borrow_copy(self) -> bool:
        """Borrow one copy. Returns True if successful."""
        if self.is_available():
            self.available_copies -= 1
            return True
        return False

    def return_copy(self) -> None:
        """Return one copy."""
        if self.available_copies < self.total_copies:
            self.available_copies += 1

    def __str__(self) -> str:
        return f"{self.get_item_type().title()}: {self.title} by {self.author or 'Unknown'} ({self.year or 'N/A'})"
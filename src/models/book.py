from .library_item import LibraryItem

class Book(LibraryItem):
    def get_item_type(self) -> str:
        return "book"

    def get_borrowing_days(self) -> int:
        return 14  # Books can be borrowed for 2 weeks
from .library_item import LibraryItem

class Journal(LibraryItem):
    def get_item_type(self) -> str:
        return "journal"

    def get_borrowing_days(self) -> int:
        return 7  # Journals for 1 week
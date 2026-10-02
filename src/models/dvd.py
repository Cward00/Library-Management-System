from .library_item import LibraryItem

class DVD(LibraryItem):
    def get_item_type(self) -> str:
        return "dvd"

    def get_borrowing_days(self) -> int:
        return 5  # DVDs for 5 days
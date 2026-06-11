from abc import ABC, abstractmethod

class BrowserAccess(ABC):
    @abstractmethod
    def open_url(self, url: str) -> None:
        """
        Open the specified URL in a web browser.
        Args:
            url: The URL to open.
        """
        pass

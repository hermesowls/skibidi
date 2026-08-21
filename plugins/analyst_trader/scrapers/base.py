"""Base Analyst Scraper Interface for Discord Trade Alerts."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseAnalystScraper(ABC):
    """Abstract base class for analyst-specific trade alert scrapers."""

    def __init__(self, analyst_name: str) -> None:
        self.analyst_name = analyst_name

    @abstractmethod
    def extract_candidates(self, message: Dict[str, Any], context_history: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """Extract candidate trade signals from a Discord message and optional surrounding context."""
        pass

"""Per-Analyst Trade Alert Scrapers Package."""

from plugins.analyst_trader.scrapers.base import BaseAnalystScraper
from plugins.analyst_trader.scrapers.eva import EvaScraper
from plugins.analyst_trader.scrapers.ab import ABScraper
from plugins.analyst_trader.scrapers.muggzone import MuggzoneScraper
from plugins.analyst_trader.scrapers.jon_kian import JonKianScraper
from plugins.analyst_trader.scrapers.generic import GenericScraper


def get_scraper_for_analyst(analyst_name: str) -> BaseAnalystScraper:
    """Factory function returning dedicated scraper for analyst."""
    name_clean = analyst_name.lower().replace("🌟｜", "").replace("🛎️｜", "").strip()

    if "eva" in name_clean:
        return EvaScraper()
    elif "ab" in name_clean:
        return ABScraper()
    elif "muggzone" in name_clean:
        return MuggzoneScraper()
    elif "jon" in name_clean or "kian" in name_clean:
        return JonKianScraper()
    else:
        return GenericScraper(analyst_name)

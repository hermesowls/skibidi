"""Unit tests for per-analyst scrapers and LLM reviewer agent."""

import unittest
from plugins.analyst_trader.scrapers.eva import EvaScraper
from plugins.analyst_trader.scrapers.ab import ABScraper
from plugins.analyst_trader.scrapers.muggzone import MuggzoneScraper
from plugins.analyst_trader.scrapers.jon_kian import JonKianScraper
from plugins.analyst_trader.llm_reviewer import LLMTradeReviewer


class TestAnalystScrapers(unittest.TestCase):

    def test_eva_scraper(self):
        scraper = EvaScraper()
        msg = {
            "embeds": [{
                "title": "Open",
                "description": "BTO QQQ 08/21/2026 750C @ 0.54 (lotto)"
            }]
        }
        candidates = scraper.extract_candidates(msg)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["ticker"], "QQQ")
        self.assertEqual(candidates[0]["strike"], 750.0)
        self.assertEqual(candidates[0]["price"], 0.54)

    def test_ab_scraper(self):
        scraper = ABScraper()
        msg = {
            "content": "$BIDU 9/18 130c 3.15\n$CVNA 8/21 70c 100% - closed"
        }
        candidates = scraper.extract_candidates(msg)
        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0]["ticker"], "BIDU")
        self.assertEqual(candidates[0]["action"], "ENTRY")
        self.assertEqual(candidates[1]["ticker"], "CVNA")
        self.assertEqual(candidates[1]["action"], "EXIT")

    def test_muggzone_scraper(self):
        scraper = MuggzoneScraper()
        msg = {
            "content": "CMG Calls up 24% @everyone"
        }
        candidates = scraper.extract_candidates(msg)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["ticker"], "CMG")
        self.assertEqual(candidates[0]["action"], "TRIM")
        self.assertEqual(candidates[0]["pct_roi"], 24.0)

    def test_jon_kian_scraper(self):
        scraper = JonKianScraper()
        msg = {
            "content": "BTO RARE 50C 11/20exp 2 premium"
        }
        candidates = scraper.extract_candidates(msg)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["ticker"], "RARE")
        self.assertEqual(candidates[0]["strike"], 50.0)
        self.assertEqual(candidates[0]["price"], 2.0)

    def test_llm_reviewer_fallback(self):
        reviewer = LLMTradeReviewer()
        candidate = {
            "action": "ENTRY",
            "ticker": "QQQ",
            "strike": 750.0,
            "analyst_name": "Eva"
        }
        res = reviewer.review_candidate(candidate)
        self.assertTrue(res["valid_signal"])
        self.assertGreaterEqual(res["confidence_score"], 0.80)
        self.assertEqual(res["verification_status"], "VERIFIED")


if __name__ == "__main__":
    unittest.main()

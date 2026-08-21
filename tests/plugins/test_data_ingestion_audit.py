import unittest
import os
import requests
from pathlib import Path

class TestDataIngestionAudit(unittest.TestCase):
    def setUp(self):
        self.tickers = ["METC", "NOK", "FRMI", "QURE"]
        self.databento_key = self._get_databento_key()

    def _get_databento_key(self) -> str:
        key = os.getenv("DATABENTO_API_KEY")
        if key:
            return key
        env_file = Path.home() / ".hermes" / ".env"
        if env_file.exists():
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("DATABENTO_API_KEY="):
                        return line.strip().split("=", 1)[1].strip("\"'")
        return ""

    def test_01_databento_l2_authentication(self):
        """Verify Databento API key and L2 dataset access."""
        self.assertTrue(bool(self.databento_key), "DATABENTO_API_KEY must be configured in .env")
        import databento as db
        client = db.Historical(key=self.databento_key)
        datasets = client.metadata.list_datasets()
        self.assertIsInstance(datasets, list)
        self.assertGreater(len(datasets), 0, "Databento datasets list must not be empty")

    def test_02_finviz_data_ingestion(self):
        """Verify Finviz real-time data ingestion for target tickers."""
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        for ticker in self.tickers:
            url = f"https://finviz.com/quote.ashx?t={ticker}"
            resp = requests.get(url, headers=headers, timeout=10)
            self.assertEqual(resp.status_code, 200, f"Finviz returned HTTP {resp.status_code} for {ticker}")
            self.assertIn("quote-price", resp.text, f"Finviz page missing price element for {ticker}")

    def test_03_yahoo_ohlcv_realtime_feed(self):
        """Verify Yahoo Finance market chart data feed for target tickers."""
        headers = {"User-Agent": "Mozilla/5.0"}
        for ticker in self.tickers:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1m&range=1d"
            resp = requests.get(url, headers=headers, timeout=10)
            self.assertEqual(resp.status_code, 200, f"Yahoo Finance returned HTTP {resp.status_code} for {ticker}")
            data = resp.json()
            result = data.get("chart", {}).get("result")
            self.assertIsNotNone(result, f"Yahoo chart result empty for {ticker}")

if __name__ == "__main__":
    unittest.main()

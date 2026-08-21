"""Analyst Trader Plugin - Auto-discovery, trade ingestion, style learning, and dual portfolios."""

try:
    from .llm_reviewer import LLMTradeReviewer
except ImportError:
    from plugins.analyst_trader.llm_reviewer import LLMTradeReviewer

__all__ = ["LLMTradeReviewer"]

#!/usr/bin/env python3
"""
strategy_logger.py - Root Bridge to plugins.analyst_trader.strategy_logger.
"""

from plugins.analyst_trader.strategy_logger import log_event, list_recorded_strategies

__all__ = ["log_event", "list_recorded_strategies"]

"""TEST-only external wall-clock boundaries; no evaluator replacements."""
from contextlib import contextmanager, ExitStack
from datetime import datetime, date, timezone
from functools import wraps
from importlib import import_module
from unittest.mock import patch

ASOF = datetime(2026, 9, 23, 12, tzinfo=timezone.utc)

@contextmanager
def wall_clock(at):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return at.astimezone(tz) if tz else at.replace(tzinfo=None)
        @classmethod
        def utcnow(cls):
            return at.replace(tzinfo=None)
    class Day(date):
        @classmethod
        def today(cls):
            return at.date()
    modules = ('test_step5_kian_repair', 'step1_fixtures', 'flow_ingestion_engine',
               'owlfred_engine', 'autonomous_risk_manager',
               'plugins.analyst_trader.portfolio_engine', 'plugins.analyst_trader.db',
               'plugins.analyst_trader.strategy_logger', 'plugins.analyst_trader.learning_store',
               'plugins.analyst_trader.analyst_learning', 'plugins.analyst_trader.holding_statistics')
    with ExitStack() as stack:
        for name in modules:
            module = import_module(name)
            if isinstance(getattr(module, 'datetime', None), type) and issubclass(module.datetime, datetime):
                stack.enter_context(patch.object(module, 'datetime', Clock))
            if isinstance(getattr(module, 'date', None), type) and issubclass(module.date, date):
                stack.enter_context(patch.object(module, 'date', Day))
        yield

def frozen_test_clock(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        with wall_clock(ASOF):
            return function(*args, **kwargs)
    return wrapped

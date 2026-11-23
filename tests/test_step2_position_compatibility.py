"""Actual evaluator recommendation -> position boundary, offline TEST adapters only."""
import copy
import json
import unittest
from typing import Any
from unittest.mock import Mock
from test_step2_delivery import DeliveryTests


class PositionCompatibilityTests(unittest.TestCase):
    db: Any
    path: Any
    auth: Any
    now: Any
    calls: Any
    destinations: Any
    setUp = DeliveryTests.setUp
    manager = DeliveryTests.manager
    transport = DeliveryTests.transport
    compact = 'TEST261016C00100000'

    def evaluate(self):
        import owlfred_engine as owl
        quant, deep = Mock(), Mock()
        quant.evaluate_ticker_complete_quant.return_value = {'is_a_plus_dream_setup': True}
        deep.analyze_candidate_deep_dive.return_value = {}
        self.now[0] = 1060
        result: Any = owl.eval_ticker('TEST', db_path=str(self.path), flow_id='TEST-flow',
            publication=self.auth, delivery_destinations=self.destinations,
            delivery_transport=self.transport, delivery_clock=lambda: self.now[0],
            quant_engine=quant, deep_dive_analyzer=deep,
            observation_reader=lambda source: {'spot_price': 100})
        self.assertEqual(result['alert_delivery']['status'], 'complete')
        self.assertIsNone(result['paper_trade'])
        return result['recommendation']

    def publish(self, rec, symbol=compact, label='TEST-position'):
        return self.manager(self.transport).publish_position_exit_alert(
            rec['ticker'], symbol, 'TEST trim', 20, 2.4, 2, 'TEST guidance',
            publication=dict(self.auth, alert_id=label), source_recommendation=rec)

    def test_unmodified_actual_recommendation_with_literal_compact_display(self):
        rec = self.evaluate()
        before = copy.deepcopy(rec)
        self.assertEqual(rec['contract_symbol'], 'TEST 100C 2026-10-16')
        self.assertEqual(rec['occ_symbol'], 'TEST  261016C00100000')
        calls = len(self.calls)
        try:
            result = self.publish(rec)
        except ValueError as exc:
            self.fail('Actual unmodified evaluator recommendation rejected with valid compact display: ' + str(exc))
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(result['capability'], 'text_only')
        self.assertFalse(result['media_delivered'])
        self.assertEqual(len(result['units']), 2)
        self.assertEqual(len(self.calls), calls + 2)
        self.assertEqual(rec, before)
        with self.db._get_connection() as c:
            identity = json.loads(c.execute("SELECT identity_json FROM alert_messages WHERE alert_id='TEST-position'").fetchone()[0])
            for key, value in rec.items():
                self.assertEqual(identity['recommendation'][key], value)
            for row in c.execute("SELECT payload FROM alert_units WHERE alert_id='TEST-position'"):
                content = json.loads(row[0])['content']
                self.assertTrue(content.startswith('OWLFRED POSITION GUIDANCE:'))
                self.assertIn('\n' + self.compact + '\n', content)
        self.publish(rec)
        self.assertEqual(len(self.calls), calls + 2)
        print('ACTUAL_ROUND_TRIP: evaluator -> unchanged readable/padded recommendation -> literal compact display -> 2 durable position receipts; replay sends zero')

    def ledger(self):
        with self.db._get_connection() as c:
            return {table: [tuple(row) for row in c.execute('SELECT * FROM ' + table)]
                    for table in ('alert_messages', 'alert_units', 'alert_resolutions')}

    def rejects_unchanged(self, rec, symbol: Any = compact):
        before, calls = self.ledger(), list(self.calls)
        with self.assertRaises(ValueError):
            self.publish(rec, symbol)
        self.assertEqual(self.ledger(), before, 'Rejected identity created/changed durable units')
        self.assertEqual(self.calls, calls, 'Rejected identity reached transport')

    def test_display_literals_are_never_repaired(self):
        rec = self.evaluate()
        for symbol in (self.compact.lower(), ' ' + self.compact, self.compact + ' ',
                       self.compact + '\n', rec['occ_symbol'], rec['contract_symbol'],
                       'TEST261016C100000', 'broken', '', None,
                       'TEST261016P00100000', 'TEST261023C00100000',
                       'TEST261016C00101000', 'OTHER261016C00100000'):
            with self.subTest(display=symbol):
                self.rejects_unchanged(rec, symbol)
        with self.assertRaises(TypeError):
            self.manager(self.transport).publish_position_exit_alert(
                ticker='TEST', trigger_label='TEST', pnl_pct=20, current_price=2.4,
                entry_price=2, action_note='TEST', publication=self.auth, source_recommendation=rec)

    def test_every_supplied_symbol_is_checked_even_when_other_symbol_absent(self):
        rec = self.evaluate()
        invalid = {
            'contract_symbol': ('OTHER 100C 2026-10-16', 'TEST 101C 2026-10-16',
                'TEST 100P 2026-10-16', 'TEST 100C 2026-10-23',
                'test 100C 2026-10-16', 'TEST 100.0C 2026-10-16',
                ' TEST 100C 2026-10-16', 'TEST 100C 2026-10-16 ',
                rec['occ_symbol'], '', None),
            'occ_symbol': ('OTHER 261016C00100000', 'TEST  261016C00101000',
                'TEST  261016P00100000', 'TEST  261023C00100000',
                'test  261016C00100000', 'TEST 261016C00100000',
                ' TEST  261016C00100000', 'TEST  261016C00100000 ',
                rec['contract_symbol'], '', None)}
        for field, values in invalid.items():
            other = 'occ_symbol' if field == 'contract_symbol' else 'contract_symbol'
            for value in values:
                for partial in (False, True):
                    candidate = dict(rec, **{field: value})
                    if partial:
                        del candidate[other]
                    with self.subTest(field=field, value=value, partial=partial):
                        self.rejects_unchanged(candidate)

    def test_canonical_fields_are_required_and_cannot_conflict(self):
        rec = self.evaluate()
        for field, bad in (('ticker', 'OTHER'), ('strike', 101),
                           ('call_put', 'P'), ('expiration', '2026-10-23')):
            with self.subTest(field=field):
                self.rejects_unchanged(dict(rec, **{field: bad}))
                candidate = dict(rec)
                del candidate[field]
                if field == 'ticker':
                    # The public wrapper's explicit ticker remains present.
                    with self.assertRaises(ValueError):
                        self.manager(self.transport).publish_position_exit_alert('TEST', self.compact,
                            'TEST', 20, 2.4, 2, 'TEST', publication=self.auth,
                            source_recommendation=candidate)
                else:
                    self.rejects_unchanged(candidate)

    def test_valid_source_representations_and_partial_subjects(self):
        rec = self.evaluate()
        for i, fields in enumerate(({}, {'contract_symbol': rec['contract_symbol']},
                {'occ_symbol': rec['occ_symbol']}, {'contract_symbol': self.compact},
                {'occ_symbol': self.compact},
                {'contract_symbol': self.compact, 'occ_symbol': self.compact})):
            candidate = {k: v for k, v in rec.items() if k not in ('contract_symbol', 'occ_symbol')}
            candidate.update(fields)
            with self.subTest(fields=fields):
                result = self.publish(candidate, label='TEST-form-' + str(i))
                self.assertEqual(result['status'], 'complete')
                self.assertEqual(len(result['units']), 2)

    def test_persisted_source_remains_authority(self):
        rec = self.evaluate()
        for field, value in (('ticker', 'OTHER'), ('strike', 101),
                             ('call_put', 'P'), ('expiration', '2026-10-23'),
                             ('final_outcome', 'CLOSED')):
            with self.subTest(field=field):
                with self.db._get_connection() as c:
                    original = c.execute('SELECT ' + field + ' FROM notable_flow WHERE flow_id=?', ('TEST-flow',)).fetchone()[0]
                    c.execute('UPDATE notable_flow SET ' + field + '=? WHERE flow_id=?', (value, 'TEST-flow'))
                self.rejects_unchanged(rec)
                with self.db._get_connection() as c:
                    c.execute('UPDATE notable_flow SET ' + field + '=? WHERE flow_id=?', (original, 'TEST-flow'))
        self.rejects_unchanged(dict(rec, flow_id='OTHER-flow'))
        before, calls = self.ledger(), list(self.calls)
        original_auth = self.auth
        self.auth = dict(self.auth, flow_id='MISSING-flow')
        try:
            self.rejects_unchanged(rec)
        finally:
            self.auth = original_auth
        self.assertEqual(self.ledger(), before)
        self.assertEqual(self.calls, calls)


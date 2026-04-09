import unittest

from app.trade_state_machine import (
    InvalidTradeTransition,
    TradeAction,
    TradeState,
    can_transition,
    is_terminal,
    transition_state,
)


class TradeStateMachineTests(unittest.TestCase):
    def test_send_from_draft_to_pending(self):
        result = transition_state(TradeState.DRAFT, TradeAction.SEND)
        self.assertEqual(result.to_state, TradeState.PENDING)

    def test_pending_reply_paths(self):
        self.assertTrue(can_transition(TradeState.PENDING, TradeAction.ACCEPT))
        self.assertTrue(can_transition(TradeState.PENDING, TradeAction.REJECT))
        self.assertTrue(can_transition(TradeState.PENDING, TradeAction.COUNTER))
        self.assertTrue(can_transition(TradeState.PENDING, TradeAction.REQUEST_CLARIFICATION))

    def test_counter_flow_allows_new_counter(self):
        self.assertTrue(can_transition(TradeState.COUNTERED, TradeAction.ACCEPT))
        self.assertTrue(can_transition(TradeState.COUNTERED, TradeAction.REJECT))
        self.assertTrue(can_transition(TradeState.COUNTERED, TradeAction.COUNTER))
        self.assertTrue(can_transition(TradeState.COUNTERED, TradeAction.REQUEST_CLARIFICATION))

    def test_clarification_flow_returns_to_pending(self):
        clarified = transition_state(TradeState.NEEDS_CLARIFICATION, TradeAction.CLARIFY)
        self.assertEqual(clarified.to_state, TradeState.PENDING)

    def test_cancel_and_expire_paths(self):
        cancelled = transition_state(TradeState.PENDING, TradeAction.CANCEL)
        self.assertEqual(cancelled.to_state, TradeState.CANCELLED)
        expired = transition_state(TradeState.COUNTERED, TradeAction.EXPIRE)
        self.assertEqual(expired.to_state, TradeState.EXPIRED)

    def test_invalid_transition_raises(self):
        with self.assertRaises(InvalidTradeTransition):
            transition_state(TradeState.ACCEPTED, TradeAction.ACCEPT)

    def test_terminal_states(self):
        self.assertTrue(is_terminal(TradeState.ACCEPTED))
        self.assertTrue(is_terminal(TradeState.REJECTED))
        self.assertTrue(is_terminal(TradeState.CANCELLED))
        self.assertTrue(is_terminal(TradeState.EXPIRED))
        self.assertFalse(is_terminal(TradeState.PENDING))


if __name__ == "__main__":
    unittest.main()

import json
import unittest

from app.models import TradeRequest
from app.trade_requests import _parse_items, resolve_request_status
from app.trade_state_machine import TradeState


class TradeRequestsHelpersTests(unittest.TestCase):
    def test_parse_items_expands_legacy_quantity(self):
        items = _parse_items(
            [
                {
                    "catTypeId": "gray",
                    "catSex": "M",
                    "quantity": 3,
                    "unitPrice": 7,
                    "side": "SELL",
                }
            ]
        )
        self.assertEqual(len(items), 3)
        self.assertTrue(all(item["quantity"] == 1 for item in items))
        self.assertTrue(all(item["proposedPrice"] == 7 for item in items))

    def test_viewer_specific_status_mapping(self):
        request = TradeRequest(
            id="req-1",
            session_id="session-1",
            season_number=1,
            from_player_id="user:1",
            to_player_id="shop:1",
            next_actor_player_id="shop:1",
            state=TradeState.PENDING,
            items_json=json.dumps(
                [{"catType": "gray", "catSex": "M", "proposedPrice": 8, "side": "SELL"}],
                ensure_ascii=False,
            ),
            total_price=8,
        )
        self.assertEqual(resolve_request_status(request, "user:1"), "PENDING_OUTGOING")
        self.assertEqual(resolve_request_status(request, "shop:1"), "PENDING_INCOMING")

        request.state = TradeState.COUNTERED
        request.next_actor_player_id = "user:1"
        self.assertEqual(resolve_request_status(request, "user:1"), "COUNTERED")
        self.assertEqual(resolve_request_status(request, "shop:1"), "PENDING_OUTGOING")

        request.state = TradeState.NEEDS_CLARIFICATION
        request.next_actor_player_id = "user:1"
        self.assertEqual(resolve_request_status(request, "user:1"), "NEEDS_CLARIFICATION")
        self.assertEqual(resolve_request_status(request, "shop:1"), "AWAITING_CLARIFICATION")


if __name__ == "__main__":
    unittest.main()

import json
import unittest
from unittest.mock import MagicMock, patch

from app.models import TradeRequest
from app.trade_bot import ShopBotState, bot_display_buy_price
from app.trade_requests import (
    _derive_direction,
    _derive_request_type,
    _parse_items,
    build_shop_market_view,
    resolve_request_status,
)
from app.trade_state_machine import TradeState


class TradeRequestsHelpersTests(unittest.TestCase):
    def test_player_sell_request_maps_to_sell_request_and_player_to_shop(self):
        items = _parse_items(
            [
                {
                    "catTypeId": "gray",
                    "catSex": "M",
                    "quantity": 1,
                    "unitPrice": 7,
                    "side": "SELL",
                }
            ]
        )
        self.assertEqual(_derive_request_type(items, is_counter=False), "SELL_REQUEST")
        self.assertEqual(_derive_direction("user:1", "shop:1", items), "PLAYER_TO_SHOP")

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

    def test_build_shop_market_view_uses_same_display_buy_price_as_bot_ai(self):
        market = {
            "gray": {"buy": 7, "sell": 18, "M": {"buy": 7, "sell": 18}, "F": {"buy": 7, "sell": 18}},
            "black": {"buy": 6, "sell": 14, "M": {"buy": 6, "sell": 14}, "F": {"buy": 6, "sell": 14}},
            "white": {"buy": 5, "sell": 12, "M": {"buy": 5, "sell": 12}, "F": {"buy": 5, "sell": 12}},
            "ginger": {"buy": 4, "sell": 10, "M": {"buy": 4, "sell": 10}, "F": {"buy": 4, "sell": 10}},
        }
        bot_state = ShopBotState(
            botId="shop:2",
            cash=200,
            relationScoreToPlayer=4,
            inventoryByType={"gray": 1, "black": 2, "white": 1, "ginger": 0},
            currentDemandByType={"gray": 0, "black": 0, "white": 1, "ginger": -1},
            expectedResaleValueByType={"gray": 133, "black": 14, "white": 12, "ginger": 8},
            recentAcceptedPricesByType={},
            pendingRequestsCount=0,
            archetype="MARKET",
        )
        db = MagicMock()
        db.query.return_value.filter.return_value.one_or_none.return_value = None

        with patch("app.trade_requests._market_prices_for_player", return_value=market), patch(
            "app.trade_requests._build_shop_bot_state", return_value=bot_state
        ):
            view = build_shop_market_view(db, "session-1", 1, "user:1", "shop:2")

        display_price = bot_display_buy_price(bot_state, "gray")
        self.assertEqual(display_price, 100)
        self.assertEqual(view["gray"]["sell"], display_price)
        self.assertEqual(view["gray"]["M"]["sell"], display_price)
        self.assertEqual(view["gray"]["F"]["sell"], display_price)


if __name__ == "__main__":
    unittest.main()

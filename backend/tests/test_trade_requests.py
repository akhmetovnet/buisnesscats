import json
import unittest
from unittest.mock import MagicMock, patch

from app import crud
from app.models import TradeRequest
from app.trade_bot import ShopBotState, bot_display_buy_price, bot_display_sell_price
from app.trade_requests import (
    _derive_direction,
    _derive_request_type,
    _parse_items,
    build_shop_market_view,
    resolve_request_status,
)
from app.trade_state_machine import TradeState


class TradeRequestsHelpersTests(unittest.TestCase):
    def test_generate_market_prices_caps_shop_sell_to_player_in_early_seasons(self):
        season_caps = {1: 6, 2: 7, 3: 8, 4: 9}
        season_mins = {1: 1, 2: 3, 3: 4, 4: 5}

        for season_number, max_price in season_caps.items():
            market = crud.generate_market_prices("session-early", season_number, "shop", 1)
            for color in ("black", "white", "gray", "ginger"):
                self.assertGreaterEqual(market[color]["buy"], season_mins[season_number])
                self.assertLessEqual(market[color]["buy"], max_price)
                if season_number == 1:
                    self.assertGreaterEqual(market[color]["buy"], market[color]["sell"])
                else:
                    self.assertGreater(market[color]["buy"], market[color]["sell"])
                for sex in ("M", "F"):
                    self.assertGreaterEqual(market[color][sex]["buy"], season_mins[season_number])
                    self.assertLessEqual(market[color][sex]["buy"], max_price)
                    if season_number == 1:
                        self.assertGreaterEqual(market[color][sex]["buy"], market[color][sex]["sell"])
                    else:
                        self.assertGreater(market[color][sex]["buy"], market[color][sex]["sell"])

    def test_generate_market_prices_season_one_biases_shop_sell_prices_toward_one_to_three(self):
        observed = []
        for shop_id in range(1, 8):
            market = crud.generate_market_prices("session-early-bias", 1, "shop", shop_id)
            for color in ("black", "white", "gray", "ginger"):
                observed.append(int(market[color]["buy"]))
                for sex in ("M", "F"):
                    observed.append(int(market[color][sex]["buy"]))

        lower_band = [price for price in observed if price <= 3]
        upper_band = [price for price in observed if price > 3]
        self.assertTrue(all(1 <= price <= 6 for price in observed))
        self.assertGreater(len(lower_band), len(upper_band))

    def test_generate_market_prices_season_five_is_not_hard_capped(self):
        observed = []
        for shop_id in range(1, 6):
            market = crud.generate_market_prices("session-normal", 5, "shop", shop_id)
            for color in ("black", "white", "gray", "ginger"):
                observed.append(int(market[color]["buy"]))
                for sex in ("M", "F"):
                    observed.append(int(market[color][sex]["buy"]))
        self.assertTrue(any(price > 9 for price in observed))

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
        display_sell_price = bot_display_sell_price(bot_state, "gray")
        self.assertEqual(view["gray"]["buy"], display_sell_price)
        self.assertEqual(view["gray"]["M"]["buy"], display_sell_price)
        self.assertEqual(view["gray"]["F"]["buy"], display_sell_price)


if __name__ == "__main__":
    unittest.main()

import os


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def _env_choice(name: str, allowed: set[str], default: str) -> str:
    raw = str(os.getenv(name, default)).strip()
    return raw if raw in allowed else default


CONFIG_MATCH_CATTERIES = _env_int("BC_MATCH_CATTERIES", 20)
CONFIG_MATCH_SHOPS = _env_int("BC_MATCH_SHOPS", 5)
CONFIG_MIN_BOT_SHOPS = _env_int("BC_MIN_BOT_SHOPS", 1)

CONFIG_START_COINS = _env_int("BC_START_COINS", 1000)
CONFIG_START_KITTENS = _env_int("BC_START_KITTENS", 0)
CONFIG_START_HOUSES = _env_int("BC_START_HOUSES", 1)

CONFIG_START_PRODUCTION_MODE = _env_choice(
    "BC_START_PRODUCTION_MODE",
    {"BUY_FROM_ZOOSHOP", "STARTER_PACK"},
    "BUY_FROM_ZOOSHOP",
)

CONFIG_ROLE_PLAYER = _env_choice(
    "BC_ROLE_PLAYER",
    {"cattery", "petshop", "random"},
    "cattery",
)

ADULT_AGE = _env_int("BC_ADULT_AGE", 3)

ARCHETYPE_DISTRIBUTION = {
    "FARMER": 4,
    "SCALPER": 4,
    "BALANCER": 6,
    "RISK_MANAGER": 3,
    "HIGH_ROLLER": 2,
}

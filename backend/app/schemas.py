from typing import Literal, List
from pydantic import BaseModel, Field, field_validator


Role = Literal["candidate", "hr", "admin"]


class DemoLoginRequest(BaseModel):
    role: Role
    fullName: str = Field(default="Demo User", max_length=200)


class DemoLoginResponse(BaseModel):
    userId: str
    role: Role


class CandidateProfileOut(BaseModel):
    userId: str
    fullName: str
    city: str
    university: str
    program: str
    studyYear: int
    skills: List[str]


class CandidateProfileUpdate(BaseModel):
    fullName: str
    city: str
    university: str
    program: str
    studyYear: int
    skills: List[str] = Field(default_factory=list)

from typing import Any, Dict, Optional

class GameSessionStartResponse(BaseModel):
    sessionId: str
    assignedRole: Literal["cattery", "petshop"]
    rules: dict
    season: dict

class GameEventIn(BaseModel):
    sessionId: str
    seasonNumber: int
    eventType: str
    payload: Dict[str, Any] = Field(default_factory=dict)

class OkResponse(BaseModel):
    ok: bool = True

class SeasonFinishIn(BaseModel):
    sessionId: str
    seasonNumber: int
    finishEarly: bool = False
    nursery: Dict[str, Any] = Field(default_factory=dict)
    nurseryCoinsDelta: int = 0

class SeasonFinishOut(BaseModel):
    seasonResult: dict
    nextSeason: Optional[dict] = None

class SessionFinishIn(BaseModel):
    sessionId: str

class SessionFinishOut(BaseModel):
    status: str
    playerCoins: int
    botCoins: int

class ComputeOut(BaseModel):
    sessionId: str
    scores: list

class SeasonStateOut(BaseModel):
    sessionId: str
    seasonNumber: int
    role: Literal["cattery", "petshop"]
    adultAge: int
    coins: int
    debtTotal: int
    debtRate: float
    market: dict
    inventory: dict
    inventoryEntities: list[dict] = []


class GameProgressSaveIn(BaseModel):
    sessionId: str
    seasonNumber: int
    nursery: Dict[str, Any] = Field(default_factory=dict)
    nurseryCoinsDelta: int = 0
    timeLeft: int = 0


class GameProgressOut(BaseModel):
    sessionId: str
    seasonNumber: int
    nursery: Dict[str, Any]
    nurseryCoinsDelta: int
    timeLeft: int
    updatedAt: str | None = None


class GameProgressGetOut(BaseModel):
    found: bool
    progress: GameProgressOut | None = None

class CompetencyScore(BaseModel):
    name: str
    score: int
    evidence: dict
    explanation: str

class CompetencyProfileOut(BaseModel):
    sessionId: str
    overall: int
    competencies: list[CompetencyScore]
    recommendations: list[str] = Field(default_factory=list)


class MarketOut(BaseModel):
    sessionId: str
    seasonNumber: int
    market: dict


class TradeIn(BaseModel):
    sessionId: str
    seasonNumber: int
    action: Literal["buy", "sell"]
    catType: str
    catSex: Literal["M", "F"] | None = None
    entityId: str | None = None
    counterpartyType: Literal["shop", "cattery"] | None = None
    counterpartyId: int | None = None
    qty: int


class GameStateOut(BaseModel):
    sessionId: str
    seasonNumber: int
    role: Literal["cattery", "petshop"]
    adultAge: int
    market: dict
    inventory: dict
    inventoryEntities: list[dict] = []
    shopTrustPercent: int | None = None
    coinsNowEstimate: int
    debtTotal: int
    debtRate: float


class TradeOut(BaseModel):
    ok: bool
    error: str | None = None
    state: GameStateOut | None = None


class CreditTakeIn(BaseModel):
    sessionId: str
    seasonNumber: int
    creditType: Literal["consumer", "investment", "special"]
    amount: int


class CreditRepayIn(BaseModel):
    sessionId: str
    seasonNumber: int
    amount: int


class GameSessionItemOut(BaseModel):
    id: str
    assignedRole: Literal["cattery", "petshop"]
    status: str
    startedAt: str
    finishedAt: str | None = None
    resultCoinsPlayer: int
    resultCoinsBot: int


class SeasonDetailOut(BaseModel):
    season_number: int
    coins_start: int
    coins_end: int
    profit: int
    bot_coins_end: int
    meta_json: str


class GameSessionDetailOut(BaseModel):
    session: GameSessionItemOut | None = None
    seasons: list[SeasonDetailOut]


TradeRequestRawState = Literal[
    "DRAFT",
    "PENDING",
    "COUNTERED",
    "ACCEPTED",
    "REJECTED",
    "CANCELLED",
    "NEEDS_CLARIFICATION",
    "AWAITING_CLARIFICATION",
    "EXPIRED",
]

TradeRequestStatus = Literal[
    "PENDING_INCOMING",
    "PENDING_OUTGOING",
    "COUNTERED",
    "ACCEPTED",
    "REJECTED",
    "NEEDS_CLARIFICATION",
    "AWAITING_CLARIFICATION",
    "CANCELLED",
    "EXPIRED",
]

TradeRequestType = Literal[
    "BUY_REQUEST",
    "SELL_REQUEST",
    "COUNTER_REQUEST",
]

TradeRequestDirection = Literal["PLAYER_TO_SHOP", "SHOP_TO_PLAYER"]

TradeRequestUiCategory = Literal[
    "OUTGOING",
    "INCOMING",
    "REJECTED_BY_OTHER",
    "ACCEPTED_BY_OTHER",
    "COUNTER",
    "REQUIRES_CLARIFICATION",
    "WAITING_FOR_CLARIFICATION",
]

TradeSide = Literal["BUY", "SELL"]


class TradeRequestItem(BaseModel):
    itemId: str | None = None
    catId: str | None = None
    catType: str | None = None
    catColor: str | None = None
    catSex: Literal["M", "F"] | None = None
    proposedPrice: int | None = None
    currency: Literal["COIN"] = "COIN"
    catTypeId: str | None = None
    quantity: int = 1
    unitPrice: int | None = None
    side: TradeSide

    @field_validator("catType", "catColor", "catTypeId")
    @classmethod
    def _validate_type(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip().lower()
        if normalized == "orange":
            normalized = "ginger"
        if normalized not in {"black", "white", "gray", "ginger"}:
            raise ValueError("invalid_cat_type")
        return normalized

    @field_validator("quantity")
    @classmethod
    def _validate_qty(cls, value: int) -> int:
        if value != 1:
            raise ValueError("quantity_must_be_exactly_one")
        return 1

    @field_validator("unitPrice", "proposedPrice")
    @classmethod
    def _validate_price(cls, value: int | None) -> int | None:
        if value is None:
            return value
        if value <= 0:
            raise ValueError("unit_price_must_be_positive")
        return value


class TradeRequestPlayerMeta(BaseModel):
    playerId: str
    kind: str
    displayName: str
    avatarText: str


class TradeRequestOut(BaseModel):
    id: str
    threadId: str
    sessionId: str
    seasonId: int
    seasonNumber: int
    createdAt: str | None = None
    updatedAt: str | None = None
    fromPlayerId: str
    toPlayerId: str
    type: TradeRequestType
    direction: TradeRequestDirection
    status: TradeRequestStatus
    state: TradeRequestStatus
    rawState: TradeRequestRawState
    uiCategory: TradeRequestUiCategory
    icon: str | None = None
    isReadBySender: bool
    isReadByReceiver: bool
    readByFrom: bool
    readByTo: bool
    unread: bool = False
    items: list[TradeRequestItem]
    totalPrice: int
    messageCode: str | None = None
    clarificationReason: str | None = None
    clarificationMeta: dict[str, Any] | None = None
    decisionMeta: dict[str, Any] | None = None
    counterOfRequestId: str | None = None
    parentRequestId: str | None = None
    ttlSeconds: int | None = None
    fromMeta: TradeRequestPlayerMeta
    toMeta: TradeRequestPlayerMeta
    nextActorPlayerId: str | None = None
    canAct: bool = False


class TradeRequestListOut(BaseModel):
    items: list[TradeRequestOut]


class TradeRequestSendIn(BaseModel):
    sessionId: str
    seasonNumber: int
    counterpartyType: Literal["shop", "cattery"]
    counterpartyId: int
    items: list[TradeRequestItem]
    ttlSeconds: int | None = None


class TradeRequestActionIn(BaseModel):
    sessionId: str
    seasonNumber: int
    action: Literal[
        "accept",
        "reject",
        "counter",
        "request_clarification",
        "clarify",
        "cancel",
        "ack",
    ]
    counterItems: list[TradeRequestItem] = Field(default_factory=list)
    messageCode: str | None = None


class TradeRequestActionOut(BaseModel):
    ok: bool
    request: TradeRequestOut | None = None
    error: str | None = None


class CatteryPublicItemOut(BaseModel):
    catTypeId: str
    catSex: Literal["M", "F"]
    quantity: int
    unitPrice: int
    ageLessThan: int


class CatteryPublicViewOut(BaseModel):
    catteryId: int
    seasonNumber: int
    spectateMode: bool
    tradeAllowed: bool
    message: str
    showcase: list[CatteryPublicItemOut]
    dealsThisSeason: int
    lastDealSecondsAgo: int | None = None
    avgSellPriceThisSeason: float

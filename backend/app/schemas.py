from typing import Literal, List
from pydantic import BaseModel, Field


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
    skills: List[str] = []

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
    payload: Dict[str, Any] = {}

class OkResponse(BaseModel):
    ok: bool = True

class SeasonFinishIn(BaseModel):
    sessionId: str
    seasonNumber: int
    finishEarly: bool = False

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
    coins: int
    debtTotal: int
    debtRate: float
    market: dict
    inventory: dict
    inventoryEntities: list[dict] = []

class CompetencyScore(BaseModel):
    name: str
    score: int
    evidence: dict
    explanation: str

class CompetencyProfileOut(BaseModel):
    sessionId: str
    overall: int
    competencies: list[CompetencyScore]
    recommendations: list[str] = []


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
    counterpartyType: Literal["shop", "cattery"] | None = None
    counterpartyId: int | None = None
    qty: int


class GameStateOut(BaseModel):
    sessionId: str
    seasonNumber: int
    role: Literal["cattery", "petshop"]
    market: dict
    inventory: dict
    inventoryEntities: list[dict] = []
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

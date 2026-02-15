import json
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .db import engine, Base
from .deps import get_db, get_demo_user
from . import crud
from .schemas import (
    DemoLoginRequest,
    DemoLoginResponse,
    CandidateProfileOut,
    CandidateProfileUpdate,
)
from .schemas import (
    GameSessionStartResponse, GameEventIn, OkResponse,
    SeasonFinishIn, SeasonFinishOut, SessionFinishIn, SessionFinishOut,
    ComputeOut, MarketOut, TradeIn, TradeOut, GameStateOut,
    CreditTakeIn, CreditRepayIn,
    GameSessionItemOut, GameSessionDetailOut, SeasonDetailOut
)
from .models import GameSession, CandidateProfile

from fastapi import Query
from .schemas import SeasonStateOut
from .models import Season
import json
from .schemas import CompetencyProfileOut
from . import models
from .generate_report import generate_competency_report


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Business Cats Lite API", version="1.0")

# чтобы React локально мог ходить на API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:8081"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/demo/login", response_model=DemoLoginResponse)
def demo_login(payload: DemoLoginRequest, db: Session = Depends(get_db)):
    user = crud.create_demo_user(db, role=payload.role, full_name=payload.fullName)
    return {"userId": user.id, "role": user.role}


@app.get("/api/candidate/profile", response_model=CandidateProfileOut)
def get_candidate_profile(user=Depends(get_demo_user), db: Session = Depends(get_db)):
    profile = crud.get_profile(db, user.id)

    skills = []
    if profile and profile.skills_json:
        try:
            skills = json.loads(profile.skills_json)
        except Exception:
            skills = []

    return {
        "userId": user.id,
        "fullName": profile.full_name if profile else "",
        "city": profile.city if profile else "",
        "university": profile.university if profile else "",
        "program": profile.program if profile else "",
        "studyYear": profile.study_year if profile else 0,
        "skills": skills,
    }


@app.put("/api/candidate/profile", response_model=CandidateProfileOut)
def put_candidate_profile(
    payload: CandidateProfileUpdate,
    user=Depends(get_demo_user),
    db: Session = Depends(get_db),
):
    profile = crud.update_profile(db, user.id, payload.model_dump())
    skills = json.loads(profile.skills_json) if profile.skills_json else []
    return {
        "userId": user.id,
        "fullName": profile.full_name,
        "city": profile.city,
        "university": profile.university,
        "program": profile.program,
        "studyYear": profile.study_year,
        "skills": skills,
    }
@app.post("/api/game/session/start", response_model=GameSessionStartResponse)
def game_session_start(user=Depends(get_demo_user), db: Session = Depends(get_db)):
    session = crud.start_game_session(db, user.id)
    role = session.assigned_role
    return {
        "sessionId": session.id,
        "assignedRole": role,
        "rules": {
            "seasonsTotal": crud.SEASONS_TOTAL,
            "startCoins": crud.START_COINS,
            "utilityCost": crud.UTILITY_COST,
            "credit": {"max": crud.CREDIT_MAX, "rates": crud.CREDIT_RATES},
        },
        "season": {"number": 1, "secondsLeft": crud.SEASON_SECONDS[1], "coins": crud.START_COINS},
    }


@app.post("/api/game/event", response_model=OkResponse)
def game_event(payload: GameEventIn, user=Depends(get_demo_user), db: Session = Depends(get_db)):
    # проверим, что сессия принадлежит пользователю
    session = db.get(GameSession, payload.sessionId)
    if not session or session.user_id != user.id:
        return {"ok": False}
    crud.add_event(db, payload.sessionId, payload.seasonNumber, payload.eventType, payload.payload)
    return {"ok": True}


@app.get("/api/game/market/{session_id}/{season_number}", response_model=MarketOut)
def game_market(
    session_id: str,
    season_number: int,
    counterpartyType: str | None = Query(default=None),
    counterpartyId: int | None = Query(default=None),
    user=Depends(get_demo_user),
    db: Session = Depends(get_db),
):
    session = db.get(GameSession, session_id)
    if not session or session.user_id != user.id:
        return {"sessionId": session_id, "seasonNumber": season_number, "market": {}}

    market = crud.get_market(session_id, season_number, counterpartyType, counterpartyId)
    return {"sessionId": session_id, "seasonNumber": season_number, "market": market}


def _build_game_state(
    db: Session,
    session: GameSession,
    season_number: int,
    counterparty_type: str | None = None,
    counterparty_id: int | None = None,
) -> dict:
    market = crud.get_market(session.id, season_number, counterparty_type, counterparty_id)
    inventory, inventory_entities = crud.get_inventory_view(session.inventory_json or "{}")
    est = crud.estimate_state(db, session.id, season_number)
    return {
        "sessionId": session.id,
        "seasonNumber": season_number,
        "role": session.assigned_role,
        "market": market,
        "inventory": inventory,
        "inventoryEntities": inventory_entities,
        "coinsNowEstimate": est["coins"],
        "debtTotal": est["debt_total"],
        "debtRate": float(est["debt_rate"]),
    }


@app.get("/api/game/state/{session_id}/{season_number}", response_model=GameStateOut)
def game_state(
    session_id: str,
    season_number: int,
    counterpartyType: str | None = Query(default=None),
    counterpartyId: int | None = Query(default=None),
    user=Depends(get_demo_user),
    db: Session = Depends(get_db),
):
    session = db.get(GameSession, session_id)
    if not session or session.user_id != user.id:
        return {
            "sessionId": session_id,
            "seasonNumber": season_number,
            "role": "cattery",
            "market": {},
            "inventory": {},
            "inventoryEntities": [],
            "coinsNowEstimate": 0,
            "debtTotal": 0,
            "debtRate": 0.0,
        }

    return _build_game_state(
        db,
        session,
        season_number,
        counterparty_type=counterpartyType,
        counterparty_id=counterpartyId,
    )


@app.post("/api/game/trade", response_model=TradeOut)
def game_trade(payload: TradeIn, user=Depends(get_demo_user), db: Session = Depends(get_db)):
    session = db.get(GameSession, payload.sessionId)
    if not session or session.user_id != user.id:
        return {"ok": False, "error": "invalid_session", "state": None}

    ok, err = crud.trade_market(
        db,
        session=session,
        season_number=payload.seasonNumber,
        action=payload.action,
        cat_type=payload.catType,
        qty=payload.qty,
        cat_sex=payload.catSex,
        counterparty_type=payload.counterpartyType,
        counterparty_id=payload.counterpartyId,
    )
    state = (
        _build_game_state(
            db,
            session,
            payload.seasonNumber,
            counterparty_type=payload.counterpartyType,
            counterparty_id=payload.counterpartyId,
        )
        if ok
        else None
    )
    return {"ok": ok, "error": err, "state": state}


@app.post("/api/game/credit/take", response_model=TradeOut)
def game_credit_take(payload: CreditTakeIn, user=Depends(get_demo_user), db: Session = Depends(get_db)):
    session = db.get(GameSession, payload.sessionId)
    if not session or session.user_id != user.id:
        return {"ok": False, "error": "invalid_session", "state": None}
    if payload.amount <= 0:
        return {"ok": False, "error": "invalid_amount", "state": None}

    crud.add_event(
        db,
        payload.sessionId,
        payload.seasonNumber,
        "credit_taken",
        {"creditType": payload.creditType, "amount": payload.amount},
    )
    state = _build_game_state(db, session, payload.seasonNumber)
    return {"ok": True, "error": None, "state": state}


@app.post("/api/game/credit/repay", response_model=TradeOut)
def game_credit_repay(payload: CreditRepayIn, user=Depends(get_demo_user), db: Session = Depends(get_db)):
    session = db.get(GameSession, payload.sessionId)
    if not session or session.user_id != user.id:
        return {"ok": False, "error": "invalid_session", "state": None}
    if payload.amount <= 0:
        return {"ok": False, "error": "invalid_amount", "state": None}

    crud.add_event(
        db,
        payload.sessionId,
        payload.seasonNumber,
        "credit_repaid",
        {"amount": payload.amount},
    )
    state = _build_game_state(db, session, payload.seasonNumber)
    return {"ok": True, "error": None, "state": state}
    



@app.post("/api/game/season/finish", response_model=SeasonFinishOut)
def game_season_finish(payload: SeasonFinishIn, user=Depends(get_demo_user), db: Session = Depends(get_db)):
    session = db.get(GameSession, payload.sessionId)
    if not session or session.user_id != user.id:
        return {"seasonResult": {"error": "invalid session"}, "nextSeason": None}

    db.refresh(session)
    season, next_season = crud.finish_season(db, payload.sessionId, payload.seasonNumber, payload.finishEarly)

    res = {
        "coinsStart": season.coins_start,
        "coinsEnd": season.coins_end,
        "profit": season.profit,
        "botCoinsEnd": season.bot_coins_end,
        "debtTotal": session.debt_total,
        "debtRate": session.debt_rate,
    }
    nxt = None
    if next_season:
        nxt = {"number": next_season.season_number, "secondsLeft": crud.SEASON_SECONDS[next_season.season_number], "coins": next_season.coins_end}
    return {"seasonResult": res, "nextSeason": nxt}


@app.post("/api/game/session/finish", response_model=SessionFinishOut)
def game_session_finish(payload: SessionFinishIn, user=Depends(get_demo_user), db: Session = Depends(get_db)):
    session = db.get(GameSession, payload.sessionId)
    if not session or session.user_id != user.id:
        return {"status": "error", "playerCoins": 0, "botCoins": 0}

    session = crud.finish_session(db, payload.sessionId)
    return {"status": session.status, "playerCoins": session.result_coins_player, "botCoins": session.result_coins_bot}


@app.post("/api/analytics/compute/{session_id}", response_model=CompetencyProfileOut)
def analytics_compute(session_id: str, user=Depends(get_demo_user), db: Session = Depends(get_db)):
    session = db.get(GameSession, session_id)
    if not session or session.user_id != user.id:
        return {"sessionId": session_id, "overall": 0, "competencies": [], "recommendations": []}
    
    competencies = crud.compute_competencies(db, session_id)

    overall = 0
    if competencies:
        overall = round(sum(c["score"] for c in competencies) / len(competencies))

    recommendations = _build_recommendations(competencies)

    return {
        "sessionId": session_id,
        "overall": overall,
        "competencies": competencies,
        "recommendations": recommendations,
    }



@app.get("/api/game/season/state", response_model=SeasonStateOut)
def season_state(
    sessionId: str = Query(...),
    seasonNumber: int = Query(...),
    counterpartyType: str | None = Query(default=None),
    counterpartyId: int | None = Query(default=None),
    user=Depends(get_demo_user),
    db: Session = Depends(get_db),
):
    session = db.get(GameSession, sessionId)
    if not session or session.user_id != user.id:
        return {
            "sessionId": sessionId,
            "seasonNumber": seasonNumber,
            "role": "cattery",
            "coins": 0,
            "debtTotal": 0,
            "debtRate": 0.0,
            "market": {},
            "inventory": {},
            "inventoryEntities": [],
        }

    season = (
        db.query(Season)
        .filter(
            Season.session_id == sessionId,
            Season.season_number == seasonNumber,
        )
        .order_by(Season.started_at.desc(), Season.id.desc())
        .first()
    )

    coins = season.coins_end if season else 0
    market = crud.generate_market_prices(sessionId, seasonNumber, counterpartyType, counterpartyId)
    inventory, inventory_entities = crud.get_inventory_view(session.inventory_json or "{}")


    return {
        "sessionId": sessionId,
        "seasonNumber": seasonNumber,
        "role": session.assigned_role,
        "coins": coins,
        "debtTotal": session.debt_total,
        "debtRate": float(session.debt_rate),
        "market": market,
        "inventory": inventory,
        "inventoryEntities": inventory_entities,
    }


@app.get("/api/game/sessions", response_model=list[GameSessionItemOut])
def game_sessions(user=Depends(get_demo_user), db: Session = Depends(get_db)):
    sessions = (
        db.query(GameSession)
        .filter(GameSession.user_id == user.id)
        .order_by(GameSession.started_at.desc())
        .all()
    )
    return [
        {
            "id": s.id,
            "assignedRole": s.assigned_role,
            "status": s.status,
            "startedAt": s.started_at.isoformat() if s.started_at else "",
            "finishedAt": s.finished_at.isoformat() if s.finished_at else None,
            "resultCoinsPlayer": s.result_coins_player,
            "resultCoinsBot": s.result_coins_bot,
        }
        for s in sessions
    ]


@app.get("/api/game/session/{session_id}", response_model=GameSessionDetailOut)
def game_session_detail(session_id: str, user=Depends(get_demo_user), db: Session = Depends(get_db)):
    session = db.get(GameSession, session_id)
    if not session or session.user_id != user.id:
        return {"session": None, "seasons": []}

    seasons = (
        db.query(Season)
        .filter(Season.session_id == session_id)
        .order_by(Season.season_number.asc())
        .all()
    )
    return {
        "session": {
            "id": session.id,
            "assignedRole": session.assigned_role,
            "status": session.status,
            "startedAt": session.started_at.isoformat() if session.started_at else "",
            "finishedAt": session.finished_at.isoformat() if session.finished_at else None,
            "resultCoinsPlayer": session.result_coins_player,
            "resultCoinsBot": session.result_coins_bot,
        },
        "seasons": [
            {
                "season_number": s.season_number,
                "coins_start": s.coins_start,
                "coins_end": s.coins_end,
                "profit": s.profit,
                "bot_coins_end": s.bot_coins_end,
                "meta_json": s.meta_json or "{}",
            }
            for s in seasons
        ],
    }


def _build_recommendations(competencies: list[dict]) -> list[str]:
    recs: list[str] = []
    for c in competencies:
        name = c.get("name", "")
        score = int(c.get("score", 0))
        ev = c.get("evidence", {}) or {}

        if name.startswith("Profitability") and score < 40:
            avg_profit = ev.get("avgProfit")
            prof = ev.get("profitableSeasons")
            seasons = ev.get("seasons")
            recs.append(
                f"Улучшите маржу и частоту прибыльных сделок (avgProfit={avg_profit}, profitableSeasons={prof}/{seasons})."
            )
        elif name.startswith("Cost Control") and score < 40:
            utility = ev.get("utilityPaid")
            interest = ev.get("interestPaid")
            recs.append(
                f"Снизьте коммунальные и процентные издержки (utilityPaid={utility}, interestPaid={interest})."
            )
        elif name.startswith("Debt Management") and score < 40:
            taken = ev.get("creditsTaken")
            repaid = ev.get("creditsRepaid")
            debt_end = ev.get("debtEnd")
            recs.append(
                f"Погашайте долг быстрее и не выходите на лимит (creditsTaken={taken}, creditsRepaid={repaid}, debtEnd={debt_end})."
            )
        elif name.startswith("Discipline") and score < 40:
            finish_early = ev.get("finishEarlySeasons")
            seasons = ev.get("seasons")
            recs.append(
                f"Не завершайте сезоны досрочно (finishEarlySeasons={finish_early}/{seasons})."
            )
    return recs


@app.get("/api/analytics/profile", response_model=CompetencyProfileOut)
def analytics_profile(user=Depends(get_demo_user), db: Session = Depends(get_db)):
    session = (
        db.query(GameSession)
        .filter(GameSession.user_id == user.id, GameSession.status == "finished")
        .order_by(GameSession.finished_at.desc())
        .first()
    )
    if not session:
        return {"sessionId": "", "overall": 0, "competencies": [], "recommendations": []}

    competencies = crud.compute_competencies(db, session.id)
    overall = 0
    if competencies:
        overall = round(sum(c["score"] for c in competencies) / len(competencies))

    recommendations = _build_recommendations(competencies)
    return {
        "sessionId": session.id,
        "overall": overall,
        "competencies": competencies,
        "recommendations": recommendations,
    }


@app.get("/api/analytics/report/{session_id}")
def analytics_report(session_id: str, user=Depends(get_demo_user), db: Session = Depends(get_db)):
    if user.role != "candidate":
        raise HTTPException(status_code=403, detail="Only candidate can access report")

    session = db.get(GameSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == user.id).one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Candidate profile not found")

    seasons = (
        db.query(Season)
        .filter(Season.session_id == session_id)
        .order_by(Season.season_number.asc())
        .all()
    )
    competencies = crud.compute_competencies(db, session_id)
    recommendations = _build_recommendations(competencies)

    pdf_bytes = generate_competency_report(
        candidate_profile=profile,
        session=session,
        seasons=seasons,
        competencies=competencies,
        recommendations=recommendations,
    )
    filename = f"business_cats_report_{session_id}.pdf"
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

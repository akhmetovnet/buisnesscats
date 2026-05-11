# Cattary Manager — диплом (контекст проекта)

## Цель
HR-платформа + бизнес-симуляция Cattary Manager для формирования профиля компетенций кандидата.

## Стек
Frontend: React  
Backend: FastAPI (Python)  
DB: SQLite + SQLAlchemy

## Игровая модель (MVP)
- Игровая сессия: 13 сезонов
- Роли: cattery / petshop (случайно)
- Есть события GameEvent (trade, credits, season_summary)
- Экономика применяется в конце сезона через apply_economy_events()
- Мета сезона сохраняется в Season.meta_json (JSON string)

## Таблицы
users, candidate_profiles, game_sessions, seasons, game_events, competency_results

## Важная логика
- finish_season(db, session_id, season_number, finish_early)
  - вызывает apply_economy_events(db, session, season_number, coins)
  - пишет meta["finishEarly"] = bool(finish_early)
  - сохраняет season.meta_json = json.dumps(meta)

- apply_economy_events()
  - обрабатывает event_type: trade_market, credit_taken, credit_repaid
  - использует generate_market_prices(session_id, season_number) (детерминированно)

- compute_competencies()
  - агрегирует meta_json по сезонам
  - считает компетенции:
    Result, Profitability, Discipline(finishEarly), Financial Discipline(interest/debt),
    Cost Control, Debt Management
  - endpoint analytics/compute возвращает CompetencyProfileOut:
    {sessionId, overall, competencies:[{name, score, evidence, explanation}]}

## Что делаем дальше (следующий шаг)
1) Добавить GET /api/game/market/{session_id}/{season_number}
2) Добавить POST /api/game/trade (создаёт GameEvent типа trade_market)
3) Привязать trade к инвентарю (buy увеличивает, sell уменьшает, проверки)

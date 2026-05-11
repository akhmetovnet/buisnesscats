import SteppedModal from './SteppedModal.jsx'

function buildLeaderboardPreview(rows) {
  const normalized = Array.isArray(rows)
    ? [...rows].sort((a, b) => Number(a?.rank || 0) - Number(b?.rank || 0))
    : []

  if (normalized.length <= 7) return normalized

  const playerIndex = normalized.findIndex((row) => row?.isPlayer)
  const previewIndexes = new Set([0, 1, 2, 3, 4])

  if (playerIndex >= 0) {
    previewIndexes.add(playerIndex)
    previewIndexes.add(playerIndex - 1)
    previewIndexes.add(playerIndex + 1)
  }

  return normalized.filter((_, index) => previewIndexes.has(index))
}

export default function SeasonResultModal({ open, result, nextSeason, onConfirm }) {
  if (!open) return null

  const completionReason = String(result?.completionReason || '').toUpperCase()
  const sessionStatus = String(result?.sessionStatus || '').toUpperCase()
  const isFinalCompleted = Boolean(result?.terminal) && completionReason === 'NORMAL_COMPLETION'
  const finishedSeasonNumber = nextSeason?.number ? nextSeason.number - 1 : Number(result?.season ?? 0)
  const coinsStart = Number(result?.coinsStart ?? result?.coins_begin ?? 0)
  const coinsEnd = Number(result?.coinsEnd ?? result?.coins_end ?? 0)
  const soldProfit = Number(result?.salesProfit ?? result?.soldProfit ?? result?.sales ?? 0)
  const escapedCats = Number(result?.escapedCats ?? result?.escaped ?? 0)
  const expenses = Number(result?.expenses ?? 0)
  const profit = Number(result?.profit ?? 0)
  const finalPlace = Number(result?.finalPlace ?? 0)
  const finalBalance = Number(result?.finalBalance ?? coinsEnd)
  const seasonCountCompleted = Number(result?.seasonCountCompleted ?? 0)
  const leaderboard = Array.isArray(result?.leaderboard) ? result.leaderboard : []
  const leaderboardPreview = buildLeaderboardPreview(leaderboard)
  const expenseBreakdown = result?.expenseBreakdown || {}
  const expenseHint = [
    Number(expenseBreakdown?.tradeBuyTotal) > 0 ? `покупка котят ${Number(expenseBreakdown.tradeBuyTotal)}` : null,
    Number(expenseBreakdown?.feedExpenses) > 0 ? `корм ${Number(expenseBreakdown.feedExpenses)}` : null,
    Number(expenseBreakdown?.insuranceExpenses) > 0 ? `страховка ${Number(expenseBreakdown.insuranceExpenses)}` : null,
    Number(expenseBreakdown?.treatmentExpenses) > 0 ? `лечение ${Number(expenseBreakdown.treatmentExpenses)}` : null,
    Number(expenseBreakdown?.homeExpenses) > 0 ? `домик ${Number(expenseBreakdown.homeExpenses)}` : null,
    Number(expenseBreakdown?.utilityPaid) > 0 ? `коммуналка ${Number(expenseBreakdown.utilityPaid)}` : null,
    Number(expenseBreakdown?.interestPaid) > 0 ? `проценты ${Number(expenseBreakdown.interestPaid)}` : null,
    Number(expenseBreakdown?.untrackedExpenses) > 0 ? `прочие расходы сезона ${Number(expenseBreakdown.untrackedExpenses)}` : null,
  ]
    .filter(Boolean)
    .join(' • ')

  const resultSummary = (
    <div className="season-final season-final--step">
      <div className="season-final__summary">
        {isFinalCompleted ? (
          <>
            <div className="season-final__card">
              <span className="season-final__label">Статус</span>
              <strong>{sessionStatus === 'COMPLETED' ? 'Сессия завершена' : 'Игра завершена'}</strong>
            </div>
            <div className="season-final__card">
              <span className="season-final__label">Итоговое место</span>
              <strong>#{finalPlace || '—'}</strong>
            </div>
            <div className="season-final__card">
              <span className="season-final__label">Финальный баланс</span>
              <strong>{finalBalance}</strong>
            </div>
            <div className="season-final__card">
              <span className="season-final__label">Пройдено сезонов</span>
              <strong>{seasonCountCompleted}</strong>
            </div>
          </>
        ) : (
          <>
            <div className="season-final__card">
              <span className="season-final__label">Сезон</span>
              <strong>{finishedSeasonNumber || '—'}</strong>
            </div>
            <div className="season-final__card">
              <span className="season-final__label">Результат сезона</span>
              <strong>{profit}</strong>
            </div>
            <div className="season-final__card">
              <span className="season-final__label">Остаток</span>
              <strong>{coinsEnd}</strong>
            </div>
            <div className="season-final__card">
              <span className="season-final__label">Следующий шаг</span>
              <strong>{nextSeason?.number ? `${nextSeason.number} сезон` : 'Завершение'}</strong>
            </div>
          </>
        )}
      </div>

      <div className="season-final__callout">
        {isFinalCompleted
          ? 'Сначала посмотри своё итоговое место, затем лидеров и ключевую статистику матча.'
          : 'Кнопка продолжения остаётся на месте: сначала короткий итог, потом подробности сезона.'}
      </div>
    </div>
  )

  const leaderboardStep = (
    <div className="season-final season-final--step">
      {leaderboardPreview.length ? (
        <div className="season-final__leaderboard">
          <div className="season-final__leaderboard-note">
            {leaderboardPreview.length < leaderboard.length
              ? 'Показываем лидеров, твой результат и ближайших соседей.'
              : 'Полная таблица лидеров этого матча.'}
          </div>
          <div className="season-final__leaderboard-table season-final__leaderboard-table--scroll">
            <div className="season-final__leaderboard-head">
              <span>Место</span>
              <span>Участник</span>
              <span>Монеты</span>
            </div>
            {leaderboardPreview.map((row) => (
              <div
                className={`season-final__leaderboard-row ${row?.isPlayer ? 'is-player' : ''}`}
                key={`${row?.rank}-${row?.catteryId}`}
              >
                <span>#{Number(row?.rank || 0)}</span>
                <span>{row?.name || 'Участник'}</span>
                <span>{Number(row?.coins || 0)}</span>
              </div>
            ))}
          </div>
          <div className="modal__desc season-change-modal__desc">
            Доходы от продажи считаются отдельно, а в расходы входят все траты сезона.
          </div>
        </div>
      ) : (
        <div className="season-final__empty">
          Таблица лидеров недоступна, но итог сессии уже сохранён.
        </div>
      )}
    </div>
  )

  const statsStep = (
    <div className="season-result-stats">
      <div className="body-balance">
        <div className="body-balance-row-header">
          <p className="body-balance-row-title">деньги на начало сезона</p>
          <p className="body-balance-row-coin"><span className="body-balance-coin notranslate">{coinsStart}</span><span className="body-balance-coin-icon coin" /></p>
        </div>
        <div className="body-balance-row-header">
          <p className="body-balance-row-title">доход от продажи котиков</p>
          <p className="body-balance-row-coin"><span className="body-balance-coin notranslate">{soldProfit}</span><span className="body-balance-coin-icon coin" /></p>
        </div>
        <div className="body-balance-row-header">
          <p className="body-balance-row-title">число сбежавших котиков</p>
          <p className="body-balance-row-coin"><span className="body-balance-coin notranslate">{escapedCats}</span></p>
        </div>
        <div className="body-balance-row-header">
          <p className="body-balance-row-title">расходы</p>
          <p className="body-balance-row-coin"><span className="body-balance-coin body-balance-coin--negative notranslate">{expenses}</span><span className="body-balance-coin-icon coin" /></p>
        </div>
        {expenseHint ? <p className="body-balance-row-hint">{expenseHint}</p> : null}
        <div className="body-balance-row-header">
          <p className="body-balance-row-title">итог сезона</p>
          <p className="body-balance-row-coin">
            <span className={`body-balance-coin ${profit < 0 ? 'body-balance-coin--negative' : 'body-balance-coin--positive'} notranslate`}>
              {profit}
            </span>
            <span className="body-balance-coin-icon coin" />
          </p>
        </div>
        <div className="body-balance-row-header">
          <p className="body-balance-row-title">остаток</p>
          <p className="body-balance-row-coin"><span className="body-balance-coin notranslate">{coinsEnd}</span><span className="body-balance-coin-icon coin" /></p>
        </div>
      </div>

      <div className="body-result">
        <div className="body-result__item">
          <span className="body-balance-season-text body-result__text">деньги на начало</span>
          <div className="body-result__cost"><span className="body-balance-coin notranslate">{coinsStart}</span><span className="body-balance-coin-icon coin" /></div>
        </div>
        <div className="body-result__item">
          <span className="body-balance-season-text body-result__text">итог сезона</span>
          <div className="body-result__cost">
            <span className={`body-balance-coin ${profit < 0 ? 'body-balance-coin--negative' : 'body-balance-coin--positive'} notranslate`}>{profit}</span>
            <span className="body-balance-coin-icon coin" />
          </div>
        </div>
        <div className="body-result__item">
          <span className="body-balance-season-text body-result__text">остаток</span>
          <div className="body-result__cost"><span className="body-balance-coin notranslate">{coinsEnd}</span><span className="body-balance-coin-icon coin" /></div>
        </div>
      </div>
    </div>
  )

  const steps = isFinalCompleted
    ? [
        {
          key: 'summary',
          icon: '🏆',
          title: 'Ваш результат',
          subtitle: 'Сначала короткий итог сессии, без длинной прокрутки до кнопки.',
          primaryLabel: 'Далее',
          body: resultSummary,
        },
        {
          key: 'leaderboard',
          icon: '📊',
          title: 'Таблица лидеров',
          subtitle: 'Компактный список: лидеры матча, твой результат и ближайшие соседи.',
          primaryLabel: 'Далее',
          body: leaderboardStep,
        },
        {
          key: 'stats',
          icon: '💼',
          title: 'Краткая статистика',
          subtitle: 'Доходы, расходы и итог сезона собраны в отдельный шаг.',
          primaryLabel: 'Вернуться на платформу',
          body: statsStep,
        },
      ]
    : [
        {
          key: 'summary',
          icon: '📘',
          title: `Итоги ${finishedSeasonNumber || ''} сезона`,
          subtitle: 'Короткий итог перед переходом к следующему сезону.',
          primaryLabel: 'Далее',
          body: resultSummary,
        },
        {
          key: 'stats',
          icon: '💰',
          title: 'Финансы сезона',
          subtitle: 'Подробные доходы и расходы вынесены на отдельный экран с фиксированной кнопкой.',
          primaryLabel: nextSeason?.number ? `К ${nextSeason.number} сезону` : 'Продолжить',
          body: statsStep,
        },
      ]

  return (
    <SteppedModal
      open={open}
      steps={steps}
      sizeClassName="modal--size-very-big"
      className="season-change-modal stepped-modal--season-result"
      onComplete={onConfirm}
    />
  )
}

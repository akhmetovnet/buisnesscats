import './Overlay.css'

export default function SeasonResultModal({ open, result, nextSeason, onConfirm }) {
  if (!open) return null

  const coinsStart = Number(result?.coinsStart ?? result?.coins_begin ?? 0)
  const coinsEnd = Number(result?.coinsEnd ?? result?.coins_end ?? 0)
  const soldProfit = Number(result?.salesProfit ?? result?.soldProfit ?? result?.sales ?? 0)
  const escapedCats = Number(result?.escapedCats ?? result?.escaped ?? 0)
  const expenses = Number(result?.expenses ?? 0)
  const profit = Number(result?.profit ?? 0)
  const credit = Number(result?.creditDelta ?? result?.creditChange ?? 0)
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

  return (
    <div className="modal-overlay" onClick={onConfirm}>
      <div className="modal modal--size-very-big season-change-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <div className="modal__title season-change-modal__title">
            <span className="season-change-modal__icon">🏆</span>
            ИТОГИ {nextSeason?.number ? nextSeason.number - 1 : ''} СЕЗОНА
          </div>
          <div className="modal__desc season-change-modal__desc">
            Доходы от продажи считаются отдельно, а в расходы входят все траты сезона.
          </div>
        </div>
        <div className="modal__body">
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
              <p className="body-balance-row-title">кредит</p>
              <p className="body-balance-row-coin">
                <span className={`body-balance-coin ${credit < 0 ? 'body-balance-coin--negative' : ''} notranslate`}>{credit}</span>
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

          <div className="modal__body-actions season-change-modal__body-actions">
            <button className="text_button text_button--color-blue" onClick={onConfirm}>ПОНЯТНО</button>
          </div>
        </div>
      </div>
    </div>
  )
}

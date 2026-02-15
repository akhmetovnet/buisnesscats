import './Overlay.css'

export default function SeasonResultModal({ open, result, nextSeason, onConfirm }) {
  if (!open) return null

  const coinsStart = Number(result?.coinsStart ?? result?.coins_begin ?? 0)
  const coinsEnd = Number(result?.coinsEnd ?? result?.coins_end ?? 0)
  const soldProfit = Number(result?.salesProfit ?? result?.soldProfit ?? result?.sales ?? 0)
  const escapedCats = Number(result?.escapedCats ?? result?.escaped ?? 0)
  const expenses = Number(result?.expenses ?? coinsStart)
  const profit = Number(result?.profit ?? coinsEnd - coinsStart)
  const credit = Number(result?.creditDelta ?? result?.creditChange ?? 0)

  return (
    <div className="modal-overlay" onClick={onConfirm}>
      <div className="modal modal--size-very-big season-change-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <div className="modal__title season-change-modal__title">
            <span className="season-change-modal__icon">🏆</span>
            ИТОГИ {nextSeason?.number ? nextSeason.number - 1 : ''} СЕЗОНА
          </div>
        </div>
        <div className="modal__body">
          <div className="body-balance">
            <div className="body-balance-row-header">
              <p className="body-balance-row-title">деньги на начало сезона</p>
              <p className="body-balance-row-coin"><span className="body-balance-coin notranslate">{coinsStart}</span><span className="body-balance-coin-icon coin" /></p>
            </div>
            <div className="body-balance-row-header">
              <p className="body-balance-row-title">продажа котиков</p>
              <p className="body-balance-row-coin"><span className="body-balance-coin notranslate">{soldProfit}</span><span className="body-balance-coin-icon coin" /></p>
            </div>
            <div className="body-balance-row-header">
              <p className="body-balance-row-title">число сбежавших котиков</p>
              <p className="body-balance-row-coin"><span className="body-balance-coin notranslate">{escapedCats}</span></p>
            </div>
            <div className="body-balance-row-header">
              <p className="body-balance-row-title">расходы</p>
              <p className="body-balance-row-coin"><span className="body-balance-coin body-balance-coin--not notranslate">{expenses}</span><span className="body-balance-coin-icon coin" /></p>
            </div>
            <div className="body-balance-row-header">
              <p className="body-balance-row-title">прибыль</p>
              <p className="body-balance-row-coin"><span className="body-balance-coin notranslate">{profit}</span><span className="body-balance-coin-icon coin" /></p>
            </div>
            <div className="body-balance-row-header">
              <p className="body-balance-row-title">кредит</p>
              <p className="body-balance-row-coin"><span className="body-balance-coin notranslate">{credit}</span><span className="body-balance-coin-icon coin" /></p>
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
              <span className="body-balance-season-text body-result__text">прибыль</span>
              <div className="body-result__cost"><span className="body-balance-coin notranslate">{profit}</span><span className="body-balance-coin-icon coin" /></div>
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

import './Overlay.css'

export default function CreditOverlay({
  open,
  onClose,
  amount,
  creditType,
  onAmountChange,
  onCreditTypeChange,
  onTake,
  onRepay,
  busy,
  debtTotal,
  debtRate,
  seasonNumber,
}) {
  if (!open) return null

  return (
    <div className="overlay credit-overlay" onClick={onClose}>
      <div className="credit-panel" onClick={(e) => e.stopPropagation()}>
        <div className="credit-panel__header">
          <div className="credit-panel__title">Кредиты</div>
          <button className="credit-panel__close" onClick={onClose}>
            ✕
          </button>
        </div>
        <div className="credit-panel__meta">
          <span>Debt: {debtTotal}</span>
          <span>Rate: {(debtRate * 100).toFixed(1)}%</span>
          <span>Season {seasonNumber}</span>
        </div>
        <label>
          Amount
          <input
            type="number"
            min="1"
            value={amount}
            onChange={(e) => onAmountChange(e.target.value)}
          />
        </label>
        <label>
          Type
          <select value={creditType} onChange={(e) => onCreditTypeChange(e.target.value)}>
            <option value="consumer">consumer</option>
            <option value="investment">investment</option>
            <option value="special">special</option>
          </select>
        </label>
        <div className="credit-panel__actions">
          <button onClick={onTake} disabled={busy}>
            TAKE
          </button>
          <button className="danger" onClick={onRepay} disabled={busy}>
            REPAY
          </button>
        </div>
      </div>
    </div>
  )
}

import './Overlay.css'

export default function LoseModal({ open, onConfirm }) {
  if (!open) return null

  return (
    <div className="overlay" onClick={onConfirm}>
      <div className="confirm-panel" onClick={(e) => e.stopPropagation()}>
        <div className="confirm-title">ВЫ ПРОИГРАЛИ</div>
        <div className="confirm-actions">
          <button className="confirm-btn confirm-btn--beige" onClick={onConfirm}>
            ОК
          </button>
        </div>
      </div>
    </div>
  )
}

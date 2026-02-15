import './Overlay.css'

export default function ConfirmEndSeasonModal({ open, onConfirm, onCancel }) {
  if (!open) return null

  return (
    <div className="overlay" onClick={onCancel}>
      <div className="confirm-panel" onClick={(e) => e.stopPropagation()}>
        <div className="confirm-title">ТОЧНО ХОЧЕШЬ ЗАВЕРШИТЬ СЕЗОН?</div>
        <div className="confirm-icon">?</div>
        <div className="confirm-actions">
          <button className="confirm-btn confirm-btn--green" onClick={onConfirm}>
            ЗАВЕРШИТЬ
          </button>
          <button className="confirm-btn confirm-btn--beige" onClick={onCancel}>
            ОТМЕНА
          </button>
        </div>
      </div>
    </div>
  )
}

import './Overlay.css'

export default function LoseModal({ open, onConfirm }) {
  if (!open) return null

  return (
    <div className="modal-overlay" onClick={onConfirm}>
      <div className="modal modal--size-cats" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <div className="modal__title">Сессия завершена</div>
          <div className="modal__desc">
            У вас закончились монеты. Проверьте историю сессий и запустите новую попытку.
          </div>
        </div>
        <div className="modal__body">
          <div className="modal__body-actions">
            <button className="text_button text_button--color-blue" onClick={onConfirm}>
              Понятно
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

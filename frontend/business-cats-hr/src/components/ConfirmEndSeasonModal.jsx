import './Overlay.css'

export default function ConfirmEndSeasonModal({ open, onConfirm, onCancel }) {
  if (!open) return null

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal modal--size-cats" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <div className="modal__title">Вы точно хотите завершить сезон?</div>
          <div className="modal__desc">
            После завершения сезона будут применены все действия текущего хода.
          </div>
        </div>
        <div className="modal__body">
          <div className="modal__body-actions">
            <button className="text_button text_button--color-blue" onClick={onConfirm}>
              Завершить сезон
            </button>
            <button className="text_button text_button--color-transparent" onClick={onCancel}>
              Отмена
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

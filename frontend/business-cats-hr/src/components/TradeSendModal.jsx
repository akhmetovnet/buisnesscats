import './TradeRequests.css'

const SIDE_LABEL = {
  BUY: 'Покупка',
  SELL: 'Продажа',
}

const COLOR_LABEL = {
  black: 'черный',
  white: 'белый',
  gray: 'серый',
  ginger: 'рыжий',
}

const SEX_LABEL = {
  M: 'мальчик',
  F: 'девочка',
}

function renderItem(item) {
  if (!item) return '—'
  const color = String(item?.catColor || item?.catType || item?.catTypeId || '').trim().toLowerCase()
  const sex = String(item?.catSex || '').trim().toUpperCase()
  const sexText = item.catSex ? ` (${SEX_LABEL[sex] || 'котик'})` : ''
  const price = Number(item?.proposedPrice ?? item?.unitPrice ?? 0)
  return `${SIDE_LABEL[item.side] || item.side} • ${COLOR_LABEL[color] || 'котик'}${sexText} • ${price}`
}

export default function TradeSendModal({ open, request, onClose }) {
  if (!open || !request) return null
  return (
    <div className="request-modal-overlay" onClick={onClose}>
      <div className="request-modal" onClick={(e) => e.stopPropagation()}>
        <h2 className="request-modal__title">ПРЕДЛОЖЕНИЕ ОТПРАВЛЕНО</h2>
        <p className="request-modal__subtitle">
          в {request.toMeta?.displayName || 'контрагенту'}
        </p>
        <ul className="request-modal__list">
          {(request.items || []).map((item, index) => (
            <li key={`${item.catTypeId}-${item.side}-${index}`} className="request-modal__line">
              {renderItem(item)}
            </li>
          ))}
        </ul>
        <div className="request-modal__sum">Итого: {request.totalPrice}</div>
        <div className="request-modal__actions">
          <button className="request-btn" type="button" onClick={onClose}>
            ПОНЯТНО
          </button>
        </div>
      </div>
    </div>
  )
}

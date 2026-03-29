import './TradeRequests.css'

const STATE_LABEL = {
  PENDING_INCOMING: 'Входящая',
  PENDING_OUTGOING: 'Отправлена',
  COUNTERED: 'Встречная',
  ACCEPTED: 'Одобрено',
  REJECTED: 'Отклонено',
  AWAITING_CLARIFICATION: 'Ждёт уточнение',
  CANCELLED: 'Отменено',
  NEEDS_CLARIFICATION: 'Нужно уточнение',
  EXPIRED: 'Истекло',
}

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

function RequestItem({ request, onOpen }) {
  const firstItem = request?.items?.[0]
  const color = String(firstItem?.catColor || firstItem?.catType || firstItem?.catTypeId || '').trim().toLowerCase()
  const sex = String(firstItem?.catSex || '').trim().toUpperCase()
  const summary = firstItem
    ? `${SIDE_LABEL[firstItem.side] || firstItem.side} ${COLOR_LABEL[color] || 'котик'}${firstItem.catSex ? ` (${SEX_LABEL[sex] || 'котик'})` : ''}`
    : 'Без позиций'
  const status = request?.status || request?.state

  return (
    <button className="request-item" type="button" onClick={() => onOpen?.(request)}>
      {request.unread ? <span className="request-item__badge">!</span> : null}
      {request.icon ? (
        <img
          src={request.icon}
          alt="иконка заявки"
          onError={(e) => {
            e.currentTarget.style.display = 'none'
          }}
        />
      ) : null}
      <span className="request-item__avatar">{request.fromMeta?.avatarText || '?'}</span>
      <span className="request-item__state">{STATE_LABEL[status] || status}</span>
      <span className="request-item__summary">{summary}</span>
      <span className="request-item__sum">{request.totalPrice}</span>
    </button>
  )
}

export default function RequestsSidebar({
  requests,
  onOpenRequest,
  variant = 'fixed',
  emptyLabel = '',
}) {
  const items = Array.isArray(requests) ? requests : []
  if (!items.length && variant === 'fixed') return null
  return (
    <aside className={`requests-sidebar requests-sidebar--${variant}`}>
      <div className="requests-sidebar__stack">
        {items.length
          ? items.map((request) => (
              <RequestItem key={request.id} request={request} onOpen={onOpenRequest} />
            ))
          : (
            <div className="requests-sidebar__empty">{emptyLabel || 'Заявок пока нет'}</div>
          )}
      </div>
    </aside>
  )
}

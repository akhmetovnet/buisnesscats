import { useEffect, useMemo, useState } from 'react'
import './TradeRequests.css'

const TERMINAL_STATES = new Set(['ACCEPTED', 'REJECTED', 'CANCELLED', 'EXPIRED'])
const MAX_PRICE = 999

const TITLE_BY_STATUS = {
  PENDING_INCOMING: 'ВХОДЯЩАЯ ЗАЯВКА',
  PENDING_OUTGOING: 'ИСХОДЯЩАЯ ЗАЯВКА',
  COUNTERED: 'ВСТРЕЧНОЕ ПРЕДЛОЖЕНИЕ',
  ACCEPTED: 'ПОКУПКА ОДОБРЕНА',
  REJECTED: 'ПОКУПКА ОТКЛОНЕНА',
  CANCELLED: 'ПОКУПКА ОТМЕНЕНА',
  EXPIRED: 'ЗАЯВКА ИСТЕКЛА',
  NEEDS_CLARIFICATION: 'ТРЕБУЕТ УТОЧНЕНИЯ',
  AWAITING_CLARIFICATION: 'УТОЧНЕНИЕ ОЖИДАЕТСЯ',
}

const CLARIFICATION_REASON_LABEL = {
  CAT_ALREADY_SOLD: 'Котик уже продан',
  CAT_NOT_AVAILABLE: 'Котик недоступен',
  CAT_STATE_CHANGED: 'Состояние котика изменилось',
  PRICE_OUTDATED: 'Цена устарела',
  UNKNOWN: 'Нужно обновить заявку',
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

const DECISION_REASON_LABEL = {
  GOOD_DEAL: 'Выгодная цена',
  FAIR_PRICE: 'Справедливая цена',
  ABOVE_MARKET_BUT_ACCEPTABLE: 'Цена выше базовой, но всё ещё приемлема',
  PRICE_TOO_HIGH: 'Цена слишком высокая',
  LOW_CASH: 'У магазина не хватает монет',
  LOW_DEMAND: 'Низкий спрос',
  OVERSTOCKED: 'Склад переполнен',
  BAD_RELATION: 'Слабые отношения',
  NO_RELATION: 'Нет доверия к игроку',
  FAIR_COUNTER: 'Магазин предлагает справедливую встречную цену',
}

const normalizeTradePriceInput = (value) =>
  String(value ?? '')
    .replace(/[^\d]/g, '')
    .slice(0, String(MAX_PRICE).length)

const parseTradePrice = (value) => {
  const normalized = normalizeTradePriceInput(value)
  if (!normalized) return null
  const parsed = Number(normalized)
  if (!Number.isInteger(parsed) || parsed <= 0 || parsed > MAX_PRICE) return null
  return parsed
}

function toDraftItems(items) {
  return (Array.isArray(items) ? items : []).map((item, index) => {
    const price = Number(item?.proposedPrice ?? item?.unitPrice ?? 0)
    return {
      key: item?.itemId || `${item?.catId || item?.catTypeId || 'cat'}-${index}`,
      itemId: item?.itemId || null,
      catId: item?.catId || null,
      catType: item?.catType || item?.catColor || item?.catTypeId || '',
      catColor: item?.catColor || item?.catType || item?.catTypeId || '',
      catTypeId: item?.catTypeId || item?.catColor || item?.catType || '',
      catSex: item?.catSex || null,
      side: item?.side || 'SELL',
      priceInput: price > 0 ? String(price) : '',
    }
  })
}

function formatLine(item) {
  const color = String(item?.catColor || item?.catType || item?.catTypeId || '').trim().toLowerCase()
  const sex = String(item?.catSex || '').trim().toUpperCase()
  const sexText = item.catSex ? ` (${SEX_LABEL[sex] || 'котик'})` : ''
  const price = Number(item?.proposedPrice ?? item?.unitPrice ?? 0)
  return `${SIDE_LABEL[item.side] || item.side} • ${COLOR_LABEL[color] || 'котик'}${sexText} • ${price}`
}

function formatDecisionLine(line, index) {
  const color = String(line?.catType || '').trim().toLowerCase()
  const title = COLOR_LABEL[color] || `котик ${index + 1}`
  const reason = DECISION_REASON_LABEL[String(line?.reason || '').trim().toUpperCase()] || null
  return {
    title,
    playerPrice: Number(line?.playerPrice ?? 0),
    shopPrice: Number(line?.shopPrice ?? 0),
    reason,
  }
}

export default function RequestModal({
  open,
  request,
  busy = false,
  onClose,
  onAction,
}) {
  const status = request?.status || request?.state
  const title = useMemo(() => TITLE_BY_STATUS[status] || 'ЗАЯВКА', [status])
  const [draftItems, setDraftItems] = useState([])

  useEffect(() => {
    if (!open || !request) return
    setDraftItems(toDraftItems(request.items))
  }, [open, request])

  if (!open || !request) return null

  const canAct = Boolean(request.canAct)
  const isTerminal = TERMINAL_STATES.has(status)
  const viewerIsInitiator = request.fromMeta?.avatarText === 'Я'
  const isCounterFlow = canAct && (status === 'PENDING_INCOMING' || status === 'COUNTERED')
  const isClarificationFlow = canAct && status === 'NEEDS_CLARIFICATION'
  const invalidDraft = draftItems.some((item) => parseTradePrice(item.priceInput) == null)
  const clarificationReason = request.clarificationReason
  const clarificationMessage = request.clarificationMeta?.message
  const clarificationTitle =
    CLARIFICATION_REASON_LABEL[clarificationReason] || CLARIFICATION_REASON_LABEL.UNKNOWN
  const decisionMeta = request.decisionMeta
  const decisionTitle =
    DECISION_REASON_LABEL[String(decisionMeta?.reason || '').trim().toUpperCase()] || null
  const decisionLines = Array.isArray(decisionMeta?.lines) ? decisionMeta.lines : []
  const showDecisionBox =
    Boolean(decisionMeta) && (status === 'COUNTERED' || status === 'REJECTED' || status === 'ACCEPTED')

  const draftPayload = draftItems.map((item) => {
    const price = Number(parseTradePrice(item.priceInput) || 1)
    return {
      itemId: item.itemId,
      catId: item.catId,
      catType: item.catType,
      catColor: item.catColor,
      catTypeId: item.catTypeId,
      catSex: item.catSex,
      proposedPrice: price,
      unitPrice: price,
      quantity: 1,
      currency: 'COIN',
      side: item.side,
    }
  })

  return (
    <div className="request-modal-overlay" onClick={onClose}>
      <div className="request-modal" onClick={(e) => e.stopPropagation()}>
        <h2 className="request-modal__title">{title}</h2>
        <p className="request-modal__subtitle">
          {request.fromMeta?.displayName} → {request.toMeta?.displayName}
        </p>

        {status === 'NEEDS_CLARIFICATION' || status === 'AWAITING_CLARIFICATION' ? (
          <div className="request-modal__notice">
            <strong>{clarificationTitle}</strong>
            {clarificationMessage ? <span>{clarificationMessage}</span> : null}
          </div>
        ) : null}

        {showDecisionBox ? (
          <div className="request-modal__decision">
            <strong>{decisionTitle || 'Решение магазина'}</strong>
            {decisionMeta?.message ? <span>{decisionMeta.message}</span> : null}
            {decisionLines.length ? (
              <div className="request-modal__decision-lines">
                {decisionLines.map((line, index) => {
                  const formatted = formatDecisionLine(line, index)
                  return (
                    <div className="request-modal__decision-line" key={`${formatted.title}-${index}`}>
                      <div className="request-modal__decision-line-title">{formatted.title}</div>
                      <div className="request-modal__decision-line-prices">
                        <span>Твоя цена: {formatted.playerPrice}</span>
                        <span>Цена магазина: {formatted.shopPrice}</span>
                      </div>
                      {formatted.reason ? (
                        <div className="request-modal__decision-line-reason">{formatted.reason}</div>
                      ) : null}
                    </div>
                  )
                })}
              </div>
            ) : null}
          </div>
        ) : null}

        <ul className="request-modal__list">
          {(isCounterFlow || isClarificationFlow ? draftItems : request.items || []).map((item, index) => {
            const priceValue = isCounterFlow || isClarificationFlow ? item.priceInput : String(item?.proposedPrice ?? item?.unitPrice ?? '')
            const invalidPrice = (isCounterFlow || isClarificationFlow) && parseTradePrice(priceValue) == null
            return (
              <li key={`${item.itemId || item.catId || index}`} className="request-modal__line request-modal__line--editable">
                <div className="request-modal__line-text">
                  {formatLine(
                    isCounterFlow || isClarificationFlow
                      ? { ...item, proposedPrice: parseTradePrice(priceValue) ?? 0 }
                      : item
                  )}
                </div>
                {isCounterFlow || isClarificationFlow ? (
                  <label className="request-modal__price-editor">
                    <span>Предлагаемая цена</span>
                    <input
                      className={invalidPrice ? 'is-invalid' : ''}
                      value={priceValue}
                      inputMode="numeric"
                      pattern="[0-9]*"
                      onChange={(event) => {
                        const nextValue = normalizeTradePriceInput(event.target.value)
                        setDraftItems((prev) =>
                          prev.map((draftItem) =>
                            draftItem.key === item.key
                              ? { ...draftItem, priceInput: nextValue }
                              : draftItem
                          )
                        )
                      }}
                    />
                  </label>
                ) : null}
              </li>
            )
          })}
        </ul>

        {(isCounterFlow || isClarificationFlow) && invalidDraft ? (
          <div className="request-modal__error">Введите корректную цену</div>
        ) : null}

        <div className="request-modal__sum">
          Итого:{' '}
          {isCounterFlow || isClarificationFlow
            ? draftPayload.reduce((sum, item) => sum + Number(item.proposedPrice || 0), 0)
            : request.totalPrice}
        </div>

        <div className="request-modal__actions">
          {isCounterFlow ? (
            <>
              <button className="request-btn" type="button" disabled={busy} onClick={() => onAction('accept')}>
                ПРИНЯТЬ
              </button>
              <button className="request-btn request-btn--danger" type="button" disabled={busy} onClick={() => onAction('reject')}>
                ОТКЛОНИТЬ
              </button>
              <button
                className="request-btn request-btn--secondary"
                type="button"
                disabled={busy || invalidDraft}
                onClick={() => onAction('counter', { counterItems: draftPayload })}
              >
                ПРЕДЛОЖИТЬ НОВУЮ ЦЕНУ
              </button>
              <button className="request-btn request-btn--secondary" type="button" disabled={busy} onClick={() => onAction('request_clarification')}>
                НУЖНО УТОЧНЕНИЕ
              </button>
            </>
          ) : null}

          {isClarificationFlow ? (
            <>
              <button
                className="request-btn"
                type="button"
                disabled={busy || invalidDraft}
                onClick={() => onAction('clarify', { counterItems: draftPayload })}
              >
                УТОЧНИТЬ И ОТПРАВИТЬ
              </button>
              <button className="request-btn request-btn--danger" type="button" disabled={busy} onClick={() => onAction('cancel')}>
                ОТМЕНИТЬ
              </button>
            </>
          ) : null}

          {!isTerminal && status === 'PENDING_OUTGOING' && viewerIsInitiator ? (
            <button className="request-btn request-btn--secondary" type="button" disabled={busy} onClick={() => onAction('cancel')}>
              ОТМЕНИТЬ
            </button>
          ) : null}

          <button
            className="request-btn request-btn--secondary"
            type="button"
            disabled={busy}
            onClick={() => onAction('ack')}
          >
            ПОНЯТНО
          </button>
        </div>
      </div>
    </div>
  )
}

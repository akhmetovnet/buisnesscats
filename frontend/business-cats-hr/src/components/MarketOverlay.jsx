import { useMemo, useState } from 'react'
import CreditOverlay from './CreditOverlay.jsx'
import './Overlay.css'

const DEFAULT_TYPES = ['black', 'white', 'ginger', 'gray']
const SEX_ORDER = ['M', 'F']
const VALID_SEX = new Set(['M', 'F'])
const COLOR_ALIAS = {
  orange: 'ginger',
}
const CAT_SPRITES = {
  M: {
    black: '/assets/male-small-cat-black.png',
    white: '/assets/male-small-cat-white.png',
    gray: '/assets/male-small-cat-gray.png',
    ginger: '/assets/male-small-cat-orange.png',
  },
  F: {
    black: '/assets/female-small-cat-black.png',
    white: '/assets/female-small-cat-white.png',
    gray: '/assets/female-small-cat-gray.png',
    ginger: '/assets/female-small-cat-orange.png',
  },
}
const SEX_CLASS = {
  M: 'male',
  F: 'female',
}

const toQty = (value) => {
  const n = Number(value)
  if (!Number.isFinite(n) || n <= 0) return 1
  return Math.floor(n)
}

const toPrice = (value) => {
  const n = Number(value)
  if (!Number.isFinite(n) || n < 0) return 0
  return Math.floor(n)
}

const normalizeColor = (value) => {
  const normalized = String(value ?? '')
    .trim()
    .toLowerCase()
  return COLOR_ALIAS[normalized] || normalized
}

const normalizeSex = (value) => {
  if (typeof value !== 'string') return null
  const normalized = value.trim().toUpperCase()
  return VALID_SEX.has(normalized) ? normalized : null
}

const resolveKittenStatus = (cat) => {
  if (typeof cat?.isKitten === 'boolean') return cat.isKitten
  if (typeof cat?.lifeStage === 'string') {
    const stage = cat.lifeStage.trim().toLowerCase()
    if (stage === 'kitten') return true
    if (stage === 'adult') return false
  }
  if (typeof cat?.entityType === 'string') {
    const entityType = cat.entityType.trim().toLowerCase()
    if (entityType === 'kitten') return true
    if (entityType === 'adult') return false
  }
  const ageValue = Number(cat?.age ?? cat?.ageSeasons)
  if (Number.isFinite(ageValue)) return ageValue < 3
  return null
}

const getCatSprite = (color, sex) => {
  const normalizedColor = normalizeColor(color)
  const normalizedSex = normalizeSex(sex) || 'M'
  return (
    CAT_SPRITES[normalizedSex]?.[normalizedColor] ||
    CAT_SPRITES.M[normalizedColor] ||
    CAT_SPRITES.M.gray
  )
}

const getMarketSidePrice = (market, color, sex, side) => {
  const normalizedColor = normalizeColor(color)
  const normalizedSex = normalizeSex(sex)
  const entry = market?.[normalizedColor]
  if (!entry) return 0
  if (normalizedSex && entry?.[normalizedSex]?.[side] != null) {
    return toPrice(entry[normalizedSex][side])
  }
  if (entry?.[side] != null) return toPrice(entry[side])
  return 0
}

const normalizeInventoryEntities = (inventoryEntities) => {
  if (!inventoryEntities) return []
  if (Array.isArray(inventoryEntities)) return inventoryEntities
  if (Array.isArray(inventoryEntities.items)) return inventoryEntities.items
  if (Array.isArray(inventoryEntities.cats)) return inventoryEntities.cats
  return []
}

const isEntityHungry = (entity) =>
  Boolean(entity?.hungry) && entity?.hungry !== 'false' && entity?.hungry !== 0

function CatTile({
  cat,
  count,
  draggable,
  onDragStart,
  onClick,
  disabled,
  imageSrc,
  sexLabel,
}) {
  const normalizedSex = normalizeSex(cat?.sex) || 'M'
  const variantClass = `cat-card--${SEX_CLASS[normalizedSex]}-${normalizeColor(cat.type)}`
  return (
    <div
      className={`cat-card ${variantClass} ${disabled ? 'is-disabled' : ''}`}
      draggable={draggable && !disabled}
      onDragStart={onDragStart}
      onClick={disabled ? undefined : onClick}
    >
      {typeof count === 'number' ? (
        <span className="cat-card__count notranslate">×{count}</span>
      ) : null}
      <span className="cat-card__image">
        <img src={imageSrc} alt={cat.type} />
      </span>
      <div className="cat-card__price-wrapper">
        <div className="cat-card__price">
          <div className="cat-card__price-name">Покупка</div>
          <div className="price-value">
            <span className="coin" />
            <span className="price-value__cost notranslate">{cat.buy}</span>
          </div>
        </div>
        <div className="cat-card__price">
          <div className="cat-card__price-name">Продажа</div>
          <div className="price-value">
            <span className="coin" />
            <span className="price-value__cost notranslate">{cat.sell}</span>
          </div>
        </div>
      </div>
      {sexLabel ? <div className="cat-card__sex">{sexLabel}</div> : null}
    </div>
  )
}

function PriceModal({ open, onClose, type, buy, sell, imageSrc, onSave }) {
  const [buyValue, setBuyValue] = useState(buy)
  const [sellValue, setSellValue] = useState(sell)

  if (!open) return null

  return (
    <div className="overlay price-modal" onClick={onClose}>
      <div className="price-modal__panel" onClick={(e) => e.stopPropagation()}>
        <div className="price-modal__title">Настройка цен: {type}</div>
        <div className="price-modal__cat">
          <img src={imageSrc || CAT_SPRITES.M.gray} alt={type} />
        </div>
        <label>
          Цена покупки
          <input
            type="number"
            value={buyValue}
            onChange={(e) => setBuyValue(toPrice(e.target.value))}
          />
        </label>
        <label>
          Цена продажи
          <input
            type="number"
            value={sellValue}
            onChange={(e) => setSellValue(toPrice(e.target.value))}
          />
        </label>
        <div className="price-modal__actions">
          <button onClick={() => onSave(buyValue, sellValue)}>СОХРАНИТЬ</button>
          <button className="ghost" onClick={onClose}>
            ОТМЕНА
          </button>
        </div>
      </div>
    </div>
  )
}

export default function MarketOverlay({
  open,
  onClose,
  buildingId,
  titleName,
  titleType,
  stripName,
  stripType,
  overlayType,
  seasonNumber,
  coinsNow,
  debtTotal,
  debtRate,
  inventory,
  market,
  inventoryEntities,
  playerRole,
  busy,
  error,
  onTrade,
  onCreditTake,
  onCreditRepay,
}) {
  const items = useMemo(() => {
    const keys = Object.keys(market || {})
    if (keys.length) return keys
    return DEFAULT_TYPES
  }, [market])

  const cats = useMemo(
    () =>
      items.map((type) => ({
        id: type,
        type,
        buy: getMarketSidePrice(market, type, null, 'buy'),
        sell: getMarketSidePrice(market, type, null, 'sell'),
      })),
    [items, market]
  )

  const marketTiles = useMemo(
    () =>
      cats.flatMap((cat) =>
        SEX_ORDER.map((sex) => ({
          ...cat,
          id: `${cat.type}:${sex}`,
          sex,
          buy: getMarketSidePrice(market, cat.type, sex, 'buy'),
          sell: getMarketSidePrice(market, cat.type, sex, 'sell'),
        }))
      ),
    [cats, market]
  )

  const [tradeItems, setTradeItems] = useState([])
  const [creditOpen, setCreditOpen] = useState(false)
  const [creditAmount, setCreditAmount] = useState(5)
  const [creditType, setCreditType] = useState('consumer')
  const [priceEditor, setPriceEditor] = useState(null)
  const [customPrices, setCustomPrices] = useState({})
  const [tradeValidationError, setTradeValidationError] = useState('')

  const ownPrices = useMemo(() => {
    const base = {}
    items.forEach((type) => {
      base[type] = {
        buy: getMarketSidePrice(market, type, null, 'buy'),
        sell: getMarketSidePrice(market, type, null, 'sell'),
      }
      SEX_ORDER.forEach((sex) => {
        base[`${type}:${sex}`] = {
          buy: getMarketSidePrice(market, type, sex, 'buy'),
          sell: getMarketSidePrice(market, type, sex, 'sell'),
        }
      })
    })
    return { ...base, ...customPrices }
  }, [items, market, customPrices])

  const normalizedEntities = useMemo(
    () => normalizeInventoryEntities(inventoryEntities),
    [inventoryEntities]
  )

  const kittenEntities = useMemo(
    () =>
      normalizedEntities.filter((entity) => {
        const color = normalizeColor(entity?.color ?? entity?.catType)
        const kitten = resolveKittenStatus(entity)
        return DEFAULT_TYPES.includes(color) && kitten === true
      }),
    [normalizedEntities]
  )

  const hasEntityMetadata = normalizedEntities.length > 0

  const mineTiles = useMemo(() => {
    if (!hasEntityMetadata) {
      return cats.map((cat) => ({
        key: `legacy:${cat.type}`,
        color: cat.type,
        sex: null,
        count: Number(inventory?.[cat.type] ?? 0),
        readyCount: Number(inventory?.[cat.type] ?? 0),
        buy: ownPrices[cat.type]?.buy ?? cat.buy,
        sell: ownPrices[cat.type]?.sell ?? cat.sell,
        strict: false,
      }))
    }

    const grouped = new Map()
    kittenEntities.forEach((entity) => {
      const color = normalizeColor(entity?.color ?? entity?.catType)
      const sex = normalizeSex(entity?.sex)
      if (!DEFAULT_TYPES.includes(color)) return
      const groupSex = sex || 'M'
      const key = `${color}:${groupSex}`
      if (!grouped.has(key)) {
        grouped.set(key, {
          key,
          color,
          sex: groupSex,
          count: 0,
          readyCount: 0,
          buy:
            ownPrices[`${color}:${groupSex}`]?.buy ??
            ownPrices[color]?.buy ??
            getMarketSidePrice(market, color, groupSex, 'buy'),
          sell:
            ownPrices[`${color}:${groupSex}`]?.sell ??
            ownPrices[color]?.sell ??
            getMarketSidePrice(market, color, groupSex, 'sell'),
          strict: true,
        })
      }
      const current = grouped.get(key)
      current.count += 1
      if (!isEntityHungry(entity)) {
        current.readyCount += 1
      }
    })
    return Array.from(grouped.values())
  }, [hasEntityMetadata, cats, inventory, ownPrices, kittenEntities, market])

  const availableSellByVariant = useMemo(() => {
    const byVariant = {}
    if (hasEntityMetadata) {
      mineTiles.forEach((tile) => {
        const variantKey = `${tile.color}:${tile.sex || 'M'}`
        byVariant[variantKey] = (byVariant[variantKey] ?? 0) + tile.readyCount
      })
    }
    return byVariant
  }, [hasEntityMetadata, mineTiles])

  const availableSellByColor = useMemo(() => {
    if (hasEntityMetadata) {
      return mineTiles.reduce((acc, tile) => {
        acc[tile.color] = (acc[tile.color] ?? 0) + tile.readyCount
        return acc
      }, {})
    }
    return DEFAULT_TYPES.reduce((acc, color) => {
      acc[color] = Number(inventory?.[color] ?? 0)
      return acc
    }, {})
  }, [hasEntityMetadata, mineTiles, inventory])

  const addTradeItem = (payload, action) => {
    const { catId, buy, sell, sex } = payload
    const safeSex = normalizeSex(sex)
    const key = safeSex ? `${action}:${catId}:${safeSex}` : `${action}:${catId}`
    setTradeItems((prev) => {
      const existing = prev.find((item) => item.key === key)
      if (existing) {
        return prev.map((item) =>
          item.key === key ? { ...item, qty: item.qty + 1 } : item
        )
      }
      const rawPrice = action === 'buy' ? buy : sell
      const price = Number.isFinite(Number(rawPrice)) ? Number(rawPrice) : 0
      return [...prev, { key, catId, sex: safeSex, action, qty: 1, price }]
    })
    setTradeValidationError('')
  }

  const updateTradeItem = (key, updates) => {
    setTradeItems((prev) =>
      prev.map((item) => (item.key === key ? { ...item, ...updates } : item))
    )
  }

  const removeTradeItem = (key) => {
    setTradeItems((prev) => prev.filter((item) => item.key !== key))
  }

  const adjustQty = (key, delta) => {
    setTradeItems((prev) =>
      prev
        .map((item) => {
          if (item.key !== key) return item
          const nextQty = item.qty + delta
          return { ...item, qty: Math.max(1, nextQty) }
        })
        .filter((item) => item.qty > 0)
    )
  }

  const totalQty = tradeItems.reduce((sum, item) => sum + item.qty, 0)
  const totalSum = tradeItems.reduce((sum, item) => sum + item.qty * item.price, 0)

  const isCattery = playerRole === 'cattery'
  const isPetshop = playerRole === 'petshop'
  const canTradeWithCounterparty =
    (isCattery && overlayType === 'shop') ||
    (isPetshop && (overlayType === 'cattery' || overlayType === 'shop'))

  const canBuy = canTradeWithCounterparty
  const canSell = canTradeWithCounterparty

  const validateSellPayload = (payload) => {
    const payloadColor = normalizeColor(payload?.color ?? payload?.catId)
    const payloadSex = normalizeSex(payload?.sex)
    const kittenStatus = resolveKittenStatus(payload)

    if (!DEFAULT_TYPES.includes(payloadColor)) {
      return 'Ошибка сущности: цвет котёнка не распознан'
    }
    if (payload?.color && payloadColor !== normalizeColor(payload.catId)) {
      return 'Ошибка сущности: цвет котёнка не совпадает с типом сделки'
    }
    if (hasEntityMetadata && !payloadSex) {
      return 'Ошибка сущности: отсутствует пол котёнка'
    }
    if (payload?.sex && !payloadSex) {
      return 'Ошибка сущности: некорректный пол котёнка'
    }
    if (kittenStatus === false) {
      return 'В торговле можно использовать только котят'
    }
    if (hasEntityMetadata && kittenStatus == null) {
      return 'Ошибка сущности: не удалось определить возраст котёнка'
    }
    if (payload?.hungry === true || payload?.hungry === 'true') {
      return 'Голодного котёнка нельзя продать: сначала покормите его'
    }
    if (payload?.readyToSell === false) {
      return 'Голодного котёнка нельзя продать: сначала покормите его'
    }
    return null
  }

  const validateBuyPayload = (payload) => {
    const payloadColor = normalizeColor(payload?.color ?? payload?.catId)
    const payloadSex = normalizeSex(payload?.sex)
    if (!DEFAULT_TYPES.includes(payloadColor)) {
      return 'Ошибка сущности: цвет котёнка не распознан'
    }
    if (!payloadSex) {
      return payload?.sex
        ? 'Ошибка сущности: некорректный пол котёнка'
        : 'Ошибка сущности: отсутствует пол котёнка'
    }
    return null
  }

  const handleDropZone = (event) => {
    event.preventDefault()
    if (!canTradeWithCounterparty) return
    try {
      const json = event.dataTransfer.getData('application/json')
      if (!json) return
      const payload = JSON.parse(json)
      if (payload?.source === 'market' && canBuy) {
        const validationError = validateBuyPayload(payload)
        if (validationError) {
          setTradeValidationError(validationError)
          return
        }
        addTradeItem(payload, 'buy')
        return
      }
      if (payload?.source === 'mine') {
        if (!canSell) return
        const validationError = validateSellPayload(payload)
        if (validationError) {
          setTradeValidationError(validationError)
          return
        }
        addTradeItem(payload, 'sell')
      }
    } catch {
      return
    }
  }

  const handleDropMarket = (event) => {
    event.preventDefault()
    if (!canSell || overlayType !== 'shop') return
    try {
      const json = event.dataTransfer.getData('application/json')
      if (!json) return
      const payload = JSON.parse(json)
      if (payload?.source !== 'mine') return
      const validationError = validateSellPayload(payload)
      if (validationError) {
        setTradeValidationError(validationError)
        return
      }
      addTradeItem(payload, 'sell')
    } catch {
      return
    }
  }

  const executeTrade = async () => {
    if (!tradeItems.length) return
    const sellDemandByColor = {}
    const sellDemandByVariant = {}
    tradeItems.forEach((item) => {
      if (item.action !== 'sell') return
      sellDemandByColor[item.catId] = (sellDemandByColor[item.catId] ?? 0) + item.qty
      if (item.sex) {
        const variantKey = `${item.catId}:${item.sex}`
        sellDemandByVariant[variantKey] = (sellDemandByVariant[variantKey] ?? 0) + item.qty
      }
    })

    if (hasEntityMetadata) {
      const invalidVariant = Object.entries(sellDemandByVariant).find(
        ([variant, requested]) => requested > (availableSellByVariant[variant] ?? 0)
      )
      if (invalidVariant) {
        const [color, sex] = invalidVariant[0].split(':')
        setTradeValidationError(`Недостаточно котят ${sex} цвета ${color} для продажи`)
        return
      }
    } else {
      const invalidSell = Object.entries(sellDemandByColor).find(
        ([color, requested]) => requested > (availableSellByColor[color] ?? 0)
      )
      if (invalidSell) {
        setTradeValidationError(`Недостаточно котят цвета ${invalidSell[0]} для продажи`)
        return
      }
    }

    for (const item of tradeItems) {
      await onTrade(
        item.action,
        item.catId,
        item.qty,
        item.sex || null,
        {
          counterpartyType: overlayType === 'shop' ? 'shop' : 'cattery',
          counterpartyId: buildingId ?? null,
        }
      )
    }
    setTradeItems([])
    setTradeValidationError('')
  }

  const handleTake = () => onCreditTake(creditType, toQty(creditAmount))
  const handleRepay = () => onCreditRepay(toQty(creditAmount))

  if (!open) return null

  return (
    <div className="overlay" onClick={onClose}>
      <div className="overlay__panel overlay__panel--trade" onClick={(e) => e.stopPropagation()}>
        <div className="trade-header">
          <button className="trade-back" onClick={onClose}>
            ← На карту
          </button>

      <div className="trade-title">
        <div className="trade-title__name">{titleName}</div>
        <div className="trade-title__type">{titleType}</div>
        <div className="trade-title__season">Сезон {seasonNumber}</div>
      </div>

          <div className="trade-balance">
            <span className="coin" />
            <span className="trade-balance__value">{coinsNow}</span>
          </div>

          <button className="trade-icon" onClick={() => setCreditOpen(true)}>
            💳
          </button>
        </div>

        {error ? <div className="trade-error">{error}</div> : null}
        {tradeValidationError ? <div className="trade-error">{tradeValidationError}</div> : null}

        <section
          className={`lot-area lot-area--shop ${!canTradeWithCounterparty ? 'is-disabled' : ''}`}
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDropMarket}
        >
          <div className="lot-area__info">
            <span className="lot-area__avatar">{(stripName || '?').slice(0, 1).toUpperCase()}</span>
            <strong>{stripName}</strong>
            <p>{stripType}</p>
          </div>

          <div className="lot-area__content">
            <div className="lot-area__cats">
            {marketTiles.map((cat) => (
              <CatTile
                key={cat.id}
                cat={cat}
                draggable={canBuy}
                disabled={!canBuy}
                imageSrc={getCatSprite(cat.type, cat.sex)}
                sexLabel={cat.sex === 'M' ? 'мальчик' : 'девочка'}
                onDragStart={(e) => {
                  if (!canBuy) return
                  const payload = {
                    catId: cat.type,
                    color: cat.type,
                    sex: cat.sex,
                    isKitten: true,
                    buy: cat.buy,
                    sell: cat.sell,
                    source: 'market',
                  }
                  e.dataTransfer.setData(
                    'application/json',
                    JSON.stringify(payload)
                  )
                  e.dataTransfer.effectAllowed = 'copy'
                  const img = new Image()
                  img.src = getCatSprite(cat.type, cat.sex)
                  e.dataTransfer.setDragImage(img, 24, 24)
                }}
              />
            ))}
            </div>
          </div>
        </section>

        <section
          className="lot-area lot-area--lot"
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDropZone}
        >
          <div className="lot-area__info lot-area__info--transaction">
            <div className="lot-area__info__arrows">⇅</div>
            <p className="lot-area__info__transaction-text">ЗОНА СДЕЛКИ</p>
          </div>

          {tradeItems.length === 0 ? (
            <div className="lot-area--lot__text">
              {canTradeWithCounterparty
                ? 'ПЕРЕТАЩИ КОТИКОВ ДЛЯ НАЧАЛА ТОРГОВЛИ'
                : 'ТОРГОВЛЯ С ЭТИМ ПАРТНЕРОМ НЕДОСТУПНА'}
            </div>
          ) : null}

          <div className="trade-items">
            {tradeItems.map((item) => (
                <div className="trade-item" key={item.key}>
                <div className="trade-item__img">
                  <img src={getCatSprite(item.catId, item.sex || 'M')} alt={item.catId} />
                </div>
                <div className="trade-item__meta">
                  <span className="trade-item__tag">
                    {item.action === 'buy' ? 'BUY' : 'SELL'}
                    {item.sex ? ` • ${item.sex}` : ''}
                  </span>
                  <div className="trade-item__price">
                    <button
                      className="trade-item__price-btn"
                      onClick={() =>
                        updateTradeItem(item.key, {
                          price: Math.max(0, item.price - 1),
                        })
                      }
                    >
                      −
                    </button>
                    <input
                      className="trade-item__price-input"
                      type="number"
                      value={item.price}
                      onChange={(e) =>
                        updateTradeItem(item.key, {
                          price: toPrice(e.target.value),
                        })
                      }
                    />
                    <button
                      className="trade-item__price-btn"
                      onClick={() =>
                        updateTradeItem(item.key, {
                          price: item.price + 1,
                        })
                      }
                    >
                      +
                    </button>
                  </div>
                </div>
                <div className="trade-item__qty">
                  <button onClick={() => adjustQty(item.key, -1)} disabled={item.qty <= 1}>
                    −
                  </button>
                  <span>{item.qty}</span>
                  <button onClick={() => adjustQty(item.key, 1)}>+</button>
                </div>
                <button className="trade-item__remove" onClick={() => removeTradeItem(item.key)}>
                  ✕
                </button>
              </div>
            ))}
          </div>

          <div className="lot-area__lot-panel">
            <div className="trade-summary">
              <div className="trade-summary__row">
                <span className="trade-summary__muted">×</span>
                <span className="trade-summary__count">{totalQty}</span>
                <span className="trade-summary__muted">КОТИКОВ</span>
              </div>

              <div className="trade-summary__row trade-summary__row--coins">
                <span className="coin" />
                <span className="trade-summary__sum">{totalSum}</span>
              </div>

              {tradeItems.length ? (
                <div className="trade-summary__list">
                  {tradeItems.map((item) => (
                    <div key={item.key} className="trade-summary__item">
                      {item.catId}
                      {item.sex ? ` (${item.sex})` : ''}
                      {' ×'}
                      {item.qty}
                    </div>
                  ))}
                </div>
              ) : null}
            </div>

            <button
              className="trade-summary__send"
              onClick={executeTrade}
              disabled={busy || tradeItems.length === 0}
              aria-label="send trade"
            >
              ⇆
            </button>
          </div>
        </section>

        <section className={`lot-area lot-area--nursery ${!canTradeWithCounterparty ? 'is-disabled' : ''}`}>
          <div className="lot-area__info">
            <span className="lot-area__avatar">Я</span>
            <p>МОИ КОТИКИ</p>
          </div>

          <div className="lot-area__content">
            <div className="lot-area__cats">
            {mineTiles.map((tile) => {
              const prices = { buy: tile.buy, sell: tile.sell }
              const disabled = !canSell || tile.readyCount <= 0
              const displayType = tile.color
              const displaySex = tile.sex ? (tile.sex === 'M' ? 'мальчик' : 'девочка') : null
              return (
                <CatTile
                  key={`mine-${tile.key}`}
                  cat={{
                    id: tile.key,
                    type: displayType,
                    sex: tile.sex || 'M',
                    buy: prices.buy,
                    sell: prices.sell,
                  }}
                  count={tile.count}
                  draggable={canSell && tile.readyCount > 0}
                  imageSrc={getCatSprite(displayType, tile.sex || 'M')}
                  sexLabel={
                    tile.count > tile.readyCount
                      ? `${displaySex || ''} (сытых: ${tile.readyCount})`.trim()
                      : displaySex
                  }
                  onDragStart={(e) => {
                    if (disabled) return
                    const payload = {
                      catId: displayType,
                      color: displayType,
                      sex: tile.sex,
                      isKitten: true,
                      hungry: false,
                      readyToSell: true,
                      buy: prices.buy,
                      sell: prices.sell,
                      strict: tile.strict,
                      source: 'mine',
                    }
                    e.dataTransfer.setData(
                      'application/json',
                      JSON.stringify(payload)
                    )
                    e.dataTransfer.effectAllowed = 'copy'
                    const img = new Image()
                    img.src = getCatSprite(displayType, tile.sex || 'M')
                    e.dataTransfer.setDragImage(img, 24, 24)
                  }}
                  onClick={() =>
                    setPriceEditor({
                      type: displaySex ? `${displayType} • ${displaySex}` : displayType,
                      key: tile.sex ? `${displayType}:${tile.sex}` : displayType,
                      color: displayType,
                      sex: tile.sex || null,
                      buy: prices.buy,
                      sell: prices.sell,
                    })
                  }
                  disabled={disabled}
                />
              )
            })}
            </div>
          </div>
        </section>
      </div>

      <CreditOverlay
        open={creditOpen}
        onClose={() => setCreditOpen(false)}
        amount={creditAmount}
        creditType={creditType}
        onAmountChange={(value) => setCreditAmount(toQty(value))}
        onCreditTypeChange={setCreditType}
        onTake={handleTake}
        onRepay={handleRepay}
        busy={busy}
        debtTotal={debtTotal ?? 0}
        debtRate={debtRate ?? 0}
        seasonNumber={seasonNumber}
      />

      <PriceModal
        open={Boolean(priceEditor)}
        onClose={() => setPriceEditor(null)}
        type={priceEditor?.type}
        buy={priceEditor?.buy ?? 0}
        sell={priceEditor?.sell ?? 0}
        imageSrc={
          priceEditor?.color
            ? getCatSprite(priceEditor.color, priceEditor.sex || 'M')
            : CAT_SPRITES.M.gray
        }
        onSave={(buyValue, sellValue) => {
          setCustomPrices((prev) => ({
            ...prev,
            [priceEditor.key]: { buy: buyValue, sell: sellValue },
          }))
          setPriceEditor(null)
        }}
        key={priceEditor ? `price-${priceEditor.type}-${priceEditor.buy}-${priceEditor.sell}` : 'price-closed'}
      />
    </div>
  )
}

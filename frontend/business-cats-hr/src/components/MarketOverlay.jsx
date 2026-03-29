import { useEffect, useMemo, useRef, useState } from 'react'
import CreditOverlay from './CreditOverlay.jsx'
import RequestsSidebar from './RequestsSidebar.jsx'
import './Overlay.css'

const DEFAULT_TYPES = ['black', 'white', 'ginger', 'gray']
const SEX_ORDER = ['M', 'F']
const VALID_SEX = new Set(['M', 'F'])
const COLOR_ALIAS = {
  orange: 'ginger',
}
const CAT_SPRITES = {
  M: {
    black: {
      default: '/assets/cats/black-small-male.png',
      hungry: '/assets/cats/black-hungry-small-male.png',
    },
    white: {
      default: '/assets/cats/white-small-male.png',
      hungry: '/assets/cats/male-small-cat-white-hungry.png',
    },
    gray: {
      default: '/assets/cats/male-gray-small.png',
      hungry: '/assets/cats/male-small-gray-hungry.png',
    },
    ginger: {
      default: '/assets/cats/small-orange-male.png',
      hungry: '/assets/cats/small-cat-orange-hungry.png',
    },
  },
  F: {
    black: {
      default: '/assets/cats/small-black-female.png',
      hungry: '/assets/cats/small-black-hungry-female.png',
    },
    white: {
      default: '/assets/cats/small-white-female.png',
      hungry: '/assets/cats/female-small-cat-white-hungry.png',
    },
    gray: {
      default: '/assets/cats/female-gray-small.png',
      hungry: '/assets/cats/small-gray-hungry-female.png',
    },
    ginger: {
      default: '/assets/cats/orange-small-female.png',
      hungry: '/assets/cats/cat-orange-small-female-hungry-female.png',
    },
  },
}
const SEX_CLASS = {
  M: 'male',
  F: 'female',
}
const COLOR_LABEL_RU = {
  black: 'черный',
  white: 'белый',
  ginger: 'рыжий',
  gray: 'серый',
}
const SEX_LABEL_RU = {
  M: 'мальчик',
  F: 'девочка',
}
const MAX_TRADE_PRICE = 999

const resolveColorLabel = (value) => {
  const normalized = normalizeColor(value)
  return COLOR_LABEL_RU[normalized] || 'котик'
}

const resolveSexLabel = (value) => {
  const normalized = normalizeSex(value) || 'M'
  return SEX_LABEL_RU[normalized] || 'котик'
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

const normalizeTradePriceInput = (value) =>
  String(value ?? '')
    .replace(/[^\d]/g, '')
    .slice(0, String(MAX_TRADE_PRICE).length)

const parseTradePrice = (value) => {
  const normalized = normalizeTradePriceInput(value)
  if (!normalized) return null
  const parsed = Number(normalized)
  if (!Number.isInteger(parsed) || parsed <= 0 || parsed > MAX_TRADE_PRICE) return null
  return parsed
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

const getCatSprite = (color, sex, hungry = false) => {
  const normalizedColor = normalizeColor(color)
  const normalizedSex = normalizeSex(sex) || 'M'
  const sexSprites = CAT_SPRITES[normalizedSex] || CAT_SPRITES.M
  const colorSprites = sexSprites[normalizedColor] || sexSprites.gray
  if (!colorSprites) return '/assets/cats/male-gray-small.png'
  if (hungry) return colorSprites.hungry || colorSprites.default
  return colorSprites.default || colorSprites.hungry
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
  title,
  stageLabel = 'котенок',
  statusLabel = null,
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
      {sexLabel ? <span className={`cat-card__badge cat-card__badge--${SEX_CLASS[normalizedSex]}`}>{sexLabel}</span> : null}
      <span className="cat-card__image">
        <img src={imageSrc} alt="котик" />
      </span>
      <div className="cat-card__title">{title || `${cat.type} ${sexLabel || ''}`}</div>
      <div className="cat-card__meta-row">
        <span className="cat-card__stage">{stageLabel}</span>
        {statusLabel ? <span className="cat-card__status">{statusLabel}</span> : null}
      </div>
      <div className="cat-card__price-wrapper">
        <div className="cat-card__price">
          <div className="cat-card__price-name">Покупка</div>
          <div className="price-value">
            <span className="coin" />
            <span className="price-value__cost notranslate">{cat.sell}</span>
          </div>
        </div>
        <div className="cat-card__price">
          <div className="cat-card__price-name">Продажа</div>
          <div className="price-value">
            <span className="coin" />
            <span className="price-value__cost notranslate">{cat.buy}</span>
          </div>
        </div>
      </div>
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
          <img src={imageSrc || CAT_SPRITES.M.gray.default} alt="котик" />
        </div>
        <label>
          Цена покупки (магазин у игрока)
          <input
            type="number"
            value={sellValue}
            onChange={(e) => setSellValue(toPrice(e.target.value))}
          />
        </label>
        <label>
          Цена продажи (игрок у питомника)
          <input
            type="number"
            value={buyValue}
            onChange={(e) => setBuyValue(toPrice(e.target.value))}
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
  onCreateTradeRequest,
  onCreditTake,
  onCreditRepay,
  onPrevCounterparty,
  onNextCounterparty,
  tradeRequests = [],
  onOpenRequest,
  spectateMode = false,
  spectateData = null,
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
          qty: null,
        }))
      ),
    [cats, market]
  )

  const marketTilesResolved = useMemo(() => {
    if (!spectateMode || !Array.isArray(spectateData?.showcase)) {
      return marketTiles
    }
    const qtyByKey = {}
    const priceByKey = {}
    spectateData.showcase.forEach((item) => {
      const color = normalizeColor(item?.catTypeId)
      const sex = normalizeSex(item?.catSex)
      if (!color || !sex) return
      const key = `${color}:${sex}`
      qtyByKey[key] = (qtyByKey[key] ?? 0) + Math.max(0, Number(item?.quantity || 0))
      const price = Number(item?.unitPrice || 0)
      if (price > 0) priceByKey[key] = price
    })
    return marketTiles.map((tile) => {
      const key = `${normalizeColor(tile.type)}:${normalizeSex(tile.sex) || 'M'}`
      return {
        ...tile,
        qty: qtyByKey[key] ?? 0,
        buy: priceByKey[key] ?? tile.buy,
        sell: priceByKey[key] ?? tile.sell,
      }
    })
  }, [marketTiles, spectateMode, spectateData?.showcase])

  const [tradeItems, setTradeItems] = useState([])
  const [creditOpen, setCreditOpen] = useState(false)
  const [creditAmount, setCreditAmount] = useState(5)
  const [creditType, setCreditType] = useState('consumer')
  const [priceEditor, setPriceEditor] = useState(null)
  const [customPrices, setCustomPrices] = useState({})
  const [tradeValidationError, setTradeValidationError] = useState('')
  const tradeItemsRef = useRef([])

  useEffect(() => {
    tradeItemsRef.current = tradeItems
  }, [tradeItems])

  useEffect(() => {
    setTradeItems([])
    setTradeValidationError('')
  }, [open, buildingId, overlayType, spectateMode])

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
    const templateTiles = DEFAULT_TYPES.flatMap((color) =>
      SEX_ORDER.map((sex) => ({
        key: `slot:${color}:${sex}`,
        entityId: null,
        entityIds: [],
        age: null,
        color,
        sex,
        count: 0,
        readyCount: 0,
        buy:
          ownPrices[`${color}:${sex}`]?.buy ??
          ownPrices[color]?.buy ??
          getMarketSidePrice(market, color, sex, 'buy'),
        sell:
          ownPrices[`${color}:${sex}`]?.sell ??
          ownPrices[color]?.sell ??
          getMarketSidePrice(market, color, sex, 'sell'),
        strict: true,
      }))
    )

    if (!hasEntityMetadata) {
      return templateTiles.map((tile) => {
        const total = Number(inventory?.[tile.color] ?? 0)
        const count = tile.sex === 'M' ? total : 0
        return {
          ...tile,
          key: `legacy:${tile.color}:${tile.sex}`,
          count,
          readyCount: count,
          strict: false,
        }
      })
    }

    const grouped = new Map(templateTiles.map((tile) => [tile.key, { ...tile }]))
    kittenEntities.forEach((entity) => {
      const color = normalizeColor(entity?.color ?? entity?.catType)
      const sex = normalizeSex(entity?.sex) || 'M'
      const key = `slot:${color}:${sex}`
      if (!grouped.has(key)) {
        return
      }
      const current = grouped.get(key)
      current.count += 1
      if (!isEntityHungry(entity)) {
        current.readyCount += 1
        if (entity?.id) current.entityIds.push(String(entity.id))
      }
    })

    return Array.from(grouped.values()).sort((a, b) => {
      const colorDiff = DEFAULT_TYPES.indexOf(a.color) - DEFAULT_TYPES.indexOf(b.color)
      if (colorDiff !== 0) return colorDiff
      const sexDiff = SEX_ORDER.indexOf(a.sex || 'M') - SEX_ORDER.indexOf(b.sex || 'M')
      if (sexDiff !== 0) return sexDiff
      return Number(a.age || 0) - Number(b.age || 0)
    })
  }, [hasEntityMetadata, inventory, ownPrices, kittenEntities, market])

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

  const pendingSellByGroup = useMemo(
    () =>
      tradeItems.reduce((acc, item) => {
        if (item.action !== 'sell' || !item.groupKey) return acc
        acc[item.groupKey] = (acc[item.groupKey] ?? 0) + 1
        return acc
      }, {}),
    [tradeItems]
  )

  const addTradeItem = (payload, action) => {
    const { catId, buy, sell, sex, entityId, entityIds, groupKey } = payload
    const safeSex = normalizeSex(sex)
    let pickedEntityId = entityId || null
    const group = groupKey || null
    const mixedDirection =
      tradeItemsRef.current.length > 0 &&
      tradeItemsRef.current.some((item) => item.action !== action)
    if (mixedDirection) {
      setTradeValidationError('В одной заявке можно либо покупать, либо продавать')
      return
    }
    if (action === 'sell' && hasEntityMetadata) {
      const usedEntityIds = new Set(
        tradeItemsRef.current
          .filter((item) => item.action === 'sell' && item.entityId)
          .map((item) => String(item.entityId))
      )
      const candidates = Array.isArray(entityIds) ? entityIds.map((id) => String(id)) : []
      if (!pickedEntityId) {
        pickedEntityId = candidates.find((id) => !usedEntityIds.has(id)) || null
      }
      if (!pickedEntityId) {
        setTradeValidationError('Нельзя добавить одного и того же котенка дважды')
        return
      }
    }
    const key = `${action}:${catId}:${safeSex || 'X'}:${Date.now()}-${Math.random()
      .toString(16)
      .slice(2, 7)}`
    setTradeItems((prev) => {
      const rawPrice = action === 'buy' ? buy : sell
      const unitPrice = Number.isFinite(Number(rawPrice)) ? Number(rawPrice) : 0
      return [
        ...prev,
        {
          key,
          itemId: key,
          catId,
          catColor: catId,
          catType: catId,
          sex: safeSex,
          action,
          unitPriceInput: unitPrice > 0 ? String(unitPrice) : '',
          entityId: pickedEntityId,
          groupKey: group,
        },
      ]
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

  const invalidTradePriceKeys = useMemo(
    () =>
      tradeItems
        .filter((item) => parseTradePrice(item.unitPriceInput) == null)
        .map((item) => item.key),
    [tradeItems]
  )

  const invalidTradePriceKeySet = useMemo(
    () => new Set(invalidTradePriceKeys),
    [invalidTradePriceKeys]
  )

  const hasInvalidTradePrices = invalidTradePriceKeys.length > 0
  const totalQty = tradeItems.length
  const totalSum = tradeItems.reduce(
    (sum, item) => sum + Number(parseTradePrice(item.unitPriceInput) || 0),
    0
  )

  const isCattery = playerRole === 'cattery'
  const isPetshop = playerRole === 'petshop'
  const canTradeWithCounterparty =
    (isCattery && overlayType === 'shop') ||
    (isPetshop && (overlayType === 'cattery' || overlayType === 'shop'))

  const canBuy = canTradeWithCounterparty && !spectateMode
  const canSell = canTradeWithCounterparty && !spectateMode

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
    if (
      hasEntityMetadata &&
      !payload?.entityId &&
      !(Array.isArray(payload?.entityIds) && payload.entityIds.length)
    ) {
      return 'Ошибка сущности: отсутствует идентификатор котёнка'
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

  const buildMarketTradePayload = (cat) => ({
    catId: cat.type,
    color: cat.type,
    sex: cat.sex,
    entityId: `buy-${Date.now()}-${Math.random().toString(16).slice(2, 7)}`,
    isKitten: true,
    buy: cat.buy,
    sell: cat.sell,
    source: 'market',
  })

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
    if (spectateMode) {
      setTradeValidationError(
        'Торговля между питомниками недоступна. Вы можете только наблюдать.'
      )
      return
    }
    if (!tradeItems.length) return
    if (hasInvalidTradePrices) {
      setTradeValidationError('Введите корректную цену')
      return
    }
    const directionSet = new Set(tradeItems.map((item) => item.action))
    if (directionSet.size > 1) {
      setTradeValidationError('В одной заявке можно либо покупать, либо продавать')
      return
    }
    const sellDemandByColor = {}
    const sellDemandByVariant = {}
    tradeItems.forEach((item) => {
      if (item.action !== 'sell') return
      sellDemandByColor[item.catId] = (sellDemandByColor[item.catId] ?? 0) + 1
      if (item.sex) {
        const variantKey = `${item.catId}:${item.sex}`
        sellDemandByVariant[variantKey] = (sellDemandByVariant[variantKey] ?? 0) + 1
      }
    })

    if (hasEntityMetadata) {
      const sellEntityIds = tradeItems
        .filter((item) => item.action === 'sell' && item.entityId)
        .map((item) => item.entityId)
      const uniqueEntityIds = new Set(sellEntityIds)
      if (sellEntityIds.length !== uniqueEntityIds.size) {
        setTradeValidationError('Один и тот же котёнок добавлен в сделку несколько раз')
        return
      }
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

    try {
      const requestItems = tradeItems.map((item) => ({
        itemId: item.itemId,
        catId: item.entityId || item.catId,
        catType: item.catType || item.catId,
        catColor: item.catColor || item.catId,
        catTypeId: item.catColor || item.catId,
        catSex: item.sex || null,
        proposedPrice: Number(parseTradePrice(item.unitPriceInput) || 1),
        quantity: 1,
        unitPrice: Number(parseTradePrice(item.unitPriceInput) || 1),
        currency: 'COIN',
        side: item.action === 'buy' ? 'BUY' : 'SELL',
      }))

      if (typeof onCreateTradeRequest !== 'function') {
        throw new Error('trade_requests_unavailable')
      }

      await onCreateTradeRequest({
        counterpartyType: overlayType === 'shop' ? 'shop' : 'cattery',
        counterpartyId: Number.isFinite(Number(buildingId)) ? Number(buildingId) : 1,
        items: requestItems,
      })

      setTradeItems([])
      setTradeValidationError('')
    } catch (err) {
      const msg = String(err?.message || '')
      if (msg.toLowerCase().includes('not found') || msg.includes('trade_requests_unavailable')) {
        setTradeValidationError('Сервис заявок недоступен. Перезапусти backend с новыми роутами /api/game/trade-requests/*')
      } else {
        setTradeValidationError(msg || 'Не удалось отправить заявку')
      }
    }
  }

  const handleTake = () => onCreditTake(creditType, toQty(creditAmount))
  const handleRepay = () => onCreditRepay(toQty(creditAmount))
  const tradeErrors = [error, tradeValidationError].filter(Boolean)

  if (!open) return null

  return (
    <div className="overlay overlay--trade-screen" onClick={onClose}>
      <div className="overlay__panel overlay__panel--trade" onClick={(e) => e.stopPropagation()}>
        <div className="trade-screen">
          <div className="trade-screen__main">
            <div className="trade-header">
              <button className="trade-back" onClick={onClose}>
                ← На карту
              </button>

              <div className="trade-title">
                <div className="trade-title__name">{titleName}</div>
                <div className="trade-title__type">{titleType}</div>
                <div className="trade-title__season">Сезон {seasonNumber}</div>
              </div>

              <div className="trade-header__status">
                {spectateMode ? 'Наблюдение' : 'Активная сделка'}
              </div>

              {overlayType === 'shop' && (onPrevCounterparty || onNextCounterparty) ? (
                <div className="trade-shop-switch">
                  <button
                    type="button"
                    className="trade-shop-switch__btn"
                    onClick={onPrevCounterparty}
                    aria-label="prev shop"
                  >
                    ◀
                  </button>
                  <div className="trade-shop-switch__name">{stripName}</div>
                  <button
                    type="button"
                    className="trade-shop-switch__btn"
                    onClick={onNextCounterparty}
                    aria-label="next shop"
                  >
                    ▶
                  </button>
                </div>
              ) : null}

              <div className="trade-balance">
                <span className="coin" />
                <span className="trade-balance__value">{coinsNow}</span>
              </div>

              <button className="trade-icon" onClick={() => setCreditOpen(true)}>
                💳
              </button>
            </div>

            {tradeErrors.length ? (
              <div className="trade-errors">
                {tradeErrors.map((message, idx) => (
                  <div className="trade-error" key={`trade-error-${idx}`}>
                    {message}
                  </div>
                ))}
              </div>
            ) : null}

            <section
              className={`lot-area lot-area--shop ${!canTradeWithCounterparty && !spectateMode ? 'is-disabled' : ''}`}
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
                  {marketTilesResolved.map((cat) => (
                    <CatTile
                      key={cat.id}
                      cat={cat}
                      count={
                        spectateMode && Number.isFinite(Number(cat.qty))
                          ? Number(cat.qty)
                          : undefined
                      }
                      draggable={canBuy}
                      disabled={!canBuy && !spectateMode}
                      imageSrc={getCatSprite(cat.type, cat.sex)}
                      sexLabel={cat.sex === 'M' ? 'мальчик' : 'девочка'}
                      title={`${resolveColorLabel(cat.type)} ${resolveSexLabel(cat.sex)}`}
                      stageLabel="котенок"
                      statusLabel={spectateMode && Number(cat.qty || 0) <= 0 ? 'нет в наличии' : null}
                      onDragStart={(e) => {
                        if (!canBuy) return
                        const payload = buildMarketTradePayload(cat)
                        e.dataTransfer.setData(
                          'application/json',
                          JSON.stringify(payload)
                        )
                        e.dataTransfer.effectAllowed = 'copy'
                        const img = new Image()
                        img.src = getCatSprite(cat.type, cat.sex)
                        e.dataTransfer.setDragImage(img, 24, 24)
                      }}
                      onClick={() => {
                        if (!canBuy) return
                        const payload = buildMarketTradePayload(cat)
                        const validationError = validateBuyPayload(payload)
                        if (validationError) {
                          setTradeValidationError(validationError)
                          return
                        }
                        addTradeItem(payload, 'buy')
                      }}
                    />
                  ))}
                </div>
              </div>

              {spectateMode ? (
                <div className="trade-spectate-meta">
                  <div>Сделок в сезоне: {Number(spectateData?.dealsThisSeason ?? 0)}</div>
                  <div>
                    Последняя сделка:{' '}
                    {spectateData?.lastDealSecondsAgo == null
                      ? 'нет'
                      : `${Number(spectateData.lastDealSecondsAgo)} сек назад`}
                  </div>
                  <div>
                    Средняя цена продажи:{' '}
                    {Number(spectateData?.avgSellPriceThisSeason ?? 0).toFixed(2)}
                  </div>
                </div>
              ) : null}
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

              <div className="lot-area__lot-main">
                {tradeItems.length === 0 ? (
                  <div className="lot-area--lot__text">
                    {spectateMode
                      ? 'Торговля между питомниками недоступна. Вы можете только наблюдать.'
                      : canTradeWithCounterparty
                      ? 'ПЕРЕТАЩИ КОТИКОВ ДЛЯ НАЧАЛА ТОРГОВЛИ'
                      : 'ТОРГОВЛЯ С ЭТИМ ПАРТНЕРОМ НЕДОСТУПНА'}
                  </div>
                ) : null}

                <div className="trade-items">
                  {tradeItems.map((item) => {
                    const parsedPrice = parseTradePrice(item.unitPriceInput)
                    const priceError = invalidTradePriceKeySet.has(item.key)
                      ? 'Введите корректную цену'
                      : ''
                    return (
                      <div className="trade-item" key={item.key}>
                        <div className="trade-item__img">
                          <img src={getCatSprite(item.catId, item.sex || 'M')} alt="котик" />
                        </div>
                        <div className="trade-item__meta">
                          <div className="trade-item__meta-top">
                            <span className="trade-item__tag">
                              {item.action === 'buy' ? 'ПОКУПКА' : 'ПРОДАЖА'}
                            </span>
                            {item.sex ? (
                              <span className={`trade-item__sex-badge trade-item__sex-badge--${SEX_CLASS[item.sex]}`}>
                                {resolveSexLabel(item.sex)}
                              </span>
                            ) : null}
                          </div>
                          <div className="trade-item__name">
                            {resolveColorLabel(item.catId)} {item.sex ? resolveSexLabel(item.sex) : ''}
                          </div>
                          <label className="trade-item__field">
                            <span className="trade-item__field-label">Предлагаемая цена</span>
                            <div className={`trade-item__price-editor ${priceError ? 'is-invalid' : ''}`}>
                              <span className="coin" />
                              <input
                                className="trade-item__price-input notranslate"
                                inputMode="numeric"
                                pattern="[0-9]*"
                                value={item.unitPriceInput}
                                onChange={(e) => {
                                  updateTradeItem(item.key, {
                                    unitPriceInput: normalizeTradePriceInput(e.target.value),
                                  })
                                  setTradeValidationError('')
                                }}
                                placeholder="0"
                                aria-label="Предлагаемая цена"
                              />
                            </div>
                          </label>
                          {priceError ? <div className="trade-item__error">{priceError}</div> : null}
                          <div className="trade-item__price-row">
                            <span className="trade-item__price-total-label">Итого</span>
                            <span className="trade-item__price-total">
                              <span className="coin" />
                              <span className="notranslate">{parsedPrice ?? 0}</span>
                            </span>
                          </div>
                        </div>
                        <button className="trade-item__remove" onClick={() => removeTradeItem(item.key)}>
                          ✕
                        </button>
                      </div>
                    )
                  })}
                </div>
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
                          {resolveColorLabel(item.catId)}
                          {item.sex ? ` (${resolveSexLabel(item.sex)})` : ''}
                          {` • ${parseTradePrice(item.unitPriceInput) ?? 0}`}
                        </div>
                      ))}
                    </div>
                  ) : null}
                </div>

                <div className="trade-summary__actions">
                  <button
                    className="trade-summary__clear"
                    type="button"
                    onClick={() => {
                      setTradeItems([])
                      setTradeValidationError('')
                    }}
                    disabled={busy || tradeItems.length === 0}
                  >
                    Очистить
                  </button>
                  <button className="trade-summary__cancel" type="button" onClick={onClose}>
                    Отменить
                  </button>
                  <button
                    className="trade-summary__send"
                    onClick={executeTrade}
                    disabled={busy || tradeItems.length === 0 || spectateMode || hasInvalidTradePrices}
                    aria-label="send trade"
                  >
                    Отправить предложение
                  </button>
                </div>
              </div>
            </section>

            <section className={`lot-area lot-area--nursery ${!canTradeWithCounterparty && !spectateMode ? 'is-disabled' : ''}`}>
              <div className="lot-area__info">
                <span className="lot-area__avatar">Я</span>
                <p>МОИ КОТИКИ</p>
              </div>

              <div className="lot-area__content">
                <div className="lot-area__cats">
                  {mineTiles.map((tile) => {
                    const prices = { buy: tile.buy, sell: tile.sell }
                    const queuedForSell = pendingSellByGroup[tile.key] ?? 0
                    const disabled = !canSell || tile.readyCount <= 0 || queuedForSell >= tile.readyCount
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
                        draggable={!disabled}
                        imageSrc={getCatSprite(displayType, tile.sex || 'M')}
                        sexLabel={
                          tile.count > tile.readyCount
                            ? `${displaySex || ''} (сытых: ${tile.readyCount})`.trim()
                            : displaySex
                        }
                        title={`${resolveColorLabel(displayType)} ${resolveSexLabel(tile.sex) || ''}`.trim()}
                        stageLabel="котенок"
                        statusLabel={tile.count > tile.readyCount ? 'есть голодные' : null}
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
                            entityId: tile.entityId || null,
                            entityIds: tile.entityIds || [],
                            groupKey: tile.key,
                            age: tile.age,
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

          <div className="trade-screen__sidebar">
            <RequestsSidebar
              requests={tradeRequests}
              onOpenRequest={onOpenRequest}
              variant="inline"
              emptyLabel="Заявки и ответы появятся здесь"
            />
          </div>
        </div>
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
            : CAT_SPRITES.M.gray.default
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

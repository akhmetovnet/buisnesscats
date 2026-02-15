import { useEffect, useMemo, useState } from 'react'
import './MyNurseryOverlay.css'

const HOME_COST = 3
const FEED_COST = 1
const INSURANCE_COST = 1
const TREAT_COST = 2
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
const BIG_FEMALE_GRAY = '/assets/big-female-cat-gray.png'
const BIG_FEMALE_GRAY_HUNGRY = '/assets/big-female-cat-gray-hungry.png'
const BIG_MALE_WHITE_HUNGRY = '/assets/big-male-cat-white-hungry.png'
const BIG_FEMALE_WHITE_HUNGRY = '/assets/big-female-cat-hungry.png'
const MALE_SMALL_WHITE_HUNGRY = '/assets/male-small-cat-white-hungry.png'
const FEMALE_SMALL_WHITE_HUNGRY = '/assets/female-small-cat-white-hungry.png'

const DEFAULT_CATS = [
  { id: 'c1', sex: 'M', color: 'black', age: 3, hungry: true, sick: null, fedThisSeason: false, locked: false, isKitten: false },
  { id: 'c2', sex: 'F', color: 'white', age: 3, hungry: true, sick: null, fedThisSeason: false, locked: false, isKitten: false },
  { id: 'c3', sex: 'M', color: 'ginger', age: 4, hungry: true, sick: 'lichen', fedThisSeason: false, locked: false, isKitten: false },
  { id: 'c4', sex: 'F', color: 'gray', age: 4, hungry: true, sick: null, fedThisSeason: false, locked: false, isKitten: false },
]

const SICK_ICON = {
  lichen: '/assets/lichenwhite.png',
  fleas: '/assets/fleaswhite.png',
  poisoning: '/assets/poisoningwhite.png',
  brokenpaw: '/assets/brokenpawwhite.png',
}
const SEX_LABEL = {
  M: 'мальчик',
  F: 'девочка',
}
const COLOR_LABEL = {
  white: 'белый',
  black: 'черный',
  gray: 'серый',
  ginger: 'рыжий',
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

const getCatSprite = (cat) => {
  const color = normalizeColor(cat?.color)
  const sex = normalizeSex(cat?.sex) || 'M'
  const isAdult = Number(cat?.age ?? 0) >= 3 && !cat?.isKitten
  if (color === 'white' && cat?.hungry) {
    if (isAdult) {
      return sex === 'F' ? BIG_FEMALE_WHITE_HUNGRY : BIG_MALE_WHITE_HUNGRY
    }
    return sex === 'F' ? FEMALE_SMALL_WHITE_HUNGRY : MALE_SMALL_WHITE_HUNGRY
  }
  if (isAdult && sex === 'F' && color === 'gray') {
    return cat?.hungry ? BIG_FEMALE_GRAY_HUNGRY : BIG_FEMALE_GRAY
  }
  return CAT_SPRITES[sex]?.[color] || CAT_SPRITES.M[color] || CAT_SPRITES.M.gray
}

const getCatMeta = (cat) => {
  const sex = normalizeSex(cat?.sex) || 'M'
  const color = normalizeColor(cat?.color) || 'gray'
  return { sex, color }
}

export default function MyNurseryOverlay({
  open,
  onClose,
  nursery,
  setNursery,
  seasonNumber,
  coinsNow,
  timerText = '00:00:00',
  onRequestEndSeason,
  onExitPlatform,
}) {
  const [activeTool, setActiveTool] = useState(null)
  const [modal, setModal] = useState(null)
  const [feedQueue, setFeedQueue] = useState([])
  const [inspectTarget, setInspectTarget] = useState(null)

  const cats = nursery?.cats?.length ? nursery.cats : DEFAULT_CATS
  const hasHome = nursery?.hasHome
  const playerName = nursery?.playerName || 'ЛЕОПОЛЬД'
  const coins = Number.isFinite(Number(nursery?.coins))
    ? Number(nursery.coins)
    : Number(coinsNow ?? 0)

  useEffect(() => {
    if (!nursery?.cats?.length) {
      setNursery((prev) => ({ ...prev, cats: DEFAULT_CATS }))
    }
  }, [nursery?.cats?.length, setNursery])

  const assignedIds = useMemo(() => {
    const ids = new Set()
    if (!nursery?.home) return ids
    nursery.home.parents.left.forEach((id) => id && ids.add(id))
    nursery.home.parents.right.forEach((id) => id && ids.add(id))
    return ids
  }, [nursery])
  const catsById = useMemo(
    () => Object.fromEntries(cats.map((cat) => [cat.id, cat])),
    [cats]
  )

  const yardCats = cats.filter((cat) => !assignedIds.has(cat.id))
  const kittenQueueTargets = (nursery?.home?.kittens || []).filter(
    (cat) => cat && cat.hungry && !cat.fedThisSeason
  )

  const handleBuyHome = () => {
    if (hasHome) {
      setModal({ type: 'info', title: 'Домик уже куплен' })
      return
    }
    if (coins < HOME_COST) {
      setModal({ type: 'error', title: 'Недостаточно монет' })
      return
    }
    setModal({ type: 'confirmBuyHome' })
  }

  const confirmBuyHome = () => {
    setNursery((prev) => ({
      ...prev,
      coins: Number(prev.coins ?? 0) - HOME_COST,
      hasHome: true,
    }))
    setModal(null)
  }

  const handleBuyFeed = () => {
    setActiveTool(activeTool === 'feed' ? null : 'feed')
  }

  const handleInsurance = () => {
    setActiveTool(activeTool === 'insurance' ? null : 'insurance')
  }

  const handleInspect = () => {
    setActiveTool(activeTool === 'inspect' ? null : 'inspect')
  }

  const handleFeed = (cat) => {
    if (!cat?.hungry) {
      setModal({ type: 'error', title: 'ЭТОТ КОТИК НЕ ГОЛОДЕН' })
      return
    }
    if (cat.fedThisSeason) {
      setModal({ type: 'error', title: 'ВЫ НЕ МОЖЕТЕ ПОКОРМИТЬ СЫТОГО КОТИКА!' })
      return
    }
    if (coins < FEED_COST) {
      setModal({ type: 'error', title: 'Недостаточно монет' })
      return
    }
    setModal({ type: 'confirmFeed', cat })
  }

  const confirmFeed = (cat) => {
    setNursery((prev) => ({
      ...prev,
      coins: Number(prev.coins ?? 0) - FEED_COST,
      cats: prev.cats.map((c) =>
        c.id === cat.id
          ? { ...c, hungry: false, fedThisSeason: true }
          : c
      ),
      home: {
        ...prev.home,
        kittens: prev.home.kittens.map((k) =>
          k?.id === cat.id ? { ...k, hungry: false, fedThisSeason: true } : k
        ),
      },
    }))
    setModal(null)
    if (feedQueue.length) {
      const next = feedQueue[0]
      setFeedQueue((prev) => prev.slice(1))
      setModal({ type: 'confirmFeed', cat: next })
    }
  }

  const startFeedQueue = () => {
    const hungryCats = cats.filter((c) => c.hungry && !c.fedThisSeason)
    const queue = [...kittenQueueTargets, ...hungryCats]
    if (!queue.length) {
      setModal({ type: 'error', title: 'Нет голодных котиков' })
      return
    }
    setFeedQueue(queue.slice(1))
    setModal({ type: 'confirmFeed', cat: queue[0] })
  }

  const handleInspectCat = (cat) => {
    if (!cat.sick) {
      setModal({ type: 'error', title: 'Котик здоров' })
      return
    }
    setInspectTarget(cat)
  }

  const handleTreat = (cat) => {
    const insured = nursery.insuranceActive
    if (!insured && coins < TREAT_COST) {
      setModal({ type: 'error', title: 'Недостаточно монет' })
      return
    }
    setNursery((prev) => ({
      ...prev,
      coins: insured ? Number(prev.coins ?? 0) : Number(prev.coins ?? 0) - TREAT_COST,
      cats: prev.cats.map((c) => (c.id === cat.id ? { ...c, sick: null } : c)),
    }))
    setInspectTarget(null)
  }

  const handleInsuranceConfirm = () => {
    if (coins < INSURANCE_COST) {
      setModal({ type: 'error', title: 'Недостаточно монет' })
      return
    }
    setNursery((prev) => ({
      ...prev,
      coins: Number(prev.coins ?? 0) - INSURANCE_COST,
      insuranceNext: true,
    }))
    setModal(null)
  }

  const handleDropParent = (side, index, catId) => {
    const cat = cats.find((c) => c.id === catId)
    if (!cat || cat.locked || cat.isKitten || Number(cat.age ?? 0) < 3) return
    setNursery((prev) => {
      const left = [...prev.home.parents.left]
      const right = [...prev.home.parents.right]
      const clearId = (id) => (id === catId ? null : id)
      const nextParents = {
        left: left.map(clearId),
        right: right.map(clearId),
      }
      nextParents[side][index] = catId
      return {
        ...prev,
        home: {
          ...prev.home,
          parents: nextParents,
        },
      }
    })
  }

  const handleRemoveParent = (side, index) => {
    const catId = nursery?.home?.parents?.[side]?.[index]
    if (!catId) return
    const cat = catsById[catId]
    if (cat?.locked) {
      setModal({ type: 'error', title: 'Нельзя перемещать котов во время скрещивания' })
      return
    }
    setNursery((prev) => {
      const nextParents = {
        left: [...prev.home.parents.left],
        right: [...prev.home.parents.right],
      }
      nextParents[side][index] = null
      return {
        ...prev,
        home: {
          ...prev.home,
          parents: nextParents,
        },
      }
    })
  }

  const handleBreed = (side) => {
    if (!hasHome) {
      setModal({ type: 'error', title: 'Нет домика' })
      return
    }
    const pair = nursery.home.parents[side]
    const catsById = Object.fromEntries(cats.map((c) => [c.id, c]))
    const catA = catsById[pair[0]]
    const catB = catsById[pair[1]]
    if (!catA || !catB) {
      setModal({ type: 'error', title: 'Нужна пара' })
      return
    }
    if (catA.sex === catB.sex) {
      setModal({ type: 'error', title: 'Нужна разнополая пара' })
      return
    }
    if (normalizeColor(catA.color) === normalizeColor(catB.color)) {
      setModal({ type: 'error', title: 'Для скрещивания нужны коты разных цветов' })
      return
    }
    if (catA.age < 3 || catB.age < 3) {
      setModal({ type: 'error', title: 'Коты слишком молоды' })
      return
    }
    if (catA.hungry || catB.hungry) {
      setModal({ type: 'error', title: 'Сначала покормите котиков' })
      return
    }
    if (nursery.home.breedPending[side]) {
      setModal({ type: 'error', title: 'Скрещивание уже запущено' })
      return
    }
    if (nursery.home.lastBreedSeason[side] === seasonNumber - 1) {
      setModal({ type: 'error', title: 'Нужен перерыв 1 сезон' })
      return
    }
    setNursery((prev) => ({
      ...prev,
      home: {
        ...prev.home,
        breedPending: { ...prev.home.breedPending, [side]: true },
        lastBreedSeason: { ...prev.home.lastBreedSeason, [side]: seasonNumber },
      },
      cats: prev.cats.map((c) =>
        c.id === catA.id || c.id === catB.id ? { ...c, locked: true } : c
      ),
    }))
    setModal({ type: 'info', title: 'Скрещивание запущено' })
  }

  const getCatModifier = (cat) => {
    const { sex, color } = getCatMeta(cat)
    const sexClass = sex === 'F' ? 'female' : 'male'
    return `cat--${sexClass}-${color}`
  }

  const renderCat = (cat, options = {}) => {
    if (!cat) return null
    const { sex, color } = getCatMeta(cat)
    const sexClass = sex === 'F' ? 'female' : 'male'
    const variant = options.single ? 'single' : 'nursery'
    const readonly = options.readonly ? ' cat--readonly' : ''
    return (
      <div className={`cat cat--${variant} ${getCatModifier(cat)}${readonly}`}>
        {options.count ? (
          <span className="cat__count notranslate">×{options.count}</span>
        ) : null}
        <span className={`cat__image cat__image--${sexClass}-${color}`}>
          <img src={getCatSprite(cat)} alt={options.alt || 'cat'} />
        </span>
        {options.description ? (
          <div className="cat__description cat__description--info">
            <span>{SEX_LABEL[sex] || 'котик'}</span>
            <br />
            <span>{COLOR_LABEL[color] || color}</span>
          </div>
        ) : null}
      </div>
    )
  }

  const handleEndSeason = () => {
    if (typeof onRequestEndSeason === 'function') {
      onRequestEndSeason()
      return
    }
    onClose()
  }

  const handleExitPlatform = () => {
    if (typeof onExitPlatform === 'function') {
      onExitPlatform()
      return
    }
    onClose()
  }

  if (!open) return null

  return (
    <div className="nursery-overlay" onClick={onClose}>
      <div className="nursery" onClick={(e) => e.stopPropagation()}>
        <header className="nursery-header">
          <div className="nursery-header__left">
            <button className="nursery-header__home" type="button" onClick={onClose}>⌂</button>
            <div className="nursery-coins">
              <span className="nursery-coins__avatar">🐾</span>
              <div className="nursery-coins__meta">
                <span className="nursery-coins__name">{playerName}</span>
                <span className="nursery-coins__value"><span className="coin" />{coins}</span>
              </div>
            </div>
          </div>

          <div className="nursery-header__season">
            <p className="nursery-header__season-number">
              <span className="notranslate">{seasonNumber}</span> СЕЗОН
            </p>
            <p className="nursery-header__timer notranslate">{timerText}</p>
          </div>

          <div className="nursery-header__right">
            <button className="nursery-header__icon" type="button" aria-label="settings">⚙</button>
            <button className="nursery-header__icon" type="button" aria-label="profile">🐱</button>
            <button className="nursery-header__end" type="button" onClick={handleEndSeason}>ЗАВЕРШИТЬ СЕЗОН</button>
            <button className="nursery-header__icon nursery-header__icon--exit" type="button" onClick={handleExitPlatform}>⇥</button>
          </div>
        </header>

        <div className="nursery-stage">
          <img className="nursery-stage__tree-left" src="/assets/treelefts.png" alt="" />
          <img className="nursery-stage__tree-right" src="/assets/treerights.png" alt="" />

          <div className="nursery__sidebar">
            <button className="nursery__btn nursery__btn--home" type="button" onClick={handleBuyHome} title="Купить домик">
              <span className="nursery__btn-icon">🏠</span>
            </button>
            <button
              className={`nursery__btn ${activeTool === 'feed' ? 'is-active' : ''}`}
              onClick={handleBuyFeed}
              draggable={activeTool === 'feed'}
              onDragStart={(e) => {
                if (activeTool !== 'feed') return
                e.dataTransfer.setData('text/plain', 'feed')
                e.dataTransfer.effectAllowed = 'copy'
              }}
              onDoubleClick={() => activeTool === 'feed' && startFeedQueue()}
              type="button"
              title="Корм"
            >
              <span className="nursery__btn-icon">🍗</span>
            </button>
            <button
              className={`nursery__btn ${activeTool === 'insurance' ? 'is-active' : ''}`}
              onClick={handleInsurance}
              type="button"
              title="Страхование"
            >
              <span className="nursery__btn-icon">✚</span>
            </button>
            <button
              className={`nursery__btn ${activeTool === 'inspect' ? 'is-active' : ''}`}
              onClick={handleInspect}
              type="button"
              title="Осмотр"
            >
              <span className="nursery__btn-icon">⌕</span>
            </button>
          </div>

          <div className="nursery__scene">
            <div className="nursery-house-marker">1</div>
          {hasHome ? (
            <>
              <div className="nursery__house" onClick={() => activeTool === 'insurance' && setModal({ type: 'insurance' })}>
                <img src="/assets/nurseruhome.png" alt="home" />
                {nursery.insuranceActive || nursery.insuranceNext ? (
                  <span className="insurance-badge">INS</span>
                ) : null}
                <div className="own-nurseries__nursery-box nursery-box">
                  {['left', 'right'].map((side) => (
                    <div className="nursery-box__family" key={side}>
                      <div className="nursery-box__old-cats">
                        <div className="nursery-box__old-cats-window">
                          {[0, 1].map((i) => {
                            const catId = nursery.home.parents[side][i]
                            const cat = catId ? catsById[catId] : null
                            return (
                              <div
                                key={`${side}-${i}`}
                                className={`nursery-box__old-cat-card parent-slot ${
                                  cat ? 'is-filled' : 'is-empty'
                                }`}
                                onDrop={(e) =>
                                  handleDropParent(side, i, e.dataTransfer.getData('text/plain'))
                                }
                                onDragOver={(e) => e.preventDefault()}
                                onClick={() => handleRemoveParent(side, i)}
                              >
                                {renderCat(cat, { alt: 'parent' })}
                              </div>
                            )
                          })}
                        </div>
                        <button className="text_button text_button--disabled text_button--color-green nursery-box__cats-action breed-btn" onClick={() => handleBreed(side)}>
                          <svg width="32" height="32" viewBox="0 0 32 32" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
                            <path d="M27.3281 4.08488C26.0293 3.39481 24.5425 3 22.9585 3C20.1678 3 17.6603 4.22556 16.0053 6.14384C14.3391 4.22537 11.84 3 9.04224 3C7.45975 3 5.96959 3.39367 4.67208 4.08488C1.88707 5.56076 0 8.40554 0 11.691C0 12.6322 0.158953 13.5259 0.447162 14.3717C1.99386 21.0729 11.8984 29.5257 16.0061 29.5257C20.0003 29.5257 30 21.0729 31.5534 14.3717C31.8416 13.5259 32 12.6322 32 11.691C32.0013 8.40554 30.1126 5.56076 27.3281 4.08488Z" />
                          </svg>
                          СКРЕСТИТЬ
                        </button>
                      </div>
                      <div className="nursery-box__kittens" />
                    </div>
                  ))}
                </div>
              </div>

              <div className="kitten-slots">
                {Array.from({ length: 12 }).map((_, i) => (
                  <div
                    key={`kitten-${i}`}
                    className={`kitten-slot ${nursery.home.kittens[i] ? 'is-filled' : 'is-empty'}`}
                    onClick={() => {
                      const kitten = nursery.home.kittens[i]
                      if (!kitten) return
                      if (activeTool === 'feed') handleFeed(kitten)
                      if (activeTool === 'inspect') handleInspectCat(kitten)
                    }}
                    onDrop={(e) => {
                      if (activeTool !== 'feed') return
                      e.preventDefault()
                      const type = e.dataTransfer.getData('text/plain')
                      if (type !== 'feed') return
                      const kitten = nursery.home.kittens[i]
                      if (kitten) handleFeed(kitten)
                    }}
                    onDragOver={(e) => activeTool === 'feed' && e.preventDefault()}
                  >
                    {nursery.home.kittens[i] ? (
                      <>
                        {renderCat(nursery.home.kittens[i], { alt: 'kitten' })}
                        {nursery.home.kittens[i].hungry ? (
                          <img className="hungry" src="/assets/hungrywhite.png" alt="hungry" />
                        ) : null}
                        {nursery.home.kittens[i].sick ? (
                          <img className="sick" src={SICK_ICON[nursery.home.kittens[i].sick]} alt="sick" />
                        ) : null}
                      </>
                    ) : null}
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="nursery__house-placeholder">
              <div>Домик не куплен</div>
              <button className="nursery__btn" onClick={handleBuyHome}>Купить домик</button>
            </div>
          )}

          <div className="nursery-fence" />

          <div className="yard">
            {yardCats.map((cat) => (
              <div
                key={cat.id}
                className="yard-cat"
                draggable
                onDragStart={(e) => e.dataTransfer.setData('text/plain', cat.id)}
                onDoubleClick={() => activeTool === 'feed' && startFeedQueue()}
                onClick={() => {
                  if (activeTool === 'feed') handleFeed(cat)
                  if (activeTool === 'inspect') handleInspectCat(cat)
                }}
                onDrop={(e) => {
                  if (activeTool !== 'feed') return
                  e.preventDefault()
                  const type = e.dataTransfer.getData('text/plain')
                  if (type === 'feed') handleFeed(cat)
                }}
                onDragOver={(e) => e.preventDefault()}
              >
                {renderCat(cat, { alt: 'cat' })}
                {cat.hungry ? <img className="hungry" src="/assets/hungrywhite.png" alt="hungry" /> : null}
                {cat.sick ? (
                  <img className="sick" src={SICK_ICON[cat.sick]} alt="sick" />
                ) : null}
              </div>
            ))}
          </div>
          </div>

          <div className="nursery__requests">
            <button className="nursery__requests-icon" type="button" title="Домики">🏛</button>
            <div className="nursery__requests-panel">
              <div className="nursery__requests-item">🐱</div>
              <div className="nursery__requests-item nursery__requests-item--active">✉</div>
            </div>
          </div>

          <button className="nursery-relocate" type="button">РАССЕЛИ КОТИКОВ</button>
        </div>
      </div>

      {modal?.type === 'confirmFeed' ? (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal modal--color-green modal--size-cats" onClick={(e) => e.stopPropagation()}>
            <div className="modal__header">
              <div className="modal__title">ПОКУПКА ОДОБРЕНА</div>
              <div className="modal__desc"><span>корм для питомца</span></div>
            </div>
            <div className="modal__body">
              <div className="modal__body-wrapper">
                <div className="modal__body-cats">
                  {renderCat(modal.cat, { single: true, readonly: true, count: 1, description: true })}
                </div>
                <div className="modal__body-price">
                  <p className="modal__body-price-text">итого цена</p>
                  <p className="modal__body-price-coin">
                    <span className="modal__body-price-coin-icon coin" />
                    <span className="modal__body-price-coin-count notranslate">{FEED_COST}</span>
                  </p>
                </div>
              </div>
              <div className="modal__body-actions">
                <button className="text_button text_button--color-blue" onClick={() => confirmFeed(modal.cat)}>ПОКОРМИТЬ</button>
                <button className="text_button text_button--color-transparent" onClick={() => setModal(null)}>ОТМЕНА</button>
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {modal?.type === 'confirmBuyHome' ? (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal modal--color-green modal--size-cats" onClick={(e) => e.stopPropagation()}>
            <div className="modal__header">
              <div className="modal__title">ПОКУПКА ДОМИКА</div>
              <div className="modal__desc"><span>хочешь купить домик для котиков?</span></div>
            </div>
            <div className="modal__body">
              <div className="modal__body-price">
                <p className="modal__body-price-text">итого цена</p>
                <p className="modal__body-price-coin">
                  <span className="modal__body-price-coin-icon coin" />
                  <span className="modal__body-price-coin-count notranslate">{HOME_COST}</span>
                </p>
              </div>
              <div className="modal__body-actions">
                <button className="text_button text_button--color-blue" onClick={confirmBuyHome}>КУПИТЬ</button>
                <button className="text_button text_button--color-transparent" onClick={() => setModal(null)}>ОТМЕНА</button>
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {modal?.type === 'insurance' ? (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal modal--color-green modal--size-cats" onClick={(e) => e.stopPropagation()}>
            <div className="modal__header">
              <div className="modal__title">СТРАХОВАНИЕ</div>
              <div className="modal__desc"><span>застраховать домик на следующий сезон?</span></div>
            </div>
            <div className="modal__body">
              <div className="modal__body-price">
                <p className="modal__body-price-text">итого цена</p>
                <p className="modal__body-price-coin">
                  <span className="modal__body-price-coin-icon coin" />
                  <span className="modal__body-price-coin-count notranslate">{INSURANCE_COST}</span>
                </p>
              </div>
              <div className="modal__body-actions">
                <button className="text_button text_button--color-blue" onClick={handleInsuranceConfirm}>ЗАСТРАХОВАТЬ</button>
                <button className="text_button text_button--color-transparent" onClick={() => setModal(null)}>ОТМЕНА</button>
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {modal?.type === 'error' || modal?.type === 'info' ? (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal modal--color-neutral modal--size-cats" onClick={(e) => e.stopPropagation()}>
            <div className="modal__header">
              <div className="modal__title">{modal.title}</div>
            </div>
            <div className="modal__body">
              <div className="modal__body-actions">
                <button className="text_button text_button--color-blue" onClick={() => setModal(null)}>ПОНЯТНО</button>
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {inspectTarget ? (
        <div className="modal-overlay" onClick={() => setInspectTarget(null)}>
          <div className="modal modal--color-green modal--size-cats" onClick={(e) => e.stopPropagation()}>
            <div className="modal__header">
              <div className="modal__title">ЛЕЧЕНИЕ</div>
              <div className="modal__desc"><span>осмотр и лечение котика</span></div>
            </div>
            <div className="modal__body">
              <div className="modal__body-wrapper">
                <div className="modal__body-cats">
                  {renderCat(inspectTarget, { single: true, readonly: true, count: 1, description: true })}
                </div>
                <div className="modal__body-price">
                  {inspectTarget.sick ? (
                    <img className="inspect-icon" src={SICK_ICON[inspectTarget.sick]} alt="sick" />
                  ) : null}
                  <p className="modal__body-price-text">цена лечения</p>
                  <p className="modal__body-price-coin">
                    <span className="modal__body-price-coin-icon coin" />
                    <span className="modal__body-price-coin-count notranslate">
                      {nursery?.insuranceActive ? 0 : TREAT_COST}
                    </span>
                  </p>
                </div>
              </div>
              <div className="modal__body-actions">
                <button className="text_button text_button--color-blue" onClick={() => handleTreat(inspectTarget)}>ЛЕЧИТЬ</button>
                <button className="text_button text_button--color-transparent" onClick={() => setInspectTarget(null)}>ОТМЕНА</button>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}

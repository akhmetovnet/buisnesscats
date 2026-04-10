import { useCallback, useEffect, useMemo, useState } from 'react'
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
  kitten: {
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
  },
  adult: {
    M: {
      black: {
        default: '/assets/cats/big-male-black.png',
        hungry: '/assets/cats/big-black-male-hungry.png',
      },
      white: {
        default: '/assets/cats/male-big-sleep-white.png',
        hungry: '/assets/cats/big-male-cat-white-hungry.png',
      },
      gray: {
        default: '/assets/cats/gray-big-male.png',
        hungry: '/assets/cats/gray-big-hungry.png',
      },
      ginger: {
        default: '/assets/cats/orange-male-big.png',
        hungry: '/assets/cats/orange-big-hungry-male.png',
      },
    },
    F: {
      black: {
        default: '/assets/cats/big-black-female.png',
        hungry: '/assets/cats/b-fem-hungry-big.png',
      },
      white: {
        default: '/assets/cats/white-female.png',
        hungry: '/assets/cats/big-female-cat-hungry.png',
      },
      gray: {
        default: '/assets/cats/big-female-cat-gray.png',
        hungry: '/assets/cats/big-female-cat-gray-hungry.png',
      },
      ginger: {
        default: '/assets/cats/big-orange-female.png',
        hungry: '/assets/cats/orange-big-female-hungry.png',
      },
    },
  },
}

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
const DEFAULT_ADULT_AGE = 3

const resolveColorLabel = (value) => {
  const normalized = normalizeColor(value)
  return COLOR_LABEL[normalized] || 'неизвестный окрас'
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

const getCatSprite = (cat, adultAge = DEFAULT_ADULT_AGE) => {
  const color = normalizeColor(cat?.color)
  const sex = normalizeSex(cat?.sex) || 'M'
  const age = Number(cat?.age ?? cat?.ageSeasons)
  const isAdult = Number.isFinite(age) ? age >= adultAge : !Boolean(cat?.isKitten)
  const lifeStage = isAdult ? 'adult' : 'kitten'
  const stageSprites = CAT_SPRITES[lifeStage] || CAT_SPRITES.kitten
  const sexSprites = stageSprites[sex] || stageSprites.M
  const colorSprites = sexSprites[color] || sexSprites.gray
  if (!colorSprites) return '/assets/cats/male-gray-small.png'
  if (cat?.hungry) return colorSprites.hungry || colorSprites.default
  return colorSprites.default || colorSprites.hungry
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
  playerAvatarUrl = null,
  seasonNumber,
  coinsNow,
  timerText = '00:00:00',
  onRequestEndSeason,
  onExitPlatform,
  onCoinsSync,
  onSeasonSpend,
  adultAge = DEFAULT_ADULT_AGE,
}) {
  const [activeTool, setActiveTool] = useState(null)
  const [modal, setModal] = useState(null)
  const [feedQueue, setFeedQueue] = useState([])
  const [inspectTarget, setInspectTarget] = useState(null)

  useEffect(() => {
    setNursery((prev) => {
      const homeSlots = Array.isArray(prev?.home?.kittens) ? prev.home.kittens : []
      if (!homeSlots.length) return prev

      const movedToYard = []
      const nextHomeSlots = homeSlots.map((cat) => {
        if (!cat) return null
        const id = String(cat?.id ?? '')
        if (id.startsWith('born-')) return cat
        movedToYard.push(cat)
        return null
      })

      if (!movedToYard.length) return prev

      const existingCats = Array.isArray(prev?.cats) ? prev.cats : []
      const seenIds = new Set(existingCats.map((cat) => cat?.id).filter(Boolean))
      const appended = movedToYard.filter((cat) => {
        if (!cat?.id || seenIds.has(cat.id)) return false
        seenIds.add(cat.id)
        return true
      })

      return {
        ...prev,
        cats: [...existingCats, ...appended],
        home: {
          ...prev.home,
          kittens: nextHomeSlots,
        },
      }
    })
  }, [setNursery])

  const cats = Array.isArray(nursery?.cats) ? nursery.cats : []
  const hasHome = nursery?.hasHome
  const playerName = nursery?.playerName || 'ЛЕОПОЛЬД'
  const coins = Number.isFinite(Number(coinsNow))
    ? Number(coinsNow)
    : Number(nursery?.coins ?? 0)

  const assignedIds = useMemo(() => {
    const ids = new Set()
    if (!nursery?.home) return ids
    nursery.home.parents.left.forEach((id) => id && ids.add(id))
    nursery.home.parents.right.forEach((id) => id && ids.add(id))
    return ids
  }, [nursery])
  const homeWindowKittens = useMemo(
    () => Array.from({ length: 12 }, (_, idx) => nursery?.home?.kittens?.[idx] || null),
    [nursery?.home?.kittens]
  )
  const homeKittens = useMemo(
    () => (nursery?.home?.kittens || []).filter(Boolean),
    [nursery?.home?.kittens]
  )
  const catsById = useMemo(
    () => Object.fromEntries([...cats, ...homeKittens].map((cat) => [cat.id, cat])),
    [cats, homeKittens]
  )
  const bornKittenIds = useMemo(
    () => new Set(homeKittens.map((cat) => cat.id)),
    [homeKittens]
  )

  const yardCats = cats.filter((cat) => !assignedIds.has(cat.id))
  const hasMotherOnSide = useCallback(
    (side) =>
      (nursery?.home?.parents?.[side] || []).some((catId) => {
        const cat = catId ? catsById[catId] : null
        return cat?.sex === 'F'
      }),
    [nursery?.home?.parents, catsById]
  )
  const isProtectedKittenSlot = useCallback(
    (slotIndex) => {
      const side = slotIndex < 6 ? 'left' : 'right'
      return hasMotherOnSide(side)
    },
    [hasMotherOnSide]
  )
  const parentFeedTargets = useMemo(
    () =>
      ['left', 'right'].flatMap((side) =>
        [0, 1]
          .map((idx) => {
            const catId = nursery?.home?.parents?.[side]?.[idx]
            return catId ? catsById[catId] : null
          })
          .filter((cat) => cat && cat.hungry && !cat.fedThisSeason)
      ),
    [nursery?.home?.parents, catsById]
  )
  const kittenQueueTargets = useMemo(
    () =>
      homeWindowKittens.filter(
        (cat, idx) =>
          cat &&
          !assignedIds.has(cat.id) &&
          !isProtectedKittenSlot(idx) &&
          cat.hungry &&
          !cat.fedThisSeason
      ),
    [homeWindowKittens, assignedIds, isProtectedKittenSlot]
  )
  const kittensByFamilySide = useMemo(() => {
    const buckets = { left: Array(6).fill(null), right: Array(6).fill(null) }
    const slots = homeWindowKittens || []
    slots.forEach((cat, idx) => {
      if (!cat || assignedIds.has(cat.id)) return
      if (idx < 6) {
        buckets.left[idx] = cat
      } else if (idx < 12) {
        buckets.right[idx - 6] = cat
      }
    })
    return buckets
  }, [homeWindowKittens, assignedIds])
  const syncCoins = (nextCoins) => {
    const normalized = Math.max(0, Number(nextCoins) || 0)
    setNursery((prev) => ({ ...prev, coins: normalized }))
    if (typeof onCoinsSync === 'function') onCoinsSync(normalized)
  }

  const spendCoins = (amount) => {
    const cost = Number(amount) || 0
    if (coins < cost) return false
    syncCoins(coins - cost)
    return true
  }

  const recordSeasonSpend = (category, amount) => {
    if (typeof onSeasonSpend === 'function') {
      onSeasonSpend(category, amount)
    }
  }

  const openNotEnoughCoinsModal = (requiredCoins) => {
    const required = Math.max(0, Number(requiredCoins) || 0)
    setModal({
      type: 'notEnoughCoins',
      title: 'Недостаточно монет',
      required,
      current: coins,
    })
  }

  const handleBuyHome = () => {
    if (hasHome) {
      setModal({ type: 'info', title: 'Домик уже куплен' })
      return
    }
    if (coins < HOME_COST) {
      openNotEnoughCoinsModal(HOME_COST)
      return
    }
    setModal({ type: 'confirmBuyHome' })
  }

  const confirmBuyHome = () => {
    if (!spendCoins(HOME_COST)) {
      openNotEnoughCoinsModal(HOME_COST)
      return
    }
    recordSeasonSpend('home', HOME_COST)
    setNursery((prev) => ({
      ...prev,
      hasHome: true,
    }))
    setModal(null)
  }

  const handleBuyFeed = () => {
    setActiveTool(activeTool === 'feed' ? null : 'feed')
  }

  const handleInsurance = () => {
    if (!hasHome) {
      setModal({ type: 'error', title: 'Сначала купите домик' })
      return
    }
    setModal({ type: 'insurance' })
  }

  const handleInspect = () => {
    setActiveTool(activeTool === 'inspect' ? null : 'inspect')
  }

  const handleFeed = (cat) => {
    if (!cat?.hungry || cat?.fedThisSeason) {
      setModal({ type: 'error', title: 'Вы не можете покормить сытого котика' })
      return
    }
    if (coins < FEED_COST) {
      openNotEnoughCoinsModal(FEED_COST)
      return
    }
    setModal({ type: 'confirmFeed', cat })
  }

  const confirmFeed = (cat) => {
    if (!cat?.hungry || cat?.fedThisSeason) {
      setModal({ type: 'error', title: 'Вы не можете покормить сытого котика' })
      return
    }
    if (!spendCoins(FEED_COST)) {
      openNotEnoughCoinsModal(FEED_COST)
      return
    }
    recordSeasonSpend('feed', FEED_COST)
    const afterFeedCoins = coins - FEED_COST
    setNursery((prev) => ({
      ...prev,
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
      const [next, ...rest] = feedQueue
      setFeedQueue(rest)
      if (afterFeedCoins < FEED_COST) {
        openNotEnoughCoinsModal(FEED_COST)
        return
      }
      if (next?.hungry && !next?.fedThisSeason) {
        setModal({ type: 'confirmFeed', cat: next })
      }
    }
  }

  const startFeedQueue = () => {
    if (!hasHome) {
      setModal({ type: 'error', title: 'Сначала купите домик' })
      return
    }
    const queue = [...parentFeedTargets, ...kittenQueueTargets]
    if (!queue.length) {
      setModal({ type: 'error', title: 'Нет голодных котиков в домике' })
      return
    }
    if (coins < FEED_COST) {
      openNotEnoughCoinsModal(FEED_COST)
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
      openNotEnoughCoinsModal(TREAT_COST)
      return
    }
    if (!insured) {
      if (!spendCoins(TREAT_COST)) {
        openNotEnoughCoinsModal(TREAT_COST)
        return
      }
      recordSeasonSpend('treatment', TREAT_COST)
    }
    setNursery((prev) => ({
      ...prev,
      cats: prev.cats.map((c) => (c.id === cat.id ? { ...c, sick: null } : c)),
    }))
    setInspectTarget(null)
  }

  const handleInsuranceConfirm = () => {
    if (coins < INSURANCE_COST) {
      openNotEnoughCoinsModal(INSURANCE_COST)
      return
    }
    if (!spendCoins(INSURANCE_COST)) {
      openNotEnoughCoinsModal(INSURANCE_COST)
      return
    }
    recordSeasonSpend('insurance', INSURANCE_COST)
    setNursery((prev) => ({
      ...prev,
      insuranceNext: true,
    }))
    setModal(null)
  }

  const handleDropParent = (side, index, catId) => {
    if (bornKittenIds.has(catId)) {
      setModal({ type: 'error', title: 'Рожденные котята размещаются в маленьких окнах' })
      return
    }
    const cat = cats.find((c) => c.id === catId)
    if (!cat) return
    if (cat.locked || nursery?.home?.breedPending?.left || nursery?.home?.breedPending?.right) {
      setModal({ type: 'error', title: 'Во время скрещивания котиков перемещать нельзя' })
      return
    }
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
    if (cat?.locked || nursery?.home?.breedPending?.left || nursery?.home?.breedPending?.right) {
      setModal({ type: 'error', title: 'Во время скрещивания котиков перемещать нельзя' })
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
    if (catA.age < adultAge || catB.age < adultAge) {
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
    const sideSlots = side === 'left' ? [0, 1, 2, 3, 4, 5] : [6, 7, 8, 9, 10, 11]
    const hasKittensNearParents = sideSlots.some((idx) => Boolean(homeWindowKittens?.[idx]))
    if (hasKittensNearParents) {
      setModal({ type: 'error', title: 'Скрещивание невозможно: рядом с родителями сидят котята' })
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

  const canBreedOnSide = useCallback(
    (side) => {
      if (!hasHome) return false
      const pair = nursery?.home?.parents?.[side] || []
      const catA = pair[0] ? catsById[pair[0]] : null
      const catB = pair[1] ? catsById[pair[1]] : null
      if (!catA || !catB) return false
      if (catA.sex === catB.sex) return false
      if (catA.age < adultAge || catB.age < adultAge) return false
      if (catA.hungry || catB.hungry) return false
      if (nursery?.home?.breedPending?.[side]) return false
      if (nursery?.home?.lastBreedSeason?.[side] === seasonNumber - 1) return false
      const sideSlots = side === 'left' ? [0, 1, 2, 3, 4, 5] : [6, 7, 8, 9, 10, 11]
      return !sideSlots.some((idx) => Boolean(homeWindowKittens?.[idx]))
    },
    [hasHome, nursery?.home, catsById, seasonNumber, homeWindowKittens]
  )

  const moveKittenToYard = (side, idx) => {
    const slotIndex = side === 'left' ? idx : idx + 6
    const kitten = nursery?.home?.kittens?.[slotIndex]
    if (!kitten) return
    if (nursery?.home?.breedPending?.left || nursery?.home?.breedPending?.right) {
      setModal({ type: 'error', title: 'Во время скрещивания котиков перемещать нельзя' })
      return
    }
    setNursery((prev) => {
      const nextKittens = [...(prev?.home?.kittens || [])]
      const current = nextKittens[slotIndex]
      if (!current) return prev
      nextKittens[slotIndex] = null
      const already = (prev?.cats || []).some((cat) => cat.id === current.id)
      return {
        ...prev,
        cats: already
          ? prev.cats
          : [...(prev.cats || []), { ...current, hungry: true, fedThisSeason: false }],
        home: {
          ...prev.home,
          kittens: nextKittens,
        },
      }
    })
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
          <img
            src={getCatSprite(cat, adultAge)}
            alt="котик"
            onError={(e) => {
              e.currentTarget.src = '/assets/cats/male-gray-small.png'
            }}
          />
        </span>
        {options.description ? (
          <div className="cat__description cat__description--info">
            <span>{SEX_LABEL[sex] || 'котик'}</span>
            <br />
            <span>{resolveColorLabel(color)}</span>
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
      <div className="nursery nurseries-layout nurseries-layout--bg season--fall" onClick={(e) => e.stopPropagation()}>
        <header className="nursery-header header_container">
          <div className="nursery-header__left left_side_container">
            <button className="nursery-header__home header-extra" type="button" onClick={onClose}>⌂</button>
            <div className="nursery-coins avatar_container avatar_container--with-adaptation">
              {playerAvatarUrl ? (
                <img className="nursery-coins__avatar avatar" src={playerAvatarUrl} alt="avatar" />
              ) : (
                <span className="nursery-coins__avatar avatar">🐾</span>
              )}
              <div className="nursery-coins__meta user_info">
                <span className="nursery-coins__name user_name">{playerName}</span>
                <span className="nursery-coins__value coins"><span className="coin coin-icon" />{coins}</span>
              </div>
            </div>
          </div>

          <div className="nursery-header__season season_container">
            <p className="nursery-header__season-number">
              <span className="notranslate">{seasonNumber}</span> СЕЗОН
            </p>
            <p className="nursery-header__timer notranslate">{timerText}</p>
          </div>

          <div className="nursery-header__right btns_container">
            <button className="nursery-header__end end-turn-button" type="button" onClick={handleEndSeason}>ЗАВЕРШИТЬ СЕЗОН</button>
            <button className="nursery-header__icon nursery-header__icon--exit icon_button button_bg_purple session-logout-icon-button" type="button" onClick={handleExitPlatform}>⇥</button>
          </div>
        </header>

        <div className="nursery-stage">
          <div className="own-nurseries">
          <img className="nursery-stage__tree-left own-nurseries__tree" src="/assets/treelefts.png" alt="" />
          <img className="nursery-stage__tree-right" src="/assets/treerights.png" alt="" />

          <div className="nursery__sidebar own-nurseries__actions">
            <button className="nursery__btn nursery__btn--home own-nurseries__actions-item" type="button" onClick={handleBuyHome} title="Купить домик">
              <span className="nursery__btn-icon">🏠</span>
              <span className="nursery__btn-label">Домики</span>
            </button>
            <button
              className={`nursery__btn own-nurseries__actions-item own-nurseries__actions-item--eat ${activeTool === 'feed' ? 'is-active' : ''}`}
              onClick={handleBuyFeed}
              draggable={activeTool === 'feed'}
              onDragStart={(e) => {
                if (activeTool !== 'feed') return
                e.dataTransfer.setData('text/plain', 'feed')
                e.dataTransfer.effectAllowed = 'copy'
              }}
              onDoubleClick={() => {
                setActiveTool('feed')
                startFeedQueue()
              }}
              type="button"
              title="Корм"
            >
              <span className="nursery__btn-icon">🍗</span>
            </button>
            <button
              className={`nursery__btn own-nurseries__actions-item own-nurseries__actions-item--insurance`}
              onClick={handleInsurance}
              type="button"
              title="Страхование"
            >
              <span className="nursery__btn-icon">✚</span>
            </button>
            <button
              className={`nursery__btn own-nurseries__actions-item own-nurseries__actions-item--magnifier ${activeTool === 'inspect' ? 'is-active' : ''}`}
              onClick={handleInspect}
              type="button"
              title="Осмотр"
            >
              <span className="nursery__btn-icon">⌕</span>
            </button>
          </div>

          <section className="own-nurseries__houses">
          <div className="own-nurseries__houses-slider">
          <div className="nursery__scene">
          {hasHome ? (
            <>
              <div className="nursery__house">
                <img src="/assets/nurseruhome.png" alt="home" />
                {nursery.insuranceActive || nursery.insuranceNext ? (
                  <span className="insurance-badge">
                    <img src="/assets/cats/zastrachovano-domik.png" alt="insured house" />
                  </span>
                ) : null}
                <div className="own-nurseries__houses-item own-nurseries__houses-item--single-house">
                  <div className="own-nurseries__houses-tablet">
                    <div className="own-nurseries__houses-number_box">
                      <div className="own-nurseries__houses-number">1</div>
                    </div>
                  </div>
                  <div className="own-nurseries__nursery-box nursery-box">
                    {['left', 'right'].map((side) => (
                      <div className={`nursery-box__family nursery-box__family--${side}`} key={side}>
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
                                  } parent-slot--${side}-${i}`}
                                  draggable={Boolean(cat && !cat.locked)}
                                  onDragStart={(e) => {
                                    if (!cat || cat.locked) return
                                    e.dataTransfer.setData('text/plain', cat.id)
                                    e.dataTransfer.effectAllowed = 'move'
                                  }}
                                  onDrop={(e) => {
                                    const payload = e.dataTransfer.getData('text/plain')
                                    if (activeTool === 'feed' && payload === 'feed') {
                                      if (cat) handleFeed(cat)
                                      return
                                    }
                                    handleDropParent(side, i, payload)
                                  }}
                                  onDragOver={(e) => e.preventDefault()}
                                  onClick={() => {
                                    if (!cat) return
                                    if (activeTool === 'feed') {
                                      handleFeed(cat)
                                      return
                                    }
                                    if (activeTool === 'inspect') {
                                      handleInspectCat(cat)
                                      return
                                    }
                                    handleRemoveParent(side, i)
                                  }}
                                >
                                  {renderCat(cat, { alt: 'parent' })}
                                </div>
                              )
                            })}
                          </div>
                          <button
                            className={`text_button text_button--color-green nursery-box__cats-action breed-btn ${canBreedOnSide(side) ? 'is-enabled' : 'text_button--disabled'}`}
                            onClick={() => handleBreed(side)}
                            disabled={!canBreedOnSide(side)}
                          >
                            <svg width="32" height="32" viewBox="0 0 32 32" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
                              <path d="M27.3281 4.08488C26.0293 3.39481 24.5425 3 22.9585 3C20.1678 3 17.6603 4.22556 16.0053 6.14384C14.3391 4.22537 11.84 3 9.04224 3C7.45975 3 5.96959 3.39367 4.67208 4.08488C1.88707 5.56076 0 8.40554 0 11.691C0 12.6322 0.158953 13.5259 0.447162 14.3717C1.99386 21.0729 11.8984 29.5257 16.0061 29.5257C20.0003 29.5257 30 21.0729 31.5534 14.3717C31.8416 13.5259 32 12.6322 32 11.691C32.0013 8.40554 30.1126 5.56076 27.3281 4.08488Z" />
                            </svg>
                            СКРЕСТИТЬ
                          </button>
                        </div>
                        <div className="nursery-box__kittens">
                          {Array.from({ length: 6 }).map((_, idx) => {
                            const kitten = kittensByFamilySide[side][idx] || null
                            const slotIndex = side === 'left' ? idx : idx + 6
                            const isProtected = isProtectedKittenSlot(slotIndex)
                            return (
                              <div
                                key={`${side}-kitten-window-${idx}`}
                                className={`nursery-box__kitten-card ${kitten ? 'is-filled' : 'is-empty'}`}
                                draggable={false}
                                onClick={() => {
                                  if (!kitten) return
                                  if (activeTool === 'feed') {
                                    if (isProtected) {
                                      setModal({ type: 'info', title: 'Котят с мамой кормить не нужно' })
                                      return
                                    }
                                    handleFeed(kitten)
                                    return
                                  }
                                  if (activeTool === 'inspect') {
                                    handleInspectCat(kitten)
                                    return
                                  }
                                  moveKittenToYard(side, idx)
                                }}
                                onDrop={(e) => {
                                  if (activeTool !== 'feed') return
                                  e.preventDefault()
                                  const type = e.dataTransfer.getData('text/plain')
                                  if (type !== 'feed') return
                                  if (isProtected) {
                                    setModal({ type: 'info', title: 'Котят с мамой кормить не нужно' })
                                    return
                                  }
                                  if (kitten) handleFeed(kitten)
                                }}
                                onDragOver={(e) => activeTool === 'feed' && e.preventDefault()}
                              >
                                {kitten ? (
                                  <>
                                    {renderCat(kitten, { alt: 'kitten' })}
                                    {kitten.hungry && !isProtected ? (
                                      <img
                                        className="hungry"
                                        src="/assets/hungrywhite.png"
                                        alt=""
                                        onError={(e) => {
                                          e.currentTarget.style.display = 'none'
                                        }}
                                      />
                                    ) : null}
                                    {kitten.sick ? (
                                      <img
                                        className="sick"
                                        src={SICK_ICON[kitten.sick]}
                                        alt=""
                                        onError={(e) => {
                                          e.currentTarget.style.display = 'none'
                                        }}
                                      />
                                    ) : null}
                                  </>
                                ) : null}
                              </div>
                            )
                          })}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="nursery__house-placeholder">
              <div>Домик не куплен</div>
              <button className="nursery__btn" onClick={handleBuyHome}>Купить домик</button>
            </div>
          )}

          <div className="yard">
            <div className="own-nurseries__cats">
              <div className="own-nurseries__cats-slider">
            {yardCats.map((cat) => (
              <div
                key={cat.id}
                className="yard-cat"
                draggable={!cat.locked}
                onDragStart={(e) => {
                  if (cat.locked) return
                  e.dataTransfer.setData('text/plain', cat.id)
                }}
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
                {cat.hungry ? (
                  <img
                    className="hungry"
                    src="/assets/hungrywhite.png"
                    alt=""
                    onError={(e) => {
                      e.currentTarget.style.display = 'none'
                    }}
                  />
                ) : null}
                {cat.sick ? (
                  <img
                    className="sick"
                    src={SICK_ICON[cat.sick]}
                    alt=""
                    onError={(e) => {
                      e.currentTarget.style.display = 'none'
                    }}
                  />
                ) : null}
              </div>
            ))}
              </div>
            </div>
          </div>
          </div>
          </div>
          </section>

          <div className="nursery-relocate own-nurseries__bush">РАССЕЛИ КОТИКОВ</div>
          </div>
        </div>
      </div>

      {modal?.type === 'confirmFeed' ? (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal modal--size-cats" onClick={(e) => e.stopPropagation()}>
            <div className="modal__header">
              <div className="modal__title">Кормление котика</div>
              <div className="modal__desc"><span>Подтвердите действие и стоимость кормления</span></div>
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
                <button className="text_button text_button--color-blue" onClick={() => confirmFeed(modal.cat)}>Покормить</button>
                <button className="text_button text_button--color-transparent" onClick={() => setModal(null)}>Отмена</button>
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {modal?.type === 'confirmBuyHome' ? (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal modal--size-cats" onClick={(e) => e.stopPropagation()}>
            <div className="modal__header">
              <div className="modal__title">Покупка домика</div>
              <div className="modal__desc">
                <span>Домик нужен для размещения взрослых котиков и выращивания потомства</span>
              </div>
            </div>
            <div className="modal__body">
              <div className="modal__body-cats">
                <img
                  src="/assets/nurseruhome.png"
                  alt="домик"
                  style={{ width: '170px', maxWidth: '100%', objectFit: 'contain' }}
                />
              </div>
              <div className="modal__body-price">
                <p className="modal__body-price-text">итого цена</p>
                <p className="modal__body-price-coin">
                  <span className="modal__body-price-coin-icon coin" />
                  <span className="modal__body-price-coin-count notranslate">{HOME_COST}</span>
                </p>
              </div>
              <div className="modal__body-actions">
                <button className="text_button text_button--color-blue" onClick={confirmBuyHome}>Купить</button>
                <button className="text_button text_button--color-transparent" onClick={() => setModal(null)}>Отмена</button>
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {modal?.type === 'insurance' ? (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal modal--size-cats" onClick={(e) => e.stopPropagation()}>
            <div className="modal__header">
              <div className="modal__title">Страхование домика</div>
              <div className="modal__desc">
                <span>Срок: следующий сезон. Покрывает внеплановые риски в питомнике</span>
              </div>
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
                <button className="text_button text_button--color-blue" onClick={handleInsuranceConfirm}>Застраховать</button>
                <button className="text_button text_button--color-transparent" onClick={() => setModal(null)}>Отмена</button>
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {modal?.type === 'notEnoughCoins' || modal?.type === 'error' || modal?.type === 'info' ? (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal modal--size-cats" onClick={(e) => e.stopPropagation()}>
            <div className="modal__header">
              <div className="modal__title">{modal.title}</div>
              {modal?.type === 'notEnoughCoins' ? (
                <div className="modal__desc">
                  Нужно: <b className="notranslate">{Number(modal.required || 0)}</b> • Есть сейчас:{' '}
                  <b className="notranslate">{Number(modal.current || 0)}</b>
                </div>
              ) : null}
            </div>
            <div className="modal__body">
              {modal?.type === 'notEnoughCoins' ? (
                <div className="modal__desc" style={{ marginTop: 0, textAlign: 'center' }}>
                  Завершите выгодную сделку или сократите расходы.
                </div>
              ) : null}
              <div className="modal__body-actions">
                <button className="text_button text_button--color-blue" onClick={() => setModal(null)}>Понятно</button>
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {inspectTarget ? (
        <div className="modal-overlay" onClick={() => setInspectTarget(null)}>
          <div className="modal modal--size-cats" onClick={(e) => e.stopPropagation()}>
            <div className="modal__header">
              <div className="modal__title">Обследование и лечение</div>
              <div className="modal__desc"><span>Диагностика и лечение выбранного котика</span></div>
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
                <button className="text_button text_button--color-blue" onClick={() => handleTreat(inspectTarget)}>Лечить</button>
                <button className="text_button text_button--color-transparent" onClick={() => setInspectTarget(null)}>Отмена</button>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}

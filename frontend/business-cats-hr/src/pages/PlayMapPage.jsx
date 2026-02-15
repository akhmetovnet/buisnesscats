import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api.js'
import ShopOverlay from '../components/ShopOverlay.jsx'
import CatteryOverlay from '../components/CatteryOverlay.jsx'
import ConfirmEndSeasonModal from '../components/ConfirmEndSeasonModal.jsx'
import MyNurseryOverlay from '../components/MyNurseryOverlay.jsx'
import LoseModal from '../components/LoseModal.jsx'
import SeasonResultModal from '../components/SeasonResultModal.jsx'
import WelcomeStartModal from '../components/WelcomeStartModal.jsx'
import './PlayMapPage.css'

const PETSHOPS = [
  { id: 1, left: 18, top: 30 },
  { id: 2, left: 35, top: 30 },
  { id: 3, left: 50, top: 30 },
  { id: 4, left: 69, top: 30 },
  { id: 5, left: 84, top: 30 },
]

const CATTERIES = [
  { id: 1, left: 10, top: 50 },
  { id: 2, left: 23, top: 50 },
  { id: 3, left: 36, top: 49 },
  { id: 4, left: 50, top: 50.5 },
  { id: 5, left: 64, top: 49 },
  { id: 6, left: 78, top: 50.2 },
  { id: 7, left: 14, top: 62 },
  { id: 8, left: 28, top: 64 },
  { id: 9, left: 42, top: 63 },
  { id: 10, left: 56, top: 64 },
  { id: 11, left: 70, top: 63.5 },
  { id: 12, left: 84, top: 64.5 },
  { id: 13, left: 9, top: 76 },
  { id: 14, left: 24, top: 77.5 },
  { id: 15, left: 39, top: 76.5 },
  { id: 16, left: 54, top: 78 },
  { id: 17, left: 69, top: 76.8 },
  { id: 18, left: 82, top: 78.5 },
  { id: 19, left: 18, top: 89.5 },
  { id: 20, left: 60, top: 90 },
]

const YOUR_CATTTERY_ID = 1
const VALID_SEX = new Set(['M', 'F'])
const COLOR_ALIAS = {
  orange: 'ginger',
}
const MAP_CAT_SPRITES = {
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
const NURSERY_SEASON_START_COINS = 40

const imgFallback = (e) => {
  e.currentTarget.style.opacity = '0'
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

const getMapCatSprite = (cat) => {
  const color = normalizeColor(cat?.color)
  const sex = normalizeSex(cat?.sex) || 'M'
  return (
    MAP_CAT_SPRITES[sex]?.[color] ||
    MAP_CAT_SPRITES.M[color] ||
    MAP_CAT_SPRITES.M.gray
  )
}

const createBoughtKitten = (color, sex, idx = 0) => ({
  id: `buy-${Date.now()}-${idx}-${Math.random().toString(16).slice(2, 7)}`,
  sex: normalizeSex(sex) || (Math.random() > 0.5 ? 'M' : 'F'),
  color: normalizeColor(color),
  age: 0,
  hungry: true,
  sick: null,
  fedThisSeason: false,
  locked: false,
  isKitten: true,
})

export default function PlayMapPage() {
  const navigate = useNavigate()
  const { sessionId, seasonNumber } = useParams()
  const season = useMemo(() => {
    const n = Number(seasonNumber)
    return Number.isFinite(n) && n > 0 ? n : 1
  }, [seasonNumber])
  const SEASON_SECONDS = {
    1: 600,
    2: 300,
    3: 300,
    4: 300,
    5: 900,
    6: 300,
    7: 300,
    8: 300,
    9: 300,
    10: 900,
    11: 300,
    12: 300,
    13: 600,
  }

  const [state, setState] = useState(null)
  const [market, setMarket] = useState(null)
  const [overlayType, setOverlayType] = useState(null)
  const [selectedBuilding, setSelectedBuilding] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [timeLeft, setTimeLeft] = useState(SEASON_SECONDS[season] || 300)
  const [confirmEndOpen, setConfirmEndOpen] = useState(false)
  const [loseOpen, setLoseOpen] = useState(false)
  const [nurseryOpen, setNurseryOpen] = useState(false)
  const [seasonResult, setSeasonResult] = useState(null)
  const [autoFinishing, setAutoFinishing] = useState(false)
  const [autoAdvanceAfterResult, setAutoAdvanceAfterResult] = useState(false)
  const [welcomeOpen, setWelcomeOpen] = useState(false)
  const [nursery, setNursery] = useState(() => ({
    coins: NURSERY_SEASON_START_COINS,
    coinsSynced: false,
    hasHome: false,
    insuranceActive: false,
    insuranceNext: false,
    cats: [
      { id: 'c1', sex: 'M', color: 'black', age: 3, hungry: true, sick: null, fedThisSeason: false, locked: false },
      { id: 'c2', sex: 'F', color: 'white', age: 3, hungry: true, sick: null, fedThisSeason: false, locked: false },
      { id: 'c3', sex: 'M', color: 'ginger', age: 4, hungry: true, sick: 'lichen', fedThisSeason: false, locked: false },
      { id: 'c4', sex: 'F', color: 'gray', age: 4, hungry: true, sick: null, fedThisSeason: false, locked: false },
    ],
    home: {
      parents: { left: [null, null], right: [null, null] },
      kittens: Array(12).fill(null),
      breedPending: { left: false, right: false },
      lastBreedSeason: { left: 0, right: 0 },
    },
  }))

  const coinsNow = state?.coinsNowEstimate ?? 0
  const debtTotal = state?.debtTotal ?? 0
  const debtRate = state?.debtRate ?? 0
  const inventory = useMemo(() => {
    const rawInventory = state?.inventory
    if (!rawInventory || Array.isArray(rawInventory)) return {}
    return Object.fromEntries(
      Object.entries(rawInventory).filter(([, value]) => Number.isFinite(Number(value)))
    )
  }, [state?.inventory])
  const inventoryEntities = useMemo(() => {
    const nurseryEntities = [
      ...(nursery?.cats || []),
      ...(nursery?.home?.kittens || []).filter(Boolean),
    ]
      .filter((cat) => cat?.isKitten)
      .map((cat) => ({
        id: cat.id,
        color: normalizeColor(cat.color),
        sex: normalizeSex(cat.sex),
        age: Number(cat.age ?? 0),
        isKitten: true,
        hungry: Boolean(cat.hungry),
        fedThisSeason: Boolean(cat.fedThisSeason),
      }))

    const backendEntities = Array.isArray(state?.inventoryEntities)
      ? state.inventoryEntities
      : Array.isArray(state?.cats)
        ? state.cats
        : Array.isArray(state?.inventory?.entities)
          ? state.inventory.entities
          : Array.isArray(state?.inventory?.items)
            ? state.inventory.items
            : []

    if (!backendEntities.length) return nurseryEntities

    const nurseryById = new Map(nurseryEntities.map((cat) => [cat.id, cat]))
    const merged = backendEntities.map((entity) => {
      const fromNursery = nurseryById.get(entity?.id)
      return {
        ...entity,
        id: entity?.id ?? fromNursery?.id,
        color: normalizeColor(entity?.color ?? entity?.catType ?? fromNursery?.color),
        sex: normalizeSex(entity?.sex ?? fromNursery?.sex),
        age: Number(entity?.age ?? entity?.ageSeasons ?? fromNursery?.age ?? 0),
        isKitten: entity?.isKitten ?? fromNursery?.isKitten ?? true,
        hungry: Boolean(entity?.hungry ?? fromNursery?.hungry),
        fedThisSeason: Boolean(entity?.fedThisSeason ?? fromNursery?.fedThisSeason),
      }
    })

    const mergedIds = new Set(merged.map((entity) => entity.id).filter(Boolean))
    nurseryEntities.forEach((entity) => {
      if (!entity.id || mergedIds.has(entity.id)) return
      merged.push(entity)
    })
    return merged
  }, [state, nursery?.cats, nursery?.home?.kittens])
  const mapNurseryCats = useMemo(
    () =>
      [...(nursery?.cats || []), ...((nursery?.home?.kittens || []).filter(Boolean))]
        .filter((cat) => cat?.isKitten)
        .slice(0, 10),
    [nursery?.cats, nursery?.home?.kittens]
  )
  const yourCatteryPoint = useMemo(
    () => CATTERIES.find((cat) => cat.id === YOUR_CATTTERY_ID) || CATTERIES[0],
    []
  )
  const playerRole = state?.role

  const resolveCounterpartyContext = useCallback(
    (context = null) => {
      const typeSource = context?.counterpartyType || selectedBuilding?.type || null
      const idSource = context?.counterpartyId ?? selectedBuilding?.id ?? null
      if (!typeSource) return { counterpartyType: null, counterpartyId: null }
      const counterpartyType =
        typeSource === 'shop' || typeSource === 'cattery' ? typeSource : null
      const counterpartyId = Number.isFinite(Number(idSource))
        ? Number(idSource)
        : null
      return { counterpartyType, counterpartyId }
    },
    [selectedBuilding?.id, selectedBuilding?.type]
  )

  const loadData = useCallback(async () => {
    if (!sessionId) return
    try {
      setError('')
      const { counterpartyType, counterpartyId } = resolveCounterpartyContext()
      const [st, mk] = await Promise.all([
        api.getGameState(sessionId, season, counterpartyType, counterpartyId),
        api.getMarket(sessionId, season, counterpartyType, counterpartyId),
      ])
      setState(st)
      setMarket(mk?.market || mk)
    } catch (err) {
      setError(err.message || 'Failed to load state')
    }
  }, [sessionId, season, resolveCounterpartyContext])

  useEffect(() => {
    loadData()
  }, [loadData])

  useEffect(() => {
    setTimeLeft(SEASON_SECONDS[season] || 300)
    setAutoFinishing(false)
    setAutoAdvanceAfterResult(false)
    setConfirmEndOpen(false)
    setNursery((prev) => ({ ...prev, coins: NURSERY_SEASON_START_COINS }))
  }, [season])

  useEffect(() => {
    if (season !== 1 || !sessionId) {
      setWelcomeOpen(false)
      return
    }
    if (typeof window === 'undefined') return
    const key = `bc_welcome_seen_${sessionId}`
    const wasSeen = window.localStorage.getItem(key) === '1'
    setWelcomeOpen(!wasSeen)
  }, [season, sessionId])

  const handleWelcomeClose = useCallback(() => {
    setWelcomeOpen(false)
    if (season !== 1 || !sessionId || typeof window === 'undefined') return
    const key = `bc_welcome_seen_${sessionId}`
    window.localStorage.setItem(key, '1')
  }, [season, sessionId])

  useEffect(() => {
    const timer = setInterval(() => {
      setTimeLeft((prev) => Math.max(0, prev - 1))
    }, 1000)
    return () => clearInterval(timer)
  }, [season])

  const openOverlay = (type, id) => {
    if (type === 'cattery' && id === YOUR_CATTTERY_ID) {
      setNurseryOpen(true)
      return
    }
    setOverlayType(type)
    setSelectedBuilding({ type, id })
  }

  const closeOverlay = () => {
    setOverlayType(null)
    setSelectedBuilding(null)
  }

  const handleTrade = async (action, catType, qty, sex = null, context = null) => {
    try {
      setBusy(true)
      setError('')
      const normalizedColor = normalizeColor(catType)
      const normalizedSex = normalizeSex(sex)
      const { counterpartyType, counterpartyId } = resolveCounterpartyContext(context)
      const res = await api.trade({
        sessionId,
        seasonNumber: season,
        action,
        catType: normalizedColor,
        catSex: normalizedSex,
        counterpartyType,
        counterpartyId,
        qty,
      })
      if (!res.ok) throw new Error(res.error || 'Trade failed')
      setState(res.state)
      setNursery((prev) => {
        if (action === 'buy') {
          const additions = Array.from({ length: qty }, (_, idx) =>
            createBoughtKitten(normalizedColor, normalizedSex, idx)
          )
          return { ...prev, cats: [...(prev.cats || []), ...additions] }
        }
        if (action === 'sell') {
          const assigned = new Set()
          prev?.home?.parents?.left?.forEach((id) => id && assigned.add(id))
          prev?.home?.parents?.right?.forEach((id) => id && assigned.add(id))

          let remaining = qty
          const nextHomeKittens = (prev?.home?.kittens || []).map((cat) => {
            if (!cat || remaining <= 0) return cat
            const colorMatch = normalizeColor(cat?.color) === normalizedColor
            const sexMatch = normalizedSex ? normalizeSex(cat?.sex) === normalizedSex : true
            const sellableKitten =
              cat?.isKitten &&
              !assigned.has(cat.id) &&
              !cat.locked &&
              !cat.hungry
            if (sellableKitten && colorMatch && sexMatch) {
              remaining -= 1
              return null
            }
            return cat
          })
          const nextCats = []
          ;(prev.cats || []).forEach((cat) => {
            const colorMatch = normalizeColor(cat?.color) === normalizedColor
            const sexMatch = normalizedSex ? normalizeSex(cat?.sex) === normalizedSex : true
            const sellableKitten =
              cat?.isKitten &&
              !assigned.has(cat.id) &&
              !cat.locked &&
              !cat.hungry
            if (remaining > 0 && sellableKitten && colorMatch && sexMatch) {
              remaining -= 1
              return
            }
            nextCats.push(cat)
          })
          return {
            ...prev,
            cats: nextCats,
            home: {
              ...prev.home,
              kittens: nextHomeKittens,
            },
          }
        }
        return prev
      })
    } catch (err) {
      setError(err.message || 'Trade failed')
    } finally {
      setBusy(false)
    }
  }

  const handleCreditTake = async (creditType, amount) => {
    try {
      setBusy(true)
      setError('')
      const res = await api.creditTake({
        sessionId,
        seasonNumber: season,
        creditType,
        amount,
      })
      if (!res.ok) throw new Error(res.error || 'Credit take failed')
      setState(res.state)
    } catch (err) {
      setError(err.message || 'Credit take failed')
    } finally {
      setBusy(false)
    }
  }

  const handleCreditRepay = async (amount) => {
    try {
      setBusy(true)
      setError('')
      const res = await api.creditRepay({
        sessionId,
        seasonNumber: season,
        amount,
      })
      if (!res.ok) throw new Error(res.error || 'Credit repay failed')
      setState(res.state)
    } catch (err) {
      setError(err.message || 'Credit repay failed')
    } finally {
      setBusy(false)
    }
  }

  const handleEndSeason = useCallback(async ({ auto = false, finishEarly = false } = {}) => {
    try {
      setBusy(true)
      if (auto) {
        setAutoFinishing(true)
        setAutoAdvanceAfterResult(true)
      } else {
        setAutoAdvanceAfterResult(false)
      }
      if (Number(nursery?.coins ?? 0) < 3) {
        setLoseOpen(true)
        setAutoFinishing(false)
        return
      }
      setNursery((prev) => {
        let cats = prev.cats.map((c) => ({ ...c }))
        let coins = Math.max(0, Number(prev.coins ?? 0) - 3)
        // escape hungry or sick (all yard cats)
        cats = cats.filter((c) => !c.hungry && !c.sick)
        // kittens without home escape + seasonal escape for hungry/sick kittens
        let kittens = prev.hasHome
          ? prev.home.kittens.map((k) => (k ? { ...k } : null))
          : Array(12).fill(null)
        if (prev.hasHome) {
          kittens = kittens.map((k) => (k && !k.hungry && !k.sick ? k : null))
        }
        // age +1 and reset seasonal flags
        cats = cats.map((c) => ({
          ...c,
          age: c.age + 1,
          hungry: true,
          fedThisSeason: false,
          locked: false,
        }))
        // grow kittens
        const grown = []
        const nextKittens = kittens.map((k) => {
          if (!k) return null
          const next = { ...k, age: Number(k.age ?? 0) + 1, hungry: true, fedThisSeason: false }
          if (next.age >= 3) {
            grown.push({ ...next, hungry: true, fedThisSeason: false, isKitten: false })
            return null
          }
          return next
        })
        cats = [...cats, ...grown]
        // apply births
        const spawn = []
        const addBabies = (colorA, colorB) => {
          const base = Date.now()
          spawn.push(
            { id: `k${base}a`, sex: 'M', color: colorA },
            { id: `k${base}b`, sex: 'M', color: colorA },
            { id: `k${base}c`, sex: 'F', color: colorA },
            { id: `k${base}d`, sex: 'M', color: colorB },
            { id: `k${base}e`, sex: 'M', color: colorB },
            { id: `k${base}f`, sex: 'F', color: colorB }
          )
        }
        const catsById = Object.fromEntries(cats.map((c) => [c.id, c]))
        if (prev.home.breedPending.left) {
          const [leftA, leftB] = prev.home.parents.left
          const parentA = catsById[leftA]
          const parentB = catsById[leftB]
          addBabies(
            normalizeColor(parentA?.color || 'black'),
            normalizeColor(parentB?.color || 'white')
          )
        }
        if (prev.home.breedPending.right) {
          const [rightA, rightB] = prev.home.parents.right
          const parentA = catsById[rightA]
          const parentB = catsById[rightB]
          addBabies(
            normalizeColor(parentA?.color || 'gray'),
            normalizeColor(parentB?.color || 'ginger')
          )
        }
        spawn.forEach((b) => {
          const idx = nextKittens.findIndex((k) => !k)
          if (idx >= 0) nextKittens[idx] = { ...b, age: 0, hungry: true, fedThisSeason: false, isKitten: true }
        })
        return {
          ...prev,
          coins,
          cats,
          home: {
            ...prev.home,
            kittens: nextKittens,
            breedPending: { left: false, right: false },
          },
          insuranceActive: prev.insuranceNext,
          insuranceNext: false,
        }
      })
      const res = await api.finishSeason(sessionId, season, finishEarly)
      setConfirmEndOpen(false)
      setSeasonResult(res || null)
    } catch (err) {
      setError(err.message || 'Failed to finish season')
      setAutoFinishing(false)
      setAutoAdvanceAfterResult(false)
    } finally {
      setBusy(false)
    }
  }, [nursery?.coins, season, sessionId])

  useEffect(() => {
    if (timeLeft !== 0) return
    if (busy || confirmEndOpen || seasonResult || loseOpen || autoFinishing) return
    handleEndSeason({ auto: true, finishEarly: false })
  }, [timeLeft, busy, confirmEndOpen, seasonResult, loseOpen, autoFinishing, handleEndSeason])

  useEffect(() => {
    if (!autoAdvanceAfterResult || !seasonResult) return
    const timer = setTimeout(() => {
      const next = seasonResult?.nextSeason?.number
      setSeasonResult(null)
      setAutoAdvanceAfterResult(false)
      setAutoFinishing(false)
      if (next) {
        navigate(`/play/${sessionId}/${next}`)
        return
      }
      loadData()
    }, 1800)
    return () => clearTimeout(timer)
  }, [autoAdvanceAfterResult, seasonResult, navigate, sessionId, loadData])

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return `00:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  }

  return (
    <div className="mapRoot">
      <div className="mapScene">
        <div className="mapTopbar">
          <div className="topbar-left">
            <div className="topbar-coins">
              <span className="coin" />
              <span>{coinsNow}</span>
            </div>
          </div>
          <div className="topbar-center">
            <div className="topbar-season">{season} СЕЗОН</div>
            <div className="topbar-timer">{formatTime(timeLeft)}</div>
          </div>
          <div className="topbar-right">
            <button
              className="topbar-btn topbar-btn--exit"
              onClick={() => navigate('/sessions')}
            >
              ⟵
            </button>
            <button
              className="topbar-btn topbar-btn--end"
              onClick={() => setConfirmEndOpen(true)}
            >
              ЗАВЕРШИТЬ СЕЗОН
            </button>
          </div>
        </div>

        <div className="mapLabel mapLabelShops">Зоомагазины</div>
        <div className="mapLabel mapLabelCatteries">Питомники</div>

        {PETSHOPS.map((shop) => (
          <button
            className="mapBuilding shopBuilding"
            key={`shop-${shop.id}`}
            style={{ left: `${shop.left}%`, top: `${shop.top}%` }}
            onClick={() => openOverlay('shop', shop.id)}
            type="button"
          >
            <img
              src={`/assets/building-petshop${shop.id}.png`}
              alt={`petshop ${shop.id}`}
              onError={imgFallback}
            />
            <span className="mapBadge">#{shop.id}</span>
          </button>
        ))}

        {CATTERIES.map((cat) => {
          const isYours = cat.id === YOUR_CATTTERY_ID
          return (
            <button
              className={`mapBuilding catteryBuilding ${isYours ? 'yourCattery' : ''}`}
              key={`cattery-${cat.id}`}
              style={{ left: `${cat.left}%`, top: `${cat.top}%` }}
              onClick={() => openOverlay('cattery', cat.id)}
              type="button"
            >
              <img
                src={`/assets/building-cattery${cat.id}.png`}
                alt={`cattery ${cat.id}`}
                onError={imgFallback}
              />
              {isYours ? (
                <>
                  <img
                    className="yourMarker"
                    src="/assets/cattery-your.png"
                    alt="your cattery"
                    onError={imgFallback}
                  />
                  <span className="yourLabel">ТВОЙ ПИТОМНИК</span>
                </>
              ) : null}
              <span className="mapBadge">#{cat.id}</span>
            </button>
          )
        })}

        {mapNurseryCats.length ? (
          <div
            className="yourNurseryCats"
            style={{
              left: `${yourCatteryPoint.left + 9}%`,
              top: `${yourCatteryPoint.top - 6}%`,
            }}
          >
            {mapNurseryCats.map((cat) => (
              <div key={cat.id} className="yourNurseryCats__item">
                <img src={getMapCatSprite(cat)} alt={`${cat.color} kitten`} />
              </div>
            ))}
          </div>
        ) : null}

        <img
          className="mapTree mapTreeLeft"
          src="/assets/treelefts.png"
          alt="tree left"
          onError={imgFallback}
        />
        <img
          className="mapTree mapTreeRight"
          src="/assets/treerights.png"
          alt="tree right"
          onError={imgFallback}
        />
      </div>

      <ShopOverlay
        open={overlayType === 'shop'}
        onClose={closeOverlay}
        buildingId={selectedBuilding?.id}
        seasonNumber={season}
        coinsNow={coinsNow}
        debtTotal={debtTotal}
        debtRate={debtRate}
        inventory={inventory}
        inventoryEntities={inventoryEntities}
        market={market || {}}
        playerRole={playerRole}
        busy={busy}
        error={error}
        onTrade={handleTrade}
        onCreditTake={handleCreditTake}
        onCreditRepay={handleCreditRepay}
      />

      <CatteryOverlay
        open={overlayType === 'cattery'}
        onClose={closeOverlay}
        buildingId={selectedBuilding?.id}
        seasonNumber={season}
        coinsNow={coinsNow}
        debtTotal={debtTotal}
        debtRate={debtRate}
        inventory={inventory}
        inventoryEntities={inventoryEntities}
        market={market || {}}
        playerRole={playerRole}
        busy={busy}
        error={error}
        onTrade={handleTrade}
        onCreditTake={handleCreditTake}
        onCreditRepay={handleCreditRepay}
      />

      <ConfirmEndSeasonModal
        open={confirmEndOpen}
        onConfirm={() => handleEndSeason({ auto: false, finishEarly: true })}
        onCancel={() => setConfirmEndOpen(false)}
      />

      <LoseModal
        open={loseOpen}
        onConfirm={() => navigate('/sessions')}
      />

      <SeasonResultModal
        open={Boolean(seasonResult)}
        result={seasonResult?.seasonResult}
        nextSeason={seasonResult?.nextSeason}
        onConfirm={() => {
          setAutoAdvanceAfterResult(false)
          setAutoFinishing(false)
          const next = seasonResult?.nextSeason?.number
          setSeasonResult(null)
          if (next) {
            navigate(`/play/${sessionId}/${next}`)
            return
          }
          loadData()
        }}
      />

      <MyNurseryOverlay
        open={nurseryOpen}
        onClose={() => setNurseryOpen(false)}
        nursery={nursery}
        setNursery={setNursery}
        seasonNumber={season}
        coinsNow={coinsNow}
        timerText={formatTime(timeLeft)}
        onRequestEndSeason={() => setConfirmEndOpen(true)}
        onExitPlatform={() => navigate('/sessions')}
      />

      <WelcomeStartModal
        open={welcomeOpen}
        onClose={handleWelcomeClose}
        playerName="Леопольд"
      />
    </div>
  )
}

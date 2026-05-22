import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api.js'
import ShopOverlay from '../components/ShopOverlay.jsx'
import CatteryOverlay from '../components/CatteryOverlay.jsx'
import ConfirmEndSeasonModal from '../components/ConfirmEndSeasonModal.jsx'
import MyNurseryOverlay from '../components/MyNurseryOverlay.jsx'
import LoseModal from '../components/LoseModal.jsx'
import SeasonResultModal from '../components/SeasonResultModal.jsx'
import WelcomeStartModal from '../components/WelcomeStartModal.jsx'
import RequestsSidebar from '../components/RequestsSidebar.jsx'
import RequestModal from '../components/RequestModal.jsx'
import TradeSendModal from '../components/TradeSendModal.jsx'
import './PlayMapPage.css'

const PETSHOPS = [
  { id: 1, left: 38.5, top: 25, name: 'Бонифаций' },
  { id: 2, left: 50.5, top: 25, name: 'Полосатый' },
  { id: 3, left: 62.5, top: 25, name: 'Любимец' },
  { id: 4, left: 74.5, top: 25, name: 'Мурзик' },
  { id: 5, left: 86.5, top: 25, name: 'Зооцентр' },
]

const CATTERIES = [
  { id: 1, left: 25, top: 42.5 },
  { id: 2, left: 37.5, top: 42.5 },
  { id: 3, left: 50, top: 42.5 },
  { id: 4, left: 62.5, top: 42.5 },
  { id: 5, left: 75, top: 42.5 },
  { id: 6, left: 25, top: 57.5 },
  { id: 7, left: 37.5, top: 57.5 },
  { id: 8, left: 50, top: 57.5 },
  { id: 9, left: 62.5, top: 57.5 },
  { id: 10, left: 75, top: 57.5 },
  { id: 11, left: 25, top: 72.5 },
  { id: 12, left: 37.5, top: 72.5 },
  { id: 13, left: 50, top: 72.5 },
  { id: 14, left: 62.5, top: 72.5 },
  { id: 15, left: 75, top: 72.5 },
  { id: 16, left: 25, top: 87.5 },
  { id: 17, left: 37.5, top: 87.5 },
  { id: 18, left: 50, top: 87.5 },
  { id: 19, left: 62.5, top: 87.5 },
  { id: 20, left: 75, top: 87.5 },
]

const YOUR_CATTTERY_ID = 1
const VALID_SEX = new Set(['M', 'F'])
const TRACKED_INVENTORY_COLORS = ['white', 'black', 'gray', 'ginger']
const DEFAULT_ADULT_AGE = 2
const DISEASE_TYPES = ['RINGWORM', 'FLEAS', 'POISONING', 'BROKEN_PAW']
const DISEASE_CHANCE = 0.2
const LEGACY_DISEASE_MAP = {
  lichen: 'RINGWORM',
  fleas: 'FLEAS',
  poisoning: 'POISONING',
  brokenpaw: 'BROKEN_PAW',
}
const COLOR_ALIAS = {
  orange: 'ginger',
}
const MAP_CAT_SPRITES = {
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

const normalizeDiseaseType = (value) => {
  const normalized = String(value ?? '')
    .trim()
    .toUpperCase()
  if (DISEASE_TYPES.includes(normalized)) return normalized
  return LEGACY_DISEASE_MAP[String(value ?? '').trim().toLowerCase()] || null
}

const resolveDiseaseState = (cat) => {
  const diseaseType = normalizeDiseaseType(cat?.diseaseType ?? cat?.sick)
  const rawHealthStatus = String(cat?.healthStatus ?? '').trim().toUpperCase()
  const healedAtSeasonValue = Number(cat?.healedAtSeason)
  const healedAtSeason = Number.isFinite(healedAtSeasonValue) ? Math.max(0, Math.floor(healedAtSeasonValue)) : null
  if (rawHealthStatus === 'HEALED') {
    return {
      isSick: false,
      diseaseType: null,
      healthStatus: 'HEALED',
      healedAtSeason,
    }
  }
  const isSick = Boolean(cat?.isSick) || diseaseType != null || rawHealthStatus === 'SICK'
  if (isSick) {
    return {
      isSick: true,
      diseaseType,
      healthStatus: 'SICK',
      healedAtSeason,
    }
  }
  return {
    isSick: false,
    diseaseType: null,
    healthStatus: 'HEALTHY',
    healedAtSeason,
  }
}

const isNurseryCatSick = (cat) => resolveDiseaseState(cat).isSick

const randomDisease = (rng = Math.random) => {
  const safeRng = typeof rng === 'function' ? rng : Math.random
  const index = Math.max(0, Math.min(DISEASE_TYPES.length - 1, Math.floor(safeRng() * DISEASE_TYPES.length)))
  return DISEASE_TYPES[index]
}

const maybeCreateBirthDisease = (rng = Math.random) => {
  const safeRng = typeof rng === 'function' ? rng : Math.random
  if (safeRng() >= DISEASE_CHANCE) {
    return {
      isSick: false,
      diseaseType: null,
      healthStatus: 'HEALTHY',
      healedAtSeason: null,
    }
  }
  return {
    isSick: true,
    diseaseType: randomDisease(safeRng),
    healthStatus: 'SICK',
    healedAtSeason: null,
  }
}

const resolveKittenStatus = (cat, adultAge = DEFAULT_ADULT_AGE) => {
  const age = Number(cat?.age ?? cat?.ageSeasons)
  if (Number.isFinite(age)) return age < adultAge
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
  if (typeof cat?.isKitten === 'boolean') return cat.isKitten
  return null
}

const getMapCatSprite = (cat, adultAge = DEFAULT_ADULT_AGE) => {
  const color = normalizeColor(cat?.color)
  const sex = normalizeSex(cat?.sex) || 'M'
  const isAdult = !resolveKittenStatus(cat, adultAge)
  const lifeStage = isAdult ? 'adult' : 'kitten'
  const stageSprites = MAP_CAT_SPRITES[lifeStage] || MAP_CAT_SPRITES.kitten
  const sexSprites = stageSprites[sex] || stageSprites.M
  const colorSprites = sexSprites[color] || sexSprites.gray
  if (!colorSprites) return '/assets/cats/male-gray-small.png'
  if (cat?.hungry) return colorSprites.hungry || colorSprites.default
  return colorSprites.default || colorSprites.hungry
}

const createBoughtKitten = (color, sex, idx = 0) => ({
  id: `buy-${Date.now()}-${idx}-${Math.random().toString(16).slice(2, 7)}`,
  sex: normalizeSex(sex) || (Math.random() > 0.5 ? 'M' : 'F'),
  color: normalizeColor(color),
  age: 0,
  hungry: true,
  fedThisSeason: false,
  locked: false,
  isKitten: true,
  isSick: false,
  diseaseType: null,
  healthStatus: 'HEALTHY',
  healedAtSeason: null,
})

const COLOR_LABEL_RU = {
  white: 'белый',
  black: 'черный',
  gray: 'серый',
  ginger: 'рыжий',
}

const SEX_LABEL_RU = {
  M: 'мальчик',
  F: 'девочка',
}

const describeEscapedHungryCat = (cat) => {
  const sex = normalizeSex(cat?.sex) || 'M'
  const color = normalizeColor(cat?.color) || 'gray'
  const role = resolveKittenStatus(cat) ? 'котенок' : sex === 'F' ? 'кошка' : 'кот'
  const colorLabel = COLOR_LABEL_RU[color] || color
  const sexLabel = SEX_LABEL_RU[sex] || sex
  const shortId = String(cat?.id ?? '').slice(0, 6) || '------'
  const escapeReason = String(cat?.escapeReason || '').trim().toUpperCase()
  const suffix =
    escapeReason === 'SICK_UNTREATED'
      ? ' • сбежал из-за болезни'
      : escapeReason === 'OUTSIDE_HOME'
        ? ' • вне домика'
        : ''
  return `${role} (${colorLabel}, ${sexLabel}) #${shortId}${suffix}`
}

export const buildSeasonTransition = (
  prevNursery,
  adultAge = DEFAULT_ADULT_AGE,
  { rng = Math.random } = {}
) => {
  const prev = normalizeNurseryState(prevNursery, adultAge)
  const prevHomes = Array.isArray(prev?.homes) ? prev.homes : []
  const persistedEscapedIds = new Set(
    (Array.isArray(prev?.escapedCatIds) ? prev.escapedCatIds : [])
      .map((id) => (id == null ? null : String(id)))
      .filter(Boolean)
  )
  const homeParentIds = new Set(
    prevHomes
      .flatMap((home) =>
        ['left', 'right'].flatMap((side) => (Array.isArray(home?.parents?.[side]) ? home.parents[side] : []))
      )
      .map((id) => (id == null ? null : String(id)))
      .filter(Boolean)
  )
  const homeKittenIds = new Set(
    prevHomes
      .flatMap((home) => (Array.isArray(home?.kittens) ? home.kittens : []))
      .filter(Boolean)
      .map((cat) => (cat?.id == null ? null : String(cat.id)))
      .filter(Boolean)
  )
  const protectedIds = new Set([...homeParentIds, ...homeKittenIds])
  const escapedById = new Map()
  const escapedSickKittens = []
  const bornSickKittens = []
  const markEscaped = (cat) => {
    if (!cat || !cat.id) return
    const id = String(cat.id)
    if (protectedIds.has(id) || escapedById.has(id)) return
    escapedById.set(id, { ...cat, id, status: 'ESCAPED', isEscaped: true, escapeReason: 'OUTSIDE_HOME' })
  }

  const prevCats = Array.isArray(prev?.cats) ? prev.cats : []
  prevCats.forEach(markEscaped)
  if (!prevHomes.length) {
    prevHomes
      .flatMap((home) => (Array.isArray(home?.kittens) ? home.kittens : []))
      .forEach((cat) => cat && markEscaped(cat))
  }

  const escapedIds = new Set(escapedById.keys())
  const escapedCatIdsSet = new Set([...persistedEscapedIds, ...escapedIds])
  const escapedCatIds = Array.from(escapedCatIdsSet)
  let coins = Math.max(0, Number(prev.coins ?? 0) - 3)

  if (!prevHomes.length) {
    return {
      nursery: withNurseryHomeMirrors({
        ...prev,
        coins,
        cats: [],
        homes: [],
        activeHomeIndex: 0,
        escapedCatIds,
      }),
      escapedHungryCats: Array.from(escapedById.values()),
      escapedSickKittens: [],
      bornSickKittens: [],
    }
  }

  let cats = prevCats
    .map((cat) => ({ ...cat }))
    .filter((cat) => !escapedCatIdsSet.has(String(cat?.id ?? '')))

  cats = cats.map((cat) => {
    const nextAge = Number(cat.age ?? 0) + 1
    const staysKitten = resolveKittenStatus(cat, adultAge) && nextAge < adultAge
    return {
      ...cat,
      age: nextAge,
      isKitten: staysKitten,
      hungry: true,
      fedThisSeason: false,
      locked: false,
      ...resolveDiseaseState(cat),
    }
  })

  const base = Date.now()
  let birthSeq = 0
  const catsById = Object.fromEntries(cats.map((cat) => [cat.id, cat]))
  const createBaby = (homeId, side, sex, color) => ({
    id: `born-${base}-${homeId}-${side}-${birthSeq++}-${Math.random().toString(16).slice(2, 6)}`,
    sex,
    color: normalizeColor(color),
  })

  const nextHomes = prevHomes.map((home, homeIndex) => {
    const normalizeParentSide = (side) =>
      [0, 1].map((idx) => {
        const id = home?.parents?.[side]?.[idx]
        if (id == null) return null
        const normalizedId = String(id)
        return escapedCatIdsSet.has(normalizedId) ? null : normalizedId
      })

    const nextParents = {
      left: normalizeParentSide('left'),
      right: normalizeParentSide('right'),
    }

    const grown = []
    const nextKittens = Array.from({ length: 12 }, (_, idx) => {
      const kitten = home?.kittens?.[idx]
      return kitten ? { ...kitten } : null
    }).map((kitten) => {
      if (!kitten) return null
      if (escapedCatIdsSet.has(String(kitten.id))) return null
      if (isNurseryCatSick(kitten)) {
        const escaped = {
          ...kitten,
          status: 'ESCAPED',
          isEscaped: true,
          escapeReason: 'SICK_UNTREATED',
        }
        const escapedId = String(kitten.id)
        escapedById.set(escapedId, escaped)
        escapedCatIdsSet.add(escapedId)
        escapedSickKittens.push(escaped)
        return null
      }
      const next = {
        ...kitten,
        age: Number(kitten.age ?? 0) + 1,
        hungry: true,
        fedThisSeason: false,
        ...resolveDiseaseState(kitten),
      }
      if (next.age >= adultAge) {
        grown.push({ ...next, hungry: true, fedThisSeason: false, isKitten: false })
        return null
      }
      return next
    })
    if (grown.length) {
      cats = [...cats, ...grown]
      grown.forEach((cat) => {
        catsById[cat.id] = cat
      })
    }

    const spawnBySide = { left: [], right: [] }
    const addBabies = (side, colorA, colorB) => {
      const homeId = String(home.id || `home-${homeIndex + 1}`)
      spawnBySide[side].push(
        createBaby(homeId, side, 'M', colorA),
        createBaby(homeId, side, 'M', colorA),
        createBaby(homeId, side, 'F', colorA),
        createBaby(homeId, side, 'M', colorB),
        createBaby(homeId, side, 'M', colorB),
        createBaby(homeId, side, 'F', colorB)
      )
    }

    if (home?.breedPending?.left) {
      const [leftA, leftB] = nextParents.left
      const parentA = leftA ? catsById[leftA] : null
      const parentB = leftB ? catsById[leftB] : null
      if (parentA && parentB) {
        addBabies(
          'left',
          normalizeColor(parentA?.color || 'black'),
          normalizeColor(parentB?.color || 'white')
        )
      }
    }
    if (home?.breedPending?.right) {
      const [rightA, rightB] = nextParents.right
      const parentA = rightA ? catsById[rightA] : null
      const parentB = rightB ? catsById[rightB] : null
      if (parentA && parentB) {
        addBabies(
          'right',
          normalizeColor(parentA?.color || 'gray'),
          normalizeColor(parentB?.color || 'ginger')
        )
      }
    }

    const placeBySide = (side, from, to) => {
      spawnBySide[side].forEach((baby) => {
        const slice = nextKittens.slice(from, to)
        const slot = slice.findIndex((kitten) => !kitten)
        if (slot < 0) return
        const diseaseState = maybeCreateBirthDisease(rng)
        const nextBaby = {
          ...baby,
          age: 0,
          hungry: false,
          fedThisSeason: true,
          isKitten: true,
          locked: false,
          ...diseaseState,
        }
        nextKittens[from + slot] = { ...nextBaby }
        if (nextBaby.isSick) {
          bornSickKittens.push(nextBaby)
        }
      })
    }

    placeBySide('left', 0, 6)
    placeBySide('right', 6, 12)

    return {
      ...createDefaultHome(home.number || homeIndex + 1),
      ...home,
      id: String(home.id || `home-${homeIndex + 1}`),
      number: Math.max(1, Number(home.number || homeIndex + 1) || homeIndex + 1),
      parents: nextParents,
      kittens: nextKittens,
      breedPending: { left: false, right: false },
      lastBreedSeason: {
        left: normalizeSeasonNumber(home?.lastBreedSeason?.left, 0),
        right: normalizeSeasonNumber(home?.lastBreedSeason?.right, 0),
      },
      insuranceActive: Boolean(home?.insuranceNext),
      insuranceNext: false,
    }
  })

  return {
    nursery: withNurseryHomeMirrors({
      ...prev,
      coins,
      cats,
      homes: nextHomes,
      escapedCatIds: Array.from(escapedCatIdsSet),
      activeHomeIndex: clampHomeIndex(prev.activeHomeIndex, nextHomes.length),
    }),
    escapedHungryCats: Array.from(escapedById.values()),
    escapedSickKittens,
    bornSickKittens,
  }
}

const HOME_KITTEN_SLOTS = 12

const createDefaultHome = (number = 1) => ({
  id: `home-${Math.max(1, Number(number) || 1)}`,
  number: Math.max(1, Number(number) || 1),
  insuranceActive: false,
  insuranceNext: false,
  parents: { left: [null, null], right: [null, null] },
  kittens: Array(HOME_KITTEN_SLOTS).fill(null),
  breedPending: { left: false, right: false },
  lastBreedSeason: { left: 0, right: 0 },
})

const clampHomeIndex = (value, totalHomes) => {
  const count = Math.max(0, Number(totalHomes) || 0)
  if (count <= 0) return 0
  const normalized = Number(value)
  if (!Number.isFinite(normalized)) return 0
  return Math.min(count - 1, Math.max(0, Math.floor(normalized)))
}

const hasLegacyHomeState = (home) => {
  if (!home || typeof home !== 'object') return false
  const leftParents = Array.isArray(home?.parents?.left) ? home.parents.left : []
  const rightParents = Array.isArray(home?.parents?.right) ? home.parents.right : []
  const kittens = Array.isArray(home?.kittens) ? home.kittens : []
  if (leftParents.some((id) => id != null) || rightParents.some((id) => id != null)) return true
  if (kittens.some(Boolean)) return true
  if (Boolean(home?.breedPending?.left) || Boolean(home?.breedPending?.right)) return true
  if (Number(home?.lastBreedSeason?.left) > 0 || Number(home?.lastBreedSeason?.right) > 0) return true
  return false
}

const withNurseryHomeMirrors = (nursery) => {
  const base = createDefaultNursery()
  const source = nursery && typeof nursery === 'object' ? nursery : {}
  const homes = Array.isArray(source.homes) ? source.homes : []
  const activeHomeIndex = clampHomeIndex(source.activeHomeIndex, homes.length)
  const activeHome = homes[activeHomeIndex] ? { ...homes[activeHomeIndex] } : createDefaultHome(1)
  return {
    ...base,
    ...source,
    homes,
    activeHomeIndex,
    hasHome: homes.length > 0,
    insuranceActive: homes.length > 0 ? Boolean(activeHome.insuranceActive) : false,
    insuranceNext: homes.length > 0 ? Boolean(activeHome.insuranceNext) : false,
    home: activeHome,
  }
}

const createDefaultNursery = () => ({
  coins: 0,
  coinsSynced: false,
  hasHome: false,
  insuranceActive: false,
  insuranceNext: false,
  cats: [],
  escapedCatIds: [],
  homes: [],
  activeHomeIndex: 0,
  home: createDefaultHome(1),
})

const createDefaultSeasonLedger = (seasonNumber = 1, startCoins = 0) => ({
  seasonNumber: normalizeSeasonNumber(seasonNumber, 1),
  startCoins: Math.max(0, Number(startCoins) || 0),
  homeExpenses: 0,
  feedExpenses: 0,
  insuranceExpenses: 0,
  treatmentExpenses: 0,
})

const normalizeSeasonLedger = (rawLedger, seasonNumber, fallbackStartCoins = 0) => {
  const base = createDefaultSeasonLedger(seasonNumber, fallbackStartCoins)
  if (!rawLedger || typeof rawLedger !== 'object') return base
  return {
    seasonNumber: normalizeSeasonNumber(rawLedger.seasonNumber, base.seasonNumber),
    startCoins: Math.max(0, Number(rawLedger.startCoins ?? base.startCoins) || 0),
    homeExpenses: Math.max(0, Number(rawLedger.homeExpenses) || 0),
    feedExpenses: Math.max(0, Number(rawLedger.feedExpenses) || 0),
    insuranceExpenses: Math.max(0, Number(rawLedger.insuranceExpenses) || 0),
    treatmentExpenses: Math.max(0, Number(rawLedger.treatmentExpenses) || 0),
  }
}

export const buildNextSeasonProgressPayload = ({
  nursery,
  adultAge = DEFAULT_ADULT_AGE,
  nextSeasonNumber,
  nextSeasonCoins,
  targetDuration,
}) => {
  const normalizedCoins = Math.max(0, Number(nextSeasonCoins) || 0)
  const normalizedSeason = normalizeSeasonNumber(nextSeasonNumber, 1)
  const normalizedNursery = normalizeNurseryState(
    {
      ...normalizeNurseryState(nursery, adultAge),
      coins: normalizedCoins,
      coinsSynced: true,
    },
    adultAge
  )
  return {
    nursery: normalizedNursery,
    seasonLedger: createDefaultSeasonLedger(normalizedSeason, normalizedCoins),
    nurseryCoinsDelta: 0,
    timeLeft: targetDuration,
  }
}

const buildCombinedSeasonResult = ({
  backendResult,
  seasonLedger,
  actualCoinsEnd,
  escapedCats,
}) => {
  const coinsStart = Math.max(
    0,
    Number(
      seasonLedger?.startCoins ??
      backendResult?.coinsStart ??
      backendResult?.coins_begin ??
      0
    ) || 0
  )
  const salesProfit = Math.max(
    0,
    Number(
      backendResult?.salesProfit ??
      backendResult?.soldProfit ??
      backendResult?.sales ??
      0
    ) || 0
  )
  const backendCoinsEnd = Math.max(
    0,
    Number(
      backendResult?.coinsEnd ??
      backendResult?.coins_end ??
      0
    ) || 0
  )
  const keepBackendCoinsEnd =
    Boolean(backendResult?.terminal) ||
    backendCoinsEnd <= 0
  const coinsEnd = Math.max(
    0,
    Number(
      keepBackendCoinsEnd
        ? backendCoinsEnd
        : (
          actualCoinsEnd ??
          backendCoinsEnd
        ) ??
      0
    ) || 0
  )
  const tradeBuyTotal = Math.max(0, Number(backendResult?.tradeBuyTotal ?? 0) || 0)
  const utilityPaid = Math.max(0, Number(backendResult?.utilityPaid ?? 0) || 0)
  const interestPaid = Math.max(0, Number(backendResult?.interestPaid ?? 0) || 0)
  const homeExpenses = Math.max(0, Number(seasonLedger?.homeExpenses ?? 0) || 0)
  const feedExpenses = Math.max(0, Number(seasonLedger?.feedExpenses ?? 0) || 0)
  const insuranceExpenses = Math.max(0, Number(seasonLedger?.insuranceExpenses ?? 0) || 0)
  const treatmentExpenses = Math.max(0, Number(seasonLedger?.treatmentExpenses ?? 0) || 0)
  const creditDelta = Number(
    backendResult?.creditDelta ??
    (Number(backendResult?.creditsTaken ?? 0) || 0) - (Number(backendResult?.creditsRepaid ?? 0) || 0)
  ) || 0
  const explicitExpenses =
    tradeBuyTotal +
    utilityPaid +
    interestPaid +
    homeExpenses +
    feedExpenses +
    insuranceExpenses +
    treatmentExpenses
  const inferredExpenses = Math.max(
    0,
    coinsStart + salesProfit + creditDelta - coinsEnd
  )
  const untrackedExpenses = Math.max(0, inferredExpenses - explicitExpenses)
  const expenses = explicitExpenses + untrackedExpenses
  const profit = salesProfit - expenses
  return {
    ...backendResult,
    coinsStart,
    coinsEnd,
    salesProfit,
    escapedCats: Math.max(
      0,
      Number(backendResult?.escapedCats ?? escapedCats) || 0
    ),
    expenses,
    profit,
    creditDelta,
    expenseBreakdown: {
      tradeBuyTotal,
      utilityPaid,
      interestPaid,
      homeExpenses,
      feedExpenses,
      insuranceExpenses,
      treatmentExpenses,
      untrackedExpenses,
      inferredExpenses,
    },
  }
}

const normalizeSeasonNumber = (value, fallback = 0) => {
  const normalized = Number(value)
  if (!Number.isFinite(normalized)) return fallback
  return Math.max(0, Math.floor(normalized))
}

export const normalizeNurseryCat = (cat, { forceKitten = null, adultAge = DEFAULT_ADULT_AGE } = {}) => {
  if (!cat || typeof cat !== 'object') return null
  if (cat.id == null) return null
  const sex = normalizeSex(cat.sex) || 'M'
  const color = normalizeColor(cat.color || 'gray') || 'gray'
  const age = normalizeSeasonNumber(cat.age, 0)
  const resolvedKittenStatus = resolveKittenStatus(cat, adultAge)
  const isKitten =
    resolvedKittenStatus == null
      ? typeof forceKitten === 'boolean'
        ? forceKitten
        : false
      : resolvedKittenStatus
  const diseaseState = resolveDiseaseState(cat)

  return {
    ...cat,
    id: String(cat.id),
    sex,
    color,
    age,
    isKitten,
    hungry: Boolean(cat.hungry),
    fedThisSeason: Boolean(cat.fedThisSeason),
    locked: Boolean(cat.locked),
    ...diseaseState,
  }
}

const normalizeHomeState = (home, index, catsById, escapedCatIdsSet, adultAge = DEFAULT_ADULT_AGE) => {
  const base = createDefaultHome(index + 1)
  const sourceHome = home && typeof home === 'object' ? home : {}
  const sourceKittens = Array.isArray(sourceHome.kittens) ? sourceHome.kittens : []
  const kittens = Array.from({ length: HOME_KITTEN_SLOTS }, (_, idx) => {
    const kitten = normalizeNurseryCat(sourceKittens[idx], { forceKitten: true, adultAge })
    if (!kitten) return null
    return escapedCatIdsSet.has(String(kitten.id)) ? null : kitten
  })

  const normalizeParentsSide = (side) => {
    const sourceSide = Array.isArray(sourceHome?.parents?.[side]) ? sourceHome.parents[side] : []
    return [0, 1].map((slotIdx) => {
      const id = sourceSide[slotIdx]
      if (id == null) return null
      const normalizedId = String(id)
      if (escapedCatIdsSet.has(normalizedId)) return null
      return catsById.has(normalizedId) ? normalizedId : null
    })
  }

  return {
    ...base,
    ...sourceHome,
    id: String(sourceHome.id || base.id),
    number: Math.max(1, Number(sourceHome.number || index + 1) || index + 1),
    insuranceActive: Boolean(sourceHome.insuranceActive),
    insuranceNext: Boolean(sourceHome.insuranceNext),
    parents: {
      left: normalizeParentsSide('left'),
      right: normalizeParentsSide('right'),
    },
    kittens,
    breedPending: {
      left: Boolean(sourceHome?.breedPending?.left),
      right: Boolean(sourceHome?.breedPending?.right),
    },
    lastBreedSeason: {
      left: normalizeSeasonNumber(sourceHome?.lastBreedSeason?.left, 0),
      right: normalizeSeasonNumber(sourceHome?.lastBreedSeason?.right, 0),
    },
  }
}

export const normalizeNurseryState = (rawNursery, adultAge = DEFAULT_ADULT_AGE) => {
  const defaults = createDefaultNursery()
  if (!rawNursery || typeof rawNursery !== 'object') return defaults

  const escapedCatIds = Array.from(
    new Set(
      (Array.isArray(rawNursery.escapedCatIds) ? rawNursery.escapedCatIds : [])
        .map((id) => (id == null ? null : String(id)))
        .filter(Boolean)
    )
  )
  const escapedCatIdsSet = new Set(escapedCatIds)
  const cats = (Array.isArray(rawNursery.cats) ? rawNursery.cats : [])
    .map((cat) => normalizeNurseryCat(cat, { adultAge }))
    .filter((cat) => !escapedCatIdsSet.has(String(cat?.id ?? '')))
    .filter(Boolean)
  const catsById = new Set(cats.map((cat) => cat.id))
  const sourceHomes =
    Array.isArray(rawNursery.homes) && rawNursery.homes.length
      ? rawNursery.homes
      : Boolean(
          rawNursery.hasHome ||
          rawNursery.insuranceActive ||
          rawNursery.insuranceNext ||
          hasLegacyHomeState(rawNursery.home)
        )
        ? [
            {
              ...(rawNursery.home && typeof rawNursery.home === 'object' ? rawNursery.home : {}),
              id: 'home-1',
              number: 1,
              insuranceActive: Boolean(rawNursery.insuranceActive),
              insuranceNext: Boolean(rawNursery.insuranceNext),
            },
          ]
        : []
  const homes = sourceHomes.map((home, index) =>
    normalizeHomeState(home, index, catsById, escapedCatIdsSet, adultAge)
  )

  return withNurseryHomeMirrors({
    ...defaults,
    ...rawNursery,
    coins: Math.max(0, Number(rawNursery.coins) || 0),
    coinsSynced: Boolean(rawNursery.coinsSynced),
    cats,
    escapedCatIds,
    homes,
    activeHomeIndex: clampHomeIndex(rawNursery.activeHomeIndex, homes.length),
  })
}

const clearStoredPlayProgress = (sessionId) => {
  if (typeof window === 'undefined' || !sessionId) return
  const prefix = `bc_play_progress_${sessionId}_`
  Object.keys(window.localStorage).forEach((key) => {
    if (key.startsWith(prefix)) {
      window.localStorage.removeItem(key)
    }
  })
}

const formatTradeRequestError = (value) => {
  const code = String(value ?? '')
    .trim()
    .toUpperCase()
  if (code === 'ONLY_KITTENS_CAN_BE_TRADED') {
    return 'Продавать можно только котят'
  }
  if (code === 'CAT_NOT_AVAILABLE') {
    return 'Котёнок уже недоступен для сделки'
  }
  if (code === 'CAT_ALREADY_SOLD') {
    return 'Котёнок уже продан'
  }
  if (code === 'BAD_RELATION' || code === 'LOW_TRUST' || code === 'NO_RELATION') {
    return 'Магазин не доверяет вам и отказывается покупать котят'
  }
  return String(value ?? '')
}

export default function PlayMapPage({ me }) {
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
  const seasonDuration = SEASON_SECONDS[season] || 300
  const progressStorageKey = `bc_play_progress_${sessionId}_${season}`

  const [state, setState] = useState(null)
  const [market, setMarket] = useState(null)
  const [overlayType, setOverlayType] = useState(null)
  const [selectedBuilding, setSelectedBuilding] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [timeLeft, setTimeLeft] = useState(seasonDuration)
  const [confirmEndOpen, setConfirmEndOpen] = useState(false)
  const [loseOpen, setLoseOpen] = useState(false)
  const [nurseryOpen, setNurseryOpen] = useState(false)
  const [seasonResult, setSeasonResult] = useState(null)
  const [autoFinishing, setAutoFinishing] = useState(false)
  const [autoAdvanceAfterResult, setAutoAdvanceAfterResult] = useState(false)
  const [seasonFinishedLocked, setSeasonFinishedLocked] = useState(false)
  const [welcomeOpen, setWelcomeOpen] = useState(false)
  const [tradeRequests, setTradeRequests] = useState([])
  const [activeRequest, setActiveRequest] = useState(null)
  const [tradeRequestsBusy, setTradeRequestsBusy] = useState(false)
  const [tradeSendModalRequest, setTradeSendModalRequest] = useState(null)
  const [catterySpectateData, setCatterySpectateData] = useState(null)
  const [escapedHungryCats, setEscapedHungryCats] = useState([])
  const [inactiveTimeoutModalOpen, setInactiveTimeoutModalOpen] = useState(false)
  const [pendingSeasonTransition, setPendingSeasonTransition] = useState(null)
  const [nursery, setNursery] = useState(createDefaultNursery)
  const [seasonLedger, setSeasonLedger] = useState(() => createDefaultSeasonLedger(1, 0))
  const [nurseryCoinsDelta, setNurseryCoinsDelta] = useState(0)
  const [progressHydrated, setProgressHydrated] = useState(false)
  const [playAccessResolved, setPlayAccessResolved] = useState(false)
  const [playAccessDenied, setPlayAccessDenied] = useState(false)
  const progressSaveTimerRef = useRef(null)
  const hydratedProgressKeyRef = useRef(null)
  const nurseryRef = useRef(createDefaultNursery())

  const purgeSessionProgress = useCallback(() => {
    clearStoredPlayProgress(sessionId)
  }, [sessionId])

  const redirectFinishedSession = useCallback(() => {
    purgeSessionProgress()
    setPlayAccessDenied(true)
    navigate('/competencies', { replace: true })
  }, [navigate, purgeSessionProgress])

  const logGameEvent = useCallback(
    async (eventType, payload = {}, seasonNumber = season) => {
      if (!sessionId || !eventType) return
      try {
        await api.gameEvent({
          sessionId,
          seasonNumber,
          eventType,
          payload,
        })
      } catch {
        // best-effort logging; gameplay must not depend on analytics events
      }
    },
    [sessionId, season]
  )

  const isCurrentSessionRequest = useCallback(
    (request) => {
      if (!request || !sessionId) return false
      if (String(request.sessionId || '') !== String(sessionId)) return false
      if (request.seasonNumber == null) return true
      return Number(request.seasonNumber) === Number(season)
    },
    [sessionId, season]
  )

  const visibleTradeRequests = useMemo(
    () => tradeRequests.filter((request) => isCurrentSessionRequest(request)),
    [tradeRequests, isCurrentSessionRequest]
  )

  const activeSessionRequest = useMemo(
    () => (isCurrentSessionRequest(activeRequest) ? activeRequest : null),
    [activeRequest, isCurrentSessionRequest]
  )

  const activeTradeSendRequest = useMemo(
    () => (isCurrentSessionRequest(tradeSendModalRequest) ? tradeSendModalRequest : null),
    [tradeSendModalRequest, isCurrentSessionRequest]
  )

  useEffect(() => {
    nurseryRef.current = nursery
  }, [nursery])

  const backendCoinsNow = Number(state?.coinsNowEstimate ?? 0)
  const playerRole = state?.role
  const adultAge = Math.max(1, Number(state?.adultAge ?? DEFAULT_ADULT_AGE) || DEFAULT_ADULT_AGE)
  const coinsNow = Math.max(0, backendCoinsNow + nurseryCoinsDelta)
  const escapedCatIdsSet = useMemo(
    () =>
      new Set(
        (Array.isArray(nursery?.escapedCatIds) ? nursery.escapedCatIds : [])
          .map((id) => (id == null ? null : String(id)))
          .filter(Boolean)
      ),
    [nursery?.escapedCatIds]
  )
  const debtTotal = state?.debtTotal ?? 0
  const debtRate = state?.debtRate ?? 0
  const inventory = useMemo(() => {
    const rawInventory = state?.inventory
    if (!rawInventory || Array.isArray(rawInventory)) return {}
    return Object.fromEntries(
      Object.entries(rawInventory).filter(([, value]) => Number.isFinite(Number(value)))
    )
  }, [state?.inventory])
  const backendInventoryEntities = useMemo(() => {
    if (Array.isArray(state?.inventoryEntities)) return state.inventoryEntities
    if (Array.isArray(state?.cats)) return state.cats
    if (Array.isArray(state?.inventory?.entities)) return state.inventory.entities
    if (Array.isArray(state?.inventory?.items)) return state.inventory.items
    return []
  }, [state?.inventoryEntities, state?.cats, state?.inventory?.entities, state?.inventory?.items])
  const hasStructuredInventory = useMemo(
    () =>
      Array.isArray(state?.inventoryEntities) ||
      Array.isArray(state?.cats) ||
      Array.isArray(state?.inventory?.entities) ||
      Array.isArray(state?.inventory?.items),
    [state?.inventoryEntities, state?.cats, state?.inventory?.entities, state?.inventory?.items]
  )
  const inventoryForUi = useMemo(() => {
    const hasStructuredEntities = backendInventoryEntities.some(
      (entity) => entity && entity.id != null
    )
    if (!hasStructuredEntities) return inventory

    const next = { ...inventory }
    TRACKED_INVENTORY_COLORS.forEach((color) => {
      next[color] = 0
    })

    backendInventoryEntities.forEach((entity) => {
      if (!entity || entity.id == null) return
      const entityId = String(entity.id)
      if (escapedCatIdsSet.has(entityId)) return
      const isKitten = resolveKittenStatus(entity, adultAge)
      if (!isKitten) return
      const color = normalizeColor(entity?.color ?? entity?.catType)
      if (!TRACKED_INVENTORY_COLORS.includes(color)) return
      next[color] = Number(next[color] ?? 0) + 1
    })

    return next
  }, [inventory, backendInventoryEntities, escapedCatIdsSet, adultAge])

  const normalizedBackendKittens = useMemo(
    () =>
      backendInventoryEntities
        .map((entity) => {
          if (!entity || entity.id == null) return null
          const normalizedId = String(entity.id)
          if (escapedCatIdsSet.has(normalizedId)) return null
          const age = Number(entity?.age ?? entity?.ageSeasons ?? 0)
          const isKitten = resolveKittenStatus(entity, adultAge)
          if (!isKitten) return null
          return normalizeNurseryCat(
            {
              id: normalizedId,
              color: normalizeColor(entity?.color ?? entity?.catType ?? 'gray'),
              sex: normalizeSex(entity?.sex) || 'M',
              age,
              isKitten: true,
              hungry: Boolean(entity?.hungry),
              fedThisSeason: Boolean(entity?.fedThisSeason),
              locked: Boolean(entity?.locked),
              isSick: Boolean(entity?.isSick),
              diseaseType: entity?.diseaseType ?? entity?.sick ?? null,
              healthStatus: entity?.healthStatus,
              healedAtSeason: entity?.healedAtSeason ?? null,
            },
            { forceKitten: true, adultAge }
          )
        })
        .filter(Boolean),
    [backendInventoryEntities, escapedCatIdsSet, adultAge]
  )

  useEffect(() => {
    if (!hasStructuredInventory) return
    const backendIds = new Set(
      backendInventoryEntities
        .map((entity) => (entity?.id == null ? null : String(entity.id)))
        .filter(Boolean)
    )
    setNursery((prev) => {
      const escapedIds = new Set(
        (Array.isArray(prev?.escapedCatIds) ? prev.escapedCatIds : [])
          .map((id) => (id == null ? null : String(id)))
          .filter(Boolean)
      )
      const missing = normalizedBackendKittens.filter(
        (cat) =>
          cat?.id &&
          !escapedIds.has(cat.id) &&
          !(prev?.cats || []).some((existing) => existing?.id === cat.id) &&
          !((prev?.homes || []).flatMap((home) => (home?.kittens || []).filter(Boolean)).some((existing) => existing?.id === cat.id))
      )
      const keepLocalOnlyId = (id) => typeof id === 'string' && id.startsWith('born-')
      const prevCats = prev?.cats || []
      const prevHomes = Array.isArray(prev?.homes) ? prev.homes : []
      const nextCats = prevCats.filter((cat) => {
        const catId = String(cat?.id ?? '')
        return !catId || keepLocalOnlyId(catId) || backendIds.has(catId)
      })
      const nextHomes = prevHomes.map((home) => {
        const nextKittens = (home?.kittens || []).map((cat) => {
          if (!cat?.id) return cat
          const catId = String(cat.id)
          return keepLocalOnlyId(catId) || backendIds.has(catId) ? cat : null
        })
        const nextParentsLeft = (home?.parents?.left || []).map((id) => {
          const normalizedId = id == null ? null : String(id)
          return normalizedId && (backendIds.has(normalizedId) || keepLocalOnlyId(normalizedId))
            ? normalizedId
            : null
        })
        const nextParentsRight = (home?.parents?.right || []).map((id) => {
          const normalizedId = id == null ? null : String(id)
          return normalizedId && (backendIds.has(normalizedId) || keepLocalOnlyId(normalizedId))
            ? normalizedId
            : null
        })
        return {
          ...home,
          parents: {
            left: nextParentsLeft,
            right: nextParentsRight,
          },
          kittens: nextKittens,
        }
      })
      const catsChanged =
        nextCats.length !== prevCats.length ||
        nextCats.some((cat, idx) => cat !== prevCats[idx])
      const homesChanged = nextHomes.some((home, idx) => {
        const prevHome = prevHomes[idx]
        if (!prevHome) return true
        return (
          home.kittens.some((cat, kittenIdx) => cat !== prevHome?.kittens?.[kittenIdx]) ||
          home.parents.left.some((id, parentIdx) => id !== prevHome?.parents?.left?.[parentIdx]) ||
          home.parents.right.some((id, parentIdx) => id !== prevHome?.parents?.right?.[parentIdx])
        )
      })
      if (!missing.length && !catsChanged && !homesChanged) {
        return prev
      }
      return withNurseryHomeMirrors({
        ...prev,
        cats: [...nextCats, ...missing],
        homes: nextHomes,
      })
    })
  }, [backendInventoryEntities, normalizedBackendKittens, hasStructuredInventory])

  const inventoryEntities = useMemo(() => {
    const nurseryEntities = [
      ...(nursery?.cats || []),
      ...((nursery?.homes || []).flatMap((home) => (home?.kittens || []).filter(Boolean))),
    ]
      .filter((cat) => !escapedCatIdsSet.has(String(cat?.id ?? '')))
      .filter((cat) => resolveKittenStatus(cat, adultAge))
      .map((cat) => ({
        id: cat.id,
        color: normalizeColor(cat.color),
        sex: normalizeSex(cat.sex),
        age: Number(cat.age ?? 0),
        isKitten: true,
        hungry: Boolean(cat.hungry),
        fedThisSeason: Boolean(cat.fedThisSeason),
        locked: Boolean(cat.locked),
        ...resolveDiseaseState(cat),
      }))

    const backendEntities = backendInventoryEntities.filter(
      (entity) => !escapedCatIdsSet.has(String(entity?.id ?? ''))
    )

    if (!backendEntities.length) {
      if (!hasStructuredInventory) return nurseryEntities
      return nurseryEntities.filter((entity) => String(entity?.id ?? '').startsWith('born-'))
    }

    const nurseryById = new Map(nurseryEntities.map((cat) => [String(cat.id), cat]))
    const merged = backendEntities.map((entity) => {
      const entityId = entity?.id == null ? null : String(entity.id)
      const fromNursery = entityId ? nurseryById.get(entityId) : null
      return {
        ...entity,
        id: entity?.id ?? fromNursery?.id ?? entityId,
        color: normalizeColor(entity?.color ?? entity?.catType ?? fromNursery?.color),
        sex: normalizeSex(entity?.sex ?? fromNursery?.sex),
        age: Number(entity?.age ?? entity?.ageSeasons ?? fromNursery?.age ?? 0),
        isKitten: resolveKittenStatus(entity, adultAge),
        hungry: Boolean(entity?.hungry ?? fromNursery?.hungry),
        fedThisSeason: Boolean(entity?.fedThisSeason ?? fromNursery?.fedThisSeason),
        locked: Boolean(entity?.locked ?? fromNursery?.locked),
        ...resolveDiseaseState({
          ...fromNursery,
          ...entity,
        }),
      }
    })

    const mergedIds = new Set(
      merged
        .map((entity) => (entity?.id == null ? null : String(entity.id)))
        .filter(Boolean)
    )
    nurseryEntities.forEach((entity) => {
      const entityId = entity?.id == null ? null : String(entity.id)
      if (!entityId || mergedIds.has(entityId)) return
      merged.push(entity)
    })
    return merged
  }, [backendInventoryEntities, nursery?.cats, nursery?.homes, playerRole, escapedCatIdsSet, adultAge, hasStructuredInventory])

  const resolveCounterpartyContext = useCallback(
    (context = null) => {
      const typeSource = context?.counterpartyType || selectedBuilding?.type || null
      const idSource = context?.counterpartyId ?? selectedBuilding?.id ?? null
      if (!typeSource) {
        return { counterpartyType: 'shop', counterpartyId: 1 }
      }
      const counterpartyType =
        typeSource === 'shop' || typeSource === 'cattery' ? typeSource : null
      const counterpartyId = Number.isFinite(Number(idSource))
        ? Number(idSource)
        : null
      return { counterpartyType, counterpartyId }
    },
    [selectedBuilding?.id, selectedBuilding?.type]
  )

  const handleInactivityTimeoutError = useCallback(
    (err) => {
      if (!err || err.code !== 'INACTIVITY_TIMEOUT') return false
      purgeSessionProgress()
      setInactiveTimeoutModalOpen(true)
      setError('Сессия завершена из-за бездействия более 5 минут')
      return true
    },
    [purgeSessionProgress]
  )

  const handleTerminalSessionError = useCallback(
    (err) => {
      if (!err) return false
      if (err.code !== 'SESSION_ALREADY_FINISHED' && err.code !== 'SESSION_NOT_ACTIVE') {
        return false
      }
      redirectFinishedSession()
      return true
    },
    [redirectFinishedSession]
  )

  useEffect(() => {
    let cancelled = false
    setPlayAccessResolved(false)
    setPlayAccessDenied(false)

    const run = async () => {
      if (!sessionId) {
        if (!cancelled) {
          setPlayAccessDenied(true)
        }
        return
      }
      try {
        const details = await api.sessionsDetails(sessionId)
        if (cancelled) return
        if (String(details?.status || '').toUpperCase() !== 'ACTIVE') {
          redirectFinishedSession()
          return
        }
      } catch (err) {
        if (cancelled) return
        if (err?.code === 'NOT_FOUND') {
          redirectFinishedSession()
          return
        }
        if (handleTerminalSessionError(err)) {
          return
        }
        setError(err?.message || 'Не удалось проверить статус сессии')
      } finally {
        if (!cancelled) {
          setPlayAccessResolved(true)
        }
      }
    }

    run()
    return () => {
      cancelled = true
    }
  }, [sessionId, redirectFinishedSession, handleTerminalSessionError])

  const loadData = useCallback(async () => {
    if (!sessionId || !playAccessResolved || playAccessDenied) return
    try {
      setError('')
      const { counterpartyType, counterpartyId } = resolveCounterpartyContext()
      const [st, mk] = await Promise.all([
        api.getGameState(sessionId, season, counterpartyType, counterpartyId),
        api.getMarket(sessionId, season, counterpartyType, counterpartyId),
      ])
      setState(st)
      setMarket(mk?.market || mk)
      const spectateMode =
        st?.role === 'cattery' &&
        selectedBuilding?.type === 'cattery' &&
        Number(selectedBuilding?.id) !== Number(YOUR_CATTTERY_ID)

      if (spectateMode && Number.isFinite(Number(selectedBuilding?.id))) {
        try {
          const spectate = await api.catteryPublic(
            sessionId,
            season,
            Number(selectedBuilding.id)
          )
          setCatterySpectateData(spectate || null)
        } catch {
          setCatterySpectateData(null)
        }
      } else {
        setCatterySpectateData(null)
      }
    } catch (err) {
      if (handleInactivityTimeoutError(err)) {
        setCatterySpectateData(null)
        return
      }
      if (handleTerminalSessionError(err)) {
        setCatterySpectateData(null)
        return
      }
      setError(err.message || 'Failed to load state')
      setCatterySpectateData(null)
    }
  }, [
    sessionId,
    season,
    resolveCounterpartyContext,
    selectedBuilding?.id,
    selectedBuilding?.type,
    handleInactivityTimeoutError,
    handleTerminalSessionError,
    playAccessResolved,
    playAccessDenied,
  ])

  const refreshPersistedNursery = useCallback(async () => {
    if (!sessionId || !playAccessResolved || playAccessDenied) return
    try {
      const response = await api.getProgress(sessionId, season)
      if (!response?.found || !response?.progress?.nursery) return
      setNursery(normalizeNurseryState(response.progress.nursery, adultAge))
    } catch (err) {
      if (handleInactivityTimeoutError(err)) return
      if (handleTerminalSessionError(err)) return
    }
  }, [
    sessionId,
    season,
    adultAge,
    handleInactivityTimeoutError,
    handleTerminalSessionError,
    playAccessResolved,
    playAccessDenied,
  ])

  const loadTradeRequests = useCallback(async () => {
    if (!sessionId || !playAccessResolved || playAccessDenied) return
    try {
      const response = await api.tradeRequests(sessionId, season)
      const items = (Array.isArray(response?.items) ? response.items : []).filter((item) =>
        String(item?.sessionId || '') === String(sessionId) &&
        (item?.seasonNumber == null || Number(item.seasonNumber) === Number(season))
      )
      setTradeRequests(items)
      if (activeRequest?.id) {
        const refreshed = items.find((item) => item.id === activeRequest.id) || null
        setActiveRequest(refreshed)
      }
    } catch (err) {
      if (handleInactivityTimeoutError(err)) return
      if (handleTerminalSessionError(err)) return
      // ignore noisy polling/ws refresh failures
    }
  }, [
    sessionId,
    season,
    activeRequest?.id,
    handleInactivityTimeoutError,
    handleTerminalSessionError,
    playAccessResolved,
    playAccessDenied,
  ])

  useEffect(() => {
    setTradeRequests([])
    setActiveRequest(null)
    setTradeRequestsBusy(false)
    setTradeSendModalRequest(null)
  }, [sessionId, season])

  useEffect(() => {
    loadData()
  }, [loadData])

  useEffect(() => {
    loadTradeRequests()
  }, [loadTradeRequests])

  useEffect(() => {
    if (!sessionId) return
    let socket
    try {
      socket = new WebSocket(api.tradeRequestsWsUrl(sessionId))
      socket.onmessage = () => {
        void Promise.allSettled([loadTradeRequests(), loadData(), refreshPersistedNursery()])
      }
    } catch {
      return
    }
    return () => {
      if (socket && socket.readyState <= 1) socket.close()
    }
  }, [sessionId, loadTradeRequests, loadData, refreshPersistedNursery])

  useEffect(() => {
    if (!sessionId) return
    const shouldPollTradeState =
      overlayType === 'shop' ||
      overlayType === 'cattery' ||
      visibleTradeRequests.length > 0 ||
      Boolean(activeSessionRequest) ||
      Boolean(activeTradeSendRequest)
    if (!shouldPollTradeState) return

    const timerId = window.setInterval(() => {
      void Promise.allSettled([loadTradeRequests(), loadData(), refreshPersistedNursery()])
    }, 2500)

    return () => {
      window.clearInterval(timerId)
    }
  }, [
    sessionId,
    overlayType,
    visibleTradeRequests.length,
    activeSessionRequest,
    activeTradeSendRequest,
    loadTradeRequests,
    loadData,
    refreshPersistedNursery,
  ])

  useEffect(() => {
    if (!playAccessResolved || playAccessDenied) {
      hydratedProgressKeyRef.current = null
      setProgressHydrated(false)
      return
    }
    let cancelled = false
    hydratedProgressKeyRef.current = null
    setProgressHydrated(false)

    const resetTransientState = () => {
      if (cancelled) return
      setAutoFinishing(false)
      setAutoAdvanceAfterResult(false)
      setConfirmEndOpen(false)
      setSeasonFinishedLocked(false)
      setSeasonResult(null)
      setLoseOpen(false)
    }

    const applyDefaultProgress = () => {
      if (cancelled) return
      setNursery(createDefaultNursery())
      setSeasonLedger(createDefaultSeasonLedger(season, 0))
      setNurseryCoinsDelta(0)
      setTimeLeft(seasonDuration)
    }

    const applyProgress = (parsed) => {
      if (!parsed || typeof parsed !== 'object') {
        applyDefaultProgress()
        return
      }
      if (cancelled) return

      setNursery(normalizeNurseryState(parsed.nursery, adultAge))
      setSeasonLedger(normalizeSeasonLedger(parsed.seasonLedger, season, 0))

      if (Number.isFinite(Number(parsed.nurseryCoinsDelta))) {
        setNurseryCoinsDelta(Number(parsed.nurseryCoinsDelta))
      } else {
        setNurseryCoinsDelta(0)
      }
      if (Number.isFinite(Number(parsed.timeLeft))) {
        const restoredTime = Math.max(0, Number(parsed.timeLeft))
        setTimeLeft(Math.min(seasonDuration, restoredTime))
      } else {
        setTimeLeft(seasonDuration)
      }
    }

    const restoreFromLocalStorage = () => {
      if (typeof window === 'undefined') return false
      try {
        const raw = window.localStorage.getItem(progressStorageKey)
        if (!raw) return false
        const parsed = JSON.parse(raw)
        if (!parsed || typeof parsed !== 'object') return false
        applyProgress(parsed)
        return true
      } catch {
        return false
      }
    }

    const restore = async () => {
      let restored = false
      if (sessionId) {
        try {
          const response = await api.getProgress(sessionId, season)
          if (!cancelled && response?.found && response?.progress) {
            applyProgress(response.progress)
            restored = true
          }
        } catch (err) {
          if (!cancelled && (err?.code === 'SESSION_ALREADY_FINISHED' || err?.code === 'SESSION_NOT_ACTIVE')) {
            redirectFinishedSession()
            return
          }
          restored = false
        }
      }
      if (!restored) {
        restored = restoreFromLocalStorage()
      }
      if (!restored) {
        applyDefaultProgress()
      }
      resetTransientState()
      if (!cancelled) {
        hydratedProgressKeyRef.current = progressStorageKey
        setProgressHydrated(true)
      }
    }

    restore()
    return () => {
      cancelled = true
    }
  }, [season, sessionId, progressStorageKey, seasonDuration, playAccessResolved, playAccessDenied, redirectFinishedSession])

  useEffect(() => {
    if (!state) return
    const normalized = Math.max(0, Number(backendCoinsNow + nurseryCoinsDelta) || 0)
    setNursery((prev) => {
      if (Number(prev?.coins ?? normalized) === normalized) return prev
      return { ...prev, coins: normalized, coinsSynced: true }
    })
  }, [backendCoinsNow, nurseryCoinsDelta, state])

  useEffect(() => {
    if (
      !sessionId ||
      !progressHydrated ||
      hydratedProgressKeyRef.current !== progressStorageKey
    ) {
      return
    }
    const payload = {
      nursery,
      seasonLedger,
      nurseryCoinsDelta,
      timeLeft,
    }
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(progressStorageKey, JSON.stringify(payload))
    }
    if (progressSaveTimerRef.current) {
      clearTimeout(progressSaveTimerRef.current)
    }
    progressSaveTimerRef.current = setTimeout(() => {
      api
        .saveProgress({
          sessionId,
          seasonNumber: season,
          nursery,
          seasonLedger,
          nurseryCoinsDelta,
          timeLeft: Math.max(0, Number(timeLeft) || 0),
        })
        .catch(() => {})
    }, 350)
    return () => {
      if (progressSaveTimerRef.current) {
        clearTimeout(progressSaveTimerRef.current)
        progressSaveTimerRef.current = null
      }
    }
  }, [sessionId, season, progressStorageKey, nursery, seasonLedger, nurseryCoinsDelta, timeLeft, progressHydrated])

  useEffect(() => {
    if (!progressHydrated) return
    if (seasonLedger?.seasonNumber === season && Number(seasonLedger?.startCoins ?? 0) > 0) return
    if (!Number.isFinite(Number(coinsNow))) return
    setSeasonLedger((prev) => {
      if (prev?.seasonNumber === season && Number(prev?.startCoins ?? 0) > 0) return prev
      return createDefaultSeasonLedger(season, coinsNow)
    })
  }, [progressHydrated, season, seasonLedger, coinsNow])

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
    if (!playAccessResolved || playAccessDenied) return
    const timer = setInterval(() => {
      setTimeLeft((prev) => Math.max(0, prev - 1))
    }, 1000)
    return () => clearInterval(timer)
  }, [season, playAccessResolved, playAccessDenied])

  useEffect(() => {
    if (typeof window === 'undefined') return
    const guardState = { ...(window.history.state || {}), bcPlayGuard: true }
    window.history.pushState(guardState, '', window.location.href)
    const onPopState = () => {
      navigate('/competencies', { replace: true })
    }
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [navigate, sessionId, season])

  useEffect(() => {
    if (typeof window === 'undefined') return
    const guardState = { ...(window.history.state || {}), bcPlayGuard: true }
    window.history.pushState(guardState, '', window.location.href)
    const onPopState = () => {
      navigate('/competencies', { replace: true })
    }
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [navigate, sessionId, season])

  const openOverlay = (type, id) => {
    if (type === 'cattery' && playerRole === 'cattery' && id === YOUR_CATTTERY_ID) {
      setNurseryOpen(true)
      return
    }
    setNurseryOpen(false)
    setError('')
    setOverlayType(type)
    setSelectedBuilding({ type, id })
  }

  const closeOverlay = () => {
    setOverlayType(null)
    setSelectedBuilding(null)
    setCatterySpectateData(null)
  }

  const moveShopSelection = useCallback((direction) => {
    if (overlayType !== 'shop' || !selectedBuilding?.id) return
    const ids = PETSHOPS.map((shop) => shop.id)
    const currentIdx = ids.findIndex((id) => id === selectedBuilding.id)
    if (currentIdx < 0) return
    const delta = direction >= 0 ? 1 : -1
    const nextIdx = (currentIdx + delta + ids.length) % ids.length
    setSelectedBuilding({ type: 'shop', id: ids[nextIdx] })
  }, [overlayType, selectedBuilding?.id])

  const selectedShopMeta = useMemo(
    () => PETSHOPS.find((shop) => shop.id === selectedBuilding?.id) || null,
    [selectedBuilding?.id]
  )

  const catterySpectateMode = useMemo(
    () =>
      overlayType === 'cattery' &&
      playerRole === 'cattery' &&
      Number(selectedBuilding?.id) !== Number(YOUR_CATTTERY_ID),
    [overlayType, playerRole, selectedBuilding?.id]
  )

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
        entityId: context?.entityId || null,
        counterpartyType,
        counterpartyId,
        qty,
      })
      if (!res.ok) throw new Error(res.error || 'Trade failed')
      setState(res.state)
      setNursery((prev) => {
        if (action === 'buy') {
          const additions = Array.from({ length: qty }, (_, idx) => {
            const kitten = createBoughtKitten(normalizedColor, normalizedSex, idx)
            if (idx === 0 && context?.entityId) {
              kitten.id = context.entityId
            }
            kitten.hungry = false
            kitten.fedThisSeason = true
            return kitten
          })
          return withNurseryHomeMirrors({ ...prev, cats: [...(prev.cats || []), ...additions] })
        }
        if (action === 'sell') {
          const prevHomes = Array.isArray(prev?.homes) ? prev.homes : []
          if (context?.entityId) {
            const targetId = context.entityId
            return withNurseryHomeMirrors({
              ...prev,
              cats: (prev.cats || []).filter((cat) => cat.id !== targetId),
              homes: prevHomes.map((home) => ({
                ...home,
                parents: {
                  left: (home?.parents?.left || []).map((id) => (id === targetId ? null : id)),
                  right: (home?.parents?.right || []).map((id) => (id === targetId ? null : id)),
                },
                kittens: (home?.kittens || []).map((cat) => (cat?.id === targetId ? null : cat)),
              })),
            })
          }
          const assigned = new Set()
          prevHomes.forEach((home) => {
            home?.parents?.left?.forEach((id) => id && assigned.add(id))
            home?.parents?.right?.forEach((id) => id && assigned.add(id))
          })

          let remaining = qty
          const nextHomes = prevHomes.map((home) => ({
            ...home,
            kittens: (home?.kittens || []).map((cat) => {
              if (!cat || remaining <= 0) return cat
              const colorMatch = normalizeColor(cat?.color) === normalizedColor
              const sexMatch = normalizedSex ? normalizeSex(cat?.sex) === normalizedSex : true
              const sellableKitten =
                resolveKittenStatus(cat, adultAge) &&
                !assigned.has(cat.id) &&
                !cat.locked &&
                !cat.hungry
              if (sellableKitten && colorMatch && sexMatch) {
                remaining -= 1
                return null
              }
              return cat
            }),
          }))
          const nextCats = []
          ;(prev.cats || []).forEach((cat) => {
            const colorMatch = normalizeColor(cat?.color) === normalizedColor
            const sexMatch = normalizedSex ? normalizeSex(cat?.sex) === normalizedSex : true
            const sellableKitten =
              resolveKittenStatus(cat, adultAge) &&
              !assigned.has(cat.id) &&
              !cat.locked &&
              !cat.hungry
            if (remaining > 0 && sellableKitten && colorMatch && sexMatch) {
              remaining -= 1
              return
            }
            nextCats.push(cat)
          })
          return withNurseryHomeMirrors({
            ...prev,
            cats: nextCats,
            homes: nextHomes,
          })
          }
        return prev
      })
      await loadData()
      await refreshPersistedNursery()
      await refreshPersistedNursery()
    } catch (err) {
      if (handleInactivityTimeoutError(err)) return
      if (handleTerminalSessionError(err)) return
      setError(formatTradeRequestError(err?.message || 'Trade failed'))
    } finally {
      setBusy(false)
    }
  }

  const handleCreateTradeRequest = useCallback(
    async ({ counterpartyType, counterpartyId, items }) => {
      if (!sessionId) return
      try {
        const response = await api.tradeRequestSend({
          sessionId,
          seasonNumber: season,
          counterpartyType,
          counterpartyId,
          items,
        })
        if (!response?.ok) {
          throw new Error(response?.error || 'trade_request_send_failed')
        }
        if (response.request) {
          setTradeSendModalRequest(response.request)
        }
        await loadTradeRequests()
        await loadData()
      } catch (err) {
        if (handleInactivityTimeoutError(err)) return
        if (handleTerminalSessionError(err)) return
        throw new Error(formatTradeRequestError(err?.message || err))
      }
    },
    [sessionId, season, loadTradeRequests, loadData, refreshPersistedNursery, handleInactivityTimeoutError, handleTerminalSessionError]
  )

  const handleOpenRequest = useCallback((request) => {
    if (!isCurrentSessionRequest(request)) {
      setActiveRequest(null)
      return
    }
    setActiveRequest(request)
  }, [isCurrentSessionRequest])

  const handleRequestAction = useCallback(
    async (action, extra = {}) => {
      if (!activeSessionRequest?.id || !sessionId) return
      const requestId = activeSessionRequest.id
      if (action === 'ack') {
        setActiveRequest(null)
      }
      try {
        setTradeRequestsBusy(true)
        const response = await api.tradeRequestAction(requestId, {
          sessionId,
          seasonNumber: season,
          action,
          counterItems: Array.isArray(extra.counterItems) ? extra.counterItems : [],
          messageCode: extra.messageCode || null,
        })
        if (!response?.ok) {
          throw new Error(response?.error || 'trade_request_action_failed')
        }
        if (action !== 'ack' && isCurrentSessionRequest(response?.request)) {
          setActiveRequest(response.request)
        } else if (action !== 'ack') {
          setActiveRequest(null)
        }
        await loadTradeRequests()
        await loadData()
        await refreshPersistedNursery()
      } catch (err) {
        if (handleInactivityTimeoutError(err)) {
          setActiveRequest(null)
          return
        }
        if (handleTerminalSessionError(err)) {
          setActiveRequest(null)
          return
        }
        setError(formatTradeRequestError(err?.message || 'trade_request_action_failed'))
      } finally {
        setTradeRequestsBusy(false)
      }
    },
    [
      activeSessionRequest?.id,
      sessionId,
      season,
      loadTradeRequests,
      loadData,
      refreshPersistedNursery,
      handleInactivityTimeoutError,
      handleTerminalSessionError,
      isCurrentSessionRequest,
    ]
  )

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
      if (handleInactivityTimeoutError(err)) return
      if (handleTerminalSessionError(err)) return
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
      if (handleInactivityTimeoutError(err)) return
      if (handleTerminalSessionError(err)) return
      setError(err.message || 'Credit repay failed')
    } finally {
      setBusy(false)
    }
  }

  const handleNurseryCoinsSync = useCallback((nextCoins) => {
    const normalized = Math.max(0, Number(nextCoins) || 0)
    setNurseryCoinsDelta(normalized - backendCoinsNow)
  }, [backendCoinsNow])

  const handleNurserySeasonSpend = useCallback((category, amount) => {
    const normalizedAmount = Math.max(0, Number(amount) || 0)
    if (!normalizedAmount) return
    setSeasonLedger((prev) => {
      const base = normalizeSeasonLedger(prev, season, coinsNow)
      if (category === 'home') {
        return { ...base, homeExpenses: base.homeExpenses + normalizedAmount }
      }
      if (category === 'feed') {
        return { ...base, feedExpenses: base.feedExpenses + normalizedAmount }
      }
      if (category === 'insurance') {
        return { ...base, insuranceExpenses: base.insuranceExpenses + normalizedAmount }
      }
      if (category === 'treatment') {
        return { ...base, treatmentExpenses: base.treatmentExpenses + normalizedAmount }
      }
      return base
    })
  }, [season, coinsNow])

  const handleEndSeason = useCallback(async ({ auto = false, finishEarly = false } = {}) => {
    if (seasonFinishedLocked) return
    try {
      setBusy(true)
      if (auto) {
        setAutoFinishing(true)
        setAutoAdvanceAfterResult(false)
      } else {
        setAutoAdvanceAfterResult(false)
      }
      const currentNursery = normalizeNurseryState(nurseryRef.current, adultAge)
      const seasonTransition = buildSeasonTransition(currentNursery, adultAge)
      setNursery(seasonTransition.nursery)
      const res = await api.finishSeason(
        sessionId,
        season,
        finishEarly,
        currentNursery,
        nurseryCoinsDelta
      )
      if (seasonTransition?.bornSickKittens?.length) {
        await Promise.allSettled(
          seasonTransition.bornSickKittens.map((cat) =>
            logGameEvent('kitten_born_sick', {
              catId: cat.id,
              diseaseType: cat.diseaseType,
            })
          )
        )
      }
      setEscapedHungryCats(
        Array.isArray(res?.seasonResult?.escapedAnimals) && res.seasonResult.escapedAnimals.length
          ? res.seasonResult.escapedAnimals
          : seasonTransition.escapedHungryCats
      )
      setConfirmEndOpen(false)
      setSeasonResult(
        res
          ? {
              ...res,
              seasonResult: buildCombinedSeasonResult({
                backendResult: res.seasonResult,
                seasonLedger,
                actualCoinsEnd: seasonTransition?.nursery?.coins,
                escapedCats:
                  res?.seasonResult?.escapedCats ??
                  seasonTransition?.escapedHungryCats?.length ??
                  0,
              }),
            }
          : null
      )
      setSeasonFinishedLocked(true)
    } catch (err) {
      if (handleInactivityTimeoutError(err)) return
      if (handleTerminalSessionError(err)) return
      setError(err.message || 'Failed to finish season')
      setAutoFinishing(false)
      setAutoAdvanceAfterResult(false)
    } finally {
      setBusy(false)
    }
  }, [season, sessionId, seasonFinishedLocked, seasonLedger, handleInactivityTimeoutError, handleTerminalSessionError, adultAge, nurseryCoinsDelta, logGameEvent])

  useEffect(() => {
    if (timeLeft !== 0) return
    if (
      busy ||
      confirmEndOpen ||
      seasonResult ||
      loseOpen ||
      autoFinishing ||
      seasonFinishedLocked ||
      Boolean(error)
    ) {
      return
    }
    handleEndSeason({ auto: true, finishEarly: false })
  }, [timeLeft, busy, confirmEndOpen, seasonResult, loseOpen, autoFinishing, seasonFinishedLocked, error, handleEndSeason])

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return `00:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  }

  const persistProgressForSeason = useCallback(
    async (targetSeason, targetCoins = null) => {
      if (!sessionId || !Number.isFinite(Number(targetSeason))) return
      const normalizedSeason = Number(targetSeason)
      const targetDuration = SEASON_SECONDS[normalizedSeason] || 300
      const nextPayload = buildNextSeasonProgressPayload({
        nursery,
        adultAge,
        nextSeasonNumber: normalizedSeason,
        nextSeasonCoins: targetCoins ?? normalizeNurseryState(nursery, adultAge).coins,
        targetDuration,
      })
      const targetStorageKey = `bc_play_progress_${sessionId}_${normalizedSeason}`

      if (typeof window !== 'undefined') {
        window.localStorage.setItem(targetStorageKey, JSON.stringify(nextPayload))
      }
      try {
        await api.saveProgress({
          sessionId,
          seasonNumber: normalizedSeason,
          nursery: nextPayload.nursery,
          seasonLedger: nextPayload.seasonLedger,
          nurseryCoinsDelta: nextPayload.nurseryCoinsDelta,
          timeLeft: nextPayload.timeLeft,
        })
      } catch {
        // local storage already has the handoff state
      }
    },
    [sessionId, nursery, SEASON_SECONDS, adultAge]
  )

  const continueAfterSeasonResult = useCallback(
    async (transition) => {
      const next = transition?.next ?? null
      const coinsEnd = Number(transition?.coinsEnd ?? 0)
      const nextCoins = Number(transition?.nextCoins ?? coinsEnd)
      const terminal = Boolean(transition?.terminal)
      const completionReason = String(transition?.completionReason || '').toUpperCase()
      if (!terminal && coinsEnd > 0) {
        if (next) {
          await persistProgressForSeason(next, nextCoins)
          navigate(`/play/${sessionId}/${next}`)
          return
        }
        purgeSessionProgress()
        navigate('/sessions/history', { replace: true })
        return
      }
      if (terminal && completionReason === 'NORMAL_COMPLETION') {
        purgeSessionProgress()
        navigate('/sessions/history', { replace: true })
        return
      }
      purgeSessionProgress()
      setLoseOpen(true)
    },
    [persistProgressForSeason, navigate, sessionId, purgeSessionProgress]
  )

  const handleSeasonResultConfirm = useCallback(async () => {
    setAutoAdvanceAfterResult(false)
    setAutoFinishing(false)
    const transition = {
      next: seasonResult?.nextSeason?.number ?? null,
      nextCoins: Number(
        seasonResult?.nextSeason?.coins ??
        seasonResult?.seasonResult?.coinsEnd ??
        seasonResult?.seasonResult?.coins_end ??
        0
      ),
      coinsEnd: Number(
        seasonResult?.seasonResult?.coinsEnd ??
        seasonResult?.seasonResult?.coins_end ??
        0
      ),
      terminal: Boolean(seasonResult?.seasonResult?.terminal),
      completionReason: seasonResult?.seasonResult?.completionReason ?? null,
    }
    setSeasonResult(null)
    if (escapedHungryCats.length) {
      setPendingSeasonTransition(transition)
      return
    }
    await continueAfterSeasonResult(transition)
  }, [seasonResult, escapedHungryCats.length, continueAfterSeasonResult])

  const handleEscapedHungryConfirm = useCallback(async () => {
    const transition = pendingSeasonTransition
    setPendingSeasonTransition(null)
    setEscapedHungryCats([])
    await continueAfterSeasonResult(transition)
  }, [pendingSeasonTransition, continueAfterSeasonResult])

  if (!playAccessResolved && !playAccessDenied) {
    return (
      <div className="mapRoot">
        <div className="platform-muted" style={{ padding: 24 }}>
          Проверяем статус сессии...
        </div>
      </div>
    )
  }

  if (playAccessDenied) {
    return null
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
            </button>
          )
        })}

      </div>

      <ShopOverlay
        open={overlayType === 'shop'}
        onClose={closeOverlay}
        buildingId={selectedBuilding?.id}
        buildingName={selectedShopMeta?.name}
        onPrevCounterparty={() => moveShopSelection(-1)}
        onNextCounterparty={() => moveShopSelection(1)}
        seasonNumber={season}
        coinsNow={coinsNow}
        debtTotal={debtTotal}
        debtRate={debtRate}
        inventory={inventoryForUi}
        inventoryEntities={inventoryEntities}
        market={market || {}}
        playerRole={playerRole}
        busy={busy}
        error={error}
        onTrade={handleTrade}
        onCreateTradeRequest={handleCreateTradeRequest}
        onCreditTake={handleCreditTake}
        onCreditRepay={handleCreditRepay}
        tradeRequests={tradeRequests}
        onOpenRequest={handleOpenRequest}
        adultAge={adultAge}
        shopTrustPercent={state?.shopTrustPercent ?? null}
      />

      <CatteryOverlay
        open={overlayType === 'cattery'}
        onClose={closeOverlay}
        buildingId={selectedBuilding?.id}
        seasonNumber={season}
        coinsNow={coinsNow}
        debtTotal={debtTotal}
        debtRate={debtRate}
        inventory={inventoryForUi}
        inventoryEntities={inventoryEntities}
        market={market || {}}
        playerRole={playerRole}
        busy={busy}
        error={error}
        onTrade={handleTrade}
        onCreateTradeRequest={handleCreateTradeRequest}
        onCreditTake={handleCreditTake}
        onCreditRepay={handleCreditRepay}
        tradeRequests={tradeRequests}
        onOpenRequest={handleOpenRequest}
        spectateMode={catterySpectateMode}
        spectateData={catterySpectateData}
        adultAge={adultAge}
      />

      <ConfirmEndSeasonModal
        open={confirmEndOpen}
        onConfirm={() => handleEndSeason({ auto: false, finishEarly: false })}
        onCancel={() => setConfirmEndOpen(false)}
      />

      <LoseModal
        open={loseOpen}
        onConfirm={() => {
          setLoseOpen(false)
          redirectFinishedSession()
        }}
      />

      <SeasonResultModal
        open={Boolean(seasonResult)}
        result={seasonResult?.seasonResult}
        nextSeason={seasonResult?.nextSeason}
        onConfirm={handleSeasonResultConfirm}
      />

      {pendingSeasonTransition && escapedHungryCats.length ? (
        <div className="modal-overlay" onClick={handleEscapedHungryConfirm}>
          <div className="modal modal--size-big season-change-modal escaped-hungry-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal__header">
              <div className="modal__title season-change-modal__title">
                <span className="season-change-modal__icon">🏠</span>
                ЖИВОТНЫЕ СБЕЖАЛИ
              </div>
              <div className="modal__desc season-change-modal__desc">
                К концу сезона часть животных осталась вне домика или без лечения, поэтому они сбежали.
              </div>
            </div>
            <div className="modal__body">
              <div className="escaped-hungry-modal__summary">
                <div className="escaped-hungry-modal__card">
                  <span className="escaped-hungry-modal__label">Сбежало</span>
                  <strong>{escapedHungryCats.length}</strong>
                </div>
                <div className="escaped-hungry-modal__card">
                  <span className="escaped-hungry-modal__label">Правило сезона</span>
                  <strong>Домик и лечение обязательны</strong>
                </div>
              </div>
              <div className="escaped-hungry-modal__panel">
                <div className="escaped-hungry-modal__panel-title">Кто сбежал</div>
                <ul className="escaped-hungry-modal__list">
                  {escapedHungryCats.map((cat, idx) => (
                    <li className="escaped-hungry-modal__item" key={`${cat.id}-${idx}`}>
                      <span className="escaped-hungry-modal__item-marker">•</span>
                      <span>{describeEscapedHungryCat(cat)}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="modal__body-actions season-change-modal__body-actions">
                <button className="text_button text_button--color-blue" onClick={handleEscapedHungryConfirm}>ПОНЯТНО</button>
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {inactiveTimeoutModalOpen ? (
        <div className="modal-overlay">
          <div className="modal modal--size-big" onClick={(e) => e.stopPropagation()}>
            <div className="modal__header">
              <div className="modal__title">СЕССИЯ ЗАВЕРШЕНА</div>
              <div className="modal__desc">
                Вы были признаны банкротом из-за бездействия более 5 минут
              </div>
            </div>
            <div className="modal__body">
              <div className="modal__body-actions season-change-modal__body-actions">
                <button
                  className="text_button text_button--color-blue"
                  onClick={() => {
                    purgeSessionProgress()
                    setInactiveTimeoutModalOpen(false)
                    navigate('/sessions/history', { replace: true })
                  }}
                >
                  ПЕРЕЙТИ В ИСТОРИЮ СЕССИЙ
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : null}

      <MyNurseryOverlay
        open={nurseryOpen}
        onClose={() => setNurseryOpen(false)}
        sessionId={sessionId}
        nursery={nursery}
        setNursery={setNursery}
        playerAvatarUrl={me?.avatarUrl || null}
        seasonNumber={season}
        coinsNow={coinsNow}
        timerText={formatTime(timeLeft)}
        onRequestEndSeason={() => setConfirmEndOpen(true)}
        onExitPlatform={() => navigate('/competencies')}
        onCoinsSync={handleNurseryCoinsSync}
        onSeasonSpend={handleNurserySeasonSpend}
        adultAge={adultAge}
      />

      <WelcomeStartModal
        open={welcomeOpen}
        onClose={handleWelcomeClose}
        playerName="Леопольд"
        startCoins={Math.max(0, Number(state?.coinsNowEstimate ?? 40) || 40)}
      />

      <RequestsSidebar requests={visibleTradeRequests} onOpenRequest={handleOpenRequest} />

      <RequestModal
        open={Boolean(activeSessionRequest)}
        request={activeSessionRequest}
        busy={tradeRequestsBusy}
        onClose={() => setActiveRequest(null)}
        onAction={handleRequestAction}
      />

      <TradeSendModal
        open={Boolean(activeTradeSendRequest)}
        request={activeTradeSendRequest}
        onClose={() => setTradeSendModalRequest(null)}
      />

      <RequestsSidebar requests={visibleTradeRequests} onOpenRequest={handleOpenRequest} />

      <RequestModal
        open={Boolean(activeSessionRequest)}
        request={activeSessionRequest}
        busy={tradeRequestsBusy}
        onClose={() => setActiveRequest(null)}
        onAction={handleRequestAction}
      />

      <TradeSendModal
        open={Boolean(activeTradeSendRequest)}
        request={activeTradeSendRequest}
        onClose={() => setTradeSendModalRequest(null)}
      />
    </div>
  )
}

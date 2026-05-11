import { describe, expect, it } from 'vitest'
import {
  buildNextSeasonProgressPayload,
  buildSeasonTransition,
  normalizeNurseryCat,
  normalizeNurseryState,
} from './PlayMapPage.jsx'

const createBreedingNursery = () => ({
  coins: 20,
  hasHome: true,
  cats: [
    { id: 'mom', color: 'white', sex: 'F', age: 3, isKitten: false, hungry: false, fedThisSeason: true },
    { id: 'dad', color: 'black', sex: 'M', age: 3, isKitten: false, hungry: false, fedThisSeason: true },
  ],
  home: {
    parents: { left: ['mom', 'dad'], right: [null, null] },
    kittens: Array(12).fill(null),
    breedPending: { left: true, right: false },
    lastBreedSeason: { left: 1, right: 0 },
  },
})

describe('PlayMapPage nursery disease flow', () => {
  it('migrates legacy single-home nursery into homes array', () => {
    const nursery = normalizeNurseryState({
      coins: 10,
      hasHome: true,
      insuranceActive: true,
      insuranceNext: false,
      cats: [{ id: 'old-parent', color: 'white', sex: 'F', age: 3 }],
      home: {
        parents: { left: ['old-parent', null], right: [null, null] },
        kittens: [{ id: 'legacy-kitten', color: 'black', sex: 'M', age: 0 }],
        breedPending: { left: false, right: false },
        lastBreedSeason: { left: 0, right: 0 },
      },
    }, 2)

    expect(nursery.homes).toHaveLength(1)
    expect(nursery.activeHomeIndex).toBe(0)
    expect(nursery.homes[0].insuranceActive).toBe(true)
    expect(nursery.homes[0].parents.left[0]).toBe('old-parent')
    expect(nursery.homes[0].kittens[0].id).toBe('legacy-kitten')
    expect(nursery.home.kittens[0].id).toBe('legacy-kitten')
  })

  it('preserves multi-home saves and restores active home mirror on reload', () => {
    const nursery = normalizeNurseryState({
      coins: 18,
      cats: [{ id: 'yard-adult', color: 'white', sex: 'F', age: 3 }],
      homes: [
        {
          id: 'home-1',
          number: 1,
          insuranceActive: true,
          insuranceNext: false,
          parents: { left: ['yard-adult', null], right: [null, null] },
          kittens: Array(12).fill(null),
          breedPending: { left: false, right: false },
          lastBreedSeason: { left: 0, right: 0 },
        },
        {
          id: 'home-2',
          number: 2,
          insuranceActive: false,
          insuranceNext: true,
          parents: { left: [null, null], right: [null, null] },
          kittens: [
            { id: 'kitten-home-2', color: 'black', sex: 'M', age: 0 },
            ...Array(11).fill(null),
          ],
          breedPending: { left: true, right: false },
          lastBreedSeason: { left: 2, right: 0 },
        },
      ],
      activeHomeIndex: 1,
    }, 2)

    expect(nursery.homes).toHaveLength(2)
    expect(nursery.activeHomeIndex).toBe(1)
    expect(nursery.home.id).toBe('home-2')
    expect(nursery.home.number).toBe(2)
    expect(nursery.home.insuranceNext).toBe(true)
    expect(nursery.home.kittens[0].id).toBe('kitten-home-2')
    expect(nursery.hasHome).toBe(true)
    expect(nursery.insuranceActive).toBe(false)
    expect(nursery.insuranceNext).toBe(true)
  })

  it('resets nurseryCoinsDelta when handing off progress to the next season', () => {
    const payload = buildNextSeasonProgressPayload({
      nursery: {
        coins: 16,
        coinsSynced: false,
        cats: [{ id: 'yard-kitten', color: 'white', sex: 'F', age: 0 }],
        homes: [],
        activeHomeIndex: 0,
      },
      adultAge: 2,
      nextSeasonNumber: 5,
      nextSeasonCoins: 13,
      targetDuration: 900,
    })

    expect(payload.nursery.coins).toBe(13)
    expect(payload.nursery.coinsSynced).toBe(true)
    expect(payload.nurseryCoinsDelta).toBe(0)
    expect(payload.seasonLedger).toMatchObject({
      seasonNumber: 5,
      startCoins: 13,
      homeExpenses: 0,
      feedExpenses: 0,
      insuranceExpenses: 0,
      treatmentExpenses: 0,
    })
    expect(payload.timeLeft).toBe(900)
  })

  it('does not create a home from an empty default nursery mirror', () => {
    const nursery = normalizeNurseryState({
      coins: 40,
      hasHome: false,
      insuranceActive: false,
      insuranceNext: false,
      home: {
        parents: { left: [null, null], right: [null, null] },
        kittens: Array(12).fill(null),
        breedPending: { left: false, right: false },
        lastBreedSeason: { left: 0, right: 0 },
      },
      cats: [],
    }, 2)

    expect(nursery.hasHome).toBe(false)
    expect(nursery.homes).toHaveLength(0)
    expect(nursery.activeHomeIndex).toBe(0)
  })

  it('normalizes disease defaults for old nursery_json', () => {
    const cat = normalizeNurseryCat({ id: 'old-1', color: 'gray', sex: 'M', age: 0 }, { adultAge: 2 })
    expect(cat).toMatchObject({
      isSick: false,
      diseaseType: null,
      healthStatus: 'HEALTHY',
      healedAtSeason: null,
    })

    const nursery = normalizeNurseryState({
      coins: 10,
      cats: [{ id: 'old-2', color: 'white', sex: 'F', age: 1 }],
      home: {
        parents: { left: [null, null], right: [null, null] },
        kittens: [{ id: 'old-3', color: 'black', sex: 'M', age: 0 }],
      },
    }, 2)

    expect(nursery.cats[0].healthStatus).toBe('HEALTHY')
    expect(nursery.home.kittens[0].isSick).toBe(false)
  })

  it('can generate sick kittens during birth', () => {
    const result = buildSeasonTransition(createBreedingNursery(), 2, { rng: () => 0 })
    expect(result.bornSickKittens.length).toBeGreaterThan(0)
    expect(result.nursery.home.kittens.filter(Boolean)[0]).toMatchObject({
      isSick: true,
      diseaseType: 'RINGWORM',
      healthStatus: 'SICK',
    })
  })

  it('makes untreated sick kitten escape on next season', () => {
    const result = buildSeasonTransition({
      coins: 12,
      hasHome: true,
      cats: [],
      escapedCatIds: [],
      home: {
        parents: { left: [null, null], right: [null, null] },
        kittens: [
          {
            id: 'sick-1',
            color: 'gray',
            sex: 'M',
            age: 0,
            isKitten: true,
            isSick: true,
            diseaseType: 'FLEAS',
            healthStatus: 'SICK',
          },
          ...Array(11).fill(null),
        ],
        breedPending: { left: false, right: false },
        lastBreedSeason: { left: 0, right: 0 },
      },
    }, 2)

    expect(result.nursery.home.kittens.filter(Boolean)).toHaveLength(0)
    expect(result.nursery.escapedCatIds).toContain('sick-1')
    expect(result.escapedSickKittens[0]).toMatchObject({
      id: 'sick-1',
      escapeReason: 'SICK_UNTREATED',
    })
  })

  it('keeps healed kitten in the nursery and ages it normally', () => {
    const result = buildSeasonTransition({
      coins: 12,
      hasHome: true,
      cats: [],
      escapedCatIds: [],
      home: {
        parents: { left: [null, null], right: [null, null] },
        kittens: [
          {
            id: 'healed-1',
            color: 'gray',
            sex: 'F',
            age: 0,
            isKitten: true,
            isSick: false,
            diseaseType: null,
            healthStatus: 'HEALED',
            healedAtSeason: 1,
          },
          ...Array(11).fill(null),
        ],
        breedPending: { left: false, right: false },
        lastBreedSeason: { left: 0, right: 0 },
      },
    }, 2)

    expect(result.nursery.home.kittens[0]).toMatchObject({
      id: 'healed-1',
      age: 1,
      isSick: false,
      healthStatus: 'HEALED',
    })
    expect(result.escapedSickKittens).toHaveLength(0)
  })

  it('processes all homes during season transition', () => {
    const result = buildSeasonTransition({
      coins: 20,
      cats: [
        { id: 'mom-1', color: 'white', sex: 'F', age: 3, isKitten: false, hungry: false, fedThisSeason: true },
        { id: 'dad-1', color: 'black', sex: 'M', age: 3, isKitten: false, hungry: false, fedThisSeason: true },
        { id: 'mom-2', color: 'gray', sex: 'F', age: 3, isKitten: false, hungry: false, fedThisSeason: true },
        { id: 'dad-2', color: 'ginger', sex: 'M', age: 3, isKitten: false, hungry: false, fedThisSeason: true },
      ],
      homes: [
        {
          id: 'home-1',
          number: 1,
          insuranceActive: false,
          insuranceNext: true,
          parents: { left: ['mom-1', 'dad-1'], right: [null, null] },
          kittens: Array(12).fill(null),
          breedPending: { left: true, right: false },
          lastBreedSeason: { left: 1, right: 0 },
        },
        {
          id: 'home-2',
          number: 2,
          insuranceActive: false,
          insuranceNext: false,
          parents: { left: ['mom-2', 'dad-2'], right: [null, null] },
          kittens: [
            {
              id: 'sick-home-2',
              color: 'gray',
              sex: 'M',
              age: 0,
              isKitten: true,
              isSick: true,
              diseaseType: 'FLEAS',
              healthStatus: 'SICK',
            },
            ...Array(11).fill(null),
          ],
          breedPending: { left: false, right: false },
          lastBreedSeason: { left: 0, right: 0 },
        },
      ],
      activeHomeIndex: 1,
    }, 2, { rng: () => 0 })

    expect(result.nursery.homes).toHaveLength(2)
    expect(result.nursery.activeHomeIndex).toBe(1)
    expect(result.nursery.homes[0].insuranceActive).toBe(true)
    expect(result.nursery.homes[0].insuranceNext).toBe(false)
    expect(result.nursery.homes[0].kittens.filter(Boolean).length).toBeGreaterThan(0)
    expect(result.nursery.homes[1].kittens.filter(Boolean)).toHaveLength(0)
    expect(result.escapedSickKittens[0]).toMatchObject({
      id: 'sick-home-2',
      escapeReason: 'SICK_UNTREATED',
    })
  })

  it('activates insurance for one season and then expires it without a repurchase', () => {
    const seasonTwo = buildSeasonTransition({
      coins: 20,
      cats: [],
      homes: [
        {
          id: 'home-1',
          number: 1,
          insuranceActive: false,
          insuranceNext: true,
          parents: { left: [null, null], right: [null, null] },
          kittens: Array(12).fill(null),
          breedPending: { left: false, right: false },
          lastBreedSeason: { left: 0, right: 0 },
        },
      ],
      activeHomeIndex: 0,
    }, 2)

    expect(seasonTwo.nursery.homes[0].insuranceActive).toBe(true)
    expect(seasonTwo.nursery.homes[0].insuranceNext).toBe(false)

    const seasonThree = buildSeasonTransition(seasonTwo.nursery, 2)
    expect(seasonThree.nursery.homes[0].insuranceActive).toBe(false)
    expect(seasonThree.nursery.homes[0].insuranceNext).toBe(false)
  })
})

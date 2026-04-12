import { describe, expect, it } from 'vitest'
import {
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
})

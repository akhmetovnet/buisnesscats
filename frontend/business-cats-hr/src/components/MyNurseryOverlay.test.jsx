import { describe, expect, it } from 'vitest'
import { applyKittenTreatment, getTreatmentCost } from './MyNurseryOverlay.jsx'

describe('MyNurseryOverlay disease helpers', () => {
  it('charges 2 coins for treatment without insurance and 0 with insurance', () => {
    expect(getTreatmentCost(false)).toBe(2)
    expect(getTreatmentCost(true)).toBe(0)
  })

  it('marks treated kitten as healed in cats and home kittens', () => {
    const nursery = {
      activeHomeIndex: 1,
      cats: [
        {
          id: 'yard-kitten',
          age: 1,
          isKitten: true,
          isSick: true,
          diseaseType: 'FLEAS',
          healthStatus: 'SICK',
        },
      ],
      home: {
        kittens: [
          {
            id: 'home-kitten',
            age: 0,
            isKitten: true,
            isSick: true,
            diseaseType: 'RINGWORM',
            healthStatus: 'SICK',
          },
        ],
      },
      homes: [
        {
          id: 'home-1',
          number: 1,
          parents: { left: [null, null], right: [null, null] },
          kittens: [null],
          breedPending: { left: false, right: false },
          lastBreedSeason: { left: 0, right: 0 },
        },
        {
          id: 'home-2',
          number: 2,
          insuranceActive: true,
          parents: { left: [null, null], right: [null, null] },
          kittens: [
            {
              id: 'home-kitten',
              age: 0,
              isKitten: true,
              isSick: true,
              diseaseType: 'RINGWORM',
              healthStatus: 'SICK',
            },
          ],
          breedPending: { left: false, right: false },
          lastBreedSeason: { left: 0, right: 0 },
        },
      ],
    }

    const treatedHome = applyKittenTreatment(nursery, 'home-kitten', 3)
    expect(treatedHome.homes[1].kittens[0]).toMatchObject({
      isSick: false,
      diseaseType: null,
      healthStatus: 'HEALED',
      healedAtSeason: 3,
    })
    expect(treatedHome.home.kittens[0]).toMatchObject({
      id: 'home-kitten',
      healthStatus: 'HEALED',
    })

    const treatedYard = applyKittenTreatment(nursery, 'yard-kitten', 4)
    expect(treatedYard.cats[0]).toMatchObject({
      isSick: false,
      diseaseType: null,
      healthStatus: 'HEALED',
      healedAtSeason: 4,
    })
  })
})

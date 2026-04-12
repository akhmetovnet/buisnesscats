import { describe, expect, it } from 'vitest'
import { applyKittenTreatment, getTreatmentCost } from './MyNurseryOverlay.jsx'

describe('MyNurseryOverlay disease helpers', () => {
  it('charges 2 coins for treatment without insurance and 0 with insurance', () => {
    expect(getTreatmentCost(false)).toBe(2)
    expect(getTreatmentCost(true)).toBe(0)
  })

  it('marks treated kitten as healed in cats and home kittens', () => {
    const nursery = {
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
    }

    const treatedHome = applyKittenTreatment(nursery, 'home-kitten', 3)
    expect(treatedHome.home.kittens[0]).toMatchObject({
      isSick: false,
      diseaseType: null,
      healthStatus: 'HEALED',
      healedAtSeason: 3,
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

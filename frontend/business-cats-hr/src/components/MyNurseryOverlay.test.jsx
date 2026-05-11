import { useState } from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const gameEvent = vi.fn().mockResolvedValue({ ok: true })

vi.mock('../api.js', () => ({
  api: {
    gameEvent: (...args) => gameEvent(...args),
  },
}))

import MyNurseryOverlay, {
  INSURANCE_COST,
  applyKittenTreatment,
  feedCatAndFamily,
  getFamilySideForCat,
  isCatCoveredByInsurance,
  getTreatmentCost,
} from './MyNurseryOverlay.jsx'

function createNurseryWithHome(kitten = null) {
  return {
    playerName: 'Леопольд',
    activeHomeIndex: 0,
    cats: [],
    homes: [
      {
        id: 'home-1',
        number: 1,
        insuranceActive: false,
        insuranceNext: false,
        parents: { left: [null, null], right: [null, null] },
        kittens: Array.from({ length: 12 }, (_, idx) => (idx === 0 ? kitten : null)),
        breedPending: { left: false, right: false },
        lastBreedSeason: { left: 0, right: 0 },
      },
    ],
  }
}

function NurseryHarness({ nursery, coinsNow = 10 }) {
  const [state, setState] = useState(nursery)
  return (
    <MyNurseryOverlay
      open
      onClose={vi.fn()}
      sessionId="session-1"
      nursery={state}
      setNursery={setState}
      seasonNumber={2}
      coinsNow={coinsNow}
      timerText="00:09:00"
      adultAge={2}
    />
  )
}

function CoinsTrackedNurseryHarness({ nursery, initialCoins = 10 }) {
  const [state, setState] = useState(nursery)
  const [coins, setCoins] = useState(initialCoins)
  return (
    <>
      <div data-testid="coins-now">{coins}</div>
      <MyNurseryOverlay
        open
        onClose={vi.fn()}
        sessionId="session-1"
        nursery={state}
        setNursery={setState}
        seasonNumber={2}
        coinsNow={coins}
        onCoinsSync={setCoins}
        timerText="00:09:00"
        adultAge={2}
      />
    </>
  )
}

describe('MyNurseryOverlay disease helpers', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('charges 2 coins for treatment without insurance and 0 with insurance', () => {
    expect(getTreatmentCost(false)).toBe(2)
    expect(getTreatmentCost(true)).toBe(0)
  })

  it('uses insurance cost 3 for house insurance', () => {
    expect(INSURANCE_COST).toBe(3)
  })

  it('detects insurance coverage from the kitten home, not only from active home', () => {
    const nursery = {
      activeHomeIndex: 0,
      cats: [],
      homes: [
        {
          id: 'home-1',
          number: 1,
          insuranceActive: false,
          insuranceNext: false,
          parents: { left: [null, null], right: [null, null] },
          kittens: Array(12).fill(null),
          breedPending: { left: false, right: false },
          lastBreedSeason: { left: 0, right: 0 },
        },
        {
          id: 'home-2',
          number: 2,
          insuranceActive: true,
          insuranceNext: false,
          parents: { left: [null, null], right: [null, null] },
          kittens: [{ id: 'insured-kitten', age: 0, sex: 'M', color: 'black' }, ...Array(11).fill(null)],
          breedPending: { left: false, right: false },
          lastBreedSeason: { left: 0, right: 0 },
        },
      ],
    }

    expect(isCatCoveredByInsurance(nursery, 'insured-kitten')).toBe(true)
    expect(isCatCoveredByInsurance(nursery, 'missing-kitten')).toBe(false)
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

  it('shows compact disease marker for a sick kitten and does not show inspect action', () => {
    render(
      <NurseryHarness
        nursery={createNurseryWithHome({
          id: 'born-sick-kitten',
          age: 0,
          isKitten: true,
          sex: 'F',
          color: 'white',
          isSick: true,
          diseaseType: 'FLEAS',
          healthStatus: 'SICK',
        })}
      />
    )

    expect(screen.getByRole('button', { name: 'Лечить' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Осмотр' })).not.toBeInTheDocument()
    expect(screen.getByTitle('Блохи')).toBeInTheDocument()
  })

  it('does not show a disease label for healthy kittens', () => {
    render(
      <NurseryHarness
        nursery={createNurseryWithHome({
          id: 'born-healthy-kitten',
          age: 0,
          isKitten: true,
          sex: 'M',
          color: 'black',
          isSick: false,
          diseaseType: null,
          healthStatus: 'HEALTHY',
        })}
      />
    )

    expect(screen.queryByText('Стригущий лишай')).not.toBeInTheDocument()
    expect(screen.queryByText('Блохи')).not.toBeInTheDocument()
  })

  it('does not show a disease label for healed kittens', () => {
    render(
      <NurseryHarness
        nursery={createNurseryWithHome({
          id: 'born-healed-kitten',
          age: 1,
          isKitten: true,
          sex: 'F',
          color: 'gray',
          isSick: false,
          diseaseType: null,
          healthStatus: 'HEALED',
          healedAtSeason: 2,
        })}
      />
    )

    expect(screen.queryByText('Поврежденная лапа')).not.toBeInTheDocument()
    expect(screen.queryByText('Отравление')).not.toBeInTheDocument()
  })

  it('treats a sick kitten directly from treat mode and removes the disease label', async () => {
    const user = userEvent.setup()

    render(
      <NurseryHarness
        nursery={createNurseryWithHome({
          id: 'born-sick-kitten',
          age: 0,
          isKitten: true,
          sex: 'F',
          color: 'white',
          isSick: true,
          diseaseType: 'RINGWORM',
          healthStatus: 'SICK',
        })}
      />
    )

    await user.click(screen.getByRole('button', { name: 'Лечить' }))
    await user.click(screen.getByTitle('Стригущий лишай'))

    await waitFor(() => {
      expect(screen.getByText('Котёнок вылечен. Списано 2 монеты.')).toBeInTheDocument()
    })
    await waitFor(() => {
      expect(screen.queryByText('Стригущий лишай')).not.toBeInTheDocument()
    })
  })

  it('treats a sick kitten for free when its home is insured', async () => {
    const user = userEvent.setup()

    render(
      <CoinsTrackedNurseryHarness
        initialCoins={10}
        nursery={{
          playerName: 'Леопольд',
          activeHomeIndex: 0,
          cats: [],
          homes: [
            {
              id: 'home-1',
              number: 1,
              insuranceActive: true,
              insuranceNext: false,
              parents: { left: [null, null], right: [null, null] },
              kittens: [
                {
                  id: 'born-insured-sick-kitten',
                  age: 0,
                  isKitten: true,
                  sex: 'F',
                  color: 'white',
                  isSick: true,
                  diseaseType: 'RINGWORM',
                  healthStatus: 'SICK',
                },
                ...Array(11).fill(null),
              ],
              breedPending: { left: false, right: false },
              lastBreedSeason: { left: 0, right: 0 },
            },
          ],
        }}
      />
    )

    await user.click(screen.getByRole('button', { name: 'Лечить' }))
    await user.click(screen.getByTitle('Стригущий лишай'))

    await waitFor(() => {
      expect(screen.getByText('Котёнок вылечен. Лечение покрыто страховкой.')).toBeInTheDocument()
    })
    expect(screen.getByTestId('coins-now')).toHaveTextContent('10')
  })

  it('charges 2 coins for a sick kitten when its home is not insured', async () => {
    const user = userEvent.setup()

    render(
      <CoinsTrackedNurseryHarness
        initialCoins={10}
        nursery={createNurseryWithHome({
                  id: 'born-plain-sick-kitten',
          age: 0,
          isKitten: true,
          sex: 'F',
          color: 'white',
          isSick: true,
          diseaseType: 'RINGWORM',
          healthStatus: 'SICK',
        })}
      />
    )

    await user.click(screen.getByRole('button', { name: 'Лечить' }))
    await user.click(screen.getByTitle('Стригущий лишай'))

    await waitFor(() => {
      expect(screen.getByText('Котёнок вылечен. Списано 2 монеты.')).toBeInTheDocument()
    })
    expect(screen.getByTestId('coins-now')).toHaveTextContent('8')
  })

  it('shows treatment not required when clicking a healthy kitten in treat mode', async () => {
    const user = userEvent.setup()

    render(
      <NurseryHarness
        nursery={createNurseryWithHome({
          id: 'born-healthy-kitten',
          age: 0,
          isKitten: true,
          sex: 'M',
          color: 'ginger',
          isSick: false,
          diseaseType: null,
          healthStatus: 'HEALTHY',
        })}
      />
    )

    await user.click(screen.getByRole('button', { name: 'Лечить' }))
    await user.click(screen.getByAltText('котик'))

    await waitFor(() => {
      expect(screen.getByText('Лечение не требуется')).toBeInTheDocument()
    })
  })
})

describe('MyNurseryOverlay feeding helpers', () => {
  it('feeds a hungry kitten in a home slot directly', () => {
    const nursery = createNurseryWithHome({
      id: 'home-kitten-1',
      age: 0,
      isKitten: true,
      sex: 'F',
      color: 'white',
      hungry: true,
      fedThisSeason: false,
    })

    const next = feedCatAndFamily(nursery, 0, 'home-kitten-1')
    expect(next.homes[0].kittens[0]).toMatchObject({
      hungry: false,
      fedThisSeason: true,
    })
  })

  it('feeds a hungry kitten in the yard directly', () => {
    const nursery = {
      ...createNurseryWithHome(null),
      cats: [
        {
          id: 'yard-kitten-1',
          age: 0,
          isKitten: true,
          sex: 'M',
          color: 'black',
          hungry: true,
          fedThisSeason: false,
        },
      ],
    }

    const next = feedCatAndFamily(nursery, 0, 'yard-kitten-1')
    expect(next.cats[0]).toMatchObject({
      hungry: false,
      fedThisSeason: true,
    })
  })

  it('detects family side for parents and kittens', () => {
    const home = {
      ...createNurseryWithHome(null).homes[0],
      parents: { left: ['mom-left', null], right: [null, 'dad-right'] },
      kittens: Array.from({ length: 12 }, (_, idx) =>
        idx === 2
          ? { id: 'left-kitten' }
          : idx === 8
            ? { id: 'right-kitten' }
            : null
      ),
    }

    expect(getFamilySideForCat('mom-left', home)).toBe('left')
    expect(getFamilySideForCat('dad-right', home)).toBe('right')
    expect(getFamilySideForCat('left-kitten', home)).toBe('left')
    expect(getFamilySideForCat('right-kitten', home)).toBe('right')
    expect(getFamilySideForCat('missing', home)).toBeNull()
  })

  it('feeding left parent feeds left-side kittens only', () => {
    const nursery = {
      ...createNurseryWithHome(null),
      cats: [
        { id: 'mom-left', age: 3, sex: 'F', color: 'white', hungry: true, fedThisSeason: false },
        { id: 'dad-right', age: 3, sex: 'M', color: 'black', hungry: true, fedThisSeason: false },
      ],
      homes: [
        {
          ...createNurseryWithHome(null).homes[0],
          parents: { left: ['mom-left', null], right: [null, 'dad-right'] },
          kittens: Array.from({ length: 12 }, (_, idx) =>
            idx < 2
              ? { id: `left-kitten-${idx}`, age: 0, sex: 'F', color: 'white', hungry: true, fedThisSeason: false }
              : idx >= 6 && idx < 8
                ? { id: `right-kitten-${idx}`, age: 0, sex: 'M', color: 'black', hungry: true, fedThisSeason: false }
                : null
          ),
        },
      ],
    }

    const next = feedCatAndFamily(nursery, 0, 'mom-left')
    expect(next.cats.find((cat) => cat.id === 'mom-left')).toMatchObject({
      hungry: false,
      fedThisSeason: true,
    })
    expect(next.homes[0].kittens[0]).toMatchObject({ hungry: false, fedThisSeason: true })
    expect(next.homes[0].kittens[1]).toMatchObject({ hungry: false, fedThisSeason: true })
    expect(next.homes[0].kittens[6]).toMatchObject({ hungry: true, fedThisSeason: false })
    expect(next.homes[0].kittens[7]).toMatchObject({ hungry: true, fedThisSeason: false })
  })

  it('feeding right parent feeds right-side kittens only', () => {
    const nursery = {
      ...createNurseryWithHome(null),
      cats: [
        { id: 'mom-left', age: 3, sex: 'F', color: 'white', hungry: true, fedThisSeason: false },
        { id: 'dad-right', age: 3, sex: 'M', color: 'black', hungry: true, fedThisSeason: false },
      ],
      homes: [
        {
          ...createNurseryWithHome(null).homes[0],
          parents: { left: ['mom-left', null], right: [null, 'dad-right'] },
          kittens: Array.from({ length: 12 }, (_, idx) =>
            idx < 2
              ? { id: `left-kitten-${idx}`, age: 0, sex: 'F', color: 'white', hungry: true, fedThisSeason: false }
              : idx >= 6 && idx < 8
                ? { id: `right-kitten-${idx}`, age: 0, sex: 'M', color: 'black', hungry: true, fedThisSeason: false }
                : null
          ),
        },
      ],
    }

    const next = feedCatAndFamily(nursery, 0, 'dad-right')
    expect(next.cats.find((cat) => cat.id === 'dad-right')).toMatchObject({
      hungry: false,
      fedThisSeason: true,
    })
    expect(next.homes[0].kittens[0]).toMatchObject({ hungry: true, fedThisSeason: false })
    expect(next.homes[0].kittens[1]).toMatchObject({ hungry: true, fedThisSeason: false })
    expect(next.homes[0].kittens[6]).toMatchObject({ hungry: false, fedThisSeason: true })
    expect(next.homes[0].kittens[7]).toMatchObject({ hungry: false, fedThisSeason: true })
  })
})

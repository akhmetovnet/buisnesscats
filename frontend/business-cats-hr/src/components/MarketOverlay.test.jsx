import { render } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import MarketOverlay, { resolveKittenStatus } from './MarketOverlay.jsx'

const noop = vi.fn()

const market = {
  black: {
    M: { buy: 12, sell: 10 },
    F: { buy: 12, sell: 10 },
    buy: 12,
    sell: 10,
  },
  white: {
    M: { buy: 11, sell: 9 },
    F: { buy: 11, sell: 9 },
    buy: 11,
    sell: 9,
  },
  gray: {
    M: { buy: 10, sell: 8 },
    F: { buy: 10, sell: 8 },
    buy: 10,
    sell: 8,
  },
  ginger: {
    M: { buy: 13, sell: 11 },
    F: { buy: 13, sell: 11 },
    buy: 13,
    sell: 11,
  },
}

function renderMarketOverlay(inventoryEntities) {
  return render(
    <MarketOverlay
      open
      onClose={noop}
      buildingId={1}
      titleName="Магазин"
      titleType="shop"
      stripName="Полосатый"
      stripType="shop"
      overlayType="shop"
      seasonNumber={1}
      coinsNow={1000}
      debtTotal={0}
      debtRate={0}
      inventory={{ black: 2, white: 0, gray: 0, ginger: 0 }}
      market={market}
      inventoryEntities={inventoryEntities}
      playerRole="cattery"
      busy={false}
      error=""
      onTrade={noop}
      onCreateTradeRequest={noop}
      onCreditTake={noop}
      onCreditRepay={noop}
      onPrevCounterparty={noop}
      onNextCounterparty={noop}
      tradeRequests={[]}
      onOpenRequest={noop}
    />
  )
}

describe('MarketOverlay sellable cards', () => {
  it('treats age as authoritative when kitten flag is stale', () => {
    expect(resolveKittenStatus({ age: 2, isKitten: true }, 2)).toBe(false)
    expect(resolveKittenStatus({ age: 1, isKitten: false }, 2)).toBe(true)
  })

  it('shows only kittens in seller cards when adults and newborns share the same variant', () => {
    const { container } = renderMarketOverlay([
      {
        id: 'adult-black-m',
        color: 'black',
        sex: 'M',
        age: 2,
        isKitten: true,
        hungry: false,
        fedThisSeason: true,
      },
      {
        id: 'kitten-black-m',
        color: 'black',
        sex: 'M',
        age: 0,
        isKitten: true,
        hungry: false,
        fedThisSeason: true,
      },
      {
        id: 'adult-white-f',
        color: 'white',
        sex: 'F',
        age: 4,
        isKitten: false,
        hungry: false,
        fedThisSeason: true,
      },
    ])

    const nurseryArea = container.querySelector('.lot-area--nursery')
    expect(nurseryArea).not.toBeNull()
    const cards = Array.from(nurseryArea.querySelectorAll('.cat-card'))
    expect(cards).toHaveLength(1)
    expect(nurseryArea).toHaveTextContent('черный мальчик')
    expect(nurseryArea).toHaveTextContent('×1')
    expect(nurseryArea).not.toHaveTextContent('белый девочка')
    expect(nurseryArea).not.toHaveTextContent('×2')
  })

  it('counts only kittens when adults share the same color and sex group', () => {
    const { container } = renderMarketOverlay([
      {
        id: 'adult-black-m',
        color: 'black',
        sex: 'M',
        age: 5,
        isKitten: false,
        hungry: false,
        fedThisSeason: true,
      },
      {
        id: 'kitten-black-m-1',
        color: 'black',
        sex: 'M',
        age: 0,
        isKitten: true,
        hungry: false,
        fedThisSeason: true,
      },
      {
        id: 'kitten-black-m-2',
        color: 'black',
        sex: 'M',
        age: 1,
        isKitten: true,
        hungry: false,
        fedThisSeason: true,
      },
      {
        id: 'kitten-black-m-3',
        color: 'black',
        sex: 'M',
        age: 1,
        isKitten: true,
        hungry: false,
        fedThisSeason: true,
      },
    ])

    const nurseryArea = container.querySelector('.lot-area--nursery')
    expect(nurseryArea).not.toBeNull()
    expect(nurseryArea).toHaveTextContent('черный мальчик')
    expect(nurseryArea).toHaveTextContent('×3')
    expect(nurseryArea).not.toHaveTextContent('×4')
  })

  it('does not show sick kittens in seller cards until they are healed', () => {
    const { container, rerender } = render(
      <MarketOverlay
        open
        onClose={noop}
        buildingId={1}
        titleName="Магазин"
        titleType="shop"
        stripName="Полосатый"
        stripType="shop"
        overlayType="shop"
        seasonNumber={1}
        coinsNow={1000}
        debtTotal={0}
        debtRate={0}
        inventory={{ black: 2, white: 0, gray: 0, ginger: 0 }}
        market={market}
        inventoryEntities={[
          {
            id: 'sick-kitten-black-m',
            color: 'black',
            sex: 'M',
            age: 0,
            isKitten: true,
            isSick: true,
            diseaseType: 'FLEAS',
            healthStatus: 'SICK',
            hungry: false,
            fedThisSeason: true,
          },
        ]}
        playerRole="cattery"
        busy={false}
        error=""
        onTrade={noop}
        onCreateTradeRequest={noop}
        onCreditTake={noop}
        onCreditRepay={noop}
        onPrevCounterparty={noop}
        onNextCounterparty={noop}
        tradeRequests={[]}
        onOpenRequest={noop}
      />
    )

    let nurseryArea = container.querySelector('.lot-area--nursery')
    expect(nurseryArea?.querySelectorAll('.cat-card')).toHaveLength(0)

    rerender(
      <MarketOverlay
        open
        onClose={noop}
        buildingId={1}
        titleName="Магазин"
        titleType="shop"
        stripName="Полосатый"
        stripType="shop"
        overlayType="shop"
        seasonNumber={1}
        coinsNow={1000}
        debtTotal={0}
        debtRate={0}
        inventory={{ black: 2, white: 0, gray: 0, ginger: 0 }}
        market={market}
        inventoryEntities={[
          {
            id: 'healed-kitten-black-m',
            color: 'black',
            sex: 'M',
            age: 0,
            isKitten: true,
            isSick: false,
            diseaseType: null,
            healthStatus: 'HEALED',
            healedAtSeason: 1,
            hungry: false,
            fedThisSeason: true,
          },
        ]}
        playerRole="cattery"
        busy={false}
        error=""
        onTrade={noop}
        onCreateTradeRequest={noop}
        onCreditTake={noop}
        onCreditRepay={noop}
        onPrevCounterparty={noop}
        onNextCounterparty={noop}
        tradeRequests={[]}
        onOpenRequest={noop}
      />
    )

    nurseryArea = container.querySelector('.lot-area--nursery')
    expect(nurseryArea).toHaveTextContent('черный мальчик')
    expect(nurseryArea).toHaveTextContent('×1')
  })
})

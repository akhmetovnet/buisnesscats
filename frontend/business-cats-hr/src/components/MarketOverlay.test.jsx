import { fireEvent, render, screen, waitFor } from '@testing-library/react'
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

function renderMarketOverlay(inventoryEntities, extraProps = {}) {
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
      shopTrustPercent={100}
      {...extraProps}
    />
  )
}

describe('MarketOverlay sellable cards', () => {
  it('treats age as authoritative when kitten flag is stale', () => {
    expect(resolveKittenStatus({ age: 2, isKitten: true }, 2)).toBe(false)
    expect(resolveKittenStatus({ age: 1, isKitten: false }, 2)).toBe(true)
  })

  it('keeps age 1 kittens sellable and hides age 2 adults at adultAge 2', () => {
    const { container } = renderMarketOverlay([
      {
        id: 'kitten-black-m-age-0',
        color: 'black',
        sex: 'M',
        age: 0,
        isKitten: true,
        hungry: false,
        fedThisSeason: true,
      },
      {
        id: 'kitten-black-m-age-1',
        color: 'black',
        sex: 'M',
        age: 1,
        isKitten: true,
        hungry: false,
        fedThisSeason: true,
      },
      {
        id: 'adult-black-m-age-2',
        color: 'black',
        sex: 'M',
        age: 2,
        isKitten: true,
        hungry: false,
        fedThisSeason: true,
      },
    ])

    const nurseryArea = container.querySelector('.lot-area--nursery')
    expect(nurseryArea).toHaveTextContent('×2')
    expect(nurseryArea).not.toHaveTextContent('×3')
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
    expect(nurseryArea).toHaveTextContent('черный')
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

  it('shows sick kittens in seller cards and allows adding them to the deal', () => {
    const { container } = renderMarketOverlay([
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
    ])

    const nurseryArea = container.querySelector('.lot-area--nursery')
    expect(nurseryArea).toHaveTextContent('черный мальчик')
    expect(nurseryArea).toHaveTextContent('Болен: Блохи')

    const lotZone = container.querySelector('.lot-area--lot')
    expect(lotZone).not.toBeNull()
    const payload = {
      source: 'mine',
      catId: 'black',
      color: 'black',
      sex: 'M',
      isKitten: true,
      hungry: false,
      readyToSell: true,
      buy: 12,
      sell: 10,
      strict: true,
      entityId: 'sick-kitten-black-m',
      entityIds: ['sick-kitten-black-m'],
      groupKey: 'slot:black:M',
      age: 0,
      isSick: true,
      diseaseType: 'FLEAS',
      healthStatus: 'SICK',
    }
    fireEvent.drop(lotZone, {
      dataTransfer: {
        getData: () => JSON.stringify(payload),
      },
    })

    expect(container.querySelectorAll('.trade-item')).toHaveLength(1)
  })

  it('does not show disease status for healed kittens', () => {
    const { container } = renderMarketOverlay([
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
    ])

    const nurseryArea = container.querySelector('.lot-area--nursery')
    expect(nurseryArea).toHaveTextContent('черный мальчик')
    expect(nurseryArea).not.toHaveTextContent('Болен:')
  })

  it('shows total count for all kittens when six kittens are available', () => {
    const kittens = Array.from({ length: 6 }, (_, index) => ({
      id: `kitten-black-m-${index + 1}`,
      color: 'black',
      sex: 'M',
      age: 0,
      isKitten: true,
      hungry: false,
      fedThisSeason: true,
    }))

    const { container } = renderMarketOverlay(kittens)
    const nurseryArea = container.querySelector('.lot-area--nursery')
    expect(nurseryArea).toHaveTextContent('×6')
  })

  it('removes sold kittens from seller cards after accepted refresh', () => {
    const soldOutGroup = Array.from({ length: 4 }, (_, index) => ({
      id: `kitten-ginger-m-${index + 1}`,
      color: 'ginger',
      sex: 'M',
      age: 0,
      isKitten: true,
      hungry: false,
      fedThisSeason: true,
    }))
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
        inventory={{ black: 0, white: 0, gray: 0, ginger: 4 }}
        market={market}
        inventoryEntities={soldOutGroup}
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
        shopTrustPercent={100}
      />
    )

    const nurseryArea = container.querySelector('.lot-area--nursery')
    expect(nurseryArea).toHaveTextContent('×4')

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
        inventory={{ black: 0, white: 0, gray: 0, ginger: 0 }}
        market={market}
        inventoryEntities={[]}
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
        shopTrustPercent={100}
      />
    )

    expect(container.querySelector('.lot-area--nursery')).toHaveTextContent(
      'Сейчас у вас нет котят, которых можно продать магазину'
    )
  })

  it('adds two same-variant kittens with different entity ids and blocks the third add', async () => {
    const onCreateTradeRequest = vi.fn().mockResolvedValue({ ok: true })
    const { container } = renderMarketOverlay(
      [
        {
          id: 'kitten-black-f-1',
          color: 'black',
          sex: 'F',
          age: 0,
          isKitten: true,
          hungry: false,
          fedThisSeason: true,
        },
        {
          id: 'kitten-black-f-2',
          color: 'black',
          sex: 'F',
          age: 0,
          isKitten: true,
          hungry: false,
          fedThisSeason: true,
        },
      ],
      { onCreateTradeRequest }
    )

    const lotZone = container.querySelector('.lot-area--lot')
    const payload = {
      source: 'mine',
      catId: 'black',
      color: 'black',
      sex: 'F',
      isKitten: true,
      hungry: false,
      readyToSell: true,
      buy: 12,
      sell: 10,
      strict: true,
      entityIds: ['kitten-black-f-1', 'kitten-black-f-2'],
      groupKey: 'slot:black:F',
      age: 0,
    }

    fireEvent.drop(lotZone, { dataTransfer: { getData: () => JSON.stringify(payload) } })
    fireEvent.drop(lotZone, { dataTransfer: { getData: () => JSON.stringify(payload) } })
    expect(container.querySelectorAll('.trade-item')).toHaveLength(2)

    fireEvent.drop(lotZone, { dataTransfer: { getData: () => JSON.stringify(payload) } })
    expect(screen.getByText('Все доступные котята этой группы уже добавлены в сделку')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /send trade/i }))
    await waitFor(() => {
      expect(onCreateTradeRequest).toHaveBeenCalledTimes(1)
    })
    const sentItems = onCreateTradeRequest.mock.calls[0][0].items
    expect(sentItems).toHaveLength(2)
    expect(sentItems[0].catId).not.toBe(sentItems[1].catId)
    expect(new Set(sentItems.map((item) => item.catId)).size).toBe(2)
  })

  it('renders trust percent in the shop header and colors it by level', () => {
    renderMarketOverlay([], { shopTrustPercent: 65 })
    const trust = screen.getByText('Доверие: 65%')
    expect(trust).toBeInTheDocument()
    expect(trust.className).toContain('trade-title__trust--warn')
  })

  it('shows friendly error text instead of raw CAT_NOT_AVAILABLE', () => {
    renderMarketOverlay([], { error: 'CAT_NOT_AVAILABLE' })
    expect(screen.getByText('Котёнок уже недоступен для сделки')).toBeInTheDocument()
  })
})

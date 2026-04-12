import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import RequestModal from './RequestModal.jsx'

describe('RequestModal', () => {
  it('renders counter explanation with player price, bot price and propose-new-price action', () => {
    render(
      <RequestModal
        open
        busy={false}
        onClose={vi.fn()}
        onAction={vi.fn()}
        request={{
          id: 'req-1',
          status: 'COUNTERED',
          canAct: true,
          totalPrice: 105,
          fromMeta: { displayName: 'Магазин', avatarText: 'B' },
          toMeta: { displayName: 'Леопольд', avatarText: 'Я' },
          items: [
            {
              itemId: 'item-1',
              catType: 'gray',
              catColor: 'gray',
              catSex: 'M',
              proposedPrice: 110,
              unitPrice: 110,
              side: 'SELL',
            },
          ],
          decisionMeta: {
            reason: 'FAIR_COUNTER',
            message: 'Магазин готов торговаться, но предлагает цену ближе к своей рыночной оценке.',
            lines: [
              {
                catType: 'gray',
                playerPrice: 110,
                shopPrice: 105,
                displayBuyPrice: 100,
                fairBuyPrice: 100,
                expectedResaleValue: 133,
                reason: 'FAIR_COUNTER',
              },
            ],
          },
        }}
      />
    )

    expect(screen.getByText('Твоя цена: 110')).toBeInTheDocument()
    expect(screen.getByText('Цена магазина: 105')).toBeInTheDocument()
    expect(screen.getAllByText('Магазин предлагает справедливую встречную цену')).toHaveLength(2)
    expect(screen.getByRole('button', { name: 'ПРЕДЛОЖИТЬ НОВУЮ ЦЕНУ' })).toBeInTheDocument()
  })
})

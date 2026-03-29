import { MemoryRouter } from 'react-router-dom'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import ResetPasswordPage from './ResetPasswordPage.jsx'

const authResetRequest = vi.fn()
const authResetConfirm = vi.fn()

vi.mock('../api.js', () => ({
  api: {
    authResetRequest: (...args) => authResetRequest(...args),
    authResetConfirm: (...args) => authResetConfirm(...args),
  },
}))

function renderPage(path = '/reset-password') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <ResetPasswordPage />
    </MemoryRouter>
  )
}

describe('ResetPasswordPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('supports reset request flow', async () => {
    const user = userEvent.setup()
    authResetRequest.mockResolvedValue({ ok: true, devEmailPreviewUrl: 'http://preview.local/reset' })

    renderPage('/reset-password')
    await user.type(screen.getByLabelText('Email'), 'user@example.com')
    await user.click(screen.getByRole('button', { name: 'Отправить ссылку' }))

    await waitFor(() => {
      expect(screen.getByText(/Если email существует/i)).toBeInTheDocument()
    })
    expect(screen.getByRole('link', { name: 'Открыть письмо' })).toBeInTheDocument()
  })

  it('supports reset confirm flow by token', async () => {
    const user = userEvent.setup()
    authResetConfirm.mockResolvedValue({ ok: true })

    renderPage('/reset-password?token=abc123token')
    await user.type(screen.getByLabelText('Новый пароль'), 'Newpass123')
    await user.type(screen.getByLabelText('Подтвердите пароль'), 'Newpass123')
    await user.click(screen.getByRole('button', { name: 'Сохранить пароль' }))

    await waitFor(() => {
      expect(screen.getByText(/Пароль успешно изменён/i)).toBeInTheDocument()
    })
  })
})

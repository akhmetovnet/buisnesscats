import { MemoryRouter } from 'react-router-dom'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import LoginPage from './LoginPage.jsx'

const authLogin = vi.fn()
const authRegister = vi.fn()
const authResendEmail = vi.fn()
const authResetRequest = vi.fn()

vi.mock('../api.js', () => ({
  api: {
    authLogin: (...args) => authLogin(...args),
    authRegister: (...args) => authRegister(...args),
    authResendEmail: (...args) => authResendEmail(...args),
    authResetRequest: (...args) => authResetRequest(...args),
  },
}))

function renderLogin(initial = '/login') {
  return render(
    <MemoryRouter initialEntries={[initial]}>
      <LoginPage onAuthenticated={vi.fn()} />
    </MemoryRouter>
  )
}

function getInputByAutocomplete(name) {
  const el = document.querySelector(`input[autocomplete=\"${name}\"]`)
  if (!el) {
    throw new Error(`Input with autocomplete=${name} not found`)
  }
  return el
}

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('switches tabs and disables submit on invalid form', async () => {
    const user = userEvent.setup()
    renderLogin()

    expect(screen.getByRole('button', { name: 'Войти' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Регистрация' }))
    expect(screen.getByRole('button', { name: 'Зарегистрироваться' })).toBeDisabled()
  })

  it('shows verification sent state after successful registration', async () => {
    const user = userEvent.setup()
    authRegister.mockResolvedValue({ ok: true, requiresEmailVerification: true, devEmailPreviewUrl: 'http://preview.local' })

    renderLogin()
    await user.click(screen.getByRole('button', { name: 'Регистрация' }))

    await user.type(screen.getByPlaceholderText('user@example.com'), 'new@example.com')
    await user.type(getInputByAutocomplete('new-password'), 'Password1')
    const allNewPassword = document.querySelectorAll('input[autocomplete=\"new-password\"]')
    await user.type(allNewPassword[1], 'Password1')

    const submit = screen.getByRole('button', { name: 'Зарегистрироваться' })
    expect(submit).toBeEnabled()
    await user.click(submit)

    await waitFor(() => {
      expect(screen.getByText(/Проверьте почту/i)).toBeInTheDocument()
    })
    expect(screen.getByRole('link', { name: 'Открыть письмо' })).toBeInTheDocument()
  })

  it('handles EMAIL_NOT_VERIFIED and resend flow', async () => {
    const user = userEvent.setup()
    const err = new Error('not verified')
    err.code = 'EMAIL_NOT_VERIFIED'
    authLogin.mockRejectedValue(err)
    authResendEmail.mockResolvedValue({ ok: true, devEmailPreviewUrl: 'http://preview.local/resend' })

    renderLogin()
    await user.type(screen.getByPlaceholderText('user@example.com'), 'user@example.com')
    await user.type(getInputByAutocomplete('current-password'), 'Password1')
    await user.click(screen.getByRole('button', { name: 'Войти' }))

    await waitFor(() => {
      expect(screen.getByText(/Подтвердите email/i)).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: 'Отправить ещё раз' }))
    await waitFor(() => {
      expect(authResendEmail).toHaveBeenCalledTimes(1)
    })
  })
})

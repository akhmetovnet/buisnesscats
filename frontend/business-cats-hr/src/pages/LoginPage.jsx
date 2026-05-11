import { useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api.js'
import './AuthPage.css'

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const PASSWORD_RE = /^(?=.*[A-Za-z])(?=.*\d).{8,}$/

function normalizeEmail(value) {
  return String(value || '').trim().toLowerCase()
}

function formatRetry(seconds) {
  if (!Number.isFinite(Number(seconds))) return null
  const total = Math.max(1, Number(seconds))
  const minutes = Math.max(1, Math.ceil(total / 60))
  return `${minutes}`
}

export default function LoginPage({ onAuthenticated }) {
  const [searchParams] = useSearchParams()
  const verified = searchParams.get('verified') === '1'

  const navigate = useNavigate()
  const [lang, setLang] = useState('RU')
  const [tab, setTab] = useState('login')

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [rememberMe, setRememberMe] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)

  const [busy, setBusy] = useState(false)
  const [formError, setFormError] = useState('')
  const [globalStatus, setGlobalStatus] = useState(null)
  const [resendBusy, setResendBusy] = useState(false)

  const locale = lang === 'EN' ? {
    signIn: 'Sign in',
    signUp: 'Register',
    forgot: 'Forgot password?',
    resetTitle: 'Reset password',
    resetSubmit: 'Send reset link',
    loginSubmit: 'Login',
    registerSubmit: 'Create account',
    verifySent: 'Check your email. We sent a verification link.',
    resetSent: 'If the email exists, we sent a link.',
    invalidCreds: 'Invalid email or password',
    emailNotVerified: 'Please verify email first.',
    resend: 'Resend email',
    backToLogin: 'Back to login',
    verified: 'Email confirmed. You can sign in now.',
    accountLocked: 'Too many attempts. Try again in {minutes} min.',
    apiUnavailable: 'API is unavailable. Start backend on port 8000.',
  } : {
    signIn: 'Вход',
    signUp: 'Регистрация',
    forgot: 'Забыли пароль?',
    resetTitle: 'Восстановление пароля',
    resetSubmit: 'Отправить ссылку',
    loginSubmit: 'Войти',
    registerSubmit: 'Зарегистрироваться',
    verifySent: 'Проверьте почту. Мы отправили ссылку для подтверждения.',
    resetSent: 'Если email существует, мы отправили письмо.',
    invalidCreds: 'Неверный email или пароль',
    emailNotVerified: 'Подтвердите email. Мы отправили письмо.',
    resend: 'Отправить ещё раз',
    backToLogin: 'Назад ко входу',
    verified: 'Email подтверждён. Теперь можно войти.',
    accountLocked: 'Слишком много попыток. Попробуйте через {minutes} мин.',
    apiUnavailable: 'API недоступен. Запустите backend на порту 8000.',
  }

  const errors = useMemo(() => {
    const e = {}
    const normalizedEmail = normalizeEmail(email)

    if (!normalizedEmail || normalizedEmail.length > 254 || !EMAIL_RE.test(normalizedEmail)) {
      e.email = lang === 'EN' ? 'Invalid email' : 'Введите корректный email'
    }

    if (tab !== 'reset') {
      if (!password || !PASSWORD_RE.test(password)) {
        e.password =
          lang === 'EN'
            ? 'At least 8 chars, 1 letter and 1 digit'
            : 'Минимум 8 символов, 1 буква и 1 цифра'
      }
    }

    if (tab === 'register' && password !== confirmPassword) {
      e.confirmPassword = lang === 'EN' ? 'Passwords do not match' : 'Пароли не совпадают'
    }

    return e
  }, [email, password, confirmPassword, tab, lang])

  const isValid = Object.keys(errors).length === 0

  const handleApiError = (err) => {
    const code = err?.code
    if (code === 'EMAIL_NOT_VERIFIED') {
      setGlobalStatus({ type: 'email_not_verified', text: locale.emailNotVerified, retryAfterSeconds: err?.retryAfterSeconds || null })
      return
    }
    if (code === 'API_UNAVAILABLE') {
      setFormError(locale.apiUnavailable)
      return
    }
    if (code === 'ACCOUNT_LOCKED' || code === 'RATE_LIMITED') {
      const minutes = formatRetry(err?.retryAfterSeconds)
      const text = locale.accountLocked.replace('{minutes}', minutes || '1')
      setGlobalStatus({ type: 'locked', text, retryAfterSeconds: err?.retryAfterSeconds || null })
      return
    }
    if (code === 'INVALID_CREDENTIALS') {
      setFormError(locale.invalidCreds)
      return
    }
    if (code === 'EMAIL_TAKEN') {
      setFormError(lang === 'EN' ? 'Account already exists' : 'Аккаунт уже существует')
      return
    }
    if (code === 'VALIDATION_ERROR') {
      setFormError(err.message || (lang === 'EN' ? 'Validation error' : 'Ошибка валидации'))
      return
    }
    setFormError(err.message || 'Request failed')
  }

  const submitLogin = async () => {
    if (!isValid || busy) return
    try {
      setBusy(true)
      setFormError('')
      setGlobalStatus(null)
      await api.authLogin({
        email: normalizeEmail(email),
        password,
        rememberMe,
      })
      if (typeof onAuthenticated === 'function') {
        await onAuthenticated()
      }
      navigate('/competencies', { replace: true })
    } catch (err) {
      handleApiError(err)
    } finally {
      setBusy(false)
    }
  }

  const submitRegister = async () => {
    if (!isValid || busy) return
    try {
      setBusy(true)
      setFormError('')
      setGlobalStatus(null)
      const res = await api.authRegister({
        email: normalizeEmail(email),
        password,
        confirmPassword,
      })
      setGlobalStatus({
        type: 'verification_sent',
        text: locale.verifySent,
        previewUrl: res?.devEmailPreviewUrl || null,
      })
    } catch (err) {
      handleApiError(err)
    } finally {
      setBusy(false)
    }
  }

  const submitResetRequest = async () => {
    if (!isValid || busy) return
    try {
      setBusy(true)
      setFormError('')
      setGlobalStatus(null)
      const res = await api.authResetRequest({ email: normalizeEmail(email) })
      setGlobalStatus({
        type: 'reset_sent',
        text: locale.resetSent,
        previewUrl: res?.devEmailPreviewUrl || null,
      })
    } catch (err) {
      handleApiError(err)
    } finally {
      setBusy(false)
    }
  }

  const resendVerification = async () => {
    if (!email || resendBusy) return
    try {
      setResendBusy(true)
      setFormError('')
      const res = await api.authResendEmail({ email: normalizeEmail(email) })
      setGlobalStatus({
        type: 'verification_sent',
        text: locale.verifySent,
        previewUrl: res?.devEmailPreviewUrl || null,
      })
    } catch (err) {
      handleApiError(err)
    } finally {
      setResendBusy(false)
    }
  }

  const onSubmit = (e) => {
    e.preventDefault()
    if (tab === 'login') {
      submitLogin()
      return
    }
    if (tab === 'register') {
      submitRegister()
      return
    }
    submitResetRequest()
  }

  return (
    <div className="auth-layout">
      <section className="auth-brand">
        <div className="auth-brand__badge">Cattary Manager</div>
        <h1>Cattary Manager Platform</h1>
        <p>{lang === 'EN' ? 'Play, trade, and grow your cattery.' : 'Играйте, торгуйте и развивайте свой питомник.'}</p>
      </section>

      <section className="auth-card-wrap">
        <div className="auth-lang">
          <button className={lang === 'EN' ? 'is-active' : ''} onClick={() => setLang('EN')} type="button">EN</button>
          <button className={lang === 'RU' ? 'is-active' : ''} onClick={() => setLang('RU')} type="button">RU</button>
        </div>

        <div className="auth-card">
          <div className="auth-tabs">
            <button className={tab === 'login' ? 'is-active' : ''} onClick={() => setTab('login')} type="button">{locale.signIn}</button>
            <button className={tab === 'register' ? 'is-active' : ''} onClick={() => setTab('register')} type="button">{locale.signUp}</button>
          </div>

          {verified ? <div className="auth-alert auth-alert--success">{locale.verified}</div> : null}
          {globalStatus?.text ? <div className="auth-alert auth-alert--info">{globalStatus.text}</div> : null}
          {formError ? <div className="auth-alert auth-alert--error">{formError}</div> : null}

          <form onSubmit={onSubmit} className="auth-form">
            <label>
              Email
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="user@example.com"
                maxLength={254}
                autoComplete="email"
              />
              {errors.email ? <span className="auth-field-error">{errors.email}</span> : null}
            </label>

            {tab !== 'reset' ? (
              <label>
                {lang === 'EN' ? 'Password' : 'Пароль'}
                <div className="auth-password-row">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete={tab === 'login' ? 'current-password' : 'new-password'}
                  />
                  <button type="button" onClick={() => setShowPassword((v) => !v)}>
                    {showPassword ? '🙈' : '👁'}
                  </button>
                </div>
                {errors.password ? <span className="auth-field-error">{errors.password}</span> : null}
              </label>
            ) : null}

            {tab === 'register' ? (
              <label>
                {lang === 'EN' ? 'Confirm password' : 'Подтвердите пароль'}
                <div className="auth-password-row">
                  <input
                    type={showConfirm ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    autoComplete="new-password"
                  />
                  <button type="button" onClick={() => setShowConfirm((v) => !v)}>
                    {showConfirm ? '🙈' : '👁'}
                  </button>
                </div>
                {errors.confirmPassword ? <span className="auth-field-error">{errors.confirmPassword}</span> : null}
              </label>
            ) : null}

            {tab === 'login' ? (
              <label className="auth-checkbox">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                />
                <span>{lang === 'EN' ? 'Remember me' : 'Запомнить меня'}</span>
              </label>
            ) : null}

            <button type="submit" className="auth-submit" disabled={!isValid || busy}>
              {busy
                ? (lang === 'EN' ? 'Please wait...' : 'Подождите...')
                : tab === 'login'
                  ? locale.loginSubmit
                  : tab === 'register'
                    ? locale.registerSubmit
                    : locale.resetSubmit}
            </button>
          </form>

          <div className="auth-actions">
            {tab !== 'reset' ? (
              <button type="button" className="auth-link" onClick={() => setTab('reset')}>
                {locale.forgot}
              </button>
            ) : (
              <button type="button" className="auth-link" onClick={() => setTab('login')}>
                {locale.backToLogin}
              </button>
            )}

            {globalStatus?.type === 'verification_sent' || globalStatus?.type === 'email_not_verified' ? (
              <button type="button" className="auth-link" onClick={resendVerification} disabled={resendBusy}>
                {resendBusy ? '...' : locale.resend}
              </button>
            ) : null}

            {globalStatus?.previewUrl ? (
              <a className="auth-link" href={globalStatus.previewUrl} target="_blank" rel="noreferrer">
                {lang === 'EN' ? 'Open email' : 'Открыть письмо'}
              </a>
            ) : null}
          </div>
        </div>
      </section>
    </div>
  )
}

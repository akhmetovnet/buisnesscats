import { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api.js'
import './AuthPage.css'

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const PASSWORD_RE = /^(?=.*[A-Za-z])(?=.*\d).{8,}$/

export default function ResetPasswordPage() {
  const [params] = useSearchParams()
  const token = params.get('token')

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [busy, setBusy] = useState(false)
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState('')
  const [previewUrl, setPreviewUrl] = useState('')

  const isTokenMode = Boolean(token)

  const valid = useMemo(() => {
    if (isTokenMode) {
      return PASSWORD_RE.test(password) && password === confirm
    }
    return EMAIL_RE.test(String(email).trim())
  }, [isTokenMode, password, confirm, email])

  const submit = async (e) => {
    e.preventDefault()
    if (!valid || busy) return
    try {
      setBusy(true)
      setError('')
      if (isTokenMode) {
        await api.authResetConfirm({ token, newPassword: password, confirmPassword: confirm })
        setStatus('done')
        return
      }
      const res = await api.authResetRequest({ email: String(email).trim().toLowerCase() })
      setPreviewUrl(res?.devEmailPreviewUrl || '')
      setStatus('sent')
    } catch (err) {
      setError(err?.message || 'Request failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-simple-page">
      <div className="auth-simple-card">
        <h1>{isTokenMode ? 'Новый пароль' : 'Восстановление пароля'}</h1>

        {status === 'sent' ? (
          <>
            <p>Если email существует, мы отправили письмо.</p>
            {previewUrl ? (
              <p><a href={previewUrl} target="_blank" rel="noreferrer">Открыть письмо</a></p>
            ) : null}
            <Link to="/login">Ко входу</Link>
          </>
        ) : null}

        {status === 'done' ? (
          <>
            <p>Пароль успешно изменён.</p>
            <Link to="/login">Войти</Link>
          </>
        ) : null}

        {status === 'idle' ? (
          <form onSubmit={submit} className="auth-form">
            {isTokenMode ? (
              <>
                <label>
                  Новый пароль
                  <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
                </label>
                <label>
                  Подтвердите пароль
                  <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} />
                </label>
              </>
            ) : (
              <label>
                Email
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
              </label>
            )}

            {error ? <div className="auth-alert auth-alert--error">{error}</div> : null}
            <button type="submit" className="auth-submit" disabled={!valid || busy}>
              {busy ? '...' : isTokenMode ? 'Сохранить пароль' : 'Отправить ссылку'}
            </button>
            <Link to="/login" className="auth-link">Назад</Link>
          </form>
        ) : null}
      </div>
    </div>
  )
}

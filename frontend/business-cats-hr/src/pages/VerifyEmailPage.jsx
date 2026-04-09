import { useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import './AuthPage.css'

export default function VerifyEmailPage() {
  const [params] = useSearchParams()
  const token = params.get('token')

  useEffect(() => {
    if (!token) return
    const t = setTimeout(() => {
      window.location.assign(`/api/auth/email/verify?token=${encodeURIComponent(token)}`)
    }, 300)
    return () => clearTimeout(t)
  }, [token])

  return (
    <div className="auth-simple-page">
      <div className="auth-simple-card">
        <h1>Подтверждение email</h1>
        {token ? (
          <p>Проверяем токен и перенаправляем на страницу входа...</p>
        ) : (
          <p>Отсутствует токен подтверждения.</p>
        )}
      </div>
    </div>
  )
}

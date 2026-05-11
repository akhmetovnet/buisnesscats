import { useMemo, useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import './PlatformLayout.css'

function userInitials(me) {
  const source = String(me?.displayName || me?.email || '').trim()
  if (!source) return 'U'
  const parts = source.split(/\s+/).filter(Boolean)
  if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase()
  return source.slice(0, 2).toUpperCase()
}

export default function PlatformLayout({ me, onLogout }) {
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const initials = useMemo(() => userInitials(me), [me])

  const avatarNode = me?.avatarUrl ? (
    <img className="platform-topbar__avatar-image" src={me.avatarUrl} alt="avatar" />
  ) : (
    <span className="platform-topbar__avatar-fallback">{initials}</span>
  )

  return (
    <div className="platform-shell">
      <header className="platform-topbar">
        <button className="platform-logo" type="button" onClick={() => navigate('/competencies')}>
          <span className="platform-logo__mark">Cattary Manager</span>
        </button>

        <nav className="platform-nav">
          <NavLink to="/competencies" className={({ isActive }) => `platform-nav__link${isActive ? ' is-active' : ''}`}>
            Мои компетенции
          </NavLink>
          <NavLink to="/sessions/history" className={({ isActive }) => `platform-nav__link${isActive ? ' is-active' : ''}`}>
            История сессий
          </NavLink>
          <NavLink to="/faq" className={({ isActive }) => `platform-nav__link${isActive ? ' is-active' : ''}`}>
            FAQ
          </NavLink>
        </nav>

        <div className="platform-topbar__right">
          <button type="button" className="platform-icon-btn" aria-label="Уведомления">🔔</button>
          <button
            type="button"
            className="platform-topbar__avatar"
            aria-label="Профиль"
            onClick={() => setMenuOpen((v) => !v)}
          >
            {avatarNode}
          </button>
          {menuOpen ? (
            <div className="platform-user-menu">
              <button type="button" onClick={() => { setMenuOpen(false); navigate('/profile') }}>
                Мой профиль
              </button>
              <button type="button" onClick={() => { setMenuOpen(false); navigate('/profile?tab=password') }}>
                Сменить пароль
              </button>
              <button type="button" onClick={() => { setMenuOpen(false); onLogout?.() }}>
                Выйти
              </button>
            </div>
          ) : null}
        </div>
      </header>

      <main className="platform-content">
        <Outlet />
      </main>
    </div>
  )
}

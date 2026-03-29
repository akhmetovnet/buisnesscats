import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../api.js'
import './PlatformPages.css'

const EDUCATION_OPTIONS = ['Школа', 'Колледж', 'Университет', 'Другое']

const EMPTY_PROFILE = {
  firstName: '',
  lastName: '',
  middleName: '',
  birthDate: '',
  birthPlace: '',
  city: '',
  educationType: '',
  educationPlace: '',
  directions: [],
  university: '',
  eventCode: '',
  desiredSpecialties: '',
}

export default function ProfilePage({ me, onMeUpdated }) {
  const [searchParams] = useSearchParams()
  const showPasswordTab = searchParams.get('tab') === 'password'
  const [profile, setProfile] = useState(EMPTY_PROFILE)
  const [initialProfile, setInitialProfile] = useState(EMPTY_PROFILE)
  const [directionsInput, setDirectionsInput] = useState('')
  const [avatarLoading, setAvatarLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [pwdSaving, setPwdSaving] = useState(false)
  const [error, setError] = useState('')
  const [ok, setOk] = useState('')
  const [pwdForm, setPwdForm] = useState({ currentPassword: '', newPassword: '', confirmPassword: '' })

  useEffect(() => {
    let active = true
    const run = async () => {
      try {
        setError('')
        const loaded = await api.meProfile()
        if (!active) return
        const normalized = {
          ...EMPTY_PROFILE,
          ...loaded,
          birthDate: loaded?.birthDate || '',
          directions: Array.isArray(loaded?.directions) ? loaded.directions : [],
        }
        setProfile(normalized)
        setInitialProfile(normalized)
        setDirectionsInput((normalized.directions || []).join(', '))
      } catch (err) {
        if (active) setError(err.message || 'Не удалось загрузить профиль')
      }
    }
    run()
    return () => {
      active = false
    }
  }, [])

  const avatarPreview = useMemo(() => me?.avatarUrl || null, [me?.avatarUrl])

  const handleField = (key, value) => {
    setProfile((prev) => ({ ...prev, [key]: value }))
  }

  const handleSaveProfile = async () => {
    try {
      setSaving(true)
      setError('')
      setOk('')
      const directions = directionsInput
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean)
      const payload = { ...profile, directions }
      await api.meProfileUpdate(payload)
      setProfile((prev) => ({ ...prev, directions }))
      setInitialProfile((prev) => ({ ...prev, ...payload, directions }))
      await onMeUpdated?.()
      setOk('Профиль сохранен')
    } catch (err) {
      setError(err.message || 'Не удалось сохранить профиль')
    } finally {
      setSaving(false)
    }
  }

  const handleAvatarUpload = async (event) => {
    const file = event.target.files?.[0]
    if (!file) return
    try {
      setAvatarLoading(true)
      setError('')
      setOk('')
      await api.meAvatarUpload(file)
      await onMeUpdated?.()
      setOk('Аватар обновлен')
    } catch (err) {
      setError(err.message || 'Не удалось загрузить аватар')
    } finally {
      setAvatarLoading(false)
      event.target.value = ''
    }
  }

  const handleAvatarDelete = async () => {
    try {
      setAvatarLoading(true)
      setError('')
      setOk('')
      await api.meAvatarDelete()
      await onMeUpdated?.()
      setOk('Аватар удален')
    } catch (err) {
      setError(err.message || 'Не удалось удалить аватар')
    } finally {
      setAvatarLoading(false)
    }
  }

  const handleChangePassword = async () => {
    try {
      setPwdSaving(true)
      setError('')
      setOk('')
      await api.meChangePassword(pwdForm)
      setPwdForm({ currentPassword: '', newPassword: '', confirmPassword: '' })
      setOk('Пароль изменен. Войдите снова.')
    } catch (err) {
      setError(err.message || 'Не удалось изменить пароль')
    } finally {
      setPwdSaving(false)
    }
  }

  return (
    <div className="platform-page">
      <section className="platform-card profile-grid">
        <div className="profile-avatar-block">
          <div className="profile-avatar-preview">
            {avatarPreview ? <img src={avatarPreview} alt="avatar" /> : <span>🐾</span>}
          </div>
          <label className="platform-secondary-btn profile-upload-btn">
            {avatarLoading ? 'Загрузка...' : 'Загрузить аватар'}
            <input type="file" hidden accept=".jpg,.jpeg,.png,.webp" onChange={handleAvatarUpload} />
          </label>
          <button type="button" className="platform-link-btn" onClick={handleAvatarDelete} disabled={avatarLoading}>
            Удалить аватар
          </button>
        </div>

        <div className="profile-form">
          <h2>Мой профиль</h2>
          {error ? <div className="platform-error">{error}</div> : null}
          {ok ? <div className="platform-ok">{ok}</div> : null}

          <div className="platform-form-grid">
            <label>
              Имя
              <input value={profile.firstName} onChange={(e) => handleField('firstName', e.target.value)} />
            </label>
            <label>
              Фамилия
              <input value={profile.lastName} onChange={(e) => handleField('lastName', e.target.value)} />
            </label>
            <label>
              Отчество
              <input value={profile.middleName || ''} onChange={(e) => handleField('middleName', e.target.value)} />
            </label>
            <label>
              Дата рождения
              <input type="date" value={profile.birthDate || ''} onChange={(e) => handleField('birthDate', e.target.value)} />
            </label>
            <label>
              E-mail
              <input value={me?.email || ''} disabled />
            </label>
            <label>
              Место рождения
              <input value={profile.birthPlace || ''} onChange={(e) => handleField('birthPlace', e.target.value)} />
            </label>
            <label>
              Населенный пункт
              <input value={profile.city || ''} onChange={(e) => handleField('city', e.target.value)} />
            </label>
            <label>
              Образование
              <select value={profile.educationType || ''} onChange={(e) => handleField('educationType', e.target.value)}>
                <option value="">Выберите</option>
                {EDUCATION_OPTIONS.map((opt) => <option key={opt} value={opt}>{opt}</option>)}
              </select>
            </label>
            <label>
              Место учебы/работы/класс
              <input value={profile.educationPlace || ''} onChange={(e) => handleField('educationPlace', e.target.value)} />
            </label>
            <label>
              Направления (через запятую)
              <input value={directionsInput} onChange={(e) => setDirectionsInput(e.target.value)} />
            </label>
            <label>
              Университет (после 11 класса)
              <input value={profile.university || ''} onChange={(e) => handleField('university', e.target.value)} />
            </label>
            <label>
              Код мероприятия
              <input value={profile.eventCode || ''} onChange={(e) => handleField('eventCode', e.target.value)} />
            </label>
          </div>

          <label className="platform-block-label">
            Желаемые специальности
            <textarea
              value={profile.desiredSpecialties || ''}
              onChange={(e) => handleField('desiredSpecialties', e.target.value)}
              rows={4}
            />
          </label>

          <div className="platform-actions-row">
            <button type="button" className="platform-primary-btn" onClick={handleSaveProfile} disabled={saving}>
              {saving ? 'Сохранение...' : 'Сохранить'}
            </button>
            <button type="button" className="platform-secondary-btn" onClick={() => {
              setProfile(initialProfile)
              setDirectionsInput((initialProfile.directions || []).join(', '))
            }}>
              Отменить изменения
            </button>
          </div>
        </div>
      </section>

      <section className={`platform-card ${showPasswordTab ? 'is-highlight' : ''}`}>
        <h3>Сменить пароль</h3>
        <div className="platform-form-grid">
          <label>
            Текущий пароль
            <input
              type="password"
              value={pwdForm.currentPassword}
              onChange={(e) => setPwdForm((prev) => ({ ...prev, currentPassword: e.target.value }))}
            />
          </label>
          <label>
            Новый пароль
            <input
              type="password"
              value={pwdForm.newPassword}
              onChange={(e) => setPwdForm((prev) => ({ ...prev, newPassword: e.target.value }))}
            />
          </label>
          <label>
            Подтверждение нового пароля
            <input
              type="password"
              value={pwdForm.confirmPassword}
              onChange={(e) => setPwdForm((prev) => ({ ...prev, confirmPassword: e.target.value }))}
            />
          </label>
        </div>
        <div className="platform-actions-row">
          <button type="button" className="platform-primary-btn" onClick={handleChangePassword} disabled={pwdSaving}>
            {pwdSaving ? 'Сохранение...' : 'Сменить пароль'}
          </button>
        </div>
      </section>
    </div>
  )
}

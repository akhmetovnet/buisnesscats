import SteppedModal from './SteppedModal.jsx'

const SEASON_SCHEDULE_SUMMARY = [
  { label: 'Сезон 1', value: '10 минут' },
  { label: 'Сезоны 2-4, 6-9, 11-12', value: '5 минут' },
  { label: 'Сезоны 5 и 10', value: '15 минут' },
  { label: 'Сезон 13', value: '10 минут' },
]

export default function WelcomeStartModal({
  open,
  onClose,
  playerName = 'Леопольд',
  startCoins = 40,
}) {
  const steps = [
    {
      key: 'goal',
      icon: '🎯',
      title: 'Добро пожаловать',
      subtitle: 'Здесь ты соревнуешься с ботами за лучший итоговый баланс.',
      primaryLabel: 'Далее',
      body: (
        <div className="wizard-stack">
          <div className="wizard-hero-card">
            <div className="wizard-hero-card__icon">🐈</div>
            <div className="wizard-hero-card__text">
              Заработай больше монет, чем у ботов, и дойди до конца всех 13 сезонов.
            </div>
          </div>

          <div className="wizard-chip-grid">
            <div className="wizard-chip-card">
              <strong>13 сезонов</strong>
              <span>Одна полная игровая сессия</span>
            </div>
            <div className="wizard-chip-card">
              <strong>Рынок меняется</strong>
              <span>Цены на котят обновляются каждый сезон</span>
            </div>
            <div className="wizard-chip-card">
              <strong>Деньги ботов не бесконечны</strong>
              <span>Иногда придётся продавать по одному котёнку</span>
            </div>
          </div>
        </div>
      ),
    },
    {
      key: 'role',
      icon: '🐾',
      title: 'Твоя роль и старт',
      subtitle: `Ты играешь за питомник «${playerName}».`,
      primaryLabel: 'Далее',
      body: (
        <div className="wizard-stack">
          <div className="wizard-summary-grid wizard-summary-grid--two">
            <div className="wizard-summary-card">
              <span className="wizard-summary-card__label">Роль</span>
              <strong>Питомник «{playerName}»</strong>
            </div>
            <div className="wizard-summary-card">
              <span className="wizard-summary-card__label">Цель</span>
              <strong>Финишировать выше ботов</strong>
            </div>
          </div>

          <div className="wizard-balance-grid">
            <div className="wizard-balance-card">
              <span className="wizard-balance-card__label">Питомник</span>
              <strong>{startCoins} <span className="coin-icon coin" /></strong>
            </div>
            <div className="wizard-balance-card">
              <span className="wizard-balance-card__label">Зоомагазин</span>
              <strong>{startCoins} <span className="coin-icon coin" /></strong>
            </div>
          </div>

          <div className="wizard-note">
            Следи за остатком денег у магазинов: даже выгодный оффер не сработает, если у бота закончилась наличность.
          </div>
        </div>
      ),
    },
    {
      key: 'economy',
      icon: '💸',
      title: 'Экономика сезона',
      subtitle: 'Коммуналка и ограничения рынка влияют на твой темп.',
      primaryLabel: 'Далее',
      body: (
        <div className="wizard-stack">
          <div className="wizard-summary-grid wizard-summary-grid--two">
            <div className="wizard-summary-card">
              <span className="wizard-summary-card__label">Коммуналка питомника</span>
              <strong>3 <span className="coin-icon coin" /></strong>
            </div>
            <div className="wizard-summary-card">
              <span className="wizard-summary-card__label">Коммуналка магазина</span>
              <strong>1 <span className="coin-icon coin" /></strong>
            </div>
          </div>

          <div className="wizard-note">
            Рынок не всегда выкупает всех котят сразу. Планируй сделки и расходы по сезонам, а не только по текущему ходу.
          </div>
        </div>
      ),
    },
    {
      key: 'timing',
      icon: '⏱️',
      title: 'Темп игры',
      subtitle: 'CTA всегда рядом: дальше ты сразу переходишь в игру.',
      primaryLabel: 'Начать игру',
      body: (
        <div className="wizard-stack">
          <div className="wizard-summary-grid wizard-summary-grid--three">
            <div className="wizard-summary-card">
              <span className="wizard-summary-card__label">Всего сезонов</span>
              <strong>13</strong>
            </div>
            <div className="wizard-summary-card">
              <span className="wizard-summary-card__label">Полная сессия</span>
              <strong>1 ч 35 мин</strong>
            </div>
            <div className="wizard-summary-card">
              <span className="wizard-summary-card__label">Главный риск</span>
              <strong>Не уйти в минус</strong>
            </div>
          </div>

          <div className="wizard-list-card">
            <span className="wizard-list-card__title">Длина сезонов</span>
            <div className="wizard-timing-list">
              {SEASON_SCHEDULE_SUMMARY.map((item) => (
                <div key={item.label} className="wizard-timing-row">
                  <span>{item.label}</span>
                  <strong>{item.value}</strong>
                </div>
              ))}
            </div>
          </div>
        </div>
      ),
    },
  ]

  return (
    <SteppedModal
      open={open}
      steps={steps}
      sizeClassName="modal--size-big"
      className="welcome-modal stepped-modal--welcome"
      onComplete={onClose}
    />
  )
}

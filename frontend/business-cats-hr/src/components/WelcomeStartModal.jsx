import './Overlay.css'

const INTRO_TEXT =
  'Ты играешь против ботов, у ботов ограниченное количество монет, иногда придется продавать котят по одному, а не всех сразу. Твоя задача - заработать больше монет, чем у ботов. Будь внимательнее, каждый сезон цены на котят обновляются. Количество сезонов в игре - 13.'

const SEASON_SCHEDULE = [
  { season: 1, label: '10 минут' },
  { season: 2, label: '5 минут' },
  { season: 3, label: '5 минут' },
  { season: 4, label: '5 минут' },
  { season: 5, label: '15 минут' },
  { season: 6, label: '5 минут' },
  { season: 7, label: '5 минут' },
  { season: 8, label: '5 минут' },
  { season: 9, label: '5 минут' },
  { season: 10, label: '15 минут' },
  { season: 11, label: '5 минут' },
  { season: 12, label: '5 минут' },
  { season: 13, label: '10 минут' },
]

export default function WelcomeStartModal({ open, onClose, playerName = 'Леопольд' }) {
  if (!open) return null

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal--size-big welcome-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <div className="modal__title">Добро пожаловать</div>
        </div>

        <div className="modal__body">
          <div className="modal__start">{INTRO_TEXT}</div>

          <dl className="modal__description-list">
            <div className="parameters-modal__wrapper">
              <dt className="parameters-modal__title">Ваша роль</dt>
              <dd className="parameters-modal__definition">
                <span className="parameters-modal__role-title">
                  Вы играете за роль питомник «{playerName}»
                </span>
              </dd>
            </div>

            <div className="parameters-modal__wrapper">
              <dt className="parameters-modal__title">Баланс</dt>
              <dd className="parameters-modal__definition">
                <div className="parameters-modal-information">
                  <span className="parameters-modal-balance">
                    Питомник - 40 <span className="coin-icon coin" />
                  </span>
                </div>
                <div className="parameters-modal-information">
                  <span className="parameters-modal-balance">
                    Зоомагазин - 40 <span className="coin-icon coin" />
                  </span>
                </div>
              </dd>
            </div>

            <div className="parameters-modal__wrapper">
              <dt className="parameters-modal__title">Коммунальные услуги</dt>
              <dd className="parameters-modal__definition">
                <div className="parameters-modal-information">
                  <span className="parameters-modal-balance">
                    Зоомагазин - 1 <span className="coin-icon coin" />
                  </span>
                </div>
                <div className="parameters-modal-information">
                  <span className="parameters-modal-balance">
                    Питомник - 3 <span className="coin-icon coin" />
                  </span>
                </div>
              </dd>
            </div>

            <div className="parameters-modal__wrapper">
              <dt className="parameters-modal__title">Время сезона</dt>
              <dd className="parameters-modal__definition">
                <div className="parameters-modal-main-time-season">
                  <div className="parameters-modal-season__column">
                    <span className="parameters-modal-season"><b>Сезоны</b></span>
                    {SEASON_SCHEDULE.map((item) => (
                      <span key={`s-${item.season}`} className="parameters-modal-season notranslate">
                        {item.season}
                      </span>
                    ))}
                    <span className="parameters-modal-season"><b>Итого</b></span>
                  </div>
                  <span className="parameters-modal-line" />
                  <div className="parameters-modal-season__column">
                    <span className="parameters-modal-season"><b>Время сезонов</b></span>
                    {SEASON_SCHEDULE.map((item) => (
                      <span key={`t-${item.season}`} className="parameters-modal-season parameters-modal-season__time">
                        <span>{item.label}</span>
                      </span>
                    ))}
                    <span className="parameters-modal-season parameters-modal-season__time">
                      <span><b>1 час 35 минут</b></span>
                    </span>
                  </div>
                </div>
              </dd>
            </div>

            <div className="parameters-modal__wrapper">
              <dt className="parameters-modal__title">Информация о кредитах</dt>
              <dd className="parameters-modal__definition">
                <div className="parameters-modal-information">
                  <span>
                    Максимальная сумма кредитования - 35 <span className="coin-icon coin" />
                  </span>
                </div>
                <div className="parameters-modal-information parameters-modal-information-credit__type">
                  <span>Потребительский кредит - 5%</span>
                </div>
                <div className="parameters-modal-information parameters-modal-information-credit__type">
                  <span>Инвестиционный кредит - 10%</span>
                </div>
                <div className="parameters-modal-information parameters-modal-information-credit__type">
                  <span>Кредит со спец. условиями - 15%</span>
                </div>
              </dd>
            </div>
          </dl>

          <div className="modal__body-actions">
            <button className="text_button text_button--color-blue" onClick={onClose}>
              ПОНЯЛ
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}


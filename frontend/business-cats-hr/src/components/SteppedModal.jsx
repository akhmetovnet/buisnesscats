import { useEffect, useState } from 'react'
import './Overlay.css'

export default function SteppedModal({
  open,
  steps = [],
  sizeClassName = 'modal--size-big',
  className = '',
  onRequestClose,
  onComplete,
}) {
  const [stepIndex, setStepIndex] = useState(0)

  useEffect(() => {
    if (open) {
      setStepIndex(0)
    }
  }, [open, steps.length])

  if (!open || !steps.length) return null

  const totalSteps = steps.length
  const currentStep = steps[Math.min(stepIndex, totalSteps - 1)]
  const isLastStep = stepIndex === totalSteps - 1
  const primaryLabel = currentStep?.primaryLabel || (isLastStep ? 'Готово' : 'Далее')
  const secondaryLabel = currentStep?.secondaryLabel || 'Назад'

  const handlePrimary = () => {
    if (!isLastStep) {
      setStepIndex((prev) => Math.min(prev + 1, totalSteps - 1))
      return
    }
    onComplete?.()
  }

  const handleSecondary = () => {
    if (stepIndex === 0) return
    setStepIndex((prev) => Math.max(prev - 1, 0))
  }

  return (
    <div className="modal-overlay" onClick={onRequestClose}>
      <div
        className={`modal ${sizeClassName} stepped-modal ${className}`.trim()}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="stepped-modal__head">
          <div className="stepped-modal__progress">
            <span className="stepped-modal__progress-text">
              Шаг {stepIndex + 1} из {totalSteps}
            </span>
            <div className="stepped-modal__dots" aria-hidden="true">
              {steps.map((step, idx) => (
                <span
                  key={step.key || step.title || idx}
                  className={`stepped-modal__dot ${idx === stepIndex ? 'is-active' : ''} ${idx < stepIndex ? 'is-complete' : ''}`}
                />
              ))}
            </div>
          </div>

          <div className="modal__header stepped-modal__header">
            <div className="modal__title stepped-modal__title">
              {currentStep?.icon ? <span className="stepped-modal__icon">{currentStep.icon}</span> : null}
              <span>{currentStep?.title}</span>
            </div>
            {currentStep?.subtitle ? (
              <div className="modal__desc stepped-modal__subtitle">{currentStep.subtitle}</div>
            ) : null}
          </div>
        </div>

        <div className="modal__body stepped-modal__body">
          <div className="stepped-modal__content">{currentStep?.body}</div>
        </div>

        <div className="stepped-modal__footer">
          <div className="stepped-modal__footer-actions">
            {stepIndex > 0 ? (
              <button
                className="text_button text_button--color-transparent"
                type="button"
                onClick={handleSecondary}
              >
                {secondaryLabel}
              </button>
            ) : (
              <span className="stepped-modal__footer-spacer" />
            )}

            <button
              className="text_button text_button--color-blue"
              type="button"
              onClick={handlePrimary}
            >
              {primaryLabel}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
